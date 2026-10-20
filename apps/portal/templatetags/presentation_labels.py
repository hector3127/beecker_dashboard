"""Spanish presentation labels without altering source keys or filters."""

import re
from django import template

register = template.Library()


@register.filter
def commercial_stage(value):
    original = str(value or "")
    clean = re.sub(r"\s*\(Pipeline\)\s*$", "", original, flags=re.I).strip()
    labels = {
        "closed won": "Ganada",
        "closed won: pending docs": "Ganada · documentación pendiente",
        "closed lost": "Perdida",
        "proposal sent": "Propuesta enviada",
        "discovery": "Diagnóstico",
        "intent": "Intención",
        "negotiation": "Negociación",
        "contract sent": "Contrato enviado",
        "qualified": "Calificada",
        "appointment scheduled": "Reunión programada",
    }
    return labels.get(clean.casefold(), clean)
