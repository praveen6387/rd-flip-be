import hashlib
import hmac
import logging
import os
import time
from datetime import date, datetime
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
from apps.flipbooks.s3 import canonical_image_url, delete_s3_prefix, presign_image_url, presign_image_urls
from apps.photo_selection.selection import bool_attr, confirm_error, confirmation_snapshot, apply_snapshot, confirm_selection, decimal_attr, int_attr, mode_of, public_rules, toggle_photo, update_photo_details

logger = logging.getLogger(__name__)


class CreateSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    clientName = serializers.CharField(max_length=255)
    phone = serializers.CharField(max_length=30, allow_blank=True, required=False, default="")
    whatsapp = serializers.CharField(max_length=30, allow_blank=True, required=False, default="")
    clientEmail = serializers.CharField(max_length=255, allow_blank=True, required=False, default="")
    eventDate = serializers.DateField(required=False, allow_null=True)
    selectionDeadline = serializers.DateField(required=False, allow_null=True)
    photographerNotes = serializers.CharField(required=False, allow_blank=True, default="", max_length=4000)
    folderName = serializers.CharField(max_length=255)
    originalFolderPath = serializers.CharField(max_length=2048, required=False, allow_blank=True, default="")
    wizardStep = serializers.IntegerField(min_value=1, max_value=5, required=False, default=1)
    welcomeMessage = serializers.CharField(required=False, allow_blank=True, default="", max_length=4000)
    selectionMode = serializers.ChoiceField(choices=["UNLIMITED", "FIXED", "MIN_EXTRA"], required=False, default="UNLIMITED")
    requiredPhotos = serializers.IntegerField(min_value=1, max_value=100000, required=False, default=100)
    includedPhotos = serializers.IntegerField(min_value=1, max_value=100000, required=False, default=100)
    allowExtraPhotos = serializers.BooleanField(required=False, default=True)
    strictLimit = serializers.BooleanField(required=False, default=False)
    maxSelectionLimit = serializers.IntegerField(min_value=1, max_value=100000, required=False, default=100)
    photosPerSheet = serializers.IntegerField(min_value=1, max_value=100, required=False, default=4)
    includedSheets = serializers.IntegerField(min_value=1, max_value=100000, required=False, default=25)
    enableExtraPhotoPricing = serializers.BooleanField(required=False, default=False)
    extraPhotoPrice = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=0, required=False, default=0)
    enableExtraSheetPricing = serializers.BooleanField(required=False, default=False)
    extraSheetPrice = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=0, required=False, default=0)
    photos = serializers.ListField(child=serializers.DictField(), required=False, default=list)

    def validate(self, attrs):
        if not attrs.get("photos"):
            attrs["photos"] = []
            return attrs
        photo_serializer = PhotoSerializer(data=attrs["photos"], many=True, context={"album_id": str(attrs["id"])})
        photo_serializer.is_valid(raise_exception=True)
        attrs["photos"] = photo_serializer.validated_data
        if len({row["originalRelativePath"] for row in attrs["photos"]}) != len(attrs["photos"]):
            raise serializers.ValidationError("Each photo must have a unique folder path.")
        return attrs


class PhotoSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)
    imageUrl = serializers.CharField(max_length=2048)
    originalRelativePath = serializers.CharField(max_length=2048, required=False, default="")
    category = serializers.CharField(max_length=100, required=False, allow_blank=True, default="")
    uploadExpires = serializers.IntegerField()
    uploadProof = serializers.CharField(max_length=64)
    objectKey = serializers.CharField(max_length=255)

    def validate_category(self, value):
        return " ".join(str(value or "").replace("\\", " ").replace("/", " ").split())[:100]

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


def photo_folders(photo):
    relative = (photo.original_relative_path or photo.original_name or "").replace("\\", "/")
    parts = [part for part in relative.split("/") if part]
    stored = getattr(photo, "category", "")
    stored = stored.strip() if isinstance(stored, str) else ""
    if stored:
        return stored, "/".join(parts[:-1])
    if len(parts) <= 1:
        return "", ""
    return parts[0], "/".join(parts[1:-1])


def text_attr(album, name):
    value = getattr(album, name, "")
    return value if isinstance(value, str) else ""


def date_text(value):
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    return ""


def public_watermark(user):
    enabled = getattr(user, "watermark_enabled", True)
    if not isinstance(enabled, bool):
        return {"enabled": False, "text": "", "position": "bottom-right", "opacity": 0.45, "logoUrl": "", "includeLogo": False}
    text = getattr(user, "watermark_text", "")
    text = text.strip() if isinstance(text, str) else ""
    studio = getattr(user, "studio_name", "")
    if not text and isinstance(studio, str) and studio.strip():
        text = f"© {studio.strip()}"
    position = getattr(user, "watermark_position", "bottom-right")
    if position not in {"bottom-right", "bottom-left", "top-right", "top-left", "center", "diagonal"}:
        position = "bottom-right"
    try:
        opacity = float(getattr(user, "watermark_opacity", 0.45))
    except (TypeError, ValueError):
        opacity = 0.45
    include = getattr(user, "watermark_include_logo", False)
    logo = getattr(user, "watermark_logo_url", "")
    logo = logo.strip() if isinstance(include, bool) and include and isinstance(logo, str) else ""
    signed = presign_image_url(logo) if enabled and logo else ""
    shown_text = text if enabled else ""
    return {"enabled": bool(shown_text or signed), "text": shown_text, "position": position, "opacity": opacity, "logoUrl": signed or "", "includeLogo": bool(signed)}


def public_studio(user):
    name = getattr(user, "studio_name", "")
    phone = getattr(user, "whatsapp_number", "")
    if not isinstance(phone, str) or not phone.strip():
        phone = getattr(user, "phone", "")
    return {
        "studioName": name.strip() if isinstance(name, str) else "",
        "phone": phone.strip() if isinstance(phone, str) else "",
    }


def album_data(album, public=False):
    rows = list(album.photos.all())
    signed = presign_image_urls([photo.image_url for photo in rows])
    photos = []
    for photo, url in zip(rows, signed):
        category, subfolder = photo_folders(photo)
        rotation = getattr(photo, "rotation", 0)
        if rotation not in (0, 90, 180, 270):
            rotation = 0
        photos.append({"id": str(photo.id), "name": photo.original_name, "imageUrl": url, "selected": photo.selected, "originalRelativePath": photo.original_relative_path or photo.original_name, "rating": photo.rating or 0, "coverType": photo.cover_type or None, "notes": photo.notes or "", "category": category, "subfolder": "" if public else subfolder, "rotation": rotation})
    selected_count = sum(photo["selected"] for photo in photos)
    data = {"id": str(album.id), "clientName": album.client_name, "folderName": album.folder_name,
            "status": album.status, "createdAt": album.created_at, "photoCount": len(photos),
            "selectedCount": selected_count, "photos": photos, "rules": public_rules(album, len(photos), selected_count), "wizardStep": getattr(album, "wizard_step", 1) or 1, "welcomeMessage": getattr(album, "welcome_message", "") or ""}
    if public:
        owner = getattr(album, "user", None)
        submitted = getattr(album, "submitted_at", None)
        data["watermark"] = public_watermark(owner)
        data["studio"] = public_studio(owner)
        data["submittedAt"] = submitted.isoformat() if isinstance(submitted, datetime) else ""
    if not public:
        data.update(phone=album.phone, whatsapp=text_attr(album, "whatsapp"), clientEmail=text_attr(album, "client_email"), eventDate=date_text(getattr(album, "event_date", None)), selectionDeadline=date_text(getattr(album, "selection_deadline", None)), photographerNotes=text_attr(album, "photographer_notes"), originalFolderPath=album.original_folder_path, shareToken=str(album.share_token), accessCode=album.access_code, selectionMode=album.selection_mode if isinstance(getattr(album, "selection_mode", None), str) else "UNLIMITED", requiredPhotos=int_attr(album, "required_photos", 100), includedPhotos=int_attr(album, "included_photos", 100), allowExtraPhotos=bool_attr(album, "allow_extra_photos", True), strictLimit=bool_attr(album, "strict_limit", False), maxSelectionLimit=int_attr(album, "max_selection_limit", 100), photosPerSheet=int_attr(album, "photos_per_sheet", 4), includedSheets=int_attr(album, "included_sheets", 25), enableExtraPhotoPricing=bool_attr(album, "enable_extra_photo_pricing", False), extraPhotoPrice=float(decimal_attr(album, "extra_photo_price")), enableExtraSheetPricing=bool_attr(album, "enable_extra_sheet_pricing", False), extraSheetPrice=float(decimal_attr(album, "extra_sheet_price")))
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
                        album = PhotoSelection.objects.create(id=values["id"], user=user, client_name=values["clientName"], phone=values["phone"], whatsapp=values["whatsapp"], client_email=values["clientEmail"], event_date=values.get("eventDate"), selection_deadline=values.get("selectionDeadline"), photographer_notes=values["photographerNotes"], folder_name=values["folderName"], original_folder_path=values["originalFolderPath"], status="draft" if not values["photos"] else "pending", wizard_step=values["wizardStep"], welcome_message=values["welcomeMessage"], selection_mode=values["selectionMode"], required_photos=values["requiredPhotos"], included_photos=values["includedPhotos"], allow_extra_photos=values["allowExtraPhotos"], strict_limit=values["strictLimit"], max_selection_limit=values["maxSelectionLimit"], photos_per_sheet=values["photosPerSheet"], included_sheets=values["includedSheets"], enable_extra_photo_pricing=values["enableExtraPhotoPricing"], extra_photo_price=values["extraPhotoPrice"], enable_extra_sheet_pricing=values["enableExtraSheetPricing"], extra_sheet_price=values["extraSheetPrice"], rules_configured=values["selectionMode"] != "UNLIMITED")
                    break
                except IntegrityError:
                    if attempt == 19:
                        raise
            if not values["photos"]:
                return api_success("Gallery draft saved", {"album": album_data(album)}, http_status=201)
            SelectionPhoto.objects.bulk_create([
                SelectionPhoto(album=album, original_name=row_photo["name"], image_url=row_photo["imageUrl"], drive_file_id=row_photo["objectKey"], original_relative_path=row_photo["originalRelativePath"], category=row_photo.get("category") or "")
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
        album = get_object_or_404(PhotoSelection, pk=album_id, user=request.user)
        try:
            delete_s3_prefix(f"photo-selection/{album.id}/")
        except Exception:
            logger.exception("Could not delete stored photos for %s", album.id)
            return api_fail("Could not delete the stored photos. The folder was kept.")
        album.delete()
        return api_success("Folder deleted")

    def post(self, request, album_id):
        with transaction.atomic():
            album = get_object_or_404(PhotoSelection.objects.select_for_update(), pk=album_id, user=request.user)
            if request.data.get("action") == "reopen":
                if album.status != "selected":
                    return api_fail("Only a confirmed selection can be reopened.")
                album.status = "pending"
                album.save(update_fields=["status"])
                return api_success("Selection reopened", {"album": album_data(album)})
            if request.data.get("action") == "save":
                if album.status != "draft":
                    return api_fail("This gallery is already published.")
                for key, field in (("clientName", "client_name"), ("phone", "phone"), ("whatsapp", "whatsapp"), ("clientEmail", "client_email"), ("photographerNotes", "photographer_notes"), ("folderName", "folder_name"), ("originalFolderPath", "original_folder_path"), ("welcomeMessage", "welcome_message"), ("selectionMode", "selection_mode")):
                    if key in request.data:
                        setattr(album, field, request.data.get(key) or "")
                for key, field in (("wizardStep", "wizard_step"), ("requiredPhotos", "required_photos"), ("includedPhotos", "included_photos"), ("maxSelectionLimit", "max_selection_limit"), ("photosPerSheet", "photos_per_sheet"), ("includedSheets", "included_sheets")):
                    if key in request.data:
                        setattr(album, field, int(request.data.get(key) or 1))
                for key, field in (("allowExtraPhotos", "allow_extra_photos"), ("strictLimit", "strict_limit"), ("enableExtraPhotoPricing", "enable_extra_photo_pricing"), ("enableExtraSheetPricing", "enable_extra_sheet_pricing")):
                    if key in request.data:
                        setattr(album, field, bool(request.data.get(key)))
                for key, field in (("extraPhotoPrice", "extra_photo_price"), ("extraSheetPrice", "extra_sheet_price")):
                    if key in request.data:
                        setattr(album, field, request.data.get(key) or 0)
                for key, field in (("eventDate", "event_date"), ("selectionDeadline", "selection_deadline")):
                    if key in request.data:
                        setattr(album, field, request.data.get(key) or None)
                if "accessCode" in request.data:
                    code = str(request.data.get("accessCode") or "").strip()
                    if not code.isdigit() or len(code) != 6:
                        return api_fail("The access code must be 6 digits.")
                    if PhotoSelection.objects.exclude(pk=album.pk).filter(access_code=code).exists():
                        return api_fail("That access code is already used. Choose another.")
                    album.access_code = code
                if int(album.wizard_step or 1) >= 3:
                    album.rules_configured = True
                album.save()
                return api_success("Draft saved", {"album": album_data(album)})
            if album.status != "draft":
                return api_fail("Photos cannot be changed after the folder is uploaded.")
            if request.data.get("action") == "publish" and "photos" not in request.data:
                if not album.photos.exists():
                    return api_fail("Upload at least one photo first.")
                owner = User.objects.select_for_update().get(pk=request.user.pk)
                plan = active_selection_plan(owner)
                if plan is None:
                    return api_fail("Buy a Photo Selection or All plan to publish a gallery.", data={"code": "selection_credit_required"}, http_status=403)
                plan.credits_used += 1
                plan.save(update_fields=["credits_used", "updated_at"])
                create_credit_transaction(user=owner, credit_type="usage", credits=-1, user_plan=plan, description=f"Photo selection folder {album.id}")
                album.status = "pending"
                album.wizard_step = 5
                album.save(update_fields=["status", "wizard_step"])
                return api_success("Gallery published", {"album": album_data(album)})
            else:
                photos = request.data.get("photos")
                if not isinstance(photos, list) or not photos:
                    return api_fail("Upload at least one photo.")
                serializer = PhotoSerializer(data=photos, many=True, context={"album_id": str(album.id)})
                serializer.is_valid(raise_exception=True)
                rows = serializer.validated_data
                if len({row["originalRelativePath"] for row in rows}) != len(rows):
                    return api_fail("Each photo must have a unique folder path.")
                SelectionPhoto.objects.bulk_create(
                    [
                        SelectionPhoto(
                            album=album,
                            original_name=row["name"],
                            image_url=row["imageUrl"],
                            drive_file_id=row["objectKey"],
                            original_relative_path=row["originalRelativePath"],
                            category=row.get("category") or "",
                        )
                        for row in rows
                    ],
                    update_conflicts=True,
                    unique_fields=["album", "original_relative_path"],
                    update_fields=["image_url", "drive_file_id", "original_relative_path", "category"],
                )
                if request.data.get("publish") is True:
                    album.status = "pending"
                    album.save(update_fields=["status"])
        return api_success("Folder updated", {"album": {"id": str(album.id), "status": album.status}})


class PhotoView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request, album_id, photo_id):
        if request.data.get("action") != "rotate":
            return api_fail("Unsupported photo action.")
        with transaction.atomic():
            album = get_object_or_404(PhotoSelection.objects.select_for_update(), pk=album_id, user=request.user)
            if album.status == "selected":
                return api_fail("This gallery is locked.")
            photo = get_object_or_404(SelectionPhoto, pk=photo_id, album=album)
            current = photo.rotation if photo.rotation in (0, 90, 180, 270) else 0
            photo.rotation = (current + 90) % 360
            photo.save(update_fields=["rotation"])
        return api_success("Photo rotated", {"photo": {"id": str(photo.id), "rotation": photo.rotation}})

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
            total = len(ids) if mode_of(album) == "UNLIMITED" else album.photos.count()
            message = confirm_error(album, len(ids), total)
            if message:
                return api_fail(message)
            album.photos.update(selected=False)
            album.photos.filter(pk__in=ids).update(selected=True)
            apply_snapshot(album, confirmation_snapshot(album, len(ids), total, request.data.get("confirmedByName") or "", request.data.get("notes") or ""))
            album.status = "selected"
            album.submitted_at = timezone.now()
            album.save(update_fields=["status", "submitted_at", "confirmed_by_name", "confirmation_notes", "confirmed_selected_count", "extra_photos_count", "extra_sheets_count", "estimated_sheets", "extra_photo_charge", "extra_sheet_charge", "total_extra_charge"])
        return api_success("Selection submitted", {"album": album_data(album, public=True)})


class PublicPhotoView(APIView):
    permission_classes = (AllowAny,)

    def post(self, request, token, photo_id):
        with transaction.atomic():
            album = get_object_or_404(PhotoSelection.objects.select_for_update(), share_token=token, status__in=["pending", "selected"])
            if not visitor_can_open(request, album):
                return api_fail("Enter the client code for this folder.", http_status=403)
            photo = get_object_or_404(SelectionPhoto, pk=photo_id, album=album)
            if any(key in request.data for key in ("rating", "coverType", "notes")):
                return update_photo_details(album, photo, request.data)
            return toggle_photo(album, photo, request.data.get("selected"))


class PublicConfirmView(APIView):
    permission_classes = (AllowAny,)

    def post(self, request, token):
        with transaction.atomic():
            album = get_object_or_404(PhotoSelection.objects.select_for_update(), share_token=token, status__in=["pending", "selected"])
            if not visitor_can_open(request, album):
                return api_fail("Enter the client code for this folder.", http_status=403)
            failed = confirm_selection(album, request.data.get("confirmedByName"), request.data.get("notes"))
            if failed:
                return failed
            album.status = "selected"
            album.submitted_at = timezone.now()
            album.save(update_fields=["status", "submitted_at", "confirmed_by_name", "confirmation_notes", "confirmed_selected_count", "extra_photos_count", "extra_sheets_count", "estimated_sheets", "extra_photo_charge", "extra_sheet_charge", "total_extra_charge"])
        return api_success("Final photo selection confirmed successfully! Your selections are now locked.", {"album": album_data(album, public=True)})


class PublicSyncView(APIView):
    permission_classes = (AllowAny,)

    def get(self, request, token):
        album = get_object_or_404(PhotoSelection, share_token=token, status__in=["pending", "selected"])
        if not visitor_can_open(request, album):
            return api_fail("Enter the client code for this folder.", http_status=403)
        rows = album.photos.filter(selected=True)
        return api_success("Selection synced", {"selectedPhotoIds": [str(photo.id) for photo in rows], "selectionsMeta": {str(photo.id): {"rating": photo.rating or 0, "coverType": photo.cover_type or None, "notes": photo.notes or ""} for photo in rows}, "selectedCount": rows.count(), "status": album.status, "isLocked": album.status == "selected", "confirmation": {"confirmedByName": album.confirmed_by_name, "confirmedAt": album.submitted_at, "selectedCount": album.confirmed_selected_count} if album.status == "selected" else None})


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
