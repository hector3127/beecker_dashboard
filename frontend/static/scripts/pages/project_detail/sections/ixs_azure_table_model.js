export function requirement(title) {
  const text = String(title || "").trim();
  return (
    (text.match(/[A-Z]{2,}\.[0-9]{3}(?:\.[0-9]{3})+/i) ||
      text.match(/[A-Z]{2,}\.[0-9]{3}(?:_[A-Z0-9]+)?/i) ||
      [])[0] || "—"
  );
}
export function titleOnly(title) {
  const text = String(title || "").trim(),
    req = requirement(text);
  return req === "—"
    ? text
    : text
        .replace(req, "")
        .replace(/^[-–—:|\s]+/, "")
        .trim() || text;
}
export function workItemOptions(items, key) {
  return Array.from(
    new Set(
      (items || [])
        .map((x) => String((x && x[key]) || "").trim())
        .filter(Boolean),
    ),
  ).sort((a, b) => a.localeCompare(b, "es", { sensitivity: "base" }));
}
export function filterWorkItems(
  items,
  { status = "", person = "", type = "", query = "" } = {},
) {
  const search = String(query || "")
      .trim()
      .toLowerCase(),
    kinds = {};
  items.forEach((x) => {
    kinds[String(x.id)] = x.tipo || "";
  });
  return items.filter((x) => {
    const kind = String(x.tipo || kinds[String(x.id)] || "");
    if (
      (status && String(x.estado || "") !== status) ||
      (person && String(x.asignadoA || "") !== person) ||
      (type && kind !== type)
    )
      return false;
    return (
      !search ||
      [
        x.id,
        requirement(x.titulo),
        titleOnly(x.titulo),
        x.asignadoA,
        x.estado,
        kind,
        x.demo,
      ]
        .join(" ")
        .toLowerCase()
        .includes(search)
    );
  });
}
