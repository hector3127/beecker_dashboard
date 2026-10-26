// These filters and CSV columns retain the previous screen's behavior.
export function date(value) {
  const parts = value.split("/");
  return parts.length === 3
    ? "20" + parts[2] + "-" + parts[1] + "-" + parts[0]
    : "";
}
export function matches(row, { manager, service, from, to }) {
  const start = date(row.start),
    end = date(row.end);
  return !(
    (manager && row.manager !== manager) ||
    (service && row.service !== service) ||
    (from && end && end < from) ||
    (to && start && start > to)
  );
}
export const headers = [
  "Delivery Manager",
  "Project ID",
  "Service",
  "Nombre",
  "Estatus",
  "Start",
  "Finish",
  "Desv. dias",
  "Budget",
  "Burn",
  "ETC",
  "Desv. Hrs",
  "Avance",
  ...["Discovery", "Development", "Deployment", "General"].flatMap((n) => [
    n + " Total",
    n + " Cerrados",
    n + " Pendientes",
  ]),
  "Riesgos",
];
export const csv = (rows, columnHeaders = headers) =>
  [columnHeaders, ...rows]
    .map((row) =>
      row.map((v) => '"' + String(v).replaceAll('"', '""') + '"').join(","),
    )
    .join("\r\n");
