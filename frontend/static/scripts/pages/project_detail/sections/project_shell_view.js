import {
  el,
  h,
  div,
  button,
  text,
  styled,
  dateText,
} from "./aer_planning_dom.js";
import { dateText as ixsDate } from "./ixs_executive_model.js";
import { icon } from "./ixs_icons.js";
import { aerStatus, stage } from "./project_shell_model.js";

export const AER_TABS = [
  ["ejecutivo", "Ejecutivo"],
  ["planeacion", "Planeación"],
  ["esfuerzo", "Esfuerzo"],
  ["riesgos", "Riesgos"],
  ["acciones", "Acciones"],
  ["recursos", "Recursos"],
  ["cliente", "Cliente"],
  ["ia", "✦ IA"],
];
export const IXS_TABS = [
  ["resumen", "Ejecutivo", ""],
  ["planeacion", "Planeación", "calendar"],
  ["esfuerzo", "Esfuerzo", "chart"],
  ["recursos", "Recursos", "people"],
  ["riesgos", "Gestión RAID", "warning"],
  ["acciones", "Acciones", "list"],
  ["cliente", "Cliente", "people"],
  ["comunicacion", "Comunicación", "megaphone"],
  ["azure", "Azure DevOps", "layers"],
  ["ia", "IA", "sparkles"],
];

export function renderShell(target, env, actions) {
  const p = env.project.proyecto || {},
    active = env.tab();
  if (env.family === "aer") {
    const separator = " \u00a0 | \u00a0 ";
    target.replaceChildren(
      div(
        "aer-shell",
        div(
          "aer-head",
          div(
            "",
            div("aer-title", `${text(p.id)} · ${text(p.nombre)}`),
            div(
              "aer-sub",
              `Cliente: ${p.cliente || "—"}${separator}Delivery Manager: ${p.deliveryManager || "—"}${separator}${dateText(p.fechaInicio)} → ${dateText(p.fechaFin)}`,
            ),
          ),
          div(
            "aer-actions",
            h(
              "span",
              `aer-badge ${aerStatus(p.estado)}`,
              p.estado || "En seguimiento",
            ),
            button("↻ Actualizar", actions.refresh),
          ),
        ),
        div(
          "aer-tabs",
          ...AER_TABS.map(([id, label]) =>
            button(
              label,
              () => actions.select(id),
              "aer-tab" + (active === id ? " active" : ""),
            ),
          ),
        ),
        el("div", { id: "aer-tab-content" }),
      ),
    );
  } else {
    const current = stage(env.project),
      service = env.metadata?.[p.id]?.servicio || "IXB / SaaS / RaaS",
      separator = " \u00a0│\u00a0 ";
    target.replaceChildren(
      el(
        "div",
        { class: "ixs-shell", "data-ixs-proyecto": text(p.id) },
        div(
          "ixs-head",
          div(
            "ixs-head-top",
            div(
              "ixs-title ixs-head-title",
              `${text(p.id)} · ${p.nombre || "Proyecto"} `,
              h("span", "ixs-badge", text(service)),
            ),
            div(
              "ixs-head-right",
              h(
                "span",
                `ixs-badge ${current.clase || ""}`,
                current.texto || "Sin etapa",
              ),
              el(
                "button",
                { class: "ixs-btn", onclick: actions.refresh },
                icon("refresh"),
                " Actualizar",
              ),
            ),
          ),
          div(
            "ixs-sub",
            `Cliente: ${p.cliente || "—"}${separator}Fecha de corte: ${ixsDate(p.fechaCorte)}${separator}Sponsor: ${p.sponsor || "—"}${separator}Project Manager: ${p.pm || "—"}${p.deliveryManager ? separator + "DM: " + p.deliveryManager : ""}`,
          ),
        ),
        el(
          "nav",
          { class: "ixs-nav", "aria-label": "Pestañas del proyecto" },
          ...IXS_TABS.map(([id, label, name]) =>
            el(
              "button",
              {
                class: active === id ? "active" : "",
                onclick: () => actions.select(id),
              },
              ...(name ? [icon(name)] : []),
              label,
            ),
          ),
        ),
        el("div", { id: "ixs-tab-contenido" }),
      ),
    );
  }
}
export function loading(target, family) {
  if (target)
    target.replaceChildren(
      family === "aer"
        ? div("loading", "Actualizando proyecto...")
        : styled(div("ixs-card", "Actualizando ejecutivo…"), {
            padding: "22px",
          }),
    );
}
export function invalidRefresh(target) {
  if (target?.isConnected)
    target.replaceChildren(
      div("ixs-card", "No se pudo actualizar el proyecto."),
    );
}
