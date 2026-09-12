from urllib.parse import unquote, urlparse


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


def public_image_urls(urls: list[str | None]) -> list[str | None]:
    """Normalize to public object URLs (no signing)."""
    return [canonical_image_url(url) if url else url for url in urls]
