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
from rd_flip_be.models import PhotoSelection, SelectionPhoto, User, UserPlan
from rd_flip_be.credits import create_credit_transaction
from rd_flip_be.responses import api_success, api_fail


class CreateSerializer(serializers.Serializer):
    clientName = serializers.CharField(max_length=255)
    phone = serializers.CharField(max_length=30, allow_blank=True, required=False, default="")
    folderName = serializers.CharField(max_length=255)
    originalFolderPath = serializers.CharField(max_length=2048)


class PhotoSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)
    imageUrl = serializers.CharField(max_length=2048)
    originalRelativePath = serializers.CharField(max_length=2048, required=False, default="")
    uploadExpires = serializers.IntegerField()
    uploadProof = serializers.CharField(max_length=64)
    driveFileId = serializers.RegexField(r"^[a-zA-Z0-9_-]+$", max_length=255)

    def validate_name(self, value):
        if value in (".", "..") or "/" in value or "\\" in value:
            raise serializers.ValidationError("Use an original filename without a directory.")
        return value

    def validate(self, attrs):
        relative = attrs["originalRelativePath"] or attrs["name"]
        if "\\" in relative or any(part in ("", ".", "..") for part in relative.split("/")) or relative.split("/")[-1] != attrs["name"]:
            raise serializers.ValidationError("Invalid original relative path.")
        attrs["originalRelativePath"] = relative
        expected = f"/selection-media/{attrs['driveFileId']}"
        if attrs['imageUrl'] != expected:
            raise serializers.ValidationError("Invalid photo URL.")
        secret = os.environ.get("PHOTO_SELECTION_UPLOAD_SECRET", "")
        album_id = self.context.get("album_id")
        message = f"{album_id}:{attrs['driveFileId']}:{attrs['name']}:{attrs['originalRelativePath']}:{attrs['uploadExpires']}"
        expected_proof = hmac.new(secret.encode(), message.encode(), hashlib.sha256).hexdigest()
        if not secret or attrs["uploadExpires"] < time.time() or attrs["uploadExpires"] > time.time() + 900 or not hmac.compare_digest(expected_proof, attrs["uploadProof"]):
            raise serializers.ValidationError("Invalid upload proof. Upload the photo again.")
        return attrs


def album_data(album, public=False):
    photos = [{"id": str(p.id), "name": p.original_name, "imageUrl": p.image_url, "selected": p.selected, "originalRelativePath": p.original_relative_path or p.original_name} for p in album.photos.all()]
    data = {"id": str(album.id), "clientName": album.client_name, "folderName": album.folder_name,
            "status": album.status, "createdAt": album.created_at, "photoCount": len(photos),
            "selectedCount": sum(p["selected"] for p in photos), "photos": photos}
    if not public:
        data.update(phone=album.phone, originalFolderPath=album.original_folder_path, shareToken=str(album.share_token), accessCode=album.access_code)
    return data


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
            rows = list(UserPlan.objects.select_for_update().filter(user=user, status="active", expiry_date__gt=timezone.now(), plan__product__in=["photo_selection", "all"], plan__price__gt=0, credits_total__gt=F("credits_used")).select_related("plan").order_by("expiry_date", "id"))
            row = next((r for r in rows if r.plan.product == "photo_selection"), rows[0] if rows else None)
            if row is None:
                return api_fail("Buy a Photo Selection or All plan to create a folder.", data={"code": "selection_credit_required"}, http_status=403)
            for attempt in range(20):
                try:
                    with transaction.atomic():
                        album = PhotoSelection.objects.create(user=user, client_name=values["clientName"], phone=values["phone"], folder_name=values["folderName"], original_folder_path=values["originalFolderPath"])
                    break
                except IntegrityError:
                    if attempt == 19:
                        raise

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
            if album.status == "selected":
                return api_fail("Submitted folders cannot be changed.")
            if request.data.get("action") == "publish":
                if not album.photos.exists():
                    return api_fail("Upload at least one photo first.")
                album.status = "pending"
                album.save(update_fields=["status"])
            else:
                serializer = PhotoSerializer(data=request.data, context={"album_id": str(album.id)})
                serializer.is_valid(raise_exception=True)
                v = serializer.validated_data
                album.photos.update_or_create(original_name=v["name"], defaults={"image_url": v["imageUrl"], "drive_file_id": v["driveFileId"], "original_relative_path": v["originalRelativePath"]})
        return api_success("Folder updated", {"album": album_data(album)})


class PhotoView(APIView):
    permission_classes = (IsAuthenticated,)

    def delete(self, request, album_id, photo_id):
        with transaction.atomic():
            album = get_object_or_404(PhotoSelection.objects.select_for_update(), pk=album_id, user=request.user)
            if album.status == "selected":
                return api_fail("Submitted folders cannot be changed.")
            get_object_or_404(SelectionPhoto, pk=photo_id, album=album).delete()
        return api_success("Photo removed")


class PublicAlbumView(APIView):
    permission_classes = (AllowAny,)
    authentication_classes = ()

    def get(self, request, token):
        album = get_object_or_404(PhotoSelection, share_token=token, status__in=["pending", "selected"])
        return api_success("Folder fetched", {"album": album_data(album, public=True)})

    def post(self, request, token):
        with transaction.atomic():
            album = get_object_or_404(PhotoSelection.objects.select_for_update(), share_token=token, status__in=["pending", "selected"])
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
