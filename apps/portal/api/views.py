"""Vistas de la API v1 que consume el frontend."""

from django.utils import timezone
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.access.checks import resolve

"""BKD.120.012 - API v1
Las respuestas llevan {"data": ..., "meta": {...}}. Los cuerpos de error
los arma DRF ({"detail": ...}); el cliente JS los normaliza.
"""


class MeView(APIView):
    """Quien es la persona y que capacidades tiene, para armar la interfaz.

    Solo informa; ocultar algo con estos datos no protege nada: cada
    endpoint revisa sus propios permisos.
    """

    def get(self, request: Request) -> Response:
        """Usuario, capacidades, forma del alcance y si se aplican."""
        access = resolve(request)
        user = request.user
        return Response(
            {
                "data": {
                    "user": {
                        "username": user.get_username(),
                        "name": user.get_full_name(),
                    }
                    if user.is_authenticated
                    else None,
                    "capabilities": sorted(access.capabilities),
                    "scope": {"kind": access.scope.kind},
                    "enforced": access.enforced,
                },
                "meta": {"generated_at": timezone.now().isoformat()},
            }
        )


class PingView(APIView):
    """Confirma que la API responde y que la sesion es valida."""

    def get(self, request: Request) -> Response:
        """Responde ok con la hora del servidor."""
        return Response(
            {
                "data": {"status": "ok"},
                "meta": {"generated_at": timezone.now().isoformat()},
            }
        )
