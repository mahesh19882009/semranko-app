"""Canonical, country-aware mobile-number handling for account verification."""

from __future__ import annotations

import re
from typing import Any

import phonenumbers
from phonenumbers import NumberParseException, PhoneNumberFormat

from app.core.errors import ApiError


DEFAULT_COUNTRY = "IN"


def _invalid_mobile(message: str) -> ApiError:
    """Return a frontend-safe validation error for the mobile field."""
    return ApiError(
        422,
        message,
        {
            "error": "INVALID_MOBILE_NUMBER",
            "fieldErrors": {"mobile": message},
        },
    )


def _selected_country(country: str | None) -> str | None:
    if country is None or not str(country).strip():
        return None
    normalized = str(country).strip().upper()
    if normalized not in phonenumbers.SUPPORTED_REGIONS:
        raise _invalid_mobile("Choose a valid country.")
    return normalized


def normalize_phone_number(value: Any, country: str | None = None) -> str:
    """Return canonical E.164 digits without ``+`` after strict validation.

    A selected country permits national-number entry. Explicit international input
    remains supported for existing clients, while a supplied country must match
    the parsed number so the country picker cannot silently change its meaning.
    """
    raw = str(value or "").strip()
    if not raw:
        raise _invalid_mobile("Mobile number is required.")

    selected_country = _selected_country(country)
    parse_country = selected_country or DEFAULT_COUNTRY
    digits = re.sub(r"\D", "", raw)
    if not digits:
        raise _invalid_mobile("Enter a valid mobile number.")

    candidates: list[tuple[str, str | None]] = []
    if raw.startswith("+"):
        candidates.append((raw, None))
    else:
        # First preserve the selected country's national-number interpretation.
        candidates.append((raw, parse_country))
        # Existing RankCare values are digits-only international numbers; this
        # fallback also permits legacy API clients to submit that representation.
        candidates.append((f"+{digits}", None))

    parsed = None
    for candidate, region in candidates:
        try:
            potential = phonenumbers.parse(candidate, region)
        except NumberParseException:
            continue
        if phonenumbers.is_possible_number(potential) and phonenumbers.is_valid_number(potential):
            parsed = potential
            break

    if parsed is None:
        raise _invalid_mobile("Enter a valid mobile number for the selected country.")

    parsed_country = phonenumbers.region_code_for_number(parsed)
    if selected_country and parsed_country != selected_country:
        raise _invalid_mobile("Enter a valid mobile number for the selected country.")

    return phonenumbers.format_number(parsed, PhoneNumberFormat.E164).lstrip("+")


def to_provider_phone_number(canonical_mobile: str) -> str:
    """Validate and adapt the launch canonical value for 2Factor's digits API."""
    canonical = normalize_phone_number(f"+{str(canonical_mobile or '').strip()}")
    return canonical


def mask_phone_number(canonical_mobile: str) -> str:
    """Provide a practical display-safe phone representation for OTP screens."""
    digits = re.sub(r"\D", "", str(canonical_mobile or ""))
    try:
        parsed = phonenumbers.parse(f"+{digits}", None)
        country_code = str(parsed.country_code)
        national = str(parsed.national_number)
        if national:
            return f"+{country_code} ••••• {national[-4:]}"
    except NumberParseException:
        pass
    return f"•••• {digits[-4:]}" if digits else "••••"
