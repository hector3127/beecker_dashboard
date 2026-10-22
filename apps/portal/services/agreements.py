"""Acuerdos y pendientes: reglas que comparten la API y la vista actual."""

from collections.abc import Mapping
from typing import Any

from django.db.models import Field

from apps.access.checks import Access
from apps.access.scope import AccessScope
from apps.portal.forms import ExecutiveAgreementForm
from apps.portal.models import ExecutiveAgreement
from core.utils.text import normalize_name

"""BKD.120.028 - Acuerdos ejecutivos
Quien ve o cambia un acuerdo se decide aqui, con la capacidad y el alcance
de la persona; ni la API ni la vista lo deciden por su cuenta. Un acuerdo
fuera del alcance se trata como si no existiera.
"""

STATUSES = frozenset({"open", "progress", "done"})
READ_CAPABILITIES = ("view_agreements", "edit_agreements")
WRITE_CAPABILITIES = ("edit_agreements",)
COLUMNS = (
    "id",
    "account",
    "meeting_source",
    "meeting_date",
    "title",
    "kind",
    "owner",
    "due_date",
    "status",
    "notes",
    "updated_at",
)
EDITABLE = (
    "account",
    "meeting_source",
    "meeting_date",
    "title",
    "kind",
    "owner",
    "due_date",
    "status",
    "notes",
)


class OutOfScopeError(Exception):
    """La cuenta del acuerdo no esta dentro del alcance de la persona."""


class InvalidAgreementError(Exception):
    """Los datos no cumplen las reglas del formulario."""

    def __init__(self, errors: dict[str, Any]) -> None:
        super().__init__("Revisa los campos del acuerdo.")
        self.errors = errors


class InvalidStatusError(Exception):
    """El estado pedido no existe."""


def agreement_account_key(name: str) -> str:
    """Match the account aliases used by the imported account view."""
    normalized = normalize_name(name)
    return {
        "heineken mexico": "heineken",
        "cadena comercial oxxo": "oxxo",
        "cadena comercial oxxo.": "oxxo",
    }.get(normalized, normalized)


def may(access: Access, *, write: bool) -> bool:
    """Si la persona puede cambiar (write) o solo consultar los acuerdos."""
    needed = WRITE_CAPABILITIES if write else READ_CAPABILITIES
    return any(access.can(code) for code in needed)


def in_scope(scope: AccessScope, account: str) -> bool:
    """Un acuerdo sin cuenta solo lo ve quien tiene todo el portafolio."""
    if scope.unrestricted:
        return True
    key = agreement_account_key(account)
    return bool(key) and key in {
        agreement_account_key(allowed) for allowed in scope.accounts
    }


def visible_agreements(
    scope: AccessScope, account: str = "", pending_only: bool = False
) -> list[dict[str, Any]]:
    """Acuerdos del alcance, opcionalmente de una cuenta o sin completar."""
    rows = [
        row
        for row in ExecutiveAgreement.objects.values(*COLUMNS)
        if in_scope(scope, row["account"])
    ]
    if account:
        wanted = agreement_account_key(account)
        rows = [
            row
            for row in rows
            if agreement_account_key(row["account"]) == wanted
        ]
    if pending_only:
        rows = [row for row in rows if row["status"] != "done"]
    return rows


def agreement_row(pk: int) -> dict[str, Any]:
    """El registro tal como se lista, para devolverlo despues de guardarlo."""
    return dict(ExecutiveAgreement.objects.values(*COLUMNS).get(pk=pk))


def find_agreement(scope: AccessScope, pk: Any) -> ExecutiveAgreement | None:
    """El acuerdo si existe y esta en el alcance; si no, None."""
    try:
        agreement = ExecutiveAgreement.objects.get(pk=int(pk))
    except (ValueError, TypeError, ExecutiveAgreement.DoesNotExist):
        return None
    return agreement if in_scope(scope, agreement.account) else None


def save_agreement(
    scope: AccessScope,
    values: Mapping[str, Any],
    instance: ExecutiveAgreement | None = None,
) -> ExecutiveAgreement:
    """Crea o edita un acuerdo; la cuenta final tambien debe estar permitida."""
    form = ExecutiveAgreementForm(values, instance=instance)
    if not form.is_valid():
        raise InvalidAgreementError(form.errors.get_json_data())
    if not in_scope(scope, form.cleaned_data["account"]):
        raise OutOfScopeError
    saved: ExecutiveAgreement = form.save()
    return saved


def change_status(agreement: ExecutiveAgreement, status: str) -> None:
    """Cambia solo el estado, sin tocar el resto del registro."""
    if status not in STATUSES:
        raise InvalidStatusError
    agreement.status = status
    agreement.save(update_fields=["status", "updated_at"])


def with_defaults(values: Mapping[str, Any]) -> dict[str, Any]:
    """Completa con los valores por defecto del modelo lo que no se envio."""
    completed = dict(values)
    for name in EDITABLE:
        field = ExecutiveAgreement._meta.get_field(name)
        if (
            name not in completed
            and isinstance(field, Field)
            and field.has_default()
        ):
            completed[name] = field.get_default()
    return completed


def current_values(agreement: ExecutiveAgreement) -> dict[str, Any]:
    """Valores editables como texto, para completar una edicion parcial."""
    values: dict[str, Any] = {}
    for name in EDITABLE:
        value = getattr(agreement, name)
        values[name] = (
            value.isoformat() if hasattr(value, "isoformat") else value
        )
    return values
