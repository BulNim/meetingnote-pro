"""할 일 기한 글자(due_text)를 기준일에서 날짜(due_date)로 바꾼다 - 고정 규칙, 같은 입력이면 같은 결과.

기준일: 회의록에서 뽑힌 할 일은 회의 시각(met_at)의 한국 날짜, 직접 등록은 등록한 날의 한국 날짜.
한 주는 월요일에 시작한다. 정할 수 없는 글자는 None (원래 글자는 호출한 쪽이 그대로 둔다).
"""
import calendar
import re
from datetime import date, datetime, timedelta, timezone

KST = timezone(timedelta(hours=9))  # 한국은 서머타임이 없어 고정 오프셋으로 충분

DAYS = "월화수목금토일"
TAILS = ("까지", "안에", "안", "내", "중", "쯤")
_DAY = r"([월화수목금토일])(?:요일)?"


def kst_date(dt: datetime) -> date:
    """UTC(tz 없음 또는 있음) 시각의 한국 날짜."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(KST).date()


def base_date(created_at: datetime, met_at: datetime | None) -> date:
    """회의록에서 뽑힌 할 일이면 회의 날짜, 아니면 등록한 날."""
    return kst_date(met_at if met_at is not None else created_at)


def _clean(text: str) -> str:
    t = "".join((text or "").split())
    changed = True
    while changed and t:
        changed = False
        for tail in TAILS:
            if t.endswith(tail) and len(t) > len(tail):
                t, changed = t[: -len(tail)], True
    return t


def _monday(d: date) -> date:
    return d - timedelta(days=d.weekday())


def _weekday_in(week_start: date, ch: str) -> date:
    return week_start + timedelta(days=DAYS.index(ch))


def _safe(y: int, m: int, d: int) -> date | None:
    try:
        return date(y, m, d)
    except ValueError:
        return None


def _add_months(y: int, m: int, n: int) -> tuple[int, int]:
    m0 = m - 1 + n
    return y + m0 // 12, m0 % 12 + 1


def _month_end(y: int, m: int) -> date:
    return date(y, m, calendar.monthrange(y, m)[1])


def resolve(text: str, base: date) -> date | None:
    t = _clean(text)
    if not t:
        return None
    B = base

    fixed = {"오늘": 0, "금일": 0, "내일": 1, "모레": 2, "어제": -1, "다음주": 7, "차주": 7, "지난주": -7}
    if t in fixed:
        return B + timedelta(days=fixed[t])

    if m := re.fullmatch(r"(\d{1,3})일(?:뒤|후)", t):
        return B + timedelta(days=int(m.group(1)))
    if m := re.fullmatch(r"(\d{1,2})주(?:뒤|후)", t):
        return B + timedelta(weeks=int(m.group(1)))

    if m := re.fullmatch(r"(이번주|다음주|차주|지난주)?" + _DAY, t):
        shift = {None: 0, "이번주": 0, "다음주": 7, "차주": 7, "지난주": -7}[m.group(1)]
        return _weekday_in(_monday(B) + timedelta(days=shift), m.group(2))

    if t in ("이번달말", "월말"):
        return _month_end(B.year, B.month)
    if t == "다음달말":
        return _month_end(*_add_months(B.year, B.month, 1))

    if m := re.fullmatch(r"(이번달|다음달)?(\d{1,2})일", t):
        y, mo = _add_months(B.year, B.month, 1 if m.group(1) == "다음달" else 0)
        return _safe(y, mo, int(m.group(2)))

    if m := re.fullmatch(r"(\d{1,2})월(\d{1,2})일", t) or re.fullmatch(r"(\d{1,2})/(\d{1,2})", t):
        d = _safe(B.year, int(m.group(1)), int(m.group(2)))
        if d is not None and d < B:
            d = _safe(B.year + 1, int(m.group(1)), int(m.group(2)))
        return d

    if m := re.fullmatch(r"(\d{4})[-.](\d{1,2})[-.](\d{1,2})", t):
        return _safe(int(m.group(1)), int(m.group(2)), int(m.group(3)))

    return None
