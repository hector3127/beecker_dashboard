import json, sys
a = json.load(open(sys.argv[1])); b = json.load(open(sys.argv[2]))
for k in b:
    if k not in a: continue
    if a[k] is None or b[k] is None:
        print(k, "missing", a[k] is None, b[k] is None); continue
    d = {p: (a[k][p], b[k][p]) for p in b[k] if a[k].get(p) != b[k][p]}
    print(k, d or "OK")
