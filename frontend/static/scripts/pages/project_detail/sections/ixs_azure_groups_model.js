// The grouping rules intentionally differ from the summary status classifier.
export function groupStatus(state) {
  const value = String(state || "")
    .trim()
    .toUpperCase();
  if (value === "CANCELLED") return "cancelled";
  if (
    ["NOT APPLICABLE", "CLOSED", "REJECTED", "COMPLETED", "INACTIVE"].includes(
      value,
    )
  )
    return "closed";
  if (value === "ACTIVE") return "active";
  if (value === "PROPOSED") return "proposed";
  if (value === "BLOCKED") return "blocked";
  return "other";
}

export function iterationStage(path) {
  const value = String(path || "").trim();
  return value ? value.split("\\").filter(Boolean).pop() : "Sin iteración";
}

export function azureGroups(state) {
  const rows = Array.isArray(state.allItems) ? state.allItems : [];
  const people = new Map(),
    stages = new Map();
  for (const item of rows) {
    const person =
      String(item.asignadoA || "Sin asignar").trim() || "Sin asignar";
    const path = String(item.iterationPath || "").trim();
    const stage = iterationStage(path),
      key = path || "Sin iteración";
    const status = groupStatus(item.estado);
    if (!people.has(person))
      people.set(person, {
        persona: person,
        items: [],
        iteraciones: new Map(),
        closed: 0,
        active: 0,
        proposed: 0,
        cancelled: 0,
        other: 0,
      });
    const p = people.get(person);
    p.items.push(item);
    p[status in p ? status : "other"]++;
    if (!p.iteraciones.has(key))
      p.iteraciones.set(key, {
        persona: person,
        etapa: stage,
        iterationPath: key,
        items: [],
        closed: 0,
        active: 0,
        proposed: 0,
        cancelled: 0,
        other: 0,
      });
    const sub = p.iteraciones.get(key);
    sub.items.push(item);
    sub[status in sub ? status : "other"]++;
    if (!stages.has(key))
      stages.set(key, {
        etapa: stage,
        iterationPath: key,
        items: [],
        active: 0,
        proposed: 0,
        blocked: 0,
        other: 0,
      });
    const g = stages.get(key);
    if (status !== "closed" && status !== "cancelled") {
      g.items.push(item);
      g[status in g ? status : "other"]++;
    }
  }
  return {
    people: Array.from(people.values())
      .map((p) => ({
        ...p,
        total: p.items.length,
        iteraciones: Array.from(p.iteraciones.values()).sort(
          (a, b) =>
            b.items.length - a.items.length ||
            a.etapa.localeCompare(b.etapa, "es"),
        ),
      }))
      .sort(
        (a, b) => b.total - a.total || a.persona.localeCompare(b.persona, "es"),
      ),
    stages: Array.from(stages.values())
      .filter((x) => x.items.length)
      .sort(
        (a, b) =>
          b.items.length - a.items.length ||
          a.etapa.localeCompare(b.etapa, "es"),
      ),
  };
}

export function matchesPerson(person, query) {
  const needle = String(query || "")
    .trim()
    .toLocaleLowerCase("es");
  return (
    !needle ||
    [person.persona, ...person.iteraciones.map((x) => x.etapa)]
      .join(" ")
      .toLocaleLowerCase("es")
      .includes(needle)
  );
}
