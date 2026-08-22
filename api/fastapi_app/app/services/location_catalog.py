"""Verified keyword-tracking location catalog and hierarchy resolution.

The catalog deliberately contains only provider location codes that are
already present in Semranko's trusted DataForSEO mapping.  It is intentionally
small and additive: locations not represented here continue through the
existing country/location fallback used by Tracking.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.services.dataforseo_client import LOCATION_MAP


_CATALOG_PATH = Path(__file__).resolve().parents[4] / "semrankoapp" / "src" / "data" / "locations.json"


def _load_catalog() -> tuple[dict, ...]:
    with _CATALOG_PATH.open(encoding="utf-8") as catalog_file:
        raw_catalog = json.load(catalog_file)
    return tuple(
        {
            "name": country["name"],
            "location_code": country["locationCode"],
            "states": tuple(
                {
                    "name": state["name"],
                    "location_code": state["locationCode"],
                    "cities": tuple(
                        {"name": city["name"], "location_code": city["locationCode"]}
                        for city in state.get("cities", [])
                    ),
                }
                for state in country.get("states", [])
            ),
        }
        for country in raw_catalog
    )


KEYWORD_LOCATION_CATALOG = _load_catalog()


def get_country_code_for_location(location_code: int | str) -> int:
    """Resolve any catalog location to its root country code.

    Tracking keeps the supplied country/state/city code as its exact SERP
    target. DataForSEO Labs Keyword Overview accepts country-level locations,
    so callers use this helper only at the Labs boundary. Resolution is based
    exclusively on the canonical hierarchy, never on display labels.

    Legacy country codes that predate the hierarchy remain valid as-is. An
    unknown code is rejected rather than guessed as a different country.
    """
    try:
        code = int(location_code)
    except (TypeError, ValueError) as exc:
        raise ValueError("location_code must be an integer") from exc

    for country in KEYWORD_LOCATION_CATALOG:
        country_code = int(country["location_code"])
        if code == country_code:
            return country_code
        for state in country.get("states", ()):
            if code == int(state["location_code"]):
                return country_code
            for city in state.get("cities", ()):
                if code == int(city["location_code"]):
                    return country_code

    # The established LOCATION_MAP contains country-level compatibility codes
    # not yet represented in locations.json.
    if code in {int(value) for value in LOCATION_MAP.values()}:
        return code

    raise ValueError(f"Unsupported tracking location code: {code}")


def _same_name(left: str | None, right: str | None) -> bool:
    return bool(left and right and left.strip().casefold() == right.strip().casefold())


def _catalog_country(country: str | None) -> dict[str, Any] | None:
    return next(
        (entry for entry in KEYWORD_LOCATION_CATALOG if _same_name(entry["name"], country)),
        None,
    )


def resolve_keyword_location(
    country: str | None,
    state: str | None = None,
    city: str | None = None,
    location_code: int | None = None,
) -> dict[str, Any]:
    """Resolve one effective code and a human-readable location label.

    State/city values are accepted only when they are present in the shared
    verified catalog. An attempted unverified child location is rejected
    rather than guessed.
    Legacy countries remain valid through ``LOCATION_MAP`` for compatibility.
    """

    country_name = (country or "").strip()
    if not country_name:
        raise ValueError("country is required")

    catalog_country = _catalog_country(country_name)
    if catalog_country:
        selected = catalog_country
        if state:
            state_entry = next(
                (entry for entry in catalog_country.get("states", ()) if _same_name(entry["name"], state)),
                None,
            )
            if not state_entry:
                raise ValueError(f"State is not available for {catalog_country['name']}")
            selected = state_entry
            if city:
                city_entry = next(
                    (entry for entry in state_entry.get("cities", ()) if _same_name(entry["name"], city)),
                    None,
                )
                if not city_entry:
                    raise ValueError(f"City is not available for {state_entry['name']}")
                selected = city_entry
        elif city:
            raise ValueError("City requires a state")

        effective_code = int(selected["location_code"])
        if (state or city) and location_code is not None and int(location_code) != effective_code:
            raise ValueError("location_code does not match the selected location")
        # Preserve the established Tracking payload contract for country-only
        # requests that explicitly supplied a provider code.
        if not state and not city and location_code is not None:
            effective_code = int(location_code)
        parts = [city, state, catalog_country["name"]]
        return {
            "country": catalog_country["name"],
            "state": state or None,
            "city": city or None,
            "location_code": effective_code,
            "label": ", ".join(part for part in parts if part),
        }

    # Existing projects can use any country already supported by the trusted
    # provider mapping.  Do not narrow that established Tracking contract.
    legacy_code = LOCATION_MAP.get(country_name)
    if legacy_code is None:
        raise ValueError("Unsupported keyword location")
    if state or city:
        raise ValueError("State/city selection is unavailable for this location")
    if location_code is not None and int(location_code) != int(legacy_code):
        raise ValueError("location_code does not match the selected location")
    return {
        "country": country_name,
        "state": None,
        "city": None,
        "location_code": int(location_code or legacy_code),
        "label": country_name,
    }


def location_label(location: str | None, project_location: str | None = None) -> str:
    """Return a human-readable stored location with legacy fallback."""

    value = (location or project_location or "India").strip() or "India"
    if value.startswith("{"):
        try:
            parsed = json.loads(value)
            if isinstance(parsed, dict):
                return ", ".join(
                    part for part in (
                        parsed.get("city"),
                        parsed.get("state"),
                        parsed.get("country"),
                    ) if part
                ) or parsed.get("country") or "India"
        except (TypeError, ValueError):
            pass
    return value


def location_label_for_code(
    location_code: int | str | None,
    fallback: str | None = None,
) -> str:
    """Return the canonical human-readable label for a catalog code.

    The provider code remains the identity used in requests and cache keys;
    this helper only supplies the display/row label used by Tracking jobs.
    Unknown legacy codes retain the caller's existing label instead of being
    guessed from the country-only compatibility map.
    """
    try:
        code = int(location_code) if location_code is not None else None
    except (TypeError, ValueError):
        code = None

    if code is not None:
        for country in KEYWORD_LOCATION_CATALOG:
            if int(country["location_code"]) == code:
                # Some established scheduled jobs use a legacy country code
                # with a stored project label (for example 2840/India).
                # Preserve that existing label when supplied; user-selected
                # state/city codes still resolve to their canonical hierarchy.
                return location_label(fallback) if fallback else country["name"]
            for state in country.get("states", ()):
                if int(state["location_code"]) == code:
                    return f"{state['name']}, {country['name']}"
                for city in state.get("cities", ()):
                    if int(city["location_code"]) == code:
                        return f"{city['name']}, {state['name']}, {country['name']}"

    return location_label(fallback)
