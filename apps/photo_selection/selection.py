import math
from decimal import Decimal

from rd_flip_be.responses import api_fail, api_success

MODES = {"UNLIMITED", "FIXED", "MIN_EXTRA"}
LOCKED = "This gallery has been confirmed and locked. Selections cannot be changed unless reopened by your photographer."


def mode_of(album):
    # A studio album stays unlimited until selection rules are explicitly saved.
    if getattr(album, "rules_configured", True) is False:
        return "UNLIMITED"
    mode = getattr(album, "selection_mode", None)
    return mode if mode in MODES else "UNLIMITED"


def int_attr(album, name, default):
    try:
        return int(getattr(album, name))
    except (TypeError, ValueError, AttributeError):
        return default


def bool_attr(album, name, default):
    value = getattr(album, name, default)
    return value if isinstance(value, bool) else default


def decimal_attr(album, name):
    try:
        return Decimal(getattr(album, name))
    except Exception:
        return Decimal("0")


def capped(limit, total):
    if total > 0 and limit:
        return min(limit, total)
    return limit


def select_limit_error(album, current_selected, total=None):
    mode = mode_of(album)
    required = capped(int_attr(album, "required_photos", 100), total or 0)
    included = capped(int_attr(album, "included_photos", 100), total or 0)
    if mode == "FIXED" and bool_attr(album, "strict_limit", False) and required and current_selected >= required:
        return f"Fixed selection target reached ({required} photos). Please unselect another photo before selecting this one."
    if mode == "MIN_EXTRA" and bool_attr(album, "allow_extra_photos", True) is False and included and current_selected >= included:
        return f"Extra photos are disabled for this gallery. Selection limit is {included} photos."
    if bool_attr(album, "strict_limit", False):
        maximum = capped(int_attr(album, "max_selection_limit", 100), total or 0)
        if maximum and current_selected >= maximum:
            return f"Album selection limit reached! Maximum {maximum} photos allowed. Please unselect another photo before selecting this one."
    return None


def confirm_error(album, selected_count, total):
    mode = mode_of(album)
    required = capped(int_attr(album, "required_photos", 100), total)
    included = capped(int_attr(album, "included_photos", 100), total)
    if mode == "UNLIMITED":
        if selected_count == 0:
            return "Please select at least one photo before confirming."
        return None
    if mode == "FIXED":
        if selected_count < required:
            remaining = required - selected_count
            return f"You need to select {remaining} more photo{'' if remaining == 1 else 's'} before submitting."
        if selected_count > required:
            extra = selected_count - required
            return f"You have selected {extra} extra photo{'' if extra == 1 else 's'}. Fixed mode requires exactly {required} photos."
        return None
    if mode == "MIN_EXTRA":
        if selected_count < included:
            remaining = included - selected_count
            return f"Please select {remaining} more photo{'' if remaining == 1 else 's'} to continue."
        return None
    if selected_count == 0:
        return "Please select at least one photo before confirming."
    return None


def sheet_quote(album, selected_count, total):
    mode = mode_of(album)
    required = capped(int_attr(album, "required_photos", 100), total)
    included = capped(int_attr(album, "included_photos", 100), total)
    per_sheet = max(1, int_attr(album, "photos_per_sheet", 4))
    estimated = math.ceil(selected_count / per_sheet) if selected_count else 0
    if mode == "FIXED":
        included_sheets = math.ceil(required / per_sheet) if required else 0
        extra_photos = 0
        extra_sheets = 0
        remaining = required - selected_count
    elif mode == "MIN_EXTRA":
        included_sheets = math.ceil(included / per_sheet) if included else 0
        extra_photos = max(0, selected_count - included)
        extra_sheets = max(0, estimated - included_sheets)
        remaining = max(0, included - selected_count)
    else:
        included_sheets = 0
        extra_photos = 0
        extra_sheets = 0
        remaining = 0 if selected_count else 1
    photo_charge = extra_photos * decimal_attr(album, "extra_photo_price") if mode == "MIN_EXTRA" and bool_attr(album, "enable_extra_photo_pricing", False) else Decimal("0")
    sheet_charge = extra_sheets * decimal_attr(album, "extra_sheet_price") if mode == "MIN_EXTRA" and bool_attr(album, "enable_extra_sheet_pricing", False) else Decimal("0")
    return {
        "mode": mode,
        "required": required if mode == "FIXED" else None,
        "included": included if mode == "MIN_EXTRA" else None,
        "per_sheet": per_sheet,
        "estimated": estimated,
        "included_sheets": included_sheets if mode in {"FIXED", "MIN_EXTRA"} else None,
        "extra_photos": extra_photos,
        "extra_sheets": extra_sheets,
        "remaining": remaining,
        "photo_charge": photo_charge,
        "sheet_charge": sheet_charge,
        "total_charge": photo_charge + sheet_charge,
    }


def confirmation_snapshot(album, selected_count, total, name="", notes=""):
    quote = sheet_quote(album, selected_count, total)
    return {
        "confirmed_by_name": (name or "").strip() if isinstance(name, str) else "",
        "confirmation_notes": (notes or "").strip() if isinstance(notes, str) else "",
        "confirmed_selected_count": selected_count,
        "extra_photos_count": quote["extra_photos"],
        "extra_sheets_count": quote["extra_sheets"],
        "estimated_sheets": quote["estimated"],
        "extra_photo_charge": quote["photo_charge"],
        "extra_sheet_charge": quote["sheet_charge"],
        "total_extra_charge": quote["total_charge"],
    }


def apply_snapshot(album, snapshot):
    for key, value in snapshot.items():
        setattr(album, key, value)


def public_rules(album, total, selected_count):
    quote = sheet_quote(album, selected_count, total)
    mode = quote["mode"]
    locked = getattr(album, "status", "") == "selected"
    extra_photos = int_attr(album, "extra_photos_count", quote["extra_photos"]) if locked else quote["extra_photos"]
    extra_sheets = int_attr(album, "extra_sheets_count", quote["extra_sheets"]) if locked else quote["extra_sheets"]
    estimated = int_attr(album, "estimated_sheets", quote["estimated"]) if locked else quote["estimated"]
    photo_charge = decimal_attr(album, "extra_photo_charge") if locked else quote["photo_charge"]
    sheet_charge = decimal_attr(album, "extra_sheet_charge") if locked else quote["sheet_charge"]
    total_charge = decimal_attr(album, "total_extra_charge") if locked else quote["total_charge"]
    return {
        "selectionMode": mode,
        "rulesConfigured": getattr(album, "rules_configured", True) is not False,
        "requiredPhotos": quote["required"],
        "includedPhotos": quote["included"],
        "allowExtraPhotos": bool_attr(album, "allow_extra_photos", True),
        "enableExtraPhotoPricing": bool_attr(album, "enable_extra_photo_pricing", False),
        "extraPhotoPrice": float(decimal_attr(album, "extra_photo_price")),
        "photosPerSheet": quote["per_sheet"],
        "includedSheets": quote["included_sheets"],
        "enableExtraSheetPricing": bool_attr(album, "enable_extra_sheet_pricing", False),
        "extraSheetPrice": float(decimal_attr(album, "extra_sheet_price")),
        "strictLimit": bool_attr(album, "strict_limit", False),
        "maxSelectionLimit": quote["required"] if mode == "FIXED" else (quote["included"] if mode == "MIN_EXTRA" else None),
        "totalPhotos": total,
        "selectedCount": selected_count,
        "remaining": quote["remaining"],
        "estimatedSheets": estimated,
        "isLocked": locked,
        "confirmedByName": getattr(album, "confirmed_by_name", "") or "",
        "confirmationNotes": getattr(album, "confirmation_notes", "") or "",
        "extraPhotos": extra_photos,
        "extraSheets": extra_sheets,
        "extraPhotoCharge": float(photo_charge),
        "extraSheetCharge": float(sheet_charge),
        "totalExtraCharge": float(total_charge),
    }


def photo_state(photo, selected_count):
    return {
        "photoId": str(photo.id),
        "selected": photo.selected,
        "rating": photo.rating or 0,
        "coverType": photo.cover_type or None,
        "notes": photo.notes or "",
        "selectedCount": selected_count,
    }


def toggle_photo(album, photo, is_selected):
    if album.status == "selected":
        return api_fail(LOCKED, data={"isLocked": True}, http_status=403)
    if not isinstance(is_selected, bool):
        return api_fail("Choose whether this photo is selected.")
    if is_selected and not photo.selected:
        message = select_limit_error(album, album.photos.filter(selected=True).count(), album.photos.count())
        if message:
            return api_fail(message, data={"limitReached": True}, http_status=400)
    photo.selected = is_selected
    photo.save(update_fields=["selected"])
    return api_success("Photo selected" if is_selected else "Photo deselected", photo_state(photo, album.photos.filter(selected=True).count()))


def update_photo_details(album, photo, payload):
    if album.status == "selected":
        return api_fail("This gallery has been confirmed and locked. Photo details cannot be changed.", data={"isLocked": True}, http_status=403)
    if not photo.selected:
        message = select_limit_error(album, album.photos.filter(selected=True).count(), album.photos.count())
        if message:
            return api_fail(message, data={"limitReached": True}, http_status=400)
    fields = ["selected"]
    if "rating" in payload:
        try:
            rating = int(payload.get("rating"))
        except (TypeError, ValueError):
            return api_fail("Rating must be from 0 to 5.")
        photo.rating = min(5, max(0, rating))
        fields.append("rating")
    if "coverType" in payload:
        cover = payload.get("coverType") or ""
        if cover not in ("", "FRONT", "BACK"):
            return api_fail("Cover must be front, back, or none.")
        if cover == "FRONT":
            album.photos.filter(cover_type="FRONT").exclude(pk=photo.pk).update(cover_type="")
        elif cover == "BACK":
            album.photos.filter(cover_type="BACK").exclude(pk=photo.pk).update(cover_type="")
        photo.cover_type = cover
        fields.append("cover_type")
    if "notes" in payload:
        notes = payload.get("notes") if payload.get("notes") is not None else ""
        if not isinstance(notes, str):
            return api_fail("Keep the photo note under 2000 characters.")
        notes = notes.strip()
        if len(notes) > 2000:
            return api_fail("Keep the photo note under 2000 characters.")
        photo.notes = notes
        fields.append("notes")
    photo.selected = True
    photo.save(update_fields=fields)
    return api_success("Photo details updated", photo_state(photo, album.photos.filter(selected=True).count()))


def confirm_selection(album, name, notes):
    if album.status == "selected":
        return api_fail("Final selection has already been confirmed.")
    if not isinstance(name, str) or len(name.strip()) < 2:
        return api_fail("सिलेक्शन फाइनल करने वाले का नाम अनिवार्य है (कृपया अपना नाम लिखें)।")
    total = album.photos.count()
    selected_count = album.photos.filter(selected=True).count()
    message = confirm_error(album, selected_count, total)
    if message:
        return api_fail(message)
    apply_snapshot(album, confirmation_snapshot(album, selected_count, total, name, notes if isinstance(notes, str) else ""))
    return None
