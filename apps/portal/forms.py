"""Validacion de acuerdos y pendientes guardados en Django."""

from django import forms

from apps.portal.models import ExecutiveAgreement


class ExecutiveAgreementForm(forms.ModelForm):  # type: ignore[type-arg]
    """Campos editables y limites del registro ejecutivo."""

    class Meta:
        """Limita los campos que puede enviar el formulario."""

        model = ExecutiveAgreement
        fields = ["title", "kind", "owner", "due_date", "status", "notes"]
