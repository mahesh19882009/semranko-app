"""Persistent identity helpers for tracked keyword targets."""

from __future__ import annotations

import json
import json

from app.services.dataforseo_client import LOCATION_MAP
from app.services.location_catalog import resolve_keyword_location
from app.services.location_catalog import KEYWORD_LOCATION_CATALOG

DEFAULT_DEVICE = "desktop"
SUPPORTED_DEVICES = frozenset(("desktop", "mobile"))


def normalize_keyword(value: str | None) -> str:
    """Match the existing add behavior: trim outer whitespace and lowercase."""
    return (value or "").strip().lower()


def normalize_device(value: str | None) -> str:
    normalized = (value or DEFAULT_DEVICE).strip().lower()
    if normalized not in SUPPORTED_DEVICES:
        raise ValueError(f"Unsupported keyword device: {value}")
    return normalized


def _location_parts(location: str | None) -> tuple[str | None, str | None, str | None]:
    if not location:
        return None, None, None
    value = location.strip()
    if value.startswith("{"):
        try:
            parsed = json.loads(value)
        except (TypeError, ValueError):
            parsed = None
        if isinstance(parsed, dict):
            return parsed.get("country"), parsed.get("state"), parsed.get("city")
    parts = [part.strip() for part in value.split(",") if part.strip()]
    if len(parts) == 3:
        return parts[2], parts[1], parts[0]
    if len(parts) == 2:
        return parts[1], parts[0], None
    if len(parts) == 1:
        return parts[0], None, None
    return None, None, None


def effective_location_code(
    *,
    location_code: int | str | None = None,
    location: str | None = None,
    project_location_code: int | str | None = None,
    project_location: str | None = None,
) -> int:
    """Resolve the effective provider code without replacing explicit codes.

    Explicit request codes win. Existing project metadata is used for legacy
    country labels, while canonical state/city labels are resolved from the
    shared catalog. The final 2840 fallback preserves the established API
    default for legacy callers that supplied no location metadata.
    """
    for candidate in (location_code,):
        if candidate is not None and str(candidate).strip():
            return int(candidate)

    if location and project_location and location.strip().casefold() == project_location.strip().casefold() and project_location_code is not None:
        return int(project_location_code)

    country, state, city = _location_parts(location)
    if country:
        try:
            return int(resolve_keyword_location(country, state, city)["location_code"])
        except (TypeError, ValueError):
            pass

    if location:
        legacy_code = LOCATION_MAP.get(location.strip())
        if legacy_code is not None:
            return int(legacy_code)

    if project_location_code is not None:
        return int(project_location_code)

    return 2840


def target_identity(
    keyword: str,
    *,
    location_code: int | str | None,
    device: str | None,
) -> tuple[str, int, str]:
    return normalize_keyword(keyword), int(location_code), normalize_device(device)


def catalog_location_labels() -> dict[str, int]:
    labels: dict[str, int] = {}
    for country in KEYWORD_LOCATION_CATALOG:
        country_name = country["name"]
        labels[country_name.casefold()] = int(country["location_code"])
        for state in country.get("states", ()):
            labels[f"{state['name']}, {country_name}".casefold()] = int(state["location_code"])
            for city in state.get("cities", ()):
                labels[f"{city['name']}, {state['name']}, {country_name}".casefold()] = int(city["location_code"])
    return labels


def _display_location(value: str | None) -> str:
    if not value:
        return ""
    raw = str(value).strip()
    if raw.startswith("{"):
        try:
            parsed = json.loads(raw)
        except (TypeError, ValueError):
            parsed = None
        if isinstance(parsed, dict):
            return ", ".join(
                part for part in (parsed.get("city"), parsed.get("state"), parsed.get("country"))
                if part
            )
    return raw


def resolve_legacy_keyword_target(row: dict, project: dict, labels: dict[str, int]) -> tuple[str, int, str] | tuple[None, str]:
    keyword = normalize_keyword(row.get("keyword"))
    if not keyword:
        return None, "empty keyword"
    raw_device = (row.get("device") or DEFAULT_DEVICE).strip().lower()
    if raw_device not in SUPPORTED_DEVICES:
        return None, f"unsupported device {row.get('device')!r}"
    row_location = _display_location(row.get("location"))
    project_location = _display_location(project.get("location"))
    project_code = project.get("locationCode")
    if row_location and project_location and row_location.casefold() == project_location.casefold() and project_code is not None:
        code = int(project_code)
    elif row_location.casefold() in labels:
        code = labels[row_location.casefold()]
    elif not row_location and project_code is not None:
        code = int(project_code)
    else:
        return None, f"unresolved location {row.get('location')!r}"
    return keyword, code, raw_device
