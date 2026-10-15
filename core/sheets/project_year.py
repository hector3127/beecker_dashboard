"""Shared MPB year eligibility for account lists and financial costs."""

from core.utils.dates import to_datetime
from core.utils.text import normalize_name


def mpb_previous_year_ids(reader, year=2026):
    """Exclude IDs whose known MPB periods all ended before 2026."""
    if not reader.sheet_exists("MPB"):
        return set()
    rows = reader.read_values("MPB")
    periods = {}
    columns = None
    for row in rows:
        headers = [normalize_name(str(cell or "")) for cell in row]
        if columns is None:
            if "id" in headers and "inicio" in headers and "fin" in headers:
                columns = tuple(
                    headers.index(name) for name in ("id", "inicio", "fin")
                )
            continue
        values = [row[i] if i < len(row) else "" for i in columns]
        pid = str(values[0] or "").strip().casefold()
        if not pid:
            continue
        start, end = to_datetime(values[1]), to_datetime(values[2])
        old = bool(
            start
            and end
            and start <= end
            and (end.year < year or start.year > year)
        )
        periods[pid] = periods.get(pid, True) and old
    return {pid for pid, old in periods.items() if old}
