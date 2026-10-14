import hashlib
import hmac
import os
import time
from contextlib import nullcontext
from unittest.mock import Mock, patch
from django.test import SimpleTestCase
from rest_framework.test import APIRequestFactory, force_authenticate
from .views import PhotoSerializer, PublicAlbumView, AlbumsView, AlbumView


class SelectionTests(SimpleTestCase):
    def setUp(self):
        self.factory = APIRequestFactory()

    def photo_payload(self, name="original.PNG"):
        expiry = int(time.time()) + 600
        message = f"album:file_123:{name}:{name}:{expiry}"
        return {"name": name, "driveFileId": "file_123", "imageUrl": "/selection-media/file_123", "uploadExpires": expiry, "uploadProof": hmac.new(b"test-secret", message.encode(), hashlib.sha256).hexdigest()}

    @patch.dict(os.environ, {"PHOTO_SELECTION_UPLOAD_SECRET": "test-secret"})
    def test_signed_upload_preserves_original_name(self):
        serializer = PhotoSerializer(data=self.photo_payload(), context={"album_id": "album"})
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(serializer.validated_data["name"], "original.PNG")

    @patch.dict(os.environ, {"PHOTO_SELECTION_UPLOAD_SECRET": "test-secret"})
    def test_upload_cannot_reference_arbitrary_drive_file(self):
        data = self.photo_payload()
        data["driveFileId"] = "private_file"
        data["imageUrl"] = "/selection-media/private_file"
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
        album = Mock(status="pending")
        album.photos.values_list.return_value = ["valid-photo"]
        get_album.return_value = album
        response = PublicAlbumView.as_view()(self.factory.post("/", {"selectedIds": ["foreign-photo"]}, format="json"), token="share")
        self.assertEqual(response.status_code, 400)
        album.photos.update.assert_not_called()
        album.save.assert_not_called()

    @patch("apps.photo_selection.views.get_object_or_404")
    @patch("apps.photo_selection.views.transaction.atomic", return_value=nullcontext())
    def test_submission_cannot_be_changed(self, atomic, get_album):
        album = Mock(status="selected")
        get_album.return_value = album
        response = PublicAlbumView.as_view()(self.factory.post("/", {"selectedIds": ["photo"]}, format="json"), token="share")
        self.assertEqual(response.status_code, 409)
        album.photos.update.assert_not_called()

    @patch("apps.photo_selection.views.get_object_or_404")
    @patch("apps.photo_selection.views.transaction.atomic", return_value=nullcontext())
    def test_successful_submission_sets_selected_and_timestamp(self, atomic, get_album):
        album = Mock(status="pending")
        album.photos.values_list.return_value = ["one", "two"]
        get_album.return_value = album
        with patch("apps.photo_selection.views.album_data", return_value={}):
            response = PublicAlbumView.as_view()(self.factory.post("/", {"selectedIds": ["two"]}, format="json"), token="share")
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
        request = self.factory.post("/", {"clientName": "Client", "folderName": "Wedding", "originalFolderPath": "/Photos/Wedding"}, format="json")
        force_authenticate(request, user=Mock(is_authenticated=True))
        with patch("apps.photo_selection.views.PhotoSelection.objects.create") as create, patch("apps.photo_selection.views.create_credit_transaction") as ledger:
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
    def test_creation_spends_one_specific_credit_before_all(self, atomic, users, plans):
        user = Mock()
        users.select_for_update.return_value.get.return_value = user
        shared = Mock(credits_used=3); shared.plan.product = "all"
        specific = Mock(credits_used=1); specific.plan.product = "photo_selection"
        plans.select_for_update.return_value.filter.return_value.select_related.return_value.order_by.return_value = [shared, specific]
        request = self.factory.post("/", {"clientName": "Client", "folderName": "Wedding", "originalFolderPath": "/Photos/Wedding"}, format="json")
        force_authenticate(request, user=Mock(is_authenticated=True))
        with patch("apps.photo_selection.views.PhotoSelection.objects.create") as create, patch("apps.photo_selection.views.create_credit_transaction") as ledger, patch("apps.photo_selection.views.album_data", return_value={}):
            response = AlbumsView.as_view()(request)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(specific.credits_used, 2)
        self.assertEqual(shared.credits_used, 3)
        self.assertEqual(ledger.call_args.kwargs["credits"], -1)
        self.assertEqual(ledger.call_args.kwargs["user_plan"], specific)


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
