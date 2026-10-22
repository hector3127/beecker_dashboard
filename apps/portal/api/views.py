"""Vistas de la API v1 que consume el frontend."""

from django.utils import timezone
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

"""BKD.120.012 - API v1
Las respuestas llevan {"data": ..., "meta": {...}}. Los cuerpos de error
los arma DRF ({"detail": ...}); el cliente JS los normaliza.
"""


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
