from functools import lru_cache
from urllib.parse import unquote, urlparse

import boto3
from botocore.exceptions import ClientError
from django.conf import settings


def canonical_image_url(url: str) -> str:
    """Store/return the object URL only — drop query strings (old signatures)."""
    raw = (url or "").strip()
    if not raw:
        return raw
    return raw.split("?", 1)[0]


def parse_s3_url(url: str) -> tuple[str, str] | None:
    parsed = urlparse(canonical_image_url(url))
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        return None

    host = parsed.netloc.lower()
    key = unquote(parsed.path.lstrip("/"))
    if not key:
        return None

    if ".s3." in host and host.endswith(".amazonaws.com"):
        bucket = host.split(".s3.", 1)[0]
        if bucket:
            return bucket, key

    if host.startswith("s3.") and host.endswith(".amazonaws.com"):
        bucket, _, remainder = key.partition("/")
        if bucket and remainder:
            return bucket, remainder

    return None


def _s3_client_kwargs():
    kwargs = {"region_name": settings.AWS_S3_REGION}
    if settings.AWS_ACCESS_KEY_ID and settings.AWS_SECRET_ACCESS_KEY:
        kwargs["aws_access_key_id"] = settings.AWS_ACCESS_KEY_ID
        kwargs["aws_secret_access_key"] = settings.AWS_SECRET_ACCESS_KEY
    return kwargs


@lru_cache(maxsize=1)
def _s3_client():
    return boto3.client("s3", **_s3_client_kwargs())


def _fresh_s3_client():
    return boto3.client("s3", **_s3_client_kwargs())


def presign_image_urls(urls: list[str | None]) -> list[str | None]:
    """
    Sign S3 image URLs (local HMAC, no S3 HTTP).
    Non-S3 URLs are returned unchanged (canonical).
    """
    client = None
    signed: list[str | None] = []
    for url in urls:
        if not url:
            signed.append(url)
            continue
        s3_parts = parse_s3_url(url)
        if s3_parts is None:
            signed.append(canonical_image_url(url))
            continue
        bucket, key = s3_parts
        try:
            if client is None:
                client = _s3_client()
            signed.append(
                client.generate_presigned_url(
                    "get_object",
                    Params={"Bucket": bucket, "Key": key},
                    ExpiresIn=settings.AWS_S3_PRESIGN_EXPIRES,
                )
            )
        except Exception:
            signed.append(canonical_image_url(url))
    return signed


def _delete_keys(client, bucket, keys):
    for start in range(0, len(keys), 1000):
        batch = keys[start:start + 1000]
        failed = batch
        try:
            response = client.delete_objects(Bucket=bucket, Delete={"Objects": [{"Key": key} for key in batch], "Quiet": True})
            failed = [item.get("Key") for item in response.get("Errors") or [] if item.get("Key")]
        except ClientError:
            failed = batch
        for key in failed:
            client.delete_object(Bucket=bucket, Key=key)


def delete_s3_prefix(prefix):
    if not isinstance(prefix, str) or not prefix.startswith("photo-selection/") or prefix.count("/") != 2 or ".." in prefix:
        raise RuntimeError("Invalid photo folder.")
    bucket = settings.AWS_S3_BUCKET
    if not bucket:
        raise RuntimeError("S3 is not configured.")
    client = _fresh_s3_client()
    token = None
    while True:
        page = client.list_objects_v2(Bucket=bucket, Prefix=prefix, **({"ContinuationToken": token} if token else {}))
        keys = [item["Key"] for item in page.get("Contents") or [] if str(item.get("Key") or "").startswith(prefix)]
        _delete_keys(client, bucket, keys)
        if not page.get("IsTruncated"):
            return
        token = page.get("NextContinuationToken")


def presign_image_url(url: str | None) -> str | None:
    if not url:
        return url
    return presign_image_urls([url])[0]
