"""El almacen de produccion pone huella tambien a los import entre modulos."""

import re

from django.core.management import call_command


def test_relative_imports_between_modules_get_the_hashed_name(
    settings, tmp_path
):
    settings.STATIC_ROOT = tmp_path
    settings.STORAGES = {
        **settings.STORAGES,
        "staticfiles": {
            "BACKEND": "core.storage.ModuleAwareStaticFilesStorage"
        },
    }

    call_command(
        "collectstatic",
        interactive=False,
        verbosity=0,
        ignore_patterns=["admin", "rest_framework", "portal", "core"],
    )

    for name, section in (("executive", "metrics"), ("operativa", "metrics")):
        page = tmp_path / "app/scripts/pages" / name
        main = next(page.glob("main.*.js")).read_text("utf-8")
        # Django reescribe el import: comillas dobles y huella en el nombre.
        pattern = rf'from "\./sections/{section}\.[0-9a-f]{{12}}\.js";'
        assert re.search(pattern, main), name
        # Los nombres estables del importmap no se tocan: el HTML los traduce.
        assert "from '#app/data/api-client.js'" in main
        assert list((page / "sections").glob(f"{section}.*.js"))
