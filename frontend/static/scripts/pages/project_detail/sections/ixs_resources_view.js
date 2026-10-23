import { el } from "#app/lib/dom.js";
import { icon } from "./ixs_icons.js";
import { num } from "./ixs_executive_model.js";
import { h, div, empty } from "./ixs_executive_view.js";
import { resourcesModel, resourceEditorSource } from "./ixs_resources_model.js";

const button = (text, action, cls = "ixs-btn", props = {}) =>
  el("button", { class: cls, onclick: action, ...props }, text);

export function renderResources(target, data, state, edit) {
  const { rows, hours, missing, inactive } = resourcesModel(data, state),
    td = (value) => h("td", "", value);
  const tableRows = rows.map(([key, x]) => {
    const used = Number((hours.get(key) || {}).horas || 0),
      balance = Number(x.horasEstimadas || 0) - used;
    return h(
      "tr",
      "",
      td(h("b", x.activo ? "" : "ixs-exec-inactive", x.nombre)),
      td(x.rol == null || x.rol === "" ? "—" : x.rol),
      td(num(x.horasEstimadas, 2) + " h"),
      td(state.cargando ? "…" : state.error ? "—" : num(used, 2) + " h"),
      h(
        "td",
        balance < 0 ? "ixs-resource-balance-red" : "ixs-resource-balance-green",
        state.cargando ? "…" : state.error ? "—" : num(balance, 2) + " h",
      ),
      td(
        h(
          "span",
          `ixs-badge ${x.activo ? "green" : "orange"}`,
          x.activo ? "Activo" : "Inactivo",
        ),
      ),
      td(button("Editar", () => edit(x.nombre))),
    );
  });
  target.replaceChildren(
    h(
      "section",
      "ixs-card ixs-resources-card",
      div(
        "ixs-section-head",
        div(
          "",
          h(
            "h3",
            "",
            icon("people"),
            " Recursos del proyecto ",
            state.proyectoId,
          ),
          h(
            "small",
            "",
            "Asignación, rol, horas estimadas y horas registradas en Clockify para este ID",
          ),
        ),
        button("+ Agregar recurso", () => edit(), "ixs-btn primary"),
      ),
      state.cargando ? empty("Consultando asignaciones y Clockify…") : null,
      state.error ? div("ixs-empty ixs-resources-error", state.error) : null,
      missing.length
        ? div(
            "ixs-resource-alert",
            h(
              "b",
              "",
              `⚠ ${missing.length} recurso(s) con horas en Clockify sin asignación`,
            ),
            missing.map(([, x]) =>
              div(
                "",
                `${x.nombre} · ${num(x.horas, 2)} h `,
                button("Asignar", () => edit(x.nombre)),
              ),
            ),
          )
        : null,
      inactive.length
        ? div(
            "ixs-resource-alert",
            h(
              "b",
              "",
              `⚠ ${inactive.length} recurso(s) inactivo(s) con horas registradas en el ID`,
            ),
          )
        : null,
      div(
        "ixs-table-scroll",
        h(
          "table",
          "ixs-table",
          h(
            "thead",
            "",
            h(
              "tr",
              "",
              [
                "Recurso",
                "Rol",
                "Horas estimadas",
                "Horas en el ID",
                "Horas restantes",
                "Estado",
                "Acción",
              ].map((x) => h("th", "", x)),
            ),
          ),
          h(
            "tbody",
            "",
            tableRows.length
              ? tableRows
              : h(
                  "tr",
                  "",
                  el(
                    "td",
                    { colspan: 7 },
                    "Sin recursos asignados. Agrega el primero para este proyecto.",
                  ),
                ),
          ),
        ),
      ),
      h(
        "small",
        "",
        "Las horas de Clockify se suman para todos los registros devueltos de este ID de proyecto. Horas restantes = estimadas − horas en el ID; un saldo negativo indica horas excedidas. Los cambios de rol, estimación y estado se guardan por proyecto.",
      ),
    ),
  );
  target.dataset.renderer = "modular-resources";
}

export function resourceEditor(data, state, name = "", actions) {
  const src = resourceEditorSource(data, state, name);
  const input = (label, props) => h("label", "", label, el("input", props));
  const modal = el(
    "div",
    { id: "ixs-recurso-modal", class: "ixs-clockify-modal" },
    el(
      "div",
      {
        class: "ixs-clockify-dialog ixs-recurso-dialog",
        role: "dialog",
        "aria-modal": "true",
        "aria-label": "Editar recurso",
      },
      div(
        "ixs-section-head",
        h(
          "h3",
          "",
          name ? "Editar asignación" : "Agregar recurso",
          " · ",
          state.proyectoId,
        ),
        button("✕", actions.close),
      ),
      el(
        "form",
        { id: "ixs-recurso-form", onsubmit: actions.save },
        input("Nombre del recurso", {
          name: "nombre",
          required: true,
          maxlength: 150,
          readonly: !!name,
          value: name,
        }),
        input("Rol", {
          name: "rol",
          required: true,
          maxlength: 100,
          value: src.rol || src.posicion || "",
        }),
        input("Horas estimadas", {
          name: "horas",
          type: "number",
          min: 0,
          max: 100000,
          step: "0.01",
          required: true,
          value: Number(src.horasEstimadas) || 0,
        }),
        h(
          "label",
          "",
          "Estado",
          el(
            "select",
            { name: "activo" },
            el(
              "option",
              { value: "true", selected: src.activo !== false },
              "Activo",
            ),
            el(
              "option",
              { value: "false", selected: src.activo === false },
              "Inactivo",
            ),
          ),
        ),
        el("div", { id: "ixs-recurso-error", class: "ixs-resources-error" }),
        div(
          "ixs-resource-form-actions",
          button("Cancelar", actions.close, "ixs-btn", { type: "button" }),
          el(
            "button",
            { type: "submit", class: "ixs-btn primary" },
            "Guardar recurso",
          ),
        ),
      ),
    ),
  );
  modal.addEventListener("click", (event) => {
    if (event.target === modal) actions.close();
  });
  document.body.append(modal);
}
