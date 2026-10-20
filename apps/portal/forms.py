"""Validacion de acuerdos y pendientes guardados en Django."""

from django import forms

from apps.portal.models import ExecutiveAgreement


class ExecutiveAgreementForm(forms.ModelForm):
    """Campos editables y limites del registro ejecutivo."""

    meeting_source = forms.ChoiceField(
        choices=[("direction", "Dirección"), ("board", "Consejo")],
        required=False,
    )

    def clean_meeting_source(self):
        return self.cleaned_data.get("meeting_source") or "direction"

    class Meta:
        """Limita los campos que puede enviar el formulario."""

        model = ExecutiveAgreement
        fields = [
            "account",
            "meeting_source",
            "meeting_date",
            "title",
            "kind",
            "owner",
            "due_date",
            "status",
            "notes",
        ]
