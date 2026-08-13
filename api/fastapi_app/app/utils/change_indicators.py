"""
Change indicator helpers for historical comparison.

Provides a generic structure for exposing previous/current/difference/direction
so the frontend can display green/red state without making extra API calls.
"""

from typing import Any, Optional


def compute_change(current: Any, previous: Any, lower_is_better: bool = False) -> Optional[dict]:
    if current is None or previous is None:
        return None

    try:
        current_val = float(current)
        previous_val = float(previous)
    except (TypeError, ValueError):
        return None

    diff = round(current_val - previous_val, 2)
    direction = _direction(diff, lower_is_better)
    is_positive = _is_positive(diff, lower_is_better)

    return {
        "previous": previous_val,
        "current": current_val,
        "difference": diff,
        "direction": direction,
        "isPositive": is_positive,
    }


def _direction(diff: float, lower_is_better: bool) -> str:
    if diff == 0:
        return "same"
    if lower_is_better:
        return "up" if diff < 0 else "down"
    return "up" if diff > 0 else "down"


def _is_positive(diff: float, lower_is_better: bool) -> bool:
    if diff == 0:
        return False
    if lower_is_better:
        return diff < 0
    return diff > 0


POSITION_LOWER_IS_BETTER = True
VOLUME_LOWER_IS_BETTER = False
KD_LOWER_IS_BETTER = False
CPC_LOWER_IS_BETTER = False
COMPETITION_LOWER_IS_BETTER = False
BACKLINKS_LOWER_IS_BETTER = False
REFERRING_DOMAINS_LOWER_IS_BETTER = False


def keyword_change(current_keyword: dict, previous_keyword: dict) -> dict:
    changes = {}

    position_change = compute_change(
        current_keyword.get("position"),
        previous_keyword.get("position"),
        lower_is_better=POSITION_LOWER_IS_BETTER,
    )
    if position_change is not None:
        changes["position"] = position_change

    volume_change = compute_change(
        current_keyword.get("volume"),
        previous_keyword.get("volume"),
        lower_is_better=VOLUME_LOWER_IS_BETTER,
    )
    if volume_change is not None:
        changes["volume"] = volume_change

    kd_change = compute_change(
        current_keyword.get("kd"),
        previous_keyword.get("kd"),
        lower_is_better=KD_LOWER_IS_BETTER,
    )
    if kd_change is not None:
        changes["kd"] = kd_change

    cpc_change = compute_change(
        current_keyword.get("cpc"),
        previous_keyword.get("cpc"),
        lower_is_better=CPC_LOWER_IS_BETTER,
    )
    if cpc_change is not None:
        changes["cpc"] = cpc_change

    competition_change = compute_change(
        current_keyword.get("competition"),
        previous_keyword.get("competition"),
        lower_is_better=COMPETITION_LOWER_IS_BETTER,
    )
    if competition_change is not None:
        changes["competition"] = competition_change

    backlinks_change = compute_change(
        current_keyword.get("backlinks"),
        previous_keyword.get("backlinks"),
        lower_is_better=BACKLINKS_LOWER_IS_BETTER,
    )
    if backlinks_change is not None:
        changes["backlinks"] = backlinks_change

    referring_domains_change = compute_change(
        current_keyword.get("referring_domains"),
        previous_keyword.get("referring_domains"),
        lower_is_better=REFERRING_DOMAINS_LOWER_IS_BETTER,
    )
    if referring_domains_change is not None:
        changes["referring_domains"] = referring_domains_change

    return changes
