// @ts-check
// Pestaña Cliente (AER/T&M e IXB/SaaS/RaaS): datos derivados, filtros y CSV.
// Son las mismas reglas del renderer anterior; no toca el DOM.

export const EMPTY_FILTERS = { q: "", rol: "", area: "", decision: "", estado: "" };

/** @param {any} dashboard */
export function clientData(dashboard) {
  const c = (dashboard && dashboard.cliente) || {};
  return {
    contactos: Array.isArray(c.contactos) ? c.contactos : [],
    info: c.info || {},
    gobierno: Array.isArray(c.gobierno) ? c.gobierno : [],
    documentos: Array.isArray(c.documentos) ? c.documentos : [],
  };
}

/** @param {any} level */
export function levelClass(level) {
  const n = String(level || "").toLowerCase();
  return n === "alto" ? "green" : n === "medio" ? "yellow" : "red";
}

/** @param {any} name */
export const initials = (name) =>
  String(name || "?")
    .trim()
    .split(/\s+/)
    .map((x) => x[0])
    .slice(0, 2)
    .join("")
    .toUpperCase();

/** @param {any} v */
export const normalize = (v) =>
  String(v || "")
    .toLowerCase()
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .trim();

/** @param {any} v */
export const csvCell = (v) => `"${String(v == null ? "" : v).replace(/"/g, '""')}"`;

/** Texto separado por coma, punto y coma o barra. @param {any} text */
export const splitList = (text) =>
  String(text || "")
    .split(/[,;|]/)
    .map((x) => x.trim())
    .filter(Boolean);

/** @param {any[]} list */
const unique = (list) => [...new Set(list)];

const WEIGHT = /** @type {Record<string, number>} */ ({ Alto: 0, Medio: 1, Bajo: 2 });

/** Reuniones que se proponen si el proyecto AER no tiene gobierno guardado. @param {string[]} channels */
export const defaultGovernance = (channels) => [
  { reunion: "Seguimiento semanal", frecuencia: "Semanal", participantes: "PO + Delivery + Cliente", canal: channels[0] || "—" },
  { reunion: "Comité operativo", frecuencia: "Quincenal", participantes: "Sponsor + PO + Delivery", canal: channels[1] || channels[0] || "—" },
  { reunion: "Comité ejecutivo", frecuencia: "Mensual", participantes: "Sponsor + Dirección", canal: channels[2] || channels[0] || "—" },
];

/** Reuniones iniciales del editor de gobierno. @param {any} data @param {string} family */
export function governanceRows(data, family) {
  if (data.gobierno.length) return data.gobierno;
  return family === "ixs" ? [] : defaultGovernance([]).map((r, i) => ({ ...r, canal: ["Teams", "Correo", "Teams"][i] }));
}

/**
 * Todo lo que pinta la pestaña, según el proyecto y los filtros.
 * @param {any} dashboard @param {typeof EMPTY_FILTERS} filters @param {string} family
 */
export function clientModel(dashboard, filters, family) {
  const project = dashboard.proyecto || {};
  const d = clientData(dashboard);
  const info = d.info;
  const all = d.contactos;
  const docs = d.documentos;
  const q = normalize(filters.q);
  const roles = unique(all.map((x) => x.rol).filter(Boolean)).sort();
  const areas = unique(all.map((x) => x.area).filter(Boolean)).sort();
  const filtered = all.filter((x) => {
    const blob = normalize([x.nombre, x.cargo, x.rol, x.area, x.correo, x.telefono, x.nivelDecision, x.estado].join(" "));
    return (!q || blob.includes(q)) && (!filters.rol || x.rol === filters.rol) && (!filters.area || x.area === filters.area) && (!filters.decision || x.nivelDecision === filters.decision) && (!filters.estado || x.estado === filters.estado);
  });
  const active = all.filter((x) => String(x.estado || "Activo").toLowerCase() !== "inactivo");
  const decisors = all.filter((x) => x.esDecisor || String(x.nivelDecision || "").toLowerCase() === "alto");
  const areaCount = new Set(all.map((x) => x.area).filter(Boolean)).size;
  const channelsText = info.canales || all.map((x) => x.canal).filter(Boolean).join(", ");
  const channels = unique(splitList(channelsText));
  const key = active
    .slice()
    .sort((a, b) => (b.esDecisor ? 1 : 0) - (a.esDecisor ? 1 : 0) || (WEIGHT[a.nivelDecision] ?? 3) - (WEIGHT[b.nivelDecision] ?? 3))
    .slice(0, 4);
  const clientName = project.cliente || "Cliente";
  const governance = d.gobierno.length ? d.gobierno : family === "ixs" ? [] : defaultGovernance(channels);
  const docsByType = (/** @type {string} */ t) => docs.filter((x) => String(x.tipo || "").toLowerCase() === t.toLowerCase());
  return {
    project,
    info,
    all,
    docs,
    filtered,
    roles,
    areas,
    active,
    clientName,
    channels,
    governance,
    key,
    facts: [
      ["🏢", "Cliente", clientName],
      ["▦", "Área principal", info.areaPrincipal || "—"],
      ["♛", "Sponsor", info.sponsor || "—"],
      ["●", "Product Owner", info.productOwner || "—"],
      ["▣", "Delivery Manager", project.deliveryManager || "—"],
      ["✉", "Correo de distribución", info.correoDistribucion || "—"],
      ["⚑", "Ruta de escalamiento", info.rutaEscalamiento || "—"],
    ],
    included: unique(all.filter((x) => x.requerimientos || x.aprueba || x.valida || x.decide).map((x) => x.area).filter(Boolean)),
    informed: unique(all.filter((x) => x.informado && !x.requerimientos && !x.aprueba && !x.valida && !x.decide).map((x) => x.area).filter(Boolean)),
    topics: unique(all.flatMap((x) => splitList(x.alcance))).slice(0, 8),
    activeRoles: unique(active.map((x) => x.rol).filter(Boolean)).slice(0, 6),
    kpis: [
      ["👥", "Contactos clave", active.length, "stakeholders registrados", "purple"],
      ["♛", "Decisores", decisors.length, "con autoridad de aprobación", "purple"],
      ["▦", "Áreas involucradas", areaCount, areas.slice(0, 3).join(", ") || "sin áreas registradas", "yellow"],
      ["✉", "Canales de comunicación", channels.length, channels.slice(0, 3).join(", ") || "sin canales configurados", "blue"],
    ],
    quickDocs: [
      ["📁", "Carpetas", docsByType("Carpeta").length + docsByType("Procedimiento").length, "carpetas"],
      ["📄", "Plantillas", docsByType("Plantilla").length, "archivos"],
      ["🔗", "Referencias", docs.filter((x) => /referencia|documento/i.test(String(x.tipo || ""))).length, "vínculos"],
    ],
  };
}

/** Ícono del canal. @param {string} channel */
export const channelIcon = (channel) => (/team/i.test(channel) ? "▦" : /correo|mail/i.test(channel) ? "✉" : /comit/i.test(channel) ? "👥" : "●");

/** CSV de contactos para Excel. @param {any[]} contacts */
export function contactsCsv(contacts) {
  const rows = [["Nombre", "Cargo", "Rol", "Área", "Correo", "Teléfono", "Nivel decisión", "Estado", "Canal", "Alcance"], ...contacts.map((x) => [x.nombre, x.cargo, x.rol, x.area, x.correo, x.telefono, x.nivelDecision, x.estado, x.canal, x.alcance])];
  return "﻿" + rows.map((r) => r.map(csvCell).join(",")).join("\r\n");
}

/** Dirección que se abre desde un vínculo. @param {any} url */
export function linkTarget(url) {
  const href = String(url || "").trim();
  if (!href) return "";
  return /^https?:\/\//i.test(href) ? href : `https://${href}`;
}
