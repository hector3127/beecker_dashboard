"""Original definitions for explicit incremental model comparisons only.

Normal UI tests do not load this reference. Startup and real services are off.
"""

from pathlib import Path


def load_project_reference(page):
    if page.evaluate("typeof initDashboard === 'function'"):
        return
    reference = "tests/reference/static/portal/js/proyecto_detalle.js"
    source = Path(reference).read_text(encoding="utf-8")
    page.add_script_tag(
        content="document.currentScript.dataset.projectBootstrap='manual';\n"
        + source
    )
