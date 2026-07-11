from datetime import date, datetime
from decimal import Decimal
from typing import Any, Optional


def _convert_value(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, list):
        return [_convert_value(item) for item in value]
    if isinstance(value, dict):
        return {k: _convert_value(v) for k, v in value.items()}
    return value


def model_to_dict(model: Any, exclude: Optional[set[str]] = None) -> dict:
    exclude = exclude or set()
    data: dict[str, Any] = {}

    for key in model.__mapper__.c.keys():
        if key in exclude:
            continue
        data[key] = _convert_value(getattr(model, key))

    return data
