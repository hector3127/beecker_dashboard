"""Correcciones mensuales de capacidad; conserva las horas Clockify."""

from datetime import date
from typing import Any

from apps.gse.services.cells import norm
from apps.portal.services.holidays import count_business_days

# Correcciones de personas confirmadas por Héctor, 11/11/2026.
PERMANENT = {
    norm("Claudia Ximena Mazon Vera"): {"capacidad_horas": 0},
    norm("Enrique Yael Badillo Gutierrez"): {"capacidad_horas": 0},
    norm("Luis Enrique Garcia Rivera"): {"capacidad_horas": 0},
    norm("Jhoan Ahumada Rivera"): {"rol": "DEV"},
    norm("Johan Ortiz Hernandez"): {"rol": "DEV"},
}

# Importes de agosto confirmados por Héctor, 11/11/2026.
AUGUST = {
    norm("Diego Ovadid Acevedo Cruz"): {"capacidad_horas": 0},
    norm("Heidy Cabieles Martinez"): {"capacidad_horas": 0},
    norm("Alfredo Miranda Alvarez"): {"capacidad_horas": 168},
    norm("Alvaro Andres Quintero Diaz"): {"capacidad_horas": 152},
    norm("Daniel Leon Pineda"): {"capacidad_horas": 152},
    norm("Nicolas Alejandro Espitia Delgado"): {"capacidad_horas": 152},
    norm("Sofia Katherin Jojoa Unigarro"): {"capacidad_horas": 160},
}

# Importes y ausencias confirmados únicamente para septiembre.
SEPTEMBER = {
    norm("Alvaro Andres Quintero Diaz"): {"capacidad_horas": 80},
    norm("Diego Ovadid Acevedo Cruz"): {"capacidad_horas": 0},
    norm("Heidy Cabieles Martinez"): {"capacidad_horas": 0},
    norm("Lidio Gonzalez Gabriel"): {"capacidad_horas": 96},
    norm("Miguel Angel Reyes Gonzalez"): {"capacidad_horas": 96},
}


OCTOBER = {
    norm("Jhoan Ahumada Rivera"): {
        "capacidad_horas": count_business_days("2026-10", date(2026, 10, 19))
        * 8,
    },
    norm("Nicolas Alejandro Espitia Delgado"): {"capacidad_horas": 168},
    norm("Sofia Katherin Jojoa Unigarro"): {"capacidad_horas": 168},
    norm("Heidy Cabieles Martinez"): {"capacidad_horas": 0},
    norm("Diego Ovadid Acevedo Cruz"): {"capacidad_horas": 0},
}


def apply_capacity_adjustments(
    people: list[dict[str, Any]], month: str
) -> list[dict[str, Any]]:
    """Combina exclusiones permanentes y ajustes del mes, sobre Bandas/rol."""
    adjustments = {
        "2026-08": AUGUST,
        "2026-09": SEPTEMBER,
        "2026-10": OCTOBER,
    }.get(month, {})
    permanent = {
        name: value
        for name, value in PERMANENT.items()
        if month != "2026-10" or name != norm("Enrique Yael Badillo Gutierrez")
    }
    return [
        {
            **person,
            **permanent.get(norm(person["nombre"]), {}),
            **adjustments.get(norm(person["nombre"]), {}),
        }
        for person in people
    ]
