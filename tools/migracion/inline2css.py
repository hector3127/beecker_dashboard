"""Herramienta temporal: pasa los style="" de una plantilla a clases en una hoja."""

import hashlib
import re
import sys

TAG = re.compile(r"<[a-zA-Z][^<>]*>")


def convert(html, prefix):
    rules = {}

    def fix(match):
        tag = match.group(0)
        found = re.search(r'\sstyle="([^"]*)"', tag)
        if not found or "{{" in found.group(1) or "{%" in found.group(1):
            return tag
        decls = [d.strip() for d in found.group(1).split(";") if d.strip()]
        body = ";".join(decls)
        name = f"{prefix}{hashlib.md5(body.encode()).hexdigest()[:6]}"
        rules[name] = body
        tag = tag.replace(found.group(0), "", 1)
        klass = re.search(r'\sclass="([^"]*)"', tag)
        if klass:
            return tag.replace(klass.group(0), f' class="{klass.group(1)} {name}"', 1)
        return re.sub(r"^<([a-zA-Z0-9]+)", rf'<\1 class="{name}"', tag, count=1)

    return TAG.sub(fix, html), rules


if __name__ == "__main__":
    src, prefix, out_css = sys.argv[1:4]
    html = open(src, encoding="utf-8").read()
    new, rules = convert(html, prefix)
    open(src, "w", encoding="utf-8").write(new)
    css = "\n".join(f".{n} {{{b}}}" for n, b in rules.items())
    open(out_css, "a", encoding="utf-8").write("\n/* Estilos que estaban en linea. */\n" + css + "\n")
    print(len(rules), "reglas")
