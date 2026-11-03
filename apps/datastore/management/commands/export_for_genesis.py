"""Exporta tablas propias a JSONL con manifiesto para importarlas en Genesis.

Uso:
    manage.py export_for_genesis --out tmp/genesis-export --group kpi
    manage.py export_for_genesis --verify tmp/genesis-export

El destino debe estar vacío y fuera del repositorio (salvo `tmp/`, que Git
ignora): el export lleva datos reales y no se sube a ningún repositorio.
"""

import logging
from argparse import ArgumentParser
from pathlib import Path
from typing import Any

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import connection
from django.utils import timezone

from apps.datastore.services.genesis_export import (
    EXCLUDED,
    GROUPS,
    ExportError,
    export_tables,
    resolve_models,
    verify_export,
)

logger = logging.getLogger(__name__)


def _outside_repository(folder: Path) -> bool:
    base = Path(settings.BASE_DIR).resolve()
    target = folder.resolve()
    if base not in (target, *target.parents):
        return True
    return (base / "tmp") in (target, *target.parents)


class Command(BaseCommand):
    """Exporta o verifica un paquete de tablas para Genesis."""

    help = "Exporta tablas propias a JSONL con manifiesto y SHA-256."

    def add_arguments(self, parser: ArgumentParser) -> None:
        """Declara los modos: exportar, verificar o listar."""
        parser.add_argument("--out", help="Carpeta de destino, vacía.")
        parser.add_argument(
            "--group",
            action="append",
            default=[],
            help=f"Grupo de tablas: {', '.join(GROUPS)}.",
        )
        parser.add_argument(
            "--table",
            action="append",
            default=[],
            help="Tabla suelta, como datastore.Client.",
        )
        parser.add_argument(
            "--verify",
            metavar="CARPETA",
            help="Verifica un export ya hecho, sin consultar la base.",
        )
        parser.add_argument(
            "--list",
            action="store_true",
            help="Muestra los grupos y lo que no se exporta.",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        """Ejecuta el modo pedido."""
        if options["list"]:
            self._list()
            return
        if options["verify"]:
            self._verify(Path(options["verify"]))
            return
        if not options["out"]:
            raise CommandError("Indica --out, --verify o --list.")
        folder = Path(options["out"])
        if not _outside_repository(folder):
            raise CommandError(
                "El destino está dentro del repositorio: usa una carpeta "
                "fuera de él o bajo tmp/."
            )
        try:
            selected = resolve_models(options["group"], options["table"])
            manifest = export_tables(
                selected,
                folder,
                created_at=timezone.now(),
                source={
                    "engine": connection.settings_dict["ENGINE"],
                    "app": "dashboard-management",
                },
            )
        except ExportError as exc:
            raise CommandError(str(exc)) from exc
        for table in manifest["tables"]:
            logger.info(
                "genesis_export_tabla",
                extra={"tabla": table["label"], "filas": table["rows"]},
            )
            self.stdout.write(f"{table['label']}: {table['rows']} filas")
        self.stdout.write(f"Manifiesto: {folder / 'manifest.json'}")

    def _verify(self, folder: Path) -> None:
        problems = verify_export(folder)
        if problems:
            for problem in problems:
                self.stderr.write(problem)
            raise CommandError(f"{len(problems)} problemas en {folder}")
        self.stdout.write(f"Export verificado: {folder}")

    def _list(self) -> None:
        for group, labels in GROUPS.items():
            self.stdout.write(f"{group}: {', '.join(labels)}")
        for label, reason in EXCLUDED.items():
            self.stdout.write(f"No se exporta {label}: {reason}")
