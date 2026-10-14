# Photo selection

Each folder spends one unexpired paid Photo Selection credit, falling back to an All credit. Flipbook and welcome credits cannot create selection folders. Credit usage and folder creation share a database transaction and lock the user and plan rows. Deleting a folder does not refund its credit. Failed uploads leave a draft, and the studio can add/retry photos there without another credit.

## Setup

Run `poetry run python manage.py migrate`. Both frontend and backend environments need the same strong `PHOTO_SELECTION_UPLOAD_SECRET`. Local development environments have been configured. Configure the same value in both deployed services; do not expose it as a NEXT_PUBLIC variable. It authenticates uploaded Drive file metadata so a studio cannot register arbitrary files from the storage account.

Frontend Drive storage uses the existing owner OAuth connection (`GOOGLE_OAUTH_CLIENT_ID`, `GOOGLE_OAUTH_CLIENT_SECRET`, `GOOGLE_OAUTH_REFRESH_TOKEN`). Set `GOOGLE_DRIVE_PHOTO_SELECTION_FOLDER_ID` to a dedicated storage folder; otherwise the existing `GOOGLE_DRIVE_FOLDER_ID` is used. Drive uploads stay private; the media route checks studio ownership or the client share token before streaming. No public Drive permissions are added.

## Workflow

1. Buy a Photo Selection or All plan through existing Plans and checkout.
2. Create a folder with client details, its title, and upload the original photo folder. The browser automatically captures the source folder name and each photo’s relative location; no local path input is shown. Upload previews. Compression preserves the original filename and extension in metadata; the preview MIME type can differ from the original.
3. Finish any draft upload. Copy the client link from the studio folder.
4. Client opens `/photo-selection/<share-token>` without an account, selects photos and submits. Status becomes `selected`. Client submission is final; studio uploads and removals are then blocked. The share URL is a bearer capability; anyone given that link can view and submit the pending selection. Clients never receive the studio's local path or phone.
5. Studio refreshes the folder to retrieve the selected photos.
6. Choose the original directory again. Where supported, Extract selected originals asks for the parent directory containing the source folder, then copies the exact original files into a new sibling named `<Original folder> Selected`. Further exports use numbered sibling names to preserve earlier copies. All selected originals are checked before creating the output folder. Alternatively Download originals ZIP reads the chosen directory and downloads a ZIP containing only selected original files under `Selected/Images`.

Browsers cannot reopen an arbitrary absolute local path or verify the full path. New uploads save the browser-provided folder name and relative photo paths, rather than claiming to know an absolute computer path. Legacy manually entered paths remain supported. The studio must re-grant directory access; the app verifies its final directory name and every selected filename before creating output. Missing originals show an error asking the studio to move the original folder back to the saved path. Photos can be inside nested subfolders; their relative paths are preserved. Selection expects unique, exact filenames. Keep originals unchanged after uploading previews. Duplicate filenames in a new upload are rejected.

Database rows store original filename, private preview URL, Drive file id, local folder path, selected flag and submission time. Preview metadata is validated with a short-lived HMAC bound to the studio folder, filename and Drive id. Old Drive previews are not automatically deleted when database folders/photos are removed or replaced; storage cleanup can be added separately.

## API

Authenticated `/api/photo-selection/`: GET list, POST create.
Authenticated `/api/photo-selection/<uuid>/`: GET folder, POST upload metadata/publish, DELETE folder.
Authenticated `/api/photo-selection/<uuid>/photos/<uuid>/`: DELETE photo.
Public `/api/photo-selection/public/<uuid>/`: GET client folder, POST `{ "selectedIds": ["photo-uuid"] }`.
Frontend `/selection-upload/<uuid>`: authenticated multipart upload; `/selection-media/<drive-id>`: authorized preview stream.

## Checks

`poetry run python manage.py test apps.photo_selection` runs validation and mocked API workflow tests without a database. These do not test PostgreSQL concurrency or real Google Drive uploads.
`node --test src/lib/photo-selection/originals.test.mjs` in the frontend checks path parsing, exact original matching and ZIP output. `unzip -t /tmp/rd-selection-test.zip` checks ZIP integrity.

The photo selection listing page fetches authenticated albums on the Next.js server with no-store caching and passes them to the client renderer. It does not make an initial browser-side listing request.

## Six-digit client codes

Every new folder receives a random unique six-digit `access_code`; migration 0032 backfills existing folders. Studio listing and detail views show the code. Copy code & entry link copies the code together with `/photo-selection`. Clients enter their code there; POST `/api/photo-selection/access/` resolves pending or submitted folders to the existing UUID selection page. Drafts cannot be opened. Invalid formats and unknown codes are rejected; anonymous lookups are limited to 10 attempts per minute per client IP using the Django cache. Multi-process production deployments should use a shared Django cache for consistent throttling. Existing UUID links remain valid. Database uniqueness and transactional retries protect concurrent folder creation from code collisions.
