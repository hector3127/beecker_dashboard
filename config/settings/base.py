"""Configuracion comun a todos los entornos del dashboard Beecker.

Las credenciales que en Apps Script vivian en PropertiesService se leen
de variables de entorno cargadas desde el archivo .env.
"""

import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

"""BKD.001.001 - Configuracion del proyecto
Centraliza rutas, aplicaciones, cache y credenciales externas.
"""

BASE_DIR = Path(__file__).resolve().parent.parent.parent

load_dotenv(
    dotenv_path=BASE_DIR / ".env",
    override=False,
)


def read_required_env(name: str) -> str:
    """
    Lee una variable de entorno obligatoria.

    Args:
        name: Nombre de la variable de entorno.

    Returns:
        El valor de la variable sin espacios alrededor.

    Raises:
        ImproperlyConfigured: Cuando la variable no existe o esta vacia.
    """
    value = os.getenv(name, "").strip()

    if not value:
        raise ImproperlyConfigured(
            f"La variable de entorno {name} debe estar configurada.",
        )

    return value


def read_int_env(name: str, default: int) -> int:
    """
    Lee una variable de entorno entera y positiva.

    Args:
        name: Nombre de la variable de entorno.
        default: Valor usado cuando la variable no existe.

    Returns:
        El valor entero configurado.

    Raises:
        ImproperlyConfigured: Cuando el valor no es un entero positivo.
    """
    raw_value = os.getenv(name, str(default)).strip()

    try:
        value = int(raw_value)
    except ValueError as error:
        raise ImproperlyConfigured(
            f"La variable {name} debe ser un numero entero.",
        ) from error

    if value <= 0:
        raise ImproperlyConfigured(
            f"La variable {name} debe ser mayor que cero.",
        )

    return value


SECRET_KEY = read_required_env("DJANGO_SECRET_KEY")

DEBUG = False

ALLOWED_HOSTS = [
    host.strip()
    for host in os.getenv(
        "DJANGO_ALLOWED_HOSTS",
        "127.0.0.1,localhost",
    ).split(",")
    if host.strip()
]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "core.apps.CoreConfig",
    "apps.dashboard.apps.DashboardConfig",
    "apps.clockify.apps.ClockifyConfig",
    "apps.azure_devops.apps.AzureDevopsConfig",
    "apps.ejecutivo.apps.EjecutivoConfig",
    "apps.capacidad.apps.CapacidadConfig",
    "apps.minutas.apps.MinutasConfig",
    "apps.daily.apps.DailyConfig",
    "apps.aer.apps.AerConfig",
    "apps.recursos.apps.RecursosConfig",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# Los datos de negocio viven en Google Sheets. SQLite solo guarda
# sesiones y usuarios de Django.
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    },
}

# Reemplaza a CacheService. Se usa cache en archivos para que los
# workers de gunicorn compartan el mismo contenido.
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.filebased.FileBasedCache",
        "LOCATION": BASE_DIR / ".cache",
    },
}

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "UserAttributeSimilarityValidator"
        ),
    },
    {
        "NAME": (
            "django.contrib.auth.password_validation.MinimumLengthValidator"
        ),
    },
]

LANGUAGE_CODE = "es-mx"

# Misma zona horaria que appsscript.json.
TIME_ZONE = "America/Mexico_City"

USE_I18N = True

USE_TZ = True

STATIC_URL = "static/"

STATIC_ROOT = BASE_DIR / "staticfiles"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
    "DEFAULT_PARSER_CLASSES": [
        "rest_framework.parsers.JSONParser",
    ],
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
}

# El panel y la API exigen sesion iniciada fuera de desarrollo local,
# como el acceso DOMAIN de la Web App original.
PORTAL_LOGIN_REQUIRED = True

LOGIN_URL = "admin:login"

# Google Sheets: sustituye a SpreadsheetApp.getActiveSpreadsheet().
GOOGLE_SPREADSHEET_ID = os.getenv("GOOGLE_SPREADSHEET_ID", "").strip()

# Una ruta relativa se toma desde la carpeta del proyecto, para que
# funcione aunque el comando se ejecute desde otra carpeta (por ejemplo
# una tarea programada).
GOOGLE_CREDENTIALS_FILE = str(
    BASE_DIR / os.getenv("GOOGLE_CREDENTIALS_FILE", "key.json").strip(),
)

# Carpeta de Drive con las notas de Gemini (CARPETA_MINUTAS_ID). Debe
# compartirse con el correo de la cuenta de servicio.
GOOGLE_MINUTES_FOLDER_ID = os.getenv("GOOGLE_MINUTES_FOLDER_ID", "").strip()

TIME_ENTRY_SOURCE = os.getenv("TIME_ENTRY_SOURCE", "clockify").strip()

DASHBOARD_CACHE_TTL_SECONDS = read_int_env(
    "DASHBOARD_CACHE_TTL_SECONDS",
    360,
)

# Segundos que se reutiliza una hoja leida de Sheets entre peticiones.
# Las escrituras de la app la invalidan; los cambios manuales en el
# Spreadsheet se ven al vencer. 0 apaga la cache.
SHEETS_READ_CACHE_SECONDS = read_int_env("SHEETS_READ_CACHE_SECONDS", 900)

# Credenciales de integraciones que se migran en fases siguientes.
CLOCKIFY_API_KEY = os.getenv("CLOCKIFY_API_KEY", "").strip()

CLOCKIFY_WORKSPACE_ID = os.getenv("CLOCKIFY_WORKSPACE_ID", "").strip()

AZURE_DEVOPS_ORGANIZATION = os.getenv(
    "AZURE_DEVOPS_ORGANIZATION",
    "",
).strip()

AZURE_DEVOPS_PAT = os.getenv("AZURE_DEVOPS_PAT", "").strip()
# Team Project inicial del panel Daily (AZURE_DEVOPS_PROJECT del original);
# el selector del panel lo cambia sin tocar el .env.
AZURE_DEVOPS_PROJECT = os.getenv("AZURE_DEVOPS_PROJECT", "").strip()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "").strip()

CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "").strip()

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
}
