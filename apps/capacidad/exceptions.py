"""Excepciones de Capacidad instalada."""

from core.exceptions import DashboardError

"""BKD.050.002 - Errores de Capacidad instalada
El frontend muestra el texto del error tal como lo escribia el Apps
Script, sin prefijos.
"""


class CapacityError(DashboardError):
    """Indica que no se pudo calcular la capacidad de un mes o proyecto."""

    code = "ERR_CAPACITY"
    public_message = "No se pudo calcular la capacidad instalada."
    http_status = 409
    expose_detail = True

    def build_message(self) -> str:
        """
        Regresa el mensaje original, sin el texto publico generico.

        Returns:
            El detalle del error.
        """
        return self.detail
