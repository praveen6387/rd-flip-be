import hashlib
import hmac
import os
import time
from contextlib import nullcontext
from types import SimpleNamespace
from unittest.mock import Mock, patch
from django.test import SimpleTestCase, override_settings
from rest_framework.test import APIRequestFactory, force_authenticate
from rd_flip_be.models import PhotoSelection, SelectionPhoto
from .views import PhotoSerializer, PublicAlbumView, AlbumsView, AlbumView


@override_settings(AWS_S3_BUCKET="rd-flip-photos", AWS_S3_REGION="ap-south-1")
class SelectionTests(SimpleTestCase):
    def setUp(self):
        self.factory = APIRequestFactory()

    def photo_payload(self, name="original.PNG", key="photo-selection/album/photo.jpg"):
        expiry = int(time.time()) + 600
        message = f"album:{key}:{name}:{name}:{expiry}"
        return {"name": name, "objectKey": key, "imageUrl": f"https://rd-flip-photos.s3.ap-south-1.amazonaws.com/{key}", "uploadExpires": expiry, "uploadProof": hmac.new(b"test-secret", message.encode(), hashlib.sha256).hexdigest()}

    @patch.dict(os.environ, {"PHOTO_SELECTION_UPLOAD_SECRET": "test-secret"})
    def test_signed_upload_preserves_original_name(self):
        serializer = PhotoSerializer(data=self.photo_payload(), context={"album_id": "album"})
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(serializer.validated_data["name"], "original.PNG")

    @patch.dict(os.environ, {"PHOTO_SELECTION_UPLOAD_SECRET": "test-secret"})
    def test_upload_cannot_reference_arbitrary_object(self):
        data = self.photo_payload()
        data["objectKey"] = "other-bucket/private.jpg"
        data["imageUrl"] = "https://rd-flip-photos.s3.ap-south-1.amazonaws.com/other-bucket/private.jpg"
        self.assertFalse(PhotoSerializer(data=data, context={"album_id": "album"}).is_valid())

    @patch.dict(os.environ, {"PHOTO_SELECTION_UPLOAD_SECRET": "test-secret"})
    def test_upload_cannot_be_replayed_for_other_album(self):
        self.assertFalse(PhotoSerializer(data=self.photo_payload(), context={"album_id": "other"}).is_valid())

    def test_rejects_path_in_filename(self):
        for name in ("../image.jpg", "folder\\image.jpg", ".."):
            self.assertFalse(PhotoSerializer(data=self.photo_payload(name), context={"album_id": "album"}).is_valid())

    def test_owner_endpoints_require_authentication(self):
        response = AlbumsView.as_view()(self.factory.get("/"))
        self.assertIn(response.status_code, (401, 403))

    @patch("apps.photo_selection.views.get_object_or_404")
    @patch("apps.photo_selection.views.transaction.atomic", return_value=nullcontext())
    def test_public_submission_rejects_foreign_photo_ids(self, atomic, get_album):
        album = Mock(status="pending", access_code="368373", user_id=9)
        album.photos.values_list.return_value = ["valid-photo"]
        get_album.return_value = album
        response = PublicAlbumView.as_view()(self.factory.post("/", {"selectedIds": ["foreign-photo"]}, format="json", HTTP_X_SELECTION_CODE="368373"), token="share")
        self.assertEqual(response.status_code, 400)
        album.photos.update.assert_not_called()
        album.save.assert_not_called()

    @patch("apps.photo_selection.views.get_object_or_404")
    @patch("apps.photo_selection.views.transaction.atomic", return_value=nullcontext())
    def test_submission_cannot_be_changed(self, atomic, get_album):
        album = Mock(status="selected", access_code="368373", user_id=9)
        get_album.return_value = album
        response = PublicAlbumView.as_view()(self.factory.post("/", {"selectedIds": ["photo"]}, format="json", HTTP_X_SELECTION_CODE="368373"), token="share")
        self.assertEqual(response.status_code, 409)
        album.photos.update.assert_not_called()

    @patch("apps.photo_selection.views.get_object_or_404")
    @patch("apps.photo_selection.views.transaction.atomic", return_value=nullcontext())
    def test_successful_submission_sets_selected_and_timestamp(self, atomic, get_album):
        album = Mock(status="pending", access_code="368373", user_id=9)
        album.photos.values_list.return_value = ["one", "two"]
        get_album.return_value = album
        with patch("apps.photo_selection.views.album_data", return_value={}):
            response = PublicAlbumView.as_view()(self.factory.post("/", {"selectedIds": ["two"]}, format="json", HTTP_X_SELECTION_CODE="368373"), token="share")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(album.status, "selected")
        self.assertIsNotNone(album.submitted_at)
        album.photos.filter.assert_called_once_with(pk__in=["two"])
        album.photos.filter.return_value.update.assert_called_once_with(selected=True)

    @patch("apps.photo_selection.views.get_object_or_404")
    @patch("apps.photo_selection.views.transaction.atomic", return_value=nullcontext())
    def test_studio_cannot_edit_submitted_folder(self, atomic, get_album):
        get_album.return_value = Mock(status="selected")
        request = self.factory.post("/", {"action": "publish"}, format="json")
        force_authenticate(request, user=Mock(is_authenticated=True))
        response = AlbumView.as_view()(request, album_id="album")
        self.assertEqual(response.status_code, 400)

    @patch("apps.photo_selection.views.UserPlan.objects")
    @patch("apps.photo_selection.views.User.objects")
    @patch("apps.photo_selection.views.transaction.atomic", return_value=nullcontext())
    def test_no_credit_rejects_creation_without_charging(self, atomic, users, plans):
        users.select_for_update.return_value.get.return_value = Mock()
        plans.select_for_update.return_value.filter.return_value.select_related.return_value.order_by.return_value = []
        request = self.factory.post("/", {"id": "11111111-1111-1111-1111-111111111111", "clientName": "Client", "folderName": "Wedding", "originalFolderPath": "/Photos/Wedding", "photos": [{"name": "A.JPG"}]}, format="json")
        force_authenticate(request, user=Mock(is_authenticated=True))
        photo_serializer = Mock(is_valid=Mock(return_value=True), validated_data=[{"name": "A.JPG", "imageUrl": "https://example.com/a.jpg", "objectKey": "photo-selection/11111111-1111-1111-1111-111111111111/a.jpg", "originalRelativePath": "A.JPG"}])
        with patch("apps.photo_selection.views.PhotoSerializer", return_value=photo_serializer), patch("apps.photo_selection.views.PhotoSelection.objects.create") as create, patch("apps.photo_selection.views.create_credit_transaction") as ledger:
            response = AlbumsView.as_view()(request)
        self.assertEqual(response.status_code, 403)
        create.assert_not_called()
        ledger.assert_not_called()
        filters = plans.select_for_update.return_value.filter.call_args.kwargs
        self.assertEqual(filters["plan__product__in"], ["photo_selection", "all"])
        self.assertEqual(filters["plan__price__gt"], 0)
        self.assertEqual(filters["status"], "active")
        self.assertIn("expiry_date__gt", filters)
        self.assertIn("credits_total__gt", filters)

    @patch("apps.photo_selection.views.UserPlan.objects")
    @patch("apps.photo_selection.views.User.objects")
    @patch("apps.photo_selection.views.transaction.atomic", return_value=nullcontext())
    def test_creation_saves_the_folder_and_photos_then_spends_one_credit(self, atomic, users, plans):
        user = Mock()
        users.select_for_update.return_value.get.return_value = user
        shared = Mock(credits_used=3); shared.plan.product = "all"
        specific = Mock(credits_used=1); specific.plan.product = "photo_selection"
        plans.select_for_update.return_value.filter.return_value.select_related.return_value.order_by.return_value = [shared, specific]
        request = self.factory.post("/", {"id": "11111111-1111-1111-1111-111111111111", "clientName": "Client", "folderName": "Wedding", "originalFolderPath": "/Photos/Wedding", "photos": [{"name": "A.JPG"}]}, format="json")
        force_authenticate(request, user=Mock(is_authenticated=True))
        photo_serializer = Mock(is_valid=Mock(return_value=True), validated_data=[{"name": "A.JPG", "imageUrl": "https://example.com/a.jpg", "objectKey": "photo-selection/11111111-1111-1111-1111-111111111111/a.jpg", "originalRelativePath": "A.JPG"}])
        with patch("apps.photo_selection.views.PhotoSerializer", return_value=photo_serializer), patch("apps.photo_selection.views.PhotoSelection.objects.create") as create, patch.object(SelectionPhoto.objects, "bulk_create") as saved_photos, patch("apps.photo_selection.views.create_credit_transaction") as ledger, patch("apps.photo_selection.views.album_data", return_value={}):
            create.return_value = PhotoSelection(client_name="Client", folder_name="Wedding", original_folder_path="/Photos/Wedding", status="pending")
            response = AlbumsView.as_view()(request)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(len(saved_photos.call_args.args[0]), 1)
        self.assertEqual(specific.credits_used, 2)
        self.assertEqual(shared.credits_used, 3)
        self.assertEqual(ledger.call_args.kwargs["credits"], -1)
        self.assertEqual(ledger.call_args.kwargs["user_plan"], specific)
        self.assertEqual(create.call_args.kwargs["status"], "pending")
        self.assertEqual(str(create.call_args.kwargs["id"]), "11111111-1111-1111-1111-111111111111")

    @patch("apps.photo_selection.views.UserPlan.objects")
    @patch("apps.photo_selection.views.User.objects")
    @patch("apps.photo_selection.views.transaction.atomic", return_value=nullcontext())
    def test_draft_folder_is_saved_without_charging(self, atomic, users, plans):
        users.select_for_update.return_value.get.return_value = Mock()
        specific = Mock(credits_used=1)
        specific.plan.product = "photo_selection"
        plans.select_for_update.return_value.filter.return_value.select_related.return_value.order_by.return_value = [specific]
        request = self.factory.post("/", {"id": "11111111-1111-1111-1111-111111111111", "clientName": "Client", "folderName": "Wedding", "wizardStep": 2}, format="json")
        force_authenticate(request, user=Mock(is_authenticated=True))
        with patch("apps.photo_selection.views.PhotoSelection.objects.create") as create, patch.object(SelectionPhoto.objects, "bulk_create") as saved_photos, patch("apps.photo_selection.views.create_credit_transaction") as ledger, patch("apps.photo_selection.views.album_data", return_value={}):
            create.return_value = PhotoSelection(client_name="Client", folder_name="Wedding", status="draft")
            response = AlbumsView.as_view()(request)
        self.assertEqual(response.status_code, 201)
        saved_photos.assert_not_called()
        ledger.assert_not_called()
        self.assertEqual(specific.credits_used, 1)
        self.assertEqual(create.call_args.kwargs["status"], "draft")
        self.assertEqual(create.call_args.kwargs["wizard_step"], 2)

    @patch("apps.photo_selection.views.album_data", return_value={})
    @patch("apps.photo_selection.views.get_object_or_404")
    @patch("apps.photo_selection.views.transaction.atomic", return_value=nullcontext())
    def test_reopen_keeps_the_receipt_and_allows_a_new_select(self, atomic, get_album, album_data):
        from apps.photo_selection.selection import toggle_photo
        album = Mock(status="selected", confirmed_by_name="Asha", confirmation_notes="keep", rules_configured=True, selection_mode="UNLIMITED")
        get_album.return_value = album
        request = self.factory.post("/", {"action": "reopen"}, format="json")
        force_authenticate(request, user=Mock(is_authenticated=True))
        response = AlbumView.as_view()(request, album_id="album")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(album.status, "pending")
        self.assertEqual(album.confirmed_by_name, "Asha")
        self.assertEqual(album.save.call_args.kwargs["update_fields"], ["status"])
        album.photos.filter.return_value.count.return_value = 0
        album.photos.count.return_value = 4
        photo = Mock(selected=False, id="photo")
        saved = toggle_photo(album, photo, True)
        self.assertEqual(saved.status_code, 200)
        self.assertTrue(photo.selected)
        photo.save.assert_called()


class SelectionRuleTests(SimpleTestCase):
    def album(self, **kwargs):
        values = {"selection_mode": "FIXED", "required_photos": 100, "included_photos": 100, "allow_extra_photos": True, "strict_limit": False, "max_selection_limit": 100, "photos_per_sheet": 4, "included_sheets": 25, "enable_extra_photo_pricing": False, "extra_photo_price": 0, "enable_extra_sheet_pricing": False, "extra_sheet_price": 0}
        values.update(kwargs)
        return SimpleNamespace(**values)

    def test_fixed_confirmation_uses_the_smaller_of_target_and_uploaded_photos(self):
        from apps.photo_selection.selection import confirm_error
        album = self.album()
        self.assertIn("2 more", confirm_error(album, 1, 3))
        self.assertIsNone(confirm_error(album, 3, 3))
        self.assertIn("exactly 100", confirm_error(album, 101, 120))

    def test_strict_fixed_mode_stops_selection_at_the_target(self):
        from apps.photo_selection.selection import select_limit_error
        album = self.album(required_photos=2, strict_limit=True)
        self.assertIn("Fixed selection target reached (2 photos)", select_limit_error(album, 2))
        self.assertIsNone(select_limit_error(album, 1))

    def test_minimum_mode_rejects_a_short_selection_and_blocks_disabled_extras(self):
        from apps.photo_selection.selection import confirm_error, select_limit_error
        album = self.album(selection_mode="MIN_EXTRA", included_photos=2, allow_extra_photos=False)
        self.assertIn("1 more", confirm_error(album, 1, 5))
        self.assertIsNone(confirm_error(album, 2, 5))
        self.assertIn("Extra photos are disabled", select_limit_error(album, 2))

    def test_unlimited_mode_only_requires_one_photo(self):
        from apps.photo_selection.selection import confirm_error, select_limit_error
        album = self.album(selection_mode="UNLIMITED", strict_limit=False)
        self.assertEqual(confirm_error(album, 0, 5), "Please select at least one photo before confirming.")
        self.assertIsNone(confirm_error(album, 4, 5))
        self.assertIsNone(select_limit_error(album, 4))

    def test_locked_gallery_rejects_a_change(self):
        album = Mock(status="selected")
        album.photos.filter.return_value.count.return_value = 1
        photo = Mock(selected=False, id="photo")
        from apps.photo_selection.selection import toggle_photo, update_photo_details
        response = toggle_photo(album, photo, True)
        self.assertEqual(response.status_code, 403)
        photo.save.assert_not_called()
        rated = update_photo_details(album, photo, {"rating": 4})
        self.assertEqual(rated.status_code, 403)
        photo.save.assert_not_called()

    def test_unconfigured_rules_behave_as_unlimited(self):
        from apps.photo_selection.selection import confirm_error, mode_of, select_limit_error
        album = self.album(rules_configured=False, strict_limit=True, required_photos=2)
        self.assertEqual(mode_of(album), "UNLIMITED")
        self.assertIsNone(select_limit_error(album, 5, 8))
        self.assertIsNone(confirm_error(album, 4, 8))
        self.assertEqual(confirm_error(album, 0, 8), "Please select at least one photo before confirming.")

    def test_fixed_confirm_requires_the_capped_exact_count(self):
        from apps.photo_selection.selection import confirm_error
        album = self.album(rules_configured=True, required_photos=100)
        self.assertIsNone(confirm_error(album, 3, 3))
        self.assertIn("1 more", confirm_error(album, 2, 3))
        self.assertIn("exactly 3", confirm_error(album, 4, 3))

    def test_fixed_strict_limit_rejects_the_next_select_without_saving(self):
        from apps.photo_selection.selection import select_limit_error, toggle_photo
        album = self.album(rules_configured=True, required_photos=100, strict_limit=True)
        self.assertIn("Fixed selection target reached (3 photos)", select_limit_error(album, 3, 3))
        self.assertIsNone(select_limit_error(album, 2, 3))
        stored = Mock(status="pending", rules_configured=True, selection_mode="FIXED", required_photos=2, strict_limit=True, allow_extra_photos=True, included_photos=2, max_selection_limit=100)
        stored.photos.filter.return_value.count.return_value = 2
        stored.photos.count.return_value = 4
        photo = Mock(selected=False, id="photo")
        response = toggle_photo(stored, photo, True)
        self.assertEqual(response.status_code, 400)
        photo.save.assert_not_called()

    def test_minimum_extra_charges_only_when_pricing_is_enabled(self):
        from decimal import Decimal
        from apps.photo_selection.selection import confirmation_snapshot, confirm_error, select_limit_error
        album = self.album(selection_mode="MIN_EXTRA", rules_configured=True, included_photos=2, photos_per_sheet=4, enable_extra_photo_pricing=True, extra_photo_price=Decimal("50"), enable_extra_sheet_pricing=True, extra_sheet_price=Decimal("300"), allow_extra_photos=False)
        self.assertIn("1 more", confirm_error(album, 1, 10))
        self.assertIsNone(confirm_error(album, 2, 10))
        self.assertIn("Selection limit is 2", select_limit_error(album, 2, 10))
        snapshot = confirmation_snapshot(album, 5, 10, "Asha", "  retouch  ")
        self.assertEqual(snapshot["confirmed_by_name"], "Asha")
        self.assertEqual(snapshot["extra_photos_count"], 3)
        self.assertEqual(snapshot["estimated_sheets"], 2)
        self.assertEqual(snapshot["extra_sheets_count"], 1)
        self.assertEqual(snapshot["extra_photo_charge"], Decimal("150"))
        self.assertEqual(snapshot["extra_sheet_charge"], Decimal("300"))
        self.assertEqual(snapshot["total_extra_charge"], Decimal("450"))
        quiet = self.album(selection_mode="MIN_EXTRA", rules_configured=True, included_photos=2, photos_per_sheet=4, extra_photo_price=Decimal("50"), extra_sheet_price=Decimal("300"))
        self.assertEqual(confirmation_snapshot(quiet, 5, 10)["total_extra_charge"], 0)

    def test_one_front_and_one_back_cover(self):
        from apps.photo_selection.selection import update_photo_details
        album = Mock(status="pending", rules_configured=True, selection_mode="UNLIMITED")
        album.photos.count.return_value = 6
        album.photos.filter.return_value.count.return_value = 0
        front = Mock(selected=False, pk="front", id="front")
        back = Mock(selected=False, pk="back", id="back")
        self.assertEqual(update_photo_details(album, front, {"coverType": "FRONT"}).status_code, 200)
        self.assertEqual(update_photo_details(album, back, {"coverType": "BACK"}).status_code, 200)
        self.assertEqual(front.cover_type, "FRONT")
        self.assertEqual(back.cover_type, "BACK")
        self.assertTrue(front.selected and back.selected)
        album.photos.filter.return_value.exclude.assert_any_call(pk="front")
        album.photos.filter.return_value.exclude.assert_any_call(pk="back")
        album.photos.filter.return_value.exclude.return_value.update.assert_called_with(cover_type="")


class SelectionCodeTests(SimpleTestCase):
    def setUp(self):
        from django.core.cache import cache
        cache.clear()
        self.factory = APIRequestFactory()

    def test_generated_codes_have_six_ascii_digits(self):
        from rd_flip_be.models import generate_selection_code
        for _ in range(100):
            code = generate_selection_code()
            self.assertEqual(len(code), 6)
            self.assertTrue(code.isascii() and code.isdigit())

    @patch("apps.photo_selection.views.PhotoSelection.objects")
    def test_code_opens_published_album(self, albums):
        from .views import SelectionCodeView
        albums.filter.return_value.first.return_value = Mock(share_token="share-id")
        response = SelectionCodeView.as_view()(self.factory.post("/", {"code": "123456"}, format="json"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["data"]["shareToken"], "share-id")
        albums.filter.assert_called_once_with(access_code="123456", status__in=["pending", "selected"])

    @patch("apps.photo_selection.views.PhotoSelection.objects")
    def test_invalid_code_does_not_query_database(self, albums):
        from .views import SelectionCodeView
        for code in ("12345", "1234567", "abcdef", 123456, "１２３４５６"):
            response = SelectionCodeView.as_view()(self.factory.post("/", {"code": code}, format="json"))
            self.assertEqual(response.status_code, 400)
        albums.filter.assert_not_called()

    @patch("apps.photo_selection.views.PhotoSelection.objects")
    def test_unknown_code_returns_not_found(self, albums):
        from .views import SelectionCodeView
        albums.filter.return_value.first.return_value = None
        response = SelectionCodeView.as_view()(self.factory.post("/", {"code": "123456"}, format="json"))
        self.assertEqual(response.status_code, 404)

    @patch("apps.photo_selection.views.PhotoSelection.objects")
    def test_repeated_code_guesses_are_throttled(self, albums):
        from .views import SelectionCodeView
        albums.filter.return_value.first.return_value = None
        for _ in range(10):
            SelectionCodeView.as_view()(self.factory.post("/", {"code": "123456"}, format="json"))
        response = SelectionCodeView.as_view()(self.factory.post("/", {"code": "123456"}, format="json"))
        self.assertEqual(response.status_code, 429)


class StorageReadinessTests(SimpleTestCase):
    @patch.dict(os.environ, {"PHOTO_SELECTION_UPLOAD_SECRET": "shared-secret"})
    def test_matching_secret_is_ready(self):
        from .views import SelectionStorageCheckView
        expires = int(time.time()) + 60
        proof = hmac.new(b"shared-secret", f"selection-storage:studio-uuid:{expires}".encode(), hashlib.sha256).hexdigest()
        request = APIRequestFactory().post("/", {"expires": expires, "proof": proof}, format="json")
        force_authenticate(request, user=Mock(user_id="studio-uuid", is_authenticated=True))
        self.assertEqual(SelectionStorageCheckView.as_view()(request).status_code, 200)

    @patch.dict(os.environ, {"PHOTO_SELECTION_UPLOAD_SECRET": "shared-secret"})
    def test_mismatched_secret_blocks_storage(self):
        from .views import SelectionStorageCheckView
        request = APIRequestFactory().post("/", {"expires": int(time.time()) + 60, "proof": "wrong"}, format="json")
        force_authenticate(request, user=Mock(user_id="studio-uuid", is_authenticated=True))
        self.assertEqual(SelectionStorageCheckView.as_view()(request).status_code, 503)

    @patch.dict(os.environ, {"PHOTO_SELECTION_UPLOAD_SECRET": ""})
    def test_missing_secret_blocks_storage(self):
        from .views import SelectionStorageCheckView
        request = APIRequestFactory().post("/", {}, format="json")
        force_authenticate(request, user=Mock(is_authenticated=True))
        self.assertEqual(SelectionStorageCheckView.as_view()(request).status_code, 503)
