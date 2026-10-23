"""Herramienta temporal: arma la plantilla modular de una pantalla anterior.

Uso: migrate_page.py <legacy.html> <nombre> <body_class> [hoja.css ...]
Escribe frontend/templates/pages/<nombre>.html y
frontend/static/styles/pages/<nombre>.css; guarda los scripts en linea en
tools/migracion/<nombre>_scripts.js para portarlos a mano.
"""

import pathlib
import re
import subprocess
import sys

legacy, name, body_class, *sheets = sys.argv[1:]
_orig = re.search(r"\{% block body_class %\}(.*?)\{% endblock %\}", pathlib.Path(legacy).read_text(encoding="utf-8"))
if _orig:
    body_class = _orig.group(1).strip()
uses_ds = "ds" in body_class.split()
ds_link = "<link rel=\"stylesheet\" href=\"{% static 'app/styles/pages/ds.css' %}\">" + chr(10) if uses_ds else ""
html = pathlib.Path(legacy).read_text(encoding="utf-8")
title = re.search(r"\{% block title %\}(.*?)\{% endblock %\}", html, re.S).group(1)
start = html.index("{% block content %}") + len("{% block content %}")
content = html[start : html.index("{% endblock %}", start)]
tail = html[html.index("{% endblock %}", start) :]
scripts = re.findall(r"<script>(.*?)</script>", content + tail, re.S)
content = re.sub(r"<script[^>]*>.*?</script>\s*", "", content, flags=re.S)
content = re.sub(r"<main", "<div", content)
content = content.replace("</main>", "</div>")
loads = " ".join(re.findall(r"\{% load ([^%]*)%\}", html)).replace("static", "").split()
load_line = "{% load static " + " ".join(loads) + " %}"
new = f'''{{% extends "layouts/app.html" %}}
{load_line}
{{% block title %}}{title}{{% endblock %}}
{{% block body_class %}}{body_class}{{% endblock %}}
{{% block head %}}<link rel="stylesheet" href="{{% static 'app/styles/pages/portal-controls.css' %}}">
<link rel="stylesheet" href="{{% static 'app/styles/pages/portal-loading.css' %}}">
<link rel="stylesheet" href="{{% static 'app/styles/pages/legacy-base.css' %}}">
{ds_link}<link rel="stylesheet" href="{{% static 'app/styles/pages/{name}.css' %}}">{{% endblock %}}
{{% block freshness %}}<span class="dot" aria-hidden="true"></span><span>{{% if loaded_at %}}Datos al {{{{ loaded_at|date:"d/m/Y, H:i" }}}}{{% else %}}Sin fecha de actualización{{% endif %}}</span>{{% endblock %}}
{{% block content %}}{content}{{% endblock %}}
{{% block scripts %}}<script type="module" src="{{% static 'app/scripts/pages/{name}/main.js' %}}"></script>{{% endblock %}}
'''
out = pathlib.Path("frontend/templates/pages", f"{name}.html")
out.write_text(new, encoding="utf-8")
css = pathlib.Path("frontend/static/styles/pages", f"{name}.css")
subprocess.run([sys.executable, "tools/migracion/migrate_css.py", legacy, str(css), *sheets], check=True)
subprocess.run([sys.executable, "tools/migracion/inline2css.py", str(out), f"{name[:2]}i-", str(css)], check=True)
pathlib.Path("shots_tmp", f"{name}_scripts.js").write_text("\n/* ---- */\n".join(scripts), encoding="utf-8")
pathlib.Path("frontend/static/scripts/pages", name).mkdir(parents=True, exist_ok=True)
print("scripts:", len(scripts))
