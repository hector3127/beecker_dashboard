"""Herramienta temporal: arma la hoja de una pantalla a partir de la anterior.

Uso: migrate_css.py <plantilla> <salida.css> [hoja.css ...]
Toma el bloque css en linea de la plantilla y las hojas indicadas (de
apps/portal/static/portal/css) y quita las reglas de la barra superior.
"""

import pathlib
import re
import sys

sys.path.insert(0, "shots_tmp")
from scope_css import split_rules  # noqa: E402

CHROME = re.compile(
    r"^(?:\.[\w-]+-page\s+)?(\.top|\.logo|\.nav|\.fresh|\.dot|#portal-freshness|#cached-page-state|\.cached-refresh-button|\.portal-navigation)\b"
)


def clean(css):
    out = []
    for rule in split_rules(css):
        head, _, body = rule.partition("{")
        body = body[:-1]
        if head.strip().startswith("@media"):
            inner = clean(body)
            if inner.strip():
                out.append(head.strip() + "{" + inner + "}")
        elif head.strip().startswith("@"):
            out.append(rule)
        else:
            keep = [p.strip() for p in head.split(",") if not CHROME.match(p.strip())]
            if keep:
                out.append(",".join(keep) + "{" + body + "}")
    return "\n".join(out)


def main(template, output, sheets):
    html = pathlib.Path(template).read_text(encoding="utf-8")
    found = re.search(r"\{% block css %\}(.*?)\{% endblock %\}", html, re.S)
    parts = []
    if found:
        parts.append(("estilo en linea", found.group(1)))
    for sheet in sheets:
        text = pathlib.Path("apps/portal/static/portal/css", sheet).read_text(encoding="utf-8")
        parts.append((sheet, text))
    result = "/* Reglas de la pantalla anterior, sin las de la barra superior. */\n"
    for name, text in parts:
        text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
        result += f"\n/* --- {name} --- */\n" + clean(text) + "\n"
    pathlib.Path(output).write_text(result, encoding="utf-8")
    print(len(result), "caracteres")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3:])
