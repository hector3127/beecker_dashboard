import { el } from "#app/lib/dom.js";
import { icon } from "./ixs_icons.js";

const note = (text) => el("p", { class: "ixai-muted", text });
const section = (name, title) =>
  el("section", { class: "ixai-card" }, el("h3", {}, icon(name), " " + title));

// Receive the unchanged model results. All source text enters through DOM text nodes.
export function renderAiPanels(capacity, changed, openResources) {
  const resources = section("chart", "Capacidad y estimaciones del proyecto");
  resources.append(
    note(
      "Horas acumuladas del ID; las vacaciones se muestran aparte. Comparativo acumulado por recurso y horas registradas en este ID.",
    ),
  );
  if (capacity.length) {
    resources.append(
      el(
        "table",
        { class: "ixai-table" },
        el(
          "thead",
          {},
          el(
            "tr",
            {},
            ...[
              "Recurso",
              "Consumidas",
              "Estimadas",
              "Balance",
              "Situación",
            ].map((text) => el("th", { text })),
          ),
        ),
        el(
          "tbody",
          {},
          ...capacity.map((r) =>
            el(
              "tr",
              {},
              ...[
                r.nombre,
                r.consumidas.toFixed(2) + " h",
                r.estimadas ? r.estimadas.toFixed(2) + " h" : "—",
                r.estimadas
                  ? (r.estimadas - r.consumidas).toFixed(2) + " h"
                  : "—",
                r.estimadas
                  ? r.consumidas > r.estimadas
                    ? "Excedido"
                    : "Dentro de estimación"
                  : "Sin estimación",
              ].map((text) => el("td", { text })),
            ),
          ),
        ),
      ),
    );
  } else
    resources.append(
      note("Cargando recursos y Clockify, o sin asignaciones activas."),
    );
  resources.append(
    el("button", {
      class: "ixai-btn",
      text: "Ver recursos",
      onclick: openResources,
    }),
  );

  const changes = section("clock", "Cambios desde el último corte");
  if (changed && !changed.incompleto) {
    changes.append(
      el(
        "div",
        { class: "ixai-three" },
        el(
          "div",
          {},
          "Horas registradas",
          el("br"),
          el("strong", {
            text:
              (changed.horas >= 0 ? "+" : "") + changed.horas.toFixed(2) + " h",
          }),
        ),
        el(
          "div",
          {},
          "WIs cerrados",
          el("br"),
          el("strong", { text: changed.cerrados }),
        ),
        el(
          "div",
          {},
          "WIs nuevos",
          el("br"),
          el("strong", { text: changed.nuevos }),
          el("br"),
          `RAID nuevos: ${changed.nuevosRaid} · Acciones completadas: ${changed.accionesCompletadas}`,
        ),
      ),
      note("Comparación con el corte del " + changed.fecha),
    );
  } else
    changes.append(
      note(
        changed
          ? "Faltan fuentes comparables para calcular diferencias."
          : "Aún no hay un análisis anterior para comparar. Guarda un corte en «Actualizar memoria».",
      ),
    );
  return el("div", { class: "ixai-two" }, resources, changes);
}
