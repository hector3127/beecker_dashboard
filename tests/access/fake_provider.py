"""Proveedor de pruebas: capacidades y alcance segun el nombre de usuario."""

from typing import Any

from apps.access.scope import AccessScope


class DictProvider:
    """Cada prueba llena GRANTS con {usuario: (capacidades, alcance)}."""

    GRANTS: dict[str, tuple[frozenset[str], AccessScope]] = {}

    def capabilities(self, user: Any) -> frozenset[str]:
        """Capacidades del usuario; ninguna si no esta en GRANTS."""
        return self.GRANTS.get(user.get_username(), (frozenset(), None))[0]

    def scope(self, user: Any) -> AccessScope:
        """Alcance del usuario; vacio si no esta en GRANTS."""
        found = self.GRANTS.get(user.get_username())
        return found[1] if found else AccessScope.limited()
