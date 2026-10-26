"""Pasa los logos de cuenta de una base de datos a otra (archivo JSON)."""

import base64
import json
from pathlib import Path
from typing import Any

from django.core.management.base import (
    BaseCommand,
    CommandError,
    CommandParser,
)

from apps.portal.models import AccountLogo


class Command(BaseCommand):
    """Exporta o importa los logos; las imagenes viajan en base64."""

    help = "account_logos export|import ARCHIVO.json"

    def add_arguments(self, parser: CommandParser) -> None:
        """Define la accion y el archivo."""
        parser.add_argument("action", choices=["export", "import"])
        parser.add_argument("path", type=Path)

    def handle(self, *args: Any, **options: Any) -> None:
        """Ejecuta la accion pedida."""
        path = options["path"]
        if options["action"] == "export":
            self.export(path)
        else:
            self.load(path)

    def export(self, path: Path) -> None:
        """Guarda todos los logos de esta base."""
        rows = [
            {
                "key": row.key,
                "account": row.account,
                "image": base64.b64encode(bytes(row.image)).decode("ascii"),
            }
            for row in AccountLogo.objects.order_by("key")
        ]
        path.write_text(json.dumps(rows, ensure_ascii=False), encoding="utf-8")
        self.stdout.write(f"{len(rows)} logos exportados a {path}")

    def load(self, path: Path) -> None:
        """Crea o actualiza cada logo por su clave; no borra los demas."""
        try:
            rows = json.loads(path.read_text(encoding="utf-8"))
            created = 0
            for row in rows:
                _, new = AccountLogo.objects.update_or_create(
                    key=row["key"],
                    defaults={
                        "account": row["account"],
                        "image": base64.b64decode(row["image"], validate=True),
                    },
                )
                created += new
        except (OSError, ValueError, KeyError, TypeError) as error:
            raise CommandError(f"Archivo no válido: {error}") from error
        self.stdout.write(f"{len(rows)} logos importados ({created} nuevos)")
