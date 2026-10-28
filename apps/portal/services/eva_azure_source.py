"""Candidate EVA rows from Azure Summary; no Sheets or external IO here."""

import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from apps.azure_devops.services.summary_parser import normalize, parse_summary

REQUIRED = (
    "delivery_manager",
    "service",
    "project_name",
    "start",
    "finish",
    "budget",
)
BUSINESS_ID = re.compile(
    r"[A-Z]{2,8}(?:\.[A-Z])?\.\d+(?:_(?:S\d+|CR\d*(?:_S\d+)?))?",
    re.IGNORECASE,
)


def summary_date(value: str) -> date | None:
    """Known Summary formats; never guess US vs Mexican day/month."""
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d/%m/%y", "%d-%m-%Y"):
        try:
            return datetime.strptime(value.strip(), fmt).date()
        except ValueError:
            continue
    months = (
        "enero",
        "febrero",
        "marzo",
        "abril",
        "mayo",
        "junio",
        "julio",
        "agosto",
        "septiembre",
        "octubre",
        "noviembre",
        "diciembre",
    )
    text = normalize(value)
    match = re.fullmatch(r"(\d{1,2}) (?:de )?([a-z]+) (?:de )?(\d{4})", text)
    if match and match[2] in months:
        try:
            return date(
                int(match[3]), months.index(match[2]) + 1, int(match[1])
            )
        except ValueError:
            pass
    return None


def summary_hours(value: str) -> Decimal | None:
    """Hours with decimal dot/comma and an optional unit, never currency."""
    text = re.sub(
        r"\s*(?:hours|hrs\.?|horas|h|a utilizar)\s*$",
        "",
        value.strip(),
        flags=re.I,
    )
    # A single separator followed by three digits is ambiguous (1.000).
    if re.fullmatch(r"\d+[.,]\d{3}", text):
        return None
    if not re.fullmatch(r"\d+(?:[.,]\d+)?", text):
        return None
    try:
        return Decimal(text.replace(",", "."))
    except InvalidOperation:
        return None


def candidate_rows(project_name: str, description: str) -> list[dict[str, Any]]:
    """Separate exact identities and report missing or ambiguous data."""
    result: list[dict[str, Any]] = []
    base = project_name.strip().upper()
    for block in parse_summary(description):
        values = block.fields
        issues = list(block.issues)
        pid = values.get("project_id", "").strip().upper()
        expected = f"{base}_{block.code}" if block.code else base
        if not pid and BUSINESS_ID.fullmatch(expected):
            pid = expected
        if not BUSINESS_ID.fullmatch(pid):
            issues.append("invalid_project_id")
        if block.code and pid and not pid.endswith(f"_{block.code}"):
            issues.append("scope_id_mismatch")
        if values.get("project_id") and pid.split("_", 1)[0] != base:
            issues.append("identity_mismatch")
        for key in REQUIRED:
            if not values.get(key):
                issues.append(f"missing:{key}")
        start = summary_date(values.get("start", ""))
        finish = summary_date(values.get("finish", ""))
        budget = summary_hours(values.get("budget", ""))
        if values.get("start") and start is None:
            issues.append("invalid_start")
        if values.get("finish") and finish is None:
            issues.append("invalid_finish")
        if start and finish and start > finish:
            issues.append("inverted_dates")
        if values.get("budget") and budget is None:
            issues.append("invalid_budget")
        result.append(
            {
                "azure_project": project_name,
                "project_id": pid,
                "scope": block.code or "BASE",
                "fields": values,
                "start": start.isoformat() if start else None,
                "finish": finish.isoformat() if finish else None,
                "budget": str(budget) if budget is not None else None,
                "issues": issues,
                "unknown_labels": block.unknown_labels,
                "metadata": block.metadata,
                "ready": not issues and not block.unknown_labels,
            }
        )
    counts: dict[str, int] = {}
    for row in result:
        counts[row["project_id"]] = counts.get(row["project_id"], 0) + 1
    for row in result:
        if counts[row["project_id"]] > 1:
            row["issues"].append("duplicate_project_id")
            row["ready"] = False
    return result


def financials(
    budget: Decimal | None, burn: Decimal | None
) -> dict[str, Decimal | None]:
    """Apply user rules, keeping pending hours distinct from zero."""
    if budget is None or burn is None:
        return {
            "burn": burn,
            "etc": None,
            "hours_deviation": None,
            "advance": None,
        }
    remaining = budget - burn
    return {
        "burn": burn,
        "etc": remaining,
        "hours_deviation": min(remaining, Decimal(0)),
        "advance": burn / budget * 100 if budget > 0 else None,
    }
