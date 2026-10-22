"""Estaticos de produccion: nombres con huella tambien en los import."""

from whitenoise.storage import (  # type: ignore[import-untyped]
    CompressedManifestStaticFilesStorage,
)

"""BKD.001.007 - Almacen de estaticos
Los modulos JS de frontend/ se importan entre si con rutas relativas
(./sections/x.js). Con esta opcion Django reescribe cada import con el nombre
con huella, igual que hace con el CSS, y el navegador nunca usa una copia
vieja de un modulo.
"""


class ModuleAwareStaticFilesStorage(
    CompressedManifestStaticFilesStorage  # type: ignore[misc]
):
    """Manifiesto con huellas que tambien alcanza a los import de JS."""

    support_js_module_import_aggregation = True
