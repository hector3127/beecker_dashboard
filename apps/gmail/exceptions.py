"""Errores de la integracion con Gmail."""

from core.exceptions import DashboardError

"""BKD.110.003 - Errores de Gmail
Mensajes que ve el usuario cuando falla el inicio de sesion o Gmail.
"""


class GmailNotConfiguredError(DashboardError):
    """Falta el cliente OAuth en el .env."""

    code = "ERR_GMAIL_NOT_CONFIGURED"
    public_message = "Falta configurar el inicio de sesion con Google."
    http_status = 409
    expose_detail = True


class GmailNotConnectedError(DashboardError):
    """El usuario no ha conectado su cuenta o el acceso vencio."""

    code = "ERR_GMAIL_NOT_CONNECTED"
    public_message = "Conecta tu cuenta de Google para continuar."
    http_status = 401


class GmailAuthError(DashboardError):
    """Google rechazo el inicio de sesion."""

    code = "ERR_GMAIL_AUTH"
    public_message = "No se pudo iniciar sesion con Google."
    http_status = 400


class DomainNotAllowedError(DashboardError):
    """La cuenta no pertenece a un dominio autorizado."""

    code = "ERR_GMAIL_DOMAIN"
    public_message = "Esa cuenta de Google no esta autorizada."
    http_status = 403
    expose_detail = True


class GmailApiError(DashboardError):
    """Gmail respondio con un error."""

    code = "ERR_GMAIL_API"
    public_message = "No se pudo consultar Gmail."
    http_status = 502
    expose_detail = True


class ReplyValidationError(DashboardError):
    """Los datos del comunicado no son validos."""

    code = "ERR_GMAIL_REPLY_INVALID"
    public_message = "El comunicado tiene datos invalidos."
    http_status = 400
    expose_detail = True
