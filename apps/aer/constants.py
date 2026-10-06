"""Hojas y columnas del dashboard AER / T&M."""

from typing import Final

"""BKD.080.002 - Constantes AER
Hojas manuales y encabezados de AER_MANUAL_SHEETS y
_aertymEnsureManualSheets() de AERTYMProyectoService.gs.
"""

SHEET_PLAN: Final[str] = "AER_Planeacion"
SHEET_RISKS: Final[str] = "AER_Riesgos"
SHEET_ACTIONS: Final[str] = "AER_Acciones"
SHEET_VACATIONS: Final[str] = "AER_Vacaciones"
SHEET_EVALUATIONS: Final[str] = "AER_Evaluaciones"
SHEET_CONTACTS: Final[str] = "AER_Contactos"
SHEET_CLIENT_INFO: Final[str] = "AER_ClienteInfo"
SHEET_GOVERNANCE: Final[str] = "AER_ClienteGobierno"
SHEET_DOCUMENTS: Final[str] = "AER_ClienteDocs"

MANUAL_SHEETS: Final[dict[str, tuple[str, ...]]] = {
    SHEET_PLAN: (
        "UID",
        "ID_Proyecto",
        "Tipo",
        "Actividad",
        "Responsable",
        "Inicio_Plan",
        "Fin_Plan",
        "Inicio_Real",
        "Fin_Real",
        "Avance",
        "Estado",
        "Dependencia",
        "Estado_Dependencia",
        "Notas",
        "Orden",
        "Actualizado",
    ),
    SHEET_RISKS: (
        "UID",
        "ID_Proyecto",
        "Riesgo",
        "Impacto",
        "Probabilidad",
        "Responsable",
        "Fecha_Limite",
        "Accion",
        "Estado",
        "Notas",
        "Actualizado",
    ),
    SHEET_ACTIONS: (
        "UID",
        "ID_Proyecto",
        "Accion",
        "Responsable",
        "Fecha_Inicio",
        "Fecha_Limite",
        "Fecha_Real",
        "Estado",
        "Dependencia",
        "Prioridad",
        "Riesgo_UID",
        "Notas",
        "Actualizado",
    ),
    SHEET_VACATIONS: (
        "UID",
        "ID_Proyecto",
        "Recurso",
        "Inicio",
        "Fin",
        "Estado",
        "Comentarios",
        "Registrado_Por",
        "Fecha_Registro",
        "Actualizado",
    ),
    SHEET_EVALUATIONS: (
        "UID",
        "ID_Proyecto",
        "Recurso",
        "Fecha_Evaluacion",
        "Periodo",
        "Evaluador",
        "Score",
        "Calidad",
        "Cumplimiento",
        "Comunicacion",
        "Colaboracion",
        "Autonomia",
        "Categoria",
        "Comentario",
        "Plan_Accion",
        "Proxima_Evaluacion",
        "Actualizado",
    ),
    SHEET_CONTACTS: (
        "UID",
        "ID_Proyecto",
        "Nombre",
        "Cargo",
        "Rol",
        "Area",
        "Correo",
        "Telefono",
        "Nivel_Decision",
        "Estado",
        "Es_Decisor",
        "Canal",
        "Alcance",
        "Requerimientos",
        "Aprueba",
        "Valida",
        "Decide",
        "Informado",
        "Notas",
        "Actualizado",
    ),
    SHEET_CLIENT_INFO: (
        "UID",
        "ID_Proyecto",
        "Area_Principal",
        "Sponsor",
        "Product_Owner",
        "Correo_Distribucion",
        "Ruta_Escalamiento",
        "Canales",
        "Proxima_Reunion",
        "Tipo_Reunion",
        "Actualizado",
    ),
    SHEET_GOVERNANCE: (
        "UID",
        "ID_Proyecto",
        "Reunion",
        "Frecuencia",
        "Participantes",
        "Canal",
        "Notas",
        "Actualizado",
    ),
    SHEET_DOCUMENTS: (
        "UID",
        "ID_Proyecto",
        "Nombre",
        "Tipo",
        "URL",
        "Accion",
        "Notas",
        "Actualizado",
    ),
}

# Columnas que se guardan como fecha YYYY-MM-DD (_aertymUpsertManual).
DATE_COLUMNS: Final[frozenset[str]] = frozenset(
    {
        "Inicio_Plan",
        "Fin_Plan",
        "Inicio_Real",
        "Fin_Real",
        "Fecha_Inicio",
        "Fecha_Limite",
        "Fecha_Real",
        "Inicio",
        "Fin",
        "Fecha_Registro",
        "Fecha_Evaluacion",
        "Proxima_Evaluacion",
    },
)

# Columnas que Sheets convierte en fecha al guardarlas (se leen como
# numero de serie y se convierten a fecha al leerlas).
SHEET_DATE_COLUMNS: Final[frozenset[str]] = DATE_COLUMNS | {
    "Actualizado",
    "Proxima_Reunion",
}

MAX_EFFORT: Final[int] = 6
WORK_START_HOUR: Final[int] = 8
WORK_END_HOUR: Final[int] = 18
DETAIL_LIMIT: Final[int] = 80
RANGE_DETAIL_LIMIT: Final[int] = 500
BACKEND_VERSION: Final[str] = "AER_DASHBOARD_V8_CLIENTE_CONTACTOS"
