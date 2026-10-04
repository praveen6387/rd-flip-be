import uuid
from datetime import timedelta

from django.db import IntegrityError, transaction
from django.db.models import F
from django.db.models.functions import Greatest
from django.utils import timezone

from rd_flip_be.models import Flipbook, FlipbookEngagement

VISITOR_COOKIE = "rd_flip_visitor"
VISITOR_COOKIE_MAX_AGE = int(timedelta(days=730).total_seconds())


def visitor_id_from_request(request) -> uuid.UUID:
    raw = (request.COOKIES.get(VISITOR_COOKIE) or "").strip()
    if raw:
        try:
            return uuid.UUID(raw)
        except ValueError:
            pass
    return uuid.uuid4()


def attach_visitor_cookie(response, visitor_id: uuid.UUID, *, secure: bool):
    response.set_cookie(
        VISITOR_COOKIE,
        str(visitor_id),
        max_age=VISITOR_COOKIE_MAX_AGE,
        httponly=True,
        samesite="Lax",
        secure=secure,
        path="/",
    )
    return response


def active_flipbook(flip_id: str):
    flip_id = (flip_id or "").strip()
    if not flip_id:
        return None
    return Flipbook.objects.filter(flip_id=flip_id, is_active=True).first()


def flipbook_is_expired(flipbook) -> bool:
    return bool(flipbook.active_until and timezone.now() > flipbook.active_until)


def engagement_payload(flipbook, engagement) -> dict:
    return {
        "view_count": flipbook.view_count,
        "like_count": flipbook.like_count,
        "liked": engagement.liked,
    }


def _lock_engagement(flipbook, visitor_id: uuid.UUID) -> FlipbookEngagement:
    try:
        engagement, _created = FlipbookEngagement.objects.get_or_create(
            flipbook=flipbook,
            visitor_id=visitor_id,
        )
    except IntegrityError:
        engagement = FlipbookEngagement.objects.get(
            flipbook=flipbook,
            visitor_id=visitor_id,
        )
    return FlipbookEngagement.objects.select_for_update().get(pk=engagement.pk)


def record_view(flipbook, visitor_id: uuid.UUID) -> dict:
    with transaction.atomic():
        engagement = _lock_engagement(flipbook, visitor_id)
        if not engagement.viewed:
            engagement.viewed = True
            engagement.save(update_fields=["viewed", "updated_at"])
            Flipbook.objects.filter(pk=flipbook.pk).update(view_count=F("view_count") + 1)
            flipbook.refresh_from_db(fields=["view_count", "like_count"])
        return engagement_payload(flipbook, engagement)


def toggle_like(flipbook, visitor_id: uuid.UUID) -> dict:
    with transaction.atomic():
        engagement = _lock_engagement(flipbook, visitor_id)
        if engagement.liked:
            engagement.liked = False
            Flipbook.objects.filter(pk=flipbook.pk).update(
                like_count=Greatest(F("like_count") - 1, 0)
            )
        else:
            engagement.liked = True
            Flipbook.objects.filter(pk=flipbook.pk).update(like_count=F("like_count") + 1)
        engagement.save(update_fields=["liked", "updated_at"])
        flipbook.refresh_from_db(fields=["view_count", "like_count"])
        return engagement_payload(flipbook, engagement)
