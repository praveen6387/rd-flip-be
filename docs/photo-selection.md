# Photo selection

Each folder spends one unexpired paid Photo Selection credit, falling back to an All credit. Flipbook and welcome credits cannot create selection folders. Credit usage and folder creation share a database transaction and lock the user and plan rows. Deleting a folder does not refund its credit. Failed uploads leave a draft, and the studio can add/retry photos there without another credit.

## Setup

Run `poetry run python manage.py migrate`. Both frontend and backend environments need the same strong `PHOTO_SELECTION_UPLOAD_SECRET`. Local development environments have been configured. Configure the same value in both deployed services; do not expose it as a NEXT_PUBLIC variable. It authenticates uploaded S3 object metadata so a studio cannot register arbitrary files from the bucket.

Photo files are stored in the S3 bucket named by `AWS_S3_BUCKET` (`rd-flip-photos`). The frontend also needs `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, and `AWS_REGION`. The backend needs the same bucket, `AWS_S3_REGION`, and the same access keys so it can return a short-lived view URL. Objects stay private. Google Drive is not used for photo selection.

## Workflow

1. Buy a Photo Selection or All plan through existing Plans and checkout.
2. Create a folder with client details, its title, and upload the original photo folder. The browser automatically captures the source folder name and each photo’s relative location; no local path input is shown. Upload previews. Compression preserves the original filename and extension in metadata; the preview MIME type can differ from the original.
3. Finish any draft upload. Copy the client link from the studio folder.
4. Client opens `/photo-selection/<share-token>` without an account, selects photos and submits. Status becomes `selected`. Client submission is final; studio uploads and removals are then blocked. The share URL is a bearer capability; anyone given that link can view and submit the pending selection. Clients never receive the studio's local path or phone.
5. Studio refreshes the folder to retrieve the selected photos.
6. Choose the original directory again. Where supported, Extract selected originals asks for the parent directory containing the source folder, then copies the exact original files into a new sibling named `<Original folder> Selected`. Further exports use numbered sibling names to preserve earlier copies. All selected originals are checked before creating the output folder. Alternatively Download originals ZIP reads the chosen directory and downloads a ZIP containing only selected original files under `Selected/Images`.

Browsers cannot reopen an arbitrary absolute local path or verify the full path. New uploads save the browser-provided folder name and relative photo paths, rather than claiming to know an absolute computer path. Legacy manually entered paths remain supported. The studio must re-grant directory access; the app verifies its final directory name and every selected filename before creating output. Missing originals show an error asking the studio to move the original folder back to the saved path. Photos can be inside nested subfolders; their relative paths are preserved. Selection expects unique, exact filenames. Keep originals unchanged after uploading previews. Duplicate filenames in a new upload are rejected.

Database rows store the original filename, the private S3 URL, the object key, the local folder path, the selected flag, and the submission time. Upload metadata is validated with a short-lived HMAC bound to the studio folder, filename, and object key. Removing a folder does not delete the S3 object.

## API

Authenticated `/api/photo-selection/`: GET list, POST create.
Authenticated `/api/photo-selection/<uuid>/`: GET folder, POST upload metadata/publish, DELETE folder.
Authenticated `/api/photo-selection/<uuid>/photos/<uuid>/`: DELETE photo.
Public `/api/photo-selection/public/<uuid>/`: GET client folder, POST `{ "selectedIds": ["photo-uuid"] }`.
Frontend `/selection-upload/<uuid>` uploads the photo to S3, then registers the object URL. Album responses return a short-lived signed URL for viewing.

## Checks

`poetry run python manage.py test apps.photo_selection` runs validation and mocked API workflow tests without a database. These do not test PostgreSQL concurrency or a real S3 upload.
`node --test src/lib/photo-selection/originals.test.mjs` in the frontend checks path parsing, exact original matching and ZIP output. `unzip -t /tmp/rd-selection-test.zip` checks ZIP integrity.

The photo selection listing page fetches authenticated albums on the Next.js server with no-store caching and passes them to the client renderer. It does not make an initial browser-side listing request.

## Six-digit client codes

Every new folder receives a random unique six-digit `access_code`; migration 0032 backfills existing folders. Studio listing and detail views show the code. Copy code & entry link copies the code together with `/photo-selection`. Clients enter their code there; POST `/api/photo-selection/access/` resolves pending or submitted folders to the existing UUID selection page. Drafts cannot be opened. Invalid formats and unknown codes are rejected; anonymous lookups are limited to 10 attempts per minute per client IP using the Django cache. Multi-process production deployments should use a shared Django cache for consistent throttling. Existing UUID links remain valid. Database uniqueness and transactional retries protect concurrent folder creation from code collisions.

## Production upload configuration errors

`Photo selection upload signing is not configured` means the deployed frontend is missing `PHOTO_SELECTION_UPLOAD_SECRET`. Set the same strong secret in the frontend hosting environment and Django hosting environment, then redeploy/restart both services. The variable is server-only; do not prefix it with NEXT_PUBLIC. A local .env file does not configure deployed services.

Creation checks `/selection-storage` before the folder-creation API: authenticated identity, matching signing secrets, and S3 configuration. A later upload failure keeps the draft so the studio can retry without another credit.

### Google invalid_grant

Photo selection no longer uses Google Drive. Song storage still does.

The existing connect callback updates process.env and a local .env file. On serverless hosting that is not durable environment configuration and does not update other instances. A successful connection page alone therefore does not establish that the hosting environment has been updated. Never send OAuth tokens in chat or commit them. Reuse an existing draft after credentials are repaired.
