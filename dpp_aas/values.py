from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from typing import Any


EMPTY_VALUES = {"", "N/A"}
TRUE_VALUES = {"true", "1", "yes", "y", "true.0"}
FALSE_VALUES = {"false", "0", "no", "n", "false.0"}
DATE_FORMATS = (
    "%Y-%m-%d",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%dT%H:%M:%SZ",
    "%d/%m/%Y",
    "%m/%d/%Y",
)


def coerce_value(value: Any, value_type: str) -> str | None:
    """Convert an Excel value to the lexical representation required by AAS."""
    if value is None or str(value).strip() in EMPTY_VALUES:
        return None

    normalized_type = value_type.lower()
    if "date" in normalized_type:
        return _coerce_date(value, include_time="datetime" in normalized_type)

    text = str(value).strip()
    if "boolean" in normalized_type:
        lowered = text.lower()
        if lowered in TRUE_VALUES:
            return "true"
        if lowered in FALSE_VALUES:
            return "false"
        raise ValueError(f"{value!r} is not a valid boolean")

    if any(token in normalized_type for token in ("integer", "int", "long", "short")):
        try:
            return str(int(Decimal(text)))
        except (InvalidOperation, ValueError) as exc:
            raise ValueError(f"{value!r} is not a valid integer") from exc

    if any(token in normalized_type for token in ("double", "float", "decimal")):
        try:
            number = Decimal(text)
        except InvalidOperation as exc:
            raise ValueError(f"{value!r} is not a valid number") from exc
        return format(number, "f")

    return text


def _coerce_date(value: Any, *, include_time: bool) -> str:
    parsed: datetime
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, date):
        parsed = datetime.combine(value, datetime.min.time())
    else:
        text = str(value).strip()
        parsed = _parse_date_text(text)

    if include_time:
        return parsed.strftime("%Y-%m-%dT%H:%M:%S")
    return parsed.strftime("%Y-%m-%d")


def _parse_date_text(text: str) -> datetime:
    for date_format in DATE_FORMATS:
        try:
            return datetime.strptime(text, date_format)
        except ValueError:
            continue

    try:
        return datetime(1899, 12, 30) + timedelta(days=float(text))
    except ValueError as exc:
        raise ValueError(f"{text!r} is not a valid date") from exc
