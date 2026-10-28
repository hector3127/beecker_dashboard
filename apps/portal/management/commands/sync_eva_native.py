"""Extract the current EVA inventory from Azure/Clockify and measure it."""

import json
from pathlib import Path
from typing import Any

from django.core.management.base import BaseCommand, CommandError, CommandParser

from apps.datastore.services.locks import sync_lock
from apps.portal.services.eva_native_sync import extract_eva
from core.exceptions import DashboardError


class Command(BaseCommand):
    """Selected subsets never replace the full observed inventory."""

    help = "Sincroniza EVA desde Azure/Clockify, sin Sheets, y reporta tiempos."

    def add_arguments(self, parser: CommandParser) -> None:
        """Optional diagnostics subset and metrics artifact."""
        parser.add_argument("--project", action="append")
        parser.add_argument("--output")

    def handle(self, *args: Any, **options: Any) -> None:
        """Keep one extraction writer across processes."""
        with sync_lock("eva_native", 7200) as acquired:
            if not acquired:
                raise CommandError("Ya hay una extracción EVA en curso.")
            try:
                run = extract_eva(options.get("project"))
            except (DashboardError, ValueError) as error:
                raise CommandError(
                    "No se publicó EVA: " + type(error).__name__
                ) from error
        report = {
            "id": run.pk,
            "published": run.published,
            "full_inventory": run.full_inventory,
            "cut": run.cut.isoformat(),
            "metrics": run.metrics,
            "issues": run.issues,
        }
        if options.get("output"):
            target = Path(options["output"])
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(
                json.dumps(report, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        self.stdout.write(json.dumps(report, ensure_ascii=False, indent=2))
        if not run.published:
            raise CommandError(
                "Extracción incompleta. Se conserva el corte anterior."
            )
