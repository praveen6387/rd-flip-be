import hashlib
import hmac
import os
import time
from django.db import IntegrityError, transaction
from django.db.models import F
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import serializers
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.views import APIView
from rest_framework.throttling import AnonRateThrottle
from django.conf import settings
from rd_flip_be.models import PhotoSelection, SelectionPhoto, User, UserPlan
from rd_flip_be.credits import create_credit_transaction
from rd_flip_be.responses import api_success, api_fail
from apps.flipbooks.s3 import canonical_image_url, presign_image_urls


class CreateSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    clientName = serializers.CharField(max_length=255)
    phone = serializers.CharField(max_length=30, allow_blank=True, required=False, default="")
    folderName = serializers.CharField(max_length=255)
    originalFolderPath = serializers.CharField(max_length=2048)
    photos = serializers.ListField(child=serializers.DictField(), allow_empty=False)

    def validate(self, attrs):
        photo_serializer = PhotoSerializer(data=attrs["photos"], many=True, context={"album_id": str(attrs["id"])})
        photo_serializer.is_valid(raise_exception=True)
        attrs["photos"] = photo_serializer.validated_data
        if len({row["name"] for row in attrs["photos"]}) != len(attrs["photos"]):
            raise serializers.ValidationError("Each photo must have a unique original filename.")
        return attrs


class PhotoSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)
    imageUrl = serializers.CharField(max_length=2048)
    originalRelativePath = serializers.CharField(max_length=2048, required=False, default="")
    uploadExpires = serializers.IntegerField()
    uploadProof = serializers.CharField(max_length=64)
    objectKey = serializers.CharField(max_length=255)

    def validate_name(self, value):
        if value in (".", "..") or "/" in value or "\\" in value:
            raise serializers.ValidationError("Use an original filename without a directory.")
        return value

    def validate(self, attrs):
        relative = attrs["originalRelativePath"] or attrs["name"]
        if "\\" in relative or any(part in ("", ".", "..") for part in relative.split("/")) or relative.split("/")[-1] != attrs["name"]:
            raise serializers.ValidationError("Invalid original relative path.")
        attrs["originalRelativePath"] = relative
        album_id = str(self.context.get("album_id") or "")
        key = attrs["objectKey"]
        prefix = f"photo-selection/{album_id}/"
        filename = key[len(prefix):] if key.startswith(prefix) else ""
        if not filename or "/" in filename or filename in {".", ".."}:
            raise serializers.ValidationError("Invalid photo storage key.")
        bucket = settings.AWS_S3_BUCKET
        region = settings.AWS_S3_REGION
        expected = f"https://{bucket}.s3.{region}.amazonaws.com/{key}"
        if not bucket or canonical_image_url(attrs["imageUrl"]) != expected:
            raise serializers.ValidationError("Invalid photo URL.")
        attrs["imageUrl"] = expected
        secret = os.environ.get("PHOTO_SELECTION_UPLOAD_SECRET", "")
        message = f"{album_id}:{key}:{attrs['name']}:{attrs['originalRelativePath']}:{attrs['uploadExpires']}"
        expected_proof = hmac.new(secret.encode(), message.encode(), hashlib.sha256).hexdigest()
        if not secret or attrs["uploadExpires"] < time.time() or attrs["uploadExpires"] > time.time() + 900 or not hmac.compare_digest(expected_proof, attrs["uploadProof"]):
            raise serializers.ValidationError("Invalid upload proof. Upload the photo again.")
        return attrs


def album_data(album, public=False):
    rows = list(album.photos.all())
    signed = presign_image_urls([photo.image_url for photo in rows])
    photos = [{"id": str(photo.id), "name": photo.original_name, "imageUrl": url, "selected": photo.selected, "originalRelativePath": photo.original_relative_path or photo.original_name} for photo, url in zip(rows, signed)]
    data = {"id": str(album.id), "clientName": album.client_name, "folderName": album.folder_name,
            "status": album.status, "createdAt": album.created_at, "photoCount": len(photos),
            "selectedCount": sum(photo["selected"] for photo in photos), "photos": photos}
    if not public:
        data.update(phone=album.phone, originalFolderPath=album.original_folder_path, shareToken=str(album.share_token), accessCode=album.access_code)
    return data


def active_selection_plan(user):
    rows = list(UserPlan.objects.select_for_update().filter(user=user, status="active", expiry_date__gt=timezone.now(), plan__product__in=["photo_selection", "all"], plan__price__gt=0, credits_total__gt=F("credits_used")).select_related("plan").order_by("expiry_date", "id"))
    return next((row for row in rows if row.plan.product == "photo_selection"), rows[0] if rows else None)


class AlbumsView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        return api_success("Folders fetched", {"albums": [album_data(a) for a in PhotoSelection.objects.filter(user=request.user).prefetch_related("photos")]})

    def post(self, request):
        serializer = CreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        values = serializer.validated_data
        with transaction.atomic():
            user = User.objects.select_for_update().get(pk=request.user.pk)
            row = active_selection_plan(user)
            if row is None:
                return api_fail("Buy a Photo Selection or All plan to create a folder.", data={"code": "selection_credit_required"}, http_status=403)
            for attempt in range(20):
                try:
                    with transaction.atomic():
                        album = PhotoSelection.objects.create(id=values["id"], user=user, client_name=values["clientName"], phone=values["phone"], folder_name=values["folderName"], original_folder_path=values["originalFolderPath"], status="pending")
                    break
                except IntegrityError:
                    if attempt == 19:
                        raise
            SelectionPhoto.objects.bulk_create([
                SelectionPhoto(album=album, original_name=row_photo["name"], image_url=row_photo["imageUrl"], drive_file_id=row_photo["objectKey"], original_relative_path=row_photo["originalRelativePath"])
                for row_photo in values["photos"]
            ])
            row.credits_used += 1
            row.save(update_fields=["credits_used", "updated_at"])
            create_credit_transaction(user=user, credit_type="usage", credits=-1, user_plan=row, description=f"Photo selection folder {album.id}")
        return api_success("Folder created", {"album": album_data(album)}, http_status=201)


class AlbumView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request, album_id):
        return api_success("Folder fetched", {"album": album_data(get_object_or_404(PhotoSelection, pk=album_id, user=request.user))})

    def delete(self, request, album_id):
        get_object_or_404(PhotoSelection, pk=album_id, user=request.user).delete()
        return api_success("Folder deleted")

    def post(self, request, album_id):
        with transaction.atomic():
            album = get_object_or_404(PhotoSelection.objects.select_for_update(), pk=album_id, user=request.user)
            if album.status != "draft":
                return api_fail("Photos cannot be changed after the folder is uploaded.")
            if request.data.get("action") == "publish" and "photos" not in request.data:
                if not album.photos.exists():
                    return api_fail("Upload at least one photo first.")
                album.status = "pending"
                album.save(update_fields=["status"])
            else:
                photos = request.data.get("photos")
                if not isinstance(photos, list) or not photos:
                    return api_fail("Upload at least one photo.")
                serializer = PhotoSerializer(data=photos, many=True, context={"album_id": str(album.id)})
                serializer.is_valid(raise_exception=True)
                rows = serializer.validated_data
                if len({row["name"] for row in rows}) != len(rows):
                    return api_fail("Each photo must have a unique original filename.")
                SelectionPhoto.objects.bulk_create(
                    [
                        SelectionPhoto(
                            album=album,
                            original_name=row["name"],
                            image_url=row["imageUrl"],
                            drive_file_id=row["objectKey"],
                            original_relative_path=row["originalRelativePath"],
                        )
                        for row in rows
                    ],
                    update_conflicts=True,
                    unique_fields=["album", "original_name"],
                    update_fields=["image_url", "drive_file_id", "original_relative_path"],
                )
                if request.data.get("publish") is True:
                    album.status = "pending"
                    album.save(update_fields=["status"])
        return api_success("Folder updated", {"album": {"id": str(album.id), "status": album.status}})


class PhotoView(APIView):
    permission_classes = (IsAuthenticated,)

    def delete(self, request, album_id, photo_id):
        with transaction.atomic():
            album = get_object_or_404(PhotoSelection.objects.select_for_update(), pk=album_id, user=request.user)
            if album.status != "draft":
                return api_fail("Photos cannot be changed after the folder is uploaded.")
            get_object_or_404(SelectionPhoto, pk=photo_id, album=album).delete()
        return api_success("Photo removed")


def visitor_can_open(request, album):
    offered = request.headers.get("X-Selection-Code", "")
    expected = album.access_code or ""
    return isinstance(offered, str) and len(offered) == len(expected) and bool(expected) and hmac.compare_digest(offered, expected)


class PublicAlbumView(APIView):
    permission_classes = (AllowAny,)

    def get(self, request, token):
        album = get_object_or_404(PhotoSelection, share_token=token, status__in=["pending", "selected"])
        if not visitor_can_open(request, album):
            return api_fail("Enter the client code for this folder.", http_status=403)
        return api_success("Folder fetched", {"album": album_data(album, public=True)})

    def post(self, request, token):
        with transaction.atomic():
            album = get_object_or_404(PhotoSelection.objects.select_for_update(), share_token=token, status__in=["pending", "selected"])
            if not visitor_can_open(request, album):
                return api_fail("Enter the client code for this folder.", http_status=403)
            if album.status == "selected":
                return api_fail("This selection has already been submitted.", http_status=409)
            ids = request.data.get("selectedIds")
            if not isinstance(ids, list) or not ids or any(not isinstance(i, str) for i in ids):
                return api_fail("Select at least one photo.")
            valid = {str(i) for i in album.photos.values_list("id", flat=True)}
            if len(set(ids)) != len(ids) or not set(ids).issubset(valid):
                return api_fail("Selection contains invalid photos. Reload the folder.")
            album.photos.update(selected=False)
            album.photos.filter(pk__in=ids).update(selected=True)
            album.status = "selected"
            album.submitted_at = timezone.now()
            album.save(update_fields=["status", "submitted_at"])
        return api_success("Selection submitted", {"album": album_data(album, public=True)})


class SelectionCodeThrottle(AnonRateThrottle):
    rate = "10/min"


class SelectionCodeView(APIView):
    permission_classes = (AllowAny,)
    authentication_classes = ()
    throttle_classes = (SelectionCodeThrottle,)

    def post(self, request):
        code = request.data.get("code", "")
        if not isinstance(code, str) or len(code) != 6 or not code.isascii() or not code.isdigit():
            return api_fail("Enter a valid six-digit code.")
        album = PhotoSelection.objects.filter(access_code=code, status__in=["pending", "selected"]).first()
        if album is None:
            return api_fail("No photo selection found for this code.", http_status=404)
        return api_success("Selection found", {"shareToken": str(album.share_token)})


class SelectionStorageCheckView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        secret = os.environ.get("PHOTO_SELECTION_UPLOAD_SECRET", "")
        expires = request.data.get("expires")
        proof = request.data.get("proof", "")
        if not secret:
            return api_fail("Photo selection storage is not configured on the backend. Contact the studio administrator.", http_status=503)
        if not isinstance(expires, int) or expires < time.time() or expires > time.time() + 120 or not isinstance(proof, str):
            return api_fail("Invalid storage readiness check.", http_status=400)
        expected = hmac.new(secret.encode(), f"selection-storage:{request.user.user_id}:{expires}".encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected, proof):
            return api_fail("Photo selection upload secrets do not match between frontend and backend. Contact the studio administrator.", http_status=503)
        return api_success("Upload signing ready")
