"""Ajustes compartidos: las pruebas no dependen del .env del equipo."""

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from pytest_django.fixtures import SettingsWrapper


@pytest.fixture(autouse=True)
def _stores_off_by_default(settings: "SettingsWrapper") -> None:
    """Apaga la lectura desde la base salvo que la prueba la encienda."""
    settings.CLOCKIFY_STORE_ENABLED = False
    settings.SHEETS_STORE_ENABLED = False
    settings.AZURE_STORE_ENABLED = False


@pytest.fixture(autouse=True)
def _access_not_enforced_by_default(settings: "SettingsWrapper") -> None:
    """El .env del equipo no enciende los accesos en las pruebas."""
    settings.ACCESS_ENFORCED = False
