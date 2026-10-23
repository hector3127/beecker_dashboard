"""Herramienta temporal: prefija con una clase las reglas de un CSS heredado."""

import re
import sys


def split_rules(css):
    """Divide en reglas de primer nivel respetando llaves anidadas."""
    rules, depth, start = [], 0, 0
    for i, ch in enumerate(css):
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                rules.append(css[start : i + 1].strip())
                start = i + 1
    return [r for r in rules if r]


def scope_selector(sel, scope, body_class, drop):
    parts = [p.strip() for p in sel.split(",")]
    out = []
    for p in parts:
        if p in drop or any(p.startswith(d + " ") or p.startswith(d + ".") or p.startswith(d + ":") or p.startswith(d + ">") for d in drop):
            continue
        if p.startswith(scope.strip()):
            out.append(p)
        elif p == "body":
            out.append(f"body.{body_class}")
        elif p == ".page":
            out.append(f"body.{body_class} .page")
        elif p.startswith("body "):
            out.append(f"body.{body_class} " + p[5:])
        else:
            out.append(f"{scope} {p}")
    return ", ".join(out)


def scope_block(css, scope, body_class, drop):
    result = []
    for rule in split_rules(css):
        head, _, body = rule.partition("{")
        body = body[:-1]
        if head.strip().startswith("@media"):
            inner = scope_block(body, scope, body_class, drop)
            if inner.strip():
                result.append(f"{head.strip()} {{\n{inner}\n}}")
        elif head.strip().startswith("@"):
            result.append(rule)
        else:
            sel = scope_selector(head, scope, body_class, drop)
            if sel:
                result.append(f"{sel} {{{body}}}")
    return "\n".join(result)


if __name__ == "__main__":
    src, dst, scope, body_class, drop = sys.argv[1:6]
    css = open(src, encoding="utf-8").read()
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    out = scope_block(css, scope, body_class, set(drop.split(",")))
    open(dst, "w", encoding="utf-8").write(out + "\n")
