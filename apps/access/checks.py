"""Preguntas de acceso para vistas y API: decoradores y permiso de DRF."""

from collections.abc import Callable
from dataclasses import dataclass
from functools import wraps
from typing import Any

from django.conf import settings
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from rest_framework.permissions import SAFE_METHODS, BasePermission

from apps.access.capabilities import CODES
from apps.access.providers import get_provider
from apps.access.scope import AccessScope

"""BKD.140.006 - Verificaciones de acceso
Con ACCESS_ENFORCED apagado todas las personas pueden todo y ven todo, como
antes de existir esta app. Encendido, se aplican las capacidades y el alcance
del proveedor. Ocultar un elemento en el frontend no sustituye estas
verificaciones: la API y las vistas las hacen siempre.
"""


@dataclass(frozen=True)
class Access:
    """Lo que la persona de una peticion puede hacer y sobre que datos."""

    capabilities: frozenset[str]
    scope: AccessScope
    enforced: bool

    def can(self, code: str) -> bool:
        """Si puede ejercer la capacidad."""
        return code in self.capabilities


def resolve(request: Any) -> Access:
    """Accesos de la peticion; se calculan una vez por peticion."""
    cached: Access | None = getattr(request, "_access", None)
    if cached is not None:
        return cached
    if settings.ACCESS_ENFORCED:
        provider = get_provider()
        user = request.user
        access = Access(
            provider.capabilities(user), provider.scope(user), enforced=True
        )
    else:
        access = Access(CODES, AccessScope.everything(), enforced=False)
    request._access = access
    return access


def scope_for(request: Any) -> AccessScope:
    """Alcance de datos de la peticion; los selectores lo reciben."""
    return resolve(request).scope


def trust(request: Any) -> Any:
    """Marca una peticion interna (calentamiento de cache) con acceso total."""
    request._access = Access(CODES, AccessScope.everything(), enforced=False)
    return request


def require_capability(
    code: str, *, whole_portfolio: bool = False
) -> Callable[[Callable[..., HttpResponse]], Callable[..., HttpResponse]]:
    """Protege una vista: sin sesion va al login; sin la capacidad, 403.

    Con whole_portfolio la pantalla muestra cifras de todo el portafolio o del
    equipo completo, que no se pueden recortar por cuenta: con alcance
    limitado tambien responde 403.
    """

    def decorator(
        view: Callable[..., HttpResponse],
    ) -> Callable[..., HttpResponse]:
        @wraps(view)
        def wrapper(request: Any, *args: Any, **kwargs: Any) -> HttpResponse:
            access = resolve(request)
            if access.enforced:
                if not request.user.is_authenticated:
                    return redirect_to_login(request.get_full_path())
                if not access.can(code):
                    raise PermissionDenied
                if whole_portfolio and not access.scope.unrestricted:
                    raise PermissionDenied
            return view(request, *args, **kwargs)

        return wrapper

    return decorator


def capability_permission(code: str) -> type[BasePermission]:
    """Permiso de DRF para una capacidad; combinalo con IsAuthenticated."""

    class HasCapability(BasePermission):
        message = "No tienes acceso a esta información."

        def has_permission(self, request: Any, view: Any) -> bool:
            access = resolve(request)
            if not access.enforced:
                return True
            return bool(request.user.is_authenticated and access.can(code))

    HasCapability.__name__ = f"Has_{code}"
    return HasCapability


def capability_by_method(
    read: tuple[str, ...], write: tuple[str, ...]
) -> type[BasePermission]:
    """Permiso de DRF por metodo: `read` para leer y `write` para cambiar."""

    class ByMethod(BasePermission):
        message = "No tienes acceso a esta información."

        def has_permission(self, request: Any, view: Any) -> bool:
            access = resolve(request)
            if not access.enforced:
                return True
            needed = read if request.method in SAFE_METHODS else write
            return bool(
                request.user.is_authenticated
                and any(access.can(code) for code in needed)
            )

    return ByMethod
