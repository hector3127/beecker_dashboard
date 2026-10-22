"""Alcance de datos: sobre que cuentas y proyectos puede actuar una persona."""

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import Literal, TypeVar

from core.utils.text import normalize_name

"""BKD.140.004 - Alcance de datos
Tiene dos formas: todo el portafolio, o una lista de cuentas y proyectos.
Los proyectos "propios" de una persona llegan ya resueltos en la lista de
proyectos. Las cuentas se comparan sin acentos ni mayusculas y los
proyectos sin mayusculas, como en el resto del portal.
"""

T = TypeVar("T")


def account_key(name: object) -> str:
    """Clave comparable de una cuenta."""
    return normalize_name(str(name or ""))


def project_key(project_id: object) -> str:
    """Clave comparable de un proyecto."""
    return str(project_id or "").strip().casefold()


@dataclass(frozen=True)
class AccessScope:
    """Cuentas y proyectos permitidos; unrestricted=True permite todo."""

    unrestricted: bool = False
    accounts: frozenset[str] = frozenset()
    projects: frozenset[str] = frozenset()

    @classmethod
    def everything(cls) -> "AccessScope":
        """Todo el portafolio."""
        return cls(unrestricted=True)

    @classmethod
    def limited(
        cls,
        accounts: Iterable[str] = (),
        projects: Iterable[str] = (),
    ) -> "AccessScope":
        """Solo las cuentas y los proyectos indicados (puede ser ninguno)."""
        # Una clave vacía nunca se guarda: un dato en blanco no concede nada.
        return cls(
            accounts=frozenset(filter(None, map(account_key, accounts))),
            projects=frozenset(filter(None, map(project_key, projects))),
        )

    @property
    def kind(self) -> Literal["all", "limited"]:
        """Forma del alcance, para mostrarla sin revelar la lista."""
        return "all" if self.unrestricted else "limited"

    def allows_account(self, name: object) -> bool:
        """Una cuenta se ve completa solo si esta en la lista de cuentas."""
        return self.unrestricted or account_key(name) in self.accounts

    def allows_project(
        self, project_id: object, account: object = None
    ) -> bool:
        """Un proyecto se ve si esta listado o si su cuenta esta permitida."""
        if self.unrestricted or project_key(project_id) in self.projects:
            return True
        return account is not None and account_key(account) in self.accounts

    def filter_accounts(self, names: Iterable[str]) -> list[str]:
        """Las cuentas permitidas, en el mismo orden."""
        return [name for name in names if self.allows_account(name)]

    def filter_projects(
        self,
        items: Iterable[T],
        project_id: Callable[[T], object],
        account: Callable[[T], object] | None = None,
    ) -> list[T]:
        """Los proyectos permitidos, en el mismo orden."""
        return [
            item
            for item in items
            if self.allows_project(
                project_id(item), account(item) if account else None
            )
        ]
