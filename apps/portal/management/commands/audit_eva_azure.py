"""Read-only audit of explicitly selected Azure Summary descriptions."""

import json
from pathlib import Path
from typing import Any

from django.core.management.base import BaseCommand, CommandError, CommandParser

from apps.azure_devops.gateway import AzureDevOpsGateway
from apps.portal.services.eva_azure_source import candidate_rows
from core.exceptions import DashboardError


class Command(BaseCommand):
    """Stage an audit artifact, never publish partially interpreted EVA data."""

    help = "Audita Summary sin Sheets, sin cambiar EVA ni escribir en Azure."

    def add_arguments(self, parser: CommandParser) -> None:
        """Select explicit projects and the local audit destination."""
        parser.add_argument("--project", action="append", required=True)
        parser.add_argument("--output", required=True)
        parser.add_argument("--input", help="JSON local proyecto: descripción.")

    def handle(self, *args: Any, **options: Any) -> None:
        """Read live Summary or replay a local sample, without publishing it."""
        samples = None
        if options.get("input"):
            try:
                samples = json.loads(
                    Path(options["input"]).read_text(encoding="utf-8")
                )
                if not isinstance(samples, dict) or not all(
                    isinstance(v, str) for v in samples.values()
                ):
                    raise ValueError(
                        "Se requiere un objeto proyecto: descripción."
                    )
            except (OSError, ValueError) as error:
                raise CommandError("Muestra JSON inválida.") from error
        try:
            client = (
                None
                if samples is not None
                else AzureDevOpsGateway().create_client()
            )
        except DashboardError as error:
            raise CommandError(error.build_message()) from error
        rows, failures = [], []
        for project in dict.fromkeys(options["project"]):
            try:
                summary = (
                    {"description": samples.get(project, "")}
                    if samples is not None
                    else client.get_project_summary(project)
                )
            except DashboardError:
                failures.append(
                    {"project": project, "error": "azure_summary_unavailable"}
                )
                continue
            rows.extend(
                candidate_rows(project, str(summary.get("description") or ""))
            )
        report = {
            "source": "azure_summary",
            "historical": False,
            "rows": rows,
            "failures": failures,
        }
        output = Path(options["output"])
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        ready = sum(row["ready"] for row in rows)
        self.stdout.write(
            f"Summary: {len(rows)} bloques; {ready} interpretados; "
            f"{len(failures)} proyectos fallidos. Informe: {output}"
        )
        if failures:
            raise CommandError(
                "Auditoría incompleta: consulta el informe; "
                "no se publicó ningún corte."
            )
