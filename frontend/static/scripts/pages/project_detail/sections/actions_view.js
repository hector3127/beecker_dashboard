import { el } from "#app/lib/dom.js";
import { icon } from "./ixs_icons.js";
import {
  STATES,
  PRIORITIES,
  actionDate,
  dateText,
  dependencies,
  normalize,
  progress,
  stateClass,
} from "./actions_model.js";

const h = (tag, cls, ...children) =>
  el(
    tag,
    cls ? { class: cls } : {},
    ...children.flat().filter((x) => x != null),
  );
const div = (cls, ...children) => h("div", cls, ...children);
const text = (value) => (value == null ? "" : String(value));
const fieldLabels = {
  accion: "Acción / Entregable",
  responsable: "Responsable",
  prioridad: "Prioridad",
  fechaInicio: "Fecha inicio",
  fechaLimite: "Fecha compromiso",
  fechaReal: "Próxima revisión",
  proximaRevision: "Próxima revisión",
  estado: "Estado",
  dependencia: "Dependencia",
};
const styled = (node, style) => {
  Object.assign(node.style, style);
  return node;
};
const button = (label, onclick, cls = "aer-btn", props = {}) =>
  el("button", { class: cls, onclick, ...props }, label);
const bar = (width, background) =>
  div("aer-bar", styled(h("i", ""), { width: width + "%", background }));
const purple = "linear-gradient(90deg,#8d65ed,#5b2ad8)",
  red = "linear-gradient(90deg,#ff6773,#e4314e)",
  green = "linear-gradient(90deg,#25b36a,#67d78f)",
  actionPurple = "linear-gradient(90deg,#5b2ad8,#8d65ed)";

function input(value, props = {}) {
  const node = el("input", props);
  node.value = text(value);
  return node;
}
function area(value, props = {}) {
  const node = el("textarea", props);
  node.textContent = text(value);
  node.value = text(value);
  return node;
}
function select(options, value, props = {}, blank = false) {
  const node = el(
    "select",
    props,
    ...options.map((v) => el("option", { value: v }, v || (blank ? "—" : ""))),
  );
  if (options.includes(value)) node.value = value;
  return node;
}
const table = (headers, rows, props = {}) =>
  el(
    "table",
    { class: "aer-action-lite-table", ...props },
    h("thead", "", h("tr", "", ...headers)),
    ...rows,
  );
const heading = (label) => h("th", "", label);
const cell = (...body) => h("td", "", ...body);

function kpi(name, value, label, sub, tone = "purple", cls = "") {
  return div(
    `aer-action-kpi2 ${tone}` + (cls ? " " + cls : ""),
    div(
      "aer-action-metric-head",
      h("span", "icon", icon(name)),
      div("label", label),
    ),
    div("value", text(value)),
    div("sub", sub),
  );
}

export function filterActions(target, query) {
  const value = normalize(query);
  target
    .querySelectorAll("#aer-actions-table-body tr[data-action-filter]")
    .forEach((row) => {
      row.style.display =
        !value || String(row.dataset.actionFilter || "").includes(value)
          ? ""
          : "none";
    });
}

export function renderParts(parts, actions) {
  const rows = (parts || []).map((a) => {
    const edit = (field, value) => actions.partField(a.uid, field, value);
    const selectField = (field, values, value, props = {}) => {
      const node = select(values, value, {
        class: "aer-inline-edit",
        "aria-label": fieldLabels[field],
        ...props,
      });
      node.addEventListener("change", () => edit(field, node.value));
      return node;
    };
    const inputField = (field, props) => {
      const node = input(a[field] || "", {
        class: "aer-inline-edit",
        "aria-label": fieldLabels[field],
        ...props,
      });
      node.addEventListener("change", () => edit(field, node.value));
      return node;
    };
    const areaField = (field, label) => {
      const node = area(a[field] || "", {
        class: "aer-inline-edit aer-inline-textarea",
        "aria-label": label,
      });
      node.addEventListener("change", () => edit(field, node.value));
      return node;
    };
    return h(
      "tr",
      "",
      cell(areaField("accion", "Acción")),
      cell(
        selectField("responsable", ["Beecker", "Cliente"], a.responsable, {
          "aria-label": "Responsable Beecker o Cliente",
        }),
      ),
      cell(inputField("fechaLimite", { type: "date" })),
      cell(inputField("proximaRevision", { type: "date" })),
      cell(selectField("estado", STATES, a.estado || "Pendiente")),
      cell(areaField("notas", "Notas")),
      cell(
        button("✕", () => actions.removePart(a.uid), "aer-btn danger", {
          "aria-label": "Eliminar pendiente",
        }),
      ),
    );
  });
  if (!rows.length)
    rows.push(
      h(
        "tr",
        "",
        el(
          "td",
          { colspan: 7 },
          "Sin pendientes registrados. Pulsa «Agregar pendiente».",
        ),
      ),
    );
  return el(
    "div",
    {
      class: "aer-action-table-card",
      id: "aeri-partes-card",
      style: { marginTop: "14px" },
    },
    div(
      "aer-action-table-head",
      div(
        "",
        styled(h("h3", "", "▤ Listado de acciones Beecker / Cliente"), {
          margin: "0",
        }),
        div(
          "aer-sub",
          "Pendientes separados por organización para alimentar el resumen ejecutivo de IA.",
        ),
      ),
      div(
        "aer-actions",
        button("＋ Agregar pendiente", actions.openPart, "aer-btn primary"),
      ),
    ),
    el(
      "div",
      {
        class: "aer-sub",
        id: "aeri-partes-status",
        "aria-live": "polite",
        style: { margin: "7px 0" },
      },
      parts === null
        ? "Cargando pendientes Beecker / Cliente…"
        : (parts || []).length + " pendiente(s) registrado(s)",
    ),
    styled(
      div(
        "",
        table(
          [
            styled(heading("Acción / Entregable"), { minWidth: "220px" }),
            styled(heading("Responsable"), { minWidth: "115px" }),
            heading("Fecha compromiso"),
            heading("Próxima revisión"),
            heading("Estado"),
            styled(heading("Notas"), { minWidth: "175px" }),
            heading("Eliminar"),
          ],
          [h("tbody", "", ...rows)],
          { style: { minWidth: "760px" } },
        ),
      ),
      { overflow: "auto" },
    ),
    styled(
      div(
        "aer-sub",
        "Edición directa: los cambios se guardan al salir del campo. Beecker / Cliente indica a quién corresponde el pendiente, no el nombre de una persona.",
      ),
      { marginTop: "8px" },
    ),
  );
}

export function renderActions(target, m, parts, actions) {
  const {
    filas,
    abiertas,
    vencidas,
    detenidas,
    proximas,
    urgente,
    respCount,
    respTop,
    weeks,
  } = m;
  const hero = div(
    "aer-vivid-card aer-action-overview",
    div(
      "aer-action-hero",
      div(
        "",
        h("h3", "", "Acciones y seguimiento"),
        div(
          "sub",
          "Control de acciones clave del proyecto y seguimiento de compromisos.",
        ),
      ),
      div(
        "aer-actions",
        el(
          "button",
          { class: "aer-btn", onclick: actions.clean },
          icon("layers"),
          "Limpiar duplicados",
        ),
        button("+ Agregar acción", () => actions.open(), "aer-btn primary"),
      ),
    ),
    div(
      "aer-action-kpi-grid",
      kpi("list", filas.length, "Total", "Acciones registradas"),
      kpi("flag", abiertas, "Abiertas", "Requieren seguimiento", "blue"),
      kpi(
        "warning",
        vencidas,
        "Vencidas",
        "Requieren atención inmediata",
        "red",
      ),
      kpi("clock", detenidas, "Detenidas", "Temporalmente en pausa", "slate"),
      kpi(
        "calendar",
        proximas ? dateText(actionDate(proximas)) : "—",
        "Próxima revisión",
        "Siguiente fecha de seguimiento",
        "purple",
        "aer-action-date",
      ),
    ),
  );
  const meta = (label, value) =>
    div("aer-action-meta-block", div("lbl", label), div("val", value));
  const alert = div(
    "aer-action-alert",
    div(
      "head",
      div(
        "",
        div(
          "title",
          styled(h("span", "aer-vivid-icon red", "!"), {
            width: "46px",
            height: "46px",
            fontSize: "20px",
          }),
          "Atención inmediata",
        ),
        div(
          "desc",
          vencidas
            ? `Tienes ${vencidas} acción${vencidas === 1 ? "" : "es"} vencida${vencidas === 1 ? "" : "s"} que requiere${vencidas === 1 ? "" : "n"} seguimiento para evitar impacto en el proyecto.`
            : "No hay acciones vencidas en este momento.",
        ),
      ),
      button("Ver todas las acciones →", actions.clean),
    ),
    ...(urgente
      ? [
          div(
            "aer-action-alert-item",
            div(
              "main",
              h("b", "", text(urgente.accion || "Acción prioritaria")),
              h(
                "small",
                "",
                text(
                  urgente.comentarios ||
                    urgente.notas ||
                    "Esta acción está fuera de la fecha compromiso. Es necesario dar seguimiento y definir próximas acciones.",
                ),
              ),
            ),
            meta("Responsable", text(urgente.responsable || "—")),
            meta("Fecha compromiso", dateText(urgente.fechaLimite)),
            meta(
              "Estado",
              h("span", "aer-pill purple", text(urgente.estado || "Pendiente")),
            ),
            meta(
              "Prioridad",
              h("span", "aer-pill red", text(urgente.prioridad || "Alta")),
            ),
          ),
        ]
      : []),
  );
  const distribution = div(
    "aer-action-strip",
    h("h4", "", "Distribución por estado"),
    div(
      "aer-state-dist",
      ...[
        ["Abiertas", abiertas, purple],
        ["Vencidas", vencidas, red],
        ["Detenidas", detenidas, "#d8d4e5"],
      ].map(([name, count, color]) =>
        div(
          "row",
          h("span", "", name),
          bar(filas.length ? (count / filas.length) * 100 : 0, color),
          h("b", "", String(count)),
        ),
      ),
    ),
  );
  const responsible = div(
    "aer-action-strip",
    h("h4", "", "Responsables activos"),
    ...(respTop
      ? [
          styled(div("", String(Object.keys(respCount).length)), {
            fontSize: "30px",
            fontWeight: "900",
            color: "#1d174d",
            lineHeight: "1",
          }),
          styled(div("aer-sub", "personas con acciones"), {
            margin: "4px 0 12px",
          }),
          div(
            "aer-action-person",
            h(
              "span",
              "avatar",
              respTop[0]
                .split(/\s+/)
                .map((s) => s[0])
                .slice(0, 2)
                .join("")
                .toUpperCase(),
            ),
            div(
              "",
              h("b", "", respTop[0]),
              h(
                "small",
                "",
                `${respTop[1]} acción${respTop[1] === 1 ? "" : "es"} asignada${respTop[1] === 1 ? "" : "s"}`,
              ),
            ),
          ),
        ]
      : [div("aer-sub", "Sin responsables activos.")]),
  );
  const weekly = div(
    "aer-action-strip",
    div(
      "aer-section-title",
      div(
        "",
        styled(h("h4", "", "Seguimiento semanal"), { margin: "0" }),
        div("hint", "Acciones en el tiempo"),
      ),
    ),
    div(
      "aer-action-line",
      ...weeks.map((w, i) =>
        div(
          "pt" + (i === 0 ? " active" : ""),
          h("i", ""),
          h("b", "", String(w.cnt)),
          h(
            "small",
            "",
            new Date(w.iso + "T12:00:00").toLocaleDateString("es-MX", {
              day: "2-digit",
              month: "short",
            }),
          ),
        ),
      ),
    ),
  );
  const rows = filas.map((x) => {
    const edit = (field, value) => actions.field(x.uid, field, value);
    const inputField = (field, type) => {
      const node = input(x[field] || "", {
        class: "aer-inline-edit",
        "aria-label": fieldLabels[field],
        ...(type ? { type } : {}),
      });
      node.addEventListener("change", () => edit(field, node.value));
      return node;
    };
    const selectField = (field, values, value, blank) => {
      const node = select(
        values,
        value,
        {
          class: "aer-inline-edit",
          "aria-label": fieldLabels[field],
        },
        blank,
      );
      node.addEventListener("change", () => edit(field, node.value));
      return node;
    };
    const action = area(x.accion || "", {
      class: "aer-inline-edit aer-inline-textarea",
      "aria-label": fieldLabels.accion,
    });
    action.addEventListener("change", () => edit("accion", action.value));
    const cls = stateClass(x.estado),
      pct = progress(x.estado);
    return el(
      "tr",
      {
        dataset: {
          actionFilter: (
            normalize(x.accion) +
            " " +
            normalize(x.responsable) +
            " " +
            normalize(x.estado)
          ).trim(),
        },
      },
      cell(action),
      cell(inputField("responsable")),
      cell(selectField("prioridad", PRIORITIES, x.prioridad || "Media")),
      cell(inputField("fechaInicio", "date")),
      cell(inputField("fechaLimite", "date")),
      cell(inputField("fechaReal", "date")),
      cell(selectField("estado", STATES, x.estado || "Pendiente")),
      cell(
        selectField(
          "dependencia",
          dependencies(x.dependencia),
          x.dependencia || "",
          true,
        ),
      ),
      cell(
        styled(
          div(
            "",
            bar(pct, cls === "bad" ? red : cls === "ok" ? green : actionPurple),
            h("b", "", pct + "%"),
          ),
          {
            display: "grid",
            gridTemplateColumns: "minmax(0,1fr) 40px",
            gap: "10px",
            alignItems: "center",
          },
        ),
      ),
      cell(
        button("✕", () => actions.remove(x.uid), "aer-btn danger", {
          "aria-label": "Eliminar acción",
        }),
      ),
    );
  });
  if (!rows.length)
    rows.push(
      h("tr", "", el("td", { colspan: 10 }, "Sin acciones registradas.")),
    );
  const search = input("", {
    class: "aer-action-search",
    type: "text",
    placeholder: "Buscar acción, responsable...",
    "aria-label": "Buscar acción o responsable",
  });
  search.addEventListener("input", () => filterActions(target, search.value));
  const listing = div(
    "aer-action-table-card",
    div(
      "aer-action-table-head",
      div("", styled(h("h3", "", "Listado de acciones"), { margin: "0" })),
      div(
        "tools",
        search,
        button("Filtros", () => actions.open()),
      ),
    ),
    styled(
      div(
        "",
        table(
          [
            styled(heading("Acción / Entregable"), { minWidth: "260px" }),
            ...[
              "Responsable",
              "Prioridad",
              "Fecha inicio",
              "Fecha compromiso",
              "Próxima revisión",
              "Estado",
              "Dependencia",
              "Avance",
              "Eliminar",
            ].map(heading),
          ],
          [el("tbody", { id: "aer-actions-table-body" }, ...rows)],
        ),
      ),
      { overflow: "auto" },
    ),
    styled(
      div("aer-sub", `Mostrando ${filas.length} de ${filas.length} acciones`),
      { marginTop: "10px" },
    ),
  );
  target.replaceChildren(
    div(
      "aer-action-shell",
      hero,
      alert,
      div("aer-action-mid", distribution, responsible, weekly),
      listing,
      renderParts(parts, actions),
    ),
  );
}

function modal(...body) {
  document.getElementById("aer-modal-back")?.remove();
  const back = el(
    "div",
    { class: "aer-modal-back", id: "aer-modal-back" },
    div("aer-modal", ...body),
  );
  back.addEventListener("click", (e) => {
    if (e.target === back) back.remove();
  });
  document.body.append(back);
  return back;
}
const label = (text, field, cls = "") => h("label", cls, text, field);
export function openAction(data, uid, actions) {
  const x = (data.acciones?.filas || []).find((row) => row.uid === uid) || {};
  return modal(
    styled(
      div(
        "",
        h("h3", "", (uid ? "Editar" : "Agregar") + " acción"),
        button("✕", () => document.getElementById("aer-modal-back")?.remove()),
      ),
      { display: "flex", justifyContent: "space-between" },
    ),
    div(
      "aer-formgrid",
      label(
        "Acción / Entregable",
        input(x.accion || "", { id: "aa-a" }),
        "aer-span2",
      ),
      label("Responsable", input(x.responsable || "", { id: "aa-r" })),
      label("Estado", select(STATES, x.estado || "Pendiente", { id: "aa-e" })),
      label(
        "Fecha inicio",
        input(x.fechaInicio || "", { type: "date", id: "aa-fi" }),
      ),
      label(
        "Fecha compromiso",
        input(x.fechaLimite || "", { type: "date", id: "aa-f" }),
      ),
      label(
        "Fecha real",
        input(x.fechaReal || "", { type: "date", id: "aa-fr" }),
      ),
      label(
        "Dependencia",
        select(
          dependencies(x.dependencia),
          x.dependencia || "",
          { id: "aa-d" },
          true,
        ),
      ),
      label(
        "Prioridad",
        select(PRIORITIES, x.prioridad || "Media", { id: "aa-p" }),
      ),
      label(
        "Comentarios",
        area(x.comentarios || x.notas || "", { id: "aa-n" }),
        "aer-span2",
      ),
    ),
    styled(
      div(
        "aer-actions",
        ...(uid
          ? [
              button(
                "Eliminar",
                () => actions.remove(uid, true),
                "aer-btn danger",
              ),
            ]
          : []),
        button("Guardar", () => actions.save(uid), "aer-btn primary"),
      ),
      { marginTop: "12px" },
    ),
  );
}

export function openPart(actions) {
  return modal(
    styled(
      div(
        "",
        styled(h("h3", "", "＋ Pendiente Beecker / Cliente"), { margin: "0" }),
        button("✕", () => document.getElementById("aer-modal-back")?.remove()),
      ),
      { display: "flex", justifyContent: "space-between", gap: "10px" },
    ),
    styled(
      div(
        "aer-formgrid",
        label(
          "Acción / entregable",
          styled(
            area("", {
              id: "aerp-new-accion",
              placeholder: "Describe el compromiso pendiente…",
            }),
            { minHeight: "66px" },
          ),
          "aer-span2",
        ),
        label(
          "Responsable",
          select(["Beecker", "Cliente"], "Beecker", { id: "aerp-new-parte" }),
        ),
        label("Estado", select(STATES, "Pendiente", { id: "aerp-new-estado" })),
        label(
          "Fecha compromiso",
          input("", { type: "date", id: "aerp-new-fecha" }),
        ),
        label(
          "Próxima revisión",
          input("", { type: "date", id: "aerp-new-revision" }),
        ),
        label("Notas", area("", { id: "aerp-new-notas" }), "aer-span2"),
      ),
      { marginTop: "12px" },
    ),
    styled(
      div(
        "aer-actions",
        button("Guardar pendiente", actions.savePart, "aer-btn primary", {
          id: "aerp-new-save",
        }),
      ),
      { marginTop: "12px", justifyContent: "flex-end" },
    ),
  );
}
