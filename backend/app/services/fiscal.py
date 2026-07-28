"""Indian fiscal-year (April–March) helpers for report grouping."""
import re
from typing import Optional
from fastapi import HTTPException

_MONTH_RE = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")
_FY_RE = re.compile(r"^\d{4}-\d{2}$")


def month_to_fy(month: str) -> str:
    """"YYYY-MM" -> fiscal year label, e.g. "2026-07" -> "2026-27", "2026-02" -> "2025-26"."""
    if not _MONTH_RE.match(month):
        raise ValueError(f"Invalid month format: {month!r}, expected YYYY-MM")
    year, mon = int(month[:4]), int(month[5:7])
    start_year = year if mon >= 4 else year - 1
    return f"{start_year}-{str(start_year + 1)[-2:]}"


def fy_to_months(fy: str) -> list[str]:
    """Fiscal year label -> the 12 "YYYY-MM" strings it spans, April through March."""
    if not _FY_RE.match(fy):
        raise ValueError(f"Invalid fiscal year format: {fy!r}, expected YYYY-YY")
    start_year = int(fy[:4])
    if int(fy[5:7]) != (start_year + 1) % 100:
        raise ValueError(f"Invalid fiscal year format: {fy!r}, expected YYYY-YY consecutive")
    months = [f"{start_year}-{m:02d}" for m in range(4, 13)]
    months += [f"{start_year + 1}-{m:02d}" for m in range(1, 4)]
    return months


def period_months(month: Optional[str], fiscal_year: Optional[str]) -> Optional[list[str]]:
    """Resolve a month/fiscal_year query-param pair (mutually exclusive) into a month list."""
    if month and fiscal_year:
        raise HTTPException(400, "Provide either month or fiscal_year, not both")
    if fiscal_year:
        return fy_to_months(fiscal_year)
    if month:
        return [month]
    return None


def month_range(from_month: str, to_month: str) -> list[str]:
    """Inclusive "YYYY-MM" list between two months, e.g. ("2026-02","2026-05") ->
    ["2026-02","2026-03","2026-04","2026-05"]."""
    if not _MONTH_RE.match(from_month):
        raise HTTPException(400, f"Invalid from_month format: {from_month!r}, expected YYYY-MM")
    if not _MONTH_RE.match(to_month):
        raise HTTPException(400, f"Invalid to_month format: {to_month!r}, expected YYYY-MM")
    y1, m1 = int(from_month[:4]), int(from_month[5:7])
    y2, m2 = int(to_month[:4]), int(to_month[5:7])
    if (y1, m1) > (y2, m2):
        raise HTTPException(400, "from_month must not be after to_month")
    months = []
    y, m = y1, m1
    while (y, m) <= (y2, m2):
        months.append(f"{y}-{m:02d}")
        m += 1
        if m > 12:
            m = 1
            y += 1
    return months
