from functools import lru_cache
from urllib.parse import unquote, urlparse

import boto3
from django.conf import settings


def canonical_image_url(url: str) -> str:
    """Store the object URL only — drop query strings (expired signatures)."""
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


@lru_cache(maxsize=1)
def _s3_client():
    kwargs = {"region_name": settings.AWS_S3_REGION}
    if settings.AWS_ACCESS_KEY_ID and settings.AWS_SECRET_ACCESS_KEY:
        kwargs["aws_access_key_id"] = settings.AWS_ACCESS_KEY_ID
        kwargs["aws_secret_access_key"] = settings.AWS_SECRET_ACCESS_KEY
    return boto3.client("s3", **kwargs)


def presign_image_url(url: str | None) -> str | None:
    """
    Turn a private S3 object URL into a time-limited GET URL the browser can load.
    Non-S3 URLs are returned unchanged.
    """
    if not url:
        return url

    s3_parts = parse_s3_url(url)
    if s3_parts is None:
        return url

    bucket, key = s3_parts
    try:
        return _s3_client().generate_presigned_url(
            "get_object",
            Params={"Bucket": bucket, "Key": key},
            ExpiresIn=settings.AWS_S3_PRESIGN_EXPIRES,
        )
    except Exception:
        return canonical_image_url(url)
