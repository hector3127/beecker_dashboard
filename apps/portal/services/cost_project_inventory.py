"""Operational projects with no booked revenue still generate account costs."""

from collections import defaultdict

from django.utils import timezone

from apps.ejecutivo.services.aer_tym_summary import (
    find_mpb_header,
    resolve_columns,
)
from apps.portal.services.executive_period import bounds
from core.utils.dates import to_datetime
from core.utils.text import normalize_name


def inventory(reader):
    """Find operational projects overlapping the financial period."""
    start, end = bounds()
    today = timezone.localdate()
    found = {}
    owners = defaultdict(set)
    for row in reader.read_values("DataRevenue")[1:]:
        if (
            len(row) > 4
            and str(row[4] or "").strip()
            and str(row[1] or "").strip()
        ):
            owners[str(row[4]).strip().casefold()].add(str(row[1]).strip())
    known_names = {
        normalize_name(name): name
        for names in owners.values()
        for name in names
    }
    # Historical ownership uses only columns A:I, matched by exact project ID.
    history_rows = (
        reader.read_values("Historico_Proyectos")
        if reader.sheet_exists("Historico_Proyectos")
        else []
    )
    historical_owners = defaultdict(set)
    for row in history_rows[1:]:
        if len(row) > 2:
            pid = str(row[2] or "").strip().casefold()
            canonical = known_names.get(normalize_name(str(row[1] or "")))
            if pid and canonical:
                historical_owners[pid].add(canonical)

    def add(pid, account, first, last):
        pid = str(pid or "").strip()
        account = str(account or "").strip()
        a, b = to_datetime(first), to_datetime(last)
        if (
            not pid
            or not a
            or (b and a > b)
            or a.date() > end
            or (b.date() if b else today) < start
        ):
            return
        from apps.portal.services.project_task_scope import variant

        task_variant = variant(pid)
        names = (
            owners.get(pid.casefold())
            or (owners.get(task_variant[0]) if task_variant else None)
            or historical_owners.get(pid.casefold())
        )
        if not names and account:
            canonical = {
                "heineken": "heineken mexico",
                "arca continental": "arca continental mexico",
            }.get(normalize_name(account), normalize_name(account))
            names = {
                known_names.get(
                    canonical,
                    "Arca Continental Mexico"
                    if canonical == "arca continental mexico"
                    else account,
                )
            }
        if names:
            found[pid.casefold()] = {"id": pid, "accounts": set(names)}

    def cell(row, index):
        return row[index] if index < len(row) else ""

    if reader.sheet_exists("MPB"):
        rows = reader.read_values("MPB")
        header = find_mpb_header(rows)
        if header is not None:
            cols = resolve_columns(rows[header])
            for row in rows[header + 1 :]:
                add(
                    cell(row, cols["project_id"]),
                    cell(row, cols["client"]),
                    cell(row, cols["start"]),
                    cell(row, cols["end"]),
                )
    if reader.sheet_exists("Historico_Proyectos"):
        events = defaultdict(list)
        for row in history_rows[1:]:
            pid = str(cell(row, 2) or "").strip()
            if pid:
                events[pid.casefold()].append(row)
        for key, rows in events.items():
            if key in found:
                continue
            starts = [
                to_datetime(cell(r, 7))
                for r in rows
                if not str(cell(r, 6)).strip().lower().endswith(" est")
            ]
            starts = [x for x in starts if x]
            ends = [
                to_datetime(cell(r, 8)) or to_datetime(cell(r, 7))
                for r in rows
                if str(cell(r, 6)).strip().lower()
                in {
                    "completed",
                    "completado",
                    "finalizado",
                    "cancelled",
                    "cancelado",
                }
            ]
            ends = [x for x in ends if x]
            if starts:
                add(
                    cell(rows[0], 2),
                    cell(rows[0], 1),
                    min(starts),
                    max(ends) if ends else today,
                )
    from core.sheets.project_year import mpb_previous_year_ids

    excluded = (
        mpb_previous_year_ids(reader, start.year)
        if start.year == end.year
        else set()
    )
    resolved = {}
    from apps.portal.services.project_task_scope import variant

    for pid, item in found.items():
        if pid in excluded:
            continue
        child = variant(item["id"])
        # MPB/history variants are not separate financial projects unless
        # DataRevenue also identifies them independently from the base ID.
        if (
            child
            and pid not in owners
            and child[0] in owners
            and child[0] not in excluded
        ):
            base = child[0]
            resolved.setdefault(
                base, {"id": base.upper(), "accounts": set(owners[base])}
            )
        else:
            resolved[pid] = item
    return resolved
