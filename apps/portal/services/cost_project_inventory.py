"""Operational projects with no booked revenue still generate account costs."""

from collections import defaultdict
from typing import Any

from django.utils import timezone

from apps.ejecutivo.services.aer_tym_summary import (
    AER_TYM_SERVICE,
    find_mpb_header,
    resolve_columns,
)
from apps.portal.services.executive_period import bounds
from apps.portal.services.financial_azure_dates import azure_scopes, scope_dates
from core.sheets.protocols import SheetReader
from core.utils.dates import to_datetime
from core.utils.text import normalize_name


def inventory(reader: SheetReader) -> dict[str, dict[str, Any]]:
    """Find operational projects overlapping the financial period."""
    start, end = bounds()
    today = timezone.localdate()
    found = {}
    history_ids = set()
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

    # Exact IDs in the right-hand block disambiguate regional account names.
    # Prefer a country already set by A:I; never merge by a generic name.
    for row in history_rows[1:]:
        if len(row) > 12:
            pid = str(row[12] or "").strip().casefold()
            canonical = known_names.get(normalize_name(str(row[11] or "")))
            if pid and canonical and not historical_owners.get(pid):
                historical_owners[pid].add(canonical)

    def add(pid: Any, account: Any, first: Any, last: Any) -> None:
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
        from apps.portal.services.project_task_scope import (
            financial_variant as variant,
        )

        task_variant = variant(pid)
        names = (
            owners.get(pid.casefold())
            or (owners.get(task_variant[0]) if task_variant else None)
            or historical_owners.get(pid.casefold())
        )
        if not names and account:
            canonical = {
                "heineken": "heineken mexico",
                "oxxo": "cadena comercial oxxo",
                "cadena comercial oxxo.": "cadena comercial oxxo",
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

    def cell(row: list[Any], index: int) -> Any:
        return row[index] if index < len(row) else ""

    if reader.sheet_exists("MPB"):
        rows = reader.read_values("MPB")
        header = find_mpb_header(rows)
        if header is not None:
            cols = resolve_columns(rows[header])
            for row in rows[header + 1 :]:
                if not AER_TYM_SERVICE.match(
                    normalize_name(str(cell(row, cols["service"]) or ""))
                ):
                    continue
                add(
                    cell(row, cols["project_id"]),
                    cell(row, cols["client"]),
                    cell(row, cols["start"]),
                    cell(row, cols["end"]),
                )
    for row in azure_scopes():
        fields = row.get("fields", {})
        if normalize_name(fields.get("service", "")) not in {
            "ixb",
            "raas",
            "saas",
        }:
            continue
        pid = row["project_id"]
        dates = scope_dates(row)
        if dates is not None and pid.casefold() not in found:
            history_ids.add(pid.casefold())
            add(pid, fields.get("client"), *dates)
    from core.sheets.project_year import mpb_previous_year_ids

    excluded = (
        mpb_previous_year_ids(reader, start.year)
        if start.year == end.year
        else set()
    )
    resolved: dict[str, dict[str, Any]] = {}
    from apps.portal.services.project_task_scope import (
        financial_variant as variant,
    )

    for pid, item in found.items():
        if pid in excluded and pid not in history_ids:
            continue
        child = variant(item["id"])
        # MPB/history variants are not separate financial projects unless
        # DataRevenue also identifies them independently from the base ID.
        if (
            child
            and pid not in owners
            and (child[0] not in excluded or pid in history_ids)
        ):
            base = child[0]
            resolved.setdefault(
                base,
                {
                    "id": found.get(base, {}).get("id", base.upper()),
                    "accounts": set(
                        owners.get(base)
                        or found.get(base, {}).get("accounts")
                        or item["accounts"]
                    ),
                },
            )
        else:
            resolved[pid] = item
    return resolved
