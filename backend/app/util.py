"""시각 변환 - 저장은 UTC(시간대 없는 값), 응답은 ISO 8601 + Z"""
from datetime import datetime, timezone


def iso(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    return dt.replace(microsecond=0).isoformat() + "Z"


def parse_iso(value: str) -> datetime:
    """ISO 8601 문자열을 UTC 기준 시간대 없는 값으로 바꾼다. 형식이 틀리면 ValueError"""
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    dt = datetime.fromisoformat(text)
    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt
