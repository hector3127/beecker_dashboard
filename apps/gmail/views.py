"""Vistas del inicio de sesion con Google y de la respuesta en Gmail."""

import html
import json
import secrets
from typing import Any

from django.conf import settings
from django.core.cache import cache
from django.http import (
    HttpRequest,
    HttpResponse,
    HttpResponseRedirect,
    JsonResponse,
)
from django.urls import reverse
from django.views.decorators.http import require_GET, require_POST

from apps.gmail.constants import (
    DELIVERY_DRAFT,
    DELIVERY_SEND,
    MAX_FILE_BYTES,
    SESSION_STATE_KEY,
)
from apps.gmail.exceptions import (
    DomainNotAllowedError,
    GmailNotConfiguredError,
    ReplyValidationError,
)
from apps.gmail.services.credentials_store import (
    StoredCredentials,
    clear_credentials,
    load_credentials,
    require_credentials,
    save_credentials,
)
from apps.gmail.services.extension_reply import (
    deliver_extension,
    parse_extension,
    validate_files,
)
from apps.gmail.services.gmail_api import GmailApi
from apps.gmail.services.oauth_client import GoogleOAuth
from apps.gmail.services.thread_finder import find_threads
from apps.gmail.services.thread_memory import recall_thread, remember_thread
from core.exceptions import DashboardError

"""BKD.110.012 - Vistas de Gmail
Conectar la cuenta, listar hilos, y crear el borrador o enviar la
extension. Todas exigen la sesion del portal cuando esta activada.
"""


def _json_error(error: DashboardError) -> JsonResponse:
    """Respuesta de error con el mismo formato que el RPC."""
    return JsonResponse(
        {"ok": False, "error": error.build_message(), "code": error.code},
        status=error.http_status,
    )


def _portal_denied(request: HttpRequest) -> JsonResponse | None:
    """Respuesta 401 si el portal exige sesion y no la hay."""
    if settings.PORTAL_LOGIN_REQUIRED and not request.user.is_authenticated:
        return JsonResponse(
            {"ok": False, "error": "Inicia sesion en el portal."},
            status=401,
        )

    return None


def _oauth() -> GoogleOAuth:
    """Cliente OAuth con las credenciales del .env."""
    client_id = settings.GOOGLE_OAUTH_CLIENT_ID
    client_secret = settings.GOOGLE_OAUTH_CLIENT_SECRET

    if not client_id or not client_secret:
        raise GmailNotConfiguredError(
            "Define GOOGLE_OAUTH_CLIENT_ID y GOOGLE_OAUTH_CLIENT_SECRET "
            "en el .env.",
        )

    return GoogleOAuth(client_id, client_secret)


def _redirect_uri(request: HttpRequest) -> str:
    """Direccion de regreso registrada en Google."""
    configured = str(settings.GOOGLE_OAUTH_REDIRECT_URI)

    return configured or str(
        request.build_absolute_uri(reverse("gmail:oauth_callback")),
    )


def _check_domain(email: str) -> None:
    """Rechaza cuentas fuera de los dominios autorizados."""
    allowed = settings.GOOGLE_OAUTH_ALLOWED_DOMAINS

    if allowed and email.rsplit("@", 1)[-1] not in allowed:
        raise DomainNotAllowedError(
            "Usa tu cuenta de Beecker para generar la extension.",
        )


def _popup_page(ok: bool, message: str, origin: str) -> HttpResponse:
    """Pagina que avisa a la ventana principal y se cierra sola."""
    event = json.dumps({"type": "gmail-oauth", "ok": ok, "message": message})
    safe_event = event.replace("<", "\\u003c")
    target = json.dumps(origin).replace("<", "\\u003c")
    body = (
        "<!doctype html><meta charset='utf-8'><title>Google</title>"
        "<body style='font-family:sans-serif;padding:24px;color:#1a1c4b'>"
        f"<p>{html.escape(message)}</p><p>Puedes cerrar esta ventana.</p>"
        "<script>try{window.opener&&window.opener.postMessage("
        f"{safe_event},{target});}}catch(e){{}}"
        "try{var c=new BroadcastChannel('gmail-oauth');"
        f"c.postMessage({safe_event});c.close();}}catch(e){{}}"
        "setTimeout(function(){window.close();},400);</script>"
    )

    return HttpResponse(body)


@require_GET
def oauth_start(request: HttpRequest) -> HttpResponse:
    """
    Manda al usuario a iniciar sesion con Google.

    Args:
        request: Peticion HTTP.

    Returns:
        Redireccion a Google, o un aviso si falta configuracion.
    """
    denied = _portal_denied(request)

    if denied is not None:
        return denied

    try:
        oauth = _oauth()
    except DashboardError as error:
        return _popup_page(
            False,
            error.build_message(),
            request.build_absolute_uri("/").rstrip("/"),
        )

    state = secrets.token_urlsafe(32)
    request.session[SESSION_STATE_KEY] = state

    return HttpResponseRedirect(
        oauth.build_authorization_url(_redirect_uri(request), state),
    )


@require_GET
def oauth_callback(request: HttpRequest) -> HttpResponse:
    """
    Recibe el regreso de Google y guarda el acceso en la sesion.

    Args:
        request: Peticion HTTP con code y state.

    Returns:
        Una pagina que avisa a la ventana principal y se cierra.
    """
    origin = request.build_absolute_uri("/").rstrip("/")
    expected = request.session.pop(SESSION_STATE_KEY, "")
    received = request.GET.get("state", "")

    if request.GET.get("error"):
        return _popup_page(False, "Cancelaste el inicio de sesion.", origin)

    if not expected or not secrets.compare_digest(str(expected), received):
        return _popup_page(False, "La sesion de acceso no es valida.", origin)

    try:
        oauth = _oauth()
        token = oauth.exchange_code(
            request.GET.get("code", ""),
            _redirect_uri(request),
        )
        email = oauth.fetch_email(token.value)
        _check_domain(email)
    except DashboardError as error:
        return _popup_page(False, error.build_message(), origin)

    save_credentials(
        request.session,
        StoredCredentials(email, token.value, token.expires_at),
    )

    return _popup_page(True, f"Conectado como {email}.", origin)


@require_GET
def status(request: HttpRequest) -> JsonResponse:
    """
    Dice si hay cuenta conectada y como se entregara el correo.

    Args:
        request: Peticion HTTP.

    Returns:
        Si esta configurado, el correo conectado y el modo de entrega.
    """
    denied = _portal_denied(request)

    if denied is not None:
        return denied

    credentials = load_credentials(request.session)

    return JsonResponse(
        {
            "ok": True,
            "result": {
                "configured": bool(
                    settings.GOOGLE_OAUTH_CLIENT_ID
                    and settings.GOOGLE_OAUTH_CLIENT_SECRET,
                ),
                "connected": credentials is not None,
                "email": credentials.email if credentials else "",
                "mode": settings.GMAIL_DELIVERY_MODE,
            },
        },
    )


@require_POST
def disconnect(request: HttpRequest) -> JsonResponse:
    """
    Olvida el acceso del usuario.

    Args:
        request: Peticion HTTP.

    Returns:
        Confirmacion.
    """
    denied = _portal_denied(request)

    if denied is not None:
        return denied

    clear_credentials(request.session)

    return JsonResponse({"ok": True, "result": {}})


@require_GET
def threads(request: HttpRequest) -> JsonResponse:
    """
    Lista los hilos "Inicio de ..." detectados en el Gmail del usuario.

    Args:
        request: Peticion con project, projectName y q.

    Returns:
        Un resumen por hilo y el correo conectado.
    """
    denied = _portal_denied(request)

    if denied is not None:
        return denied

    try:
        credentials = require_credentials(request.session)
        project = request.GET.get("project", "").strip()
        found = find_threads(
            GmailApi(credentials.access_token),
            request.GET.get("projectName", "").strip(),
            request.GET.get("q", "").strip(),
            credentials.email,
            recall_thread(cache, project),
        )
    except DashboardError as error:
        return _json_error(error)

    return JsonResponse(
        {
            "ok": True,
            "result": {"email": credentials.email, "threads": found},
        },
    )


@require_POST
def reply(request: HttpRequest) -> JsonResponse:
    """
    Crea el borrador (o envia) la extension en el hilo elegido.

    Args:
        request: Peticion multipart con los campos y los archivos.

    Returns:
        Destinatarios, asunto y enlace al borrador o al hilo.
    """
    denied = _portal_denied(request)

    if denied is not None:
        return denied

    try:
        credentials = require_credentials(request.session)
        uploads = request.FILES.getlist("files")

        if any((upload.size or 0) > MAX_FILE_BYTES for upload in uploads):
            raise ReplyValidationError("Un archivo pesa mas de 10 MB.")

        files = [(upload.name or "", upload.read()) for upload in uploads]
        attachments = validate_files(files)
        data, thread_id = parse_extension(
            {key: str(value) for key, value in request.POST.items()},
            len(attachments),
        )
        result: dict[str, Any] = deliver_extension(
            GmailApi(credentials.access_token),
            credentials.email,
            data,
            thread_id,
            attachments,
            _delivery_mode(),
        )
        remember_thread(cache, data.project, thread_id)
    except DashboardError as error:
        return _json_error(error)

    return JsonResponse({"ok": True, "result": result})


def _delivery_mode() -> str:
    """Modo configurado; solo el borrador es el valor por defecto."""
    mode = settings.GMAIL_DELIVERY_MODE

    return DELIVERY_SEND if mode == DELIVERY_SEND else DELIVERY_DRAFT
