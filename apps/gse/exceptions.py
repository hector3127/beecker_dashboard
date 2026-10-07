"""Excepciones de GSE."""

from core.exceptions import DashboardError

"""BKD.100.002 - Errores de GSE
El frontend muestra el texto del error tal como lo escribia el Apps
Script, sin prefijos.
"""


class GseError(DashboardError):
    """Indica que no se pudo leer o calcular la informacion de GSE."""

    code = "ERR_GSE"
    public_message = "No se pudo consultar GSE."
    http_status = 409
    expose_detail = True

    def build_message(self) -> str:
        """
        Regresa el mensaje original, sin el texto publico generico.

        Returns:
            El detalle del error.
        """
        return self.detail
