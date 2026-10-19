"""Configuracion de la app datastore."""

from django.apps import AppConfig

"""BKD.130.001 - App datastore
Base diaria con los datos de las fuentes externas (Clockify, Sheets y
Azure) para que las pantallas no las consulten al navegar.
"""


class DatastoreConfig(AppConfig):
    """Base diaria de datos del panel."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.datastore"
