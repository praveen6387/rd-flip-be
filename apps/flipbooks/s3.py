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


def presign_image_urls(urls: list[str | None]) -> list[str | None]:
    """
    Sign S3 image URLs (local HMAC, no S3 HTTP).
    For one URL, pass [url] and use the 0th result.
    Non-S3 URLs are returned unchanged.
    """
    client = None
    signed: list[str | None] = []
    for url in urls:
        if not url:
            signed.append(url)
            continue
        s3_parts = parse_s3_url(url)
        if s3_parts is None:
            signed.append(url)
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
