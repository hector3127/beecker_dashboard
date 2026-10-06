"""Excepciones base compartidas por todas las apps del dashboard."""

"""BKD.002.001 - Manejo de errores
Define errores con codigo, mensaje publico y estatus HTTP para que la
API responda de forma uniforme.
"""


class DashboardError(Exception):
    """Excepcion base de todo el proyecto."""

    code = "ERR_DASHBOARD"
    public_message = "Ocurrio un error en el dashboard."
    http_status = 500

    # Indica si el detalle tecnico puede mostrarse al usuario. Solo se
    # activa cuando ese detalle le permite corregir el problema.
    expose_detail = False

    def __init__(self, detail: str = "") -> None:
        super().__init__(detail or self.public_message)

        self.detail = detail or self.public_message

    def build_message(self) -> str:
        """
        Construye el mensaje que se envia al frontend.

        Returns:
            El mensaje publico, con el detalle cuando es seguro mostrarlo.
        """
        if self.expose_detail and self.detail != self.public_message:
            return f"{self.public_message} {self.detail}"

        return self.public_message


class ConfigurationError(DashboardError):
    """Indica que falta una variable de configuracion obligatoria."""

    code = "ERR_CONFIGURATION"
    public_message = "Falta configurar el dashboard."
    http_status = 409
    expose_detail = True


class InvalidRequestError(DashboardError):
    """Indica que el frontend envio parametros invalidos."""

    code = "ERR_INVALID_REQUEST"
    public_message = "La solicitud no es valida."
    http_status = 400
    expose_detail = True


class SheetsError(DashboardError):
    """Excepcion base de las fallas con Google Sheets."""

    code = "ERR_SHEETS"
    public_message = "No se pudo consultar Google Sheets."
    http_status = 502


class SheetAuthenticationError(SheetsError):
    """Indica que la cuenta de servicio no pudo autenticarse."""

    code = "ERR_SHEETS_AUTH"
    public_message = "No se pudo autenticar con Google Sheets."
    http_status = 401
    expose_detail = True


class SheetNotFoundError(SheetsError):
    """Indica que la hoja solicitada no existe en el Spreadsheet."""

    code = "ERR_SHEET_NOT_FOUND"
    public_message = "No se encontro la hoja solicitada."
    http_status = 404
    expose_detail = True


class SpreadsheetNotFoundError(SheetsError):
    """Indica que el Spreadsheet configurado no existe o no es visible."""

    code = "ERR_SPREADSHEET_NOT_FOUND"
    public_message = "No se encontro el Spreadsheet configurado."
    http_status = 409
    expose_detail = True


class SheetColumnNotFoundError(SheetsError):
    """Indica que la columna llave no existe en los encabezados."""

    code = "ERR_SHEET_COLUMN"
    public_message = "No se encontro la columna solicitada."
    http_status = 409
    expose_detail = True


class TimeEntrySourceError(DashboardError):
    """Indica que no se pudieron obtener los registros de tiempo."""

    code = "ERR_TIME_ENTRIES"
    public_message = "No se pudieron obtener las horas registradas."
    http_status = 502
    expose_detail = True


def describe_error(error: DashboardError) -> str:
    """
    Obtiene el texto del error para el frontend.

    El Apps Script mostraba e.message tal cual; aqui se usa el detalle
    cuando es seguro mostrarlo y el mensaje publico en otro caso.

    Args:
        error: Error controlado.

    Returns:
        El detalle si puede mostrarse; si no, el mensaje publico.
    """
    if error.expose_detail:
        return error.detail

    return error.build_message()
