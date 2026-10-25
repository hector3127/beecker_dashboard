export function projectParams(search, seed) {
  const params = new URLSearchParams(search);
  if (seed) params.set("proyecto", JSON.parse(seed).id);
  return params;
}

export function metadata(data) {
  const result = {};
  (data.proyectos || []).forEach((project) => {
    result[String(project.id || "")] = project;
  });
  return result;
}

export function family(id, projects) {
  const service = String(projects[String(id || "")]?.servicio || "")
    .toUpperCase()
    .trim();
  const aer = service
    ? ["AER", "T&M", "TYM"].includes(service)
    : /^(AER|TYM)\./i.test(String(id || "").trim());
  if (aer) return "aer";
  return ["IXB", "SAAS", "RAAS"].includes(service.replace(/[^A-Z0-9]/g, ""))
    ? "ixs"
    : "executive";
}
