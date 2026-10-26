// @ts-check
// controller: eva/history. Original data, ordering and interactions are preserved.
import { apiGet } from "#app/data/api-client.js";
import { el } from "#app/lib/dom.js";
import { node, renderIxbHistory, renderAerHistory } from "./history_view.js";
/**
 * @param {any} options
 */
export function mountHistory({
  box,
  body,
  path,
  aer = false,
  afterLoad = () => {},
}) {
  let loaded = false,
    busy = false;
  async function load() {
    if (loaded || busy) return;
    busy = true;
    if (aer) body.textContent = "Cargando proyectos finalizados...";
    else
      body.replaceChildren(
        el("p", {
          class: "note",
          text: "Cargando proyectos cerrados… puede tardar unos segundos.",
        }),
      );
    try {
      const result = await apiGet(path, undefined, { timeout: 90000 });
      body.replaceChildren(
        ...(aer
          ? renderAerHistory(result.data)
          : renderIxbHistory(result.data)),
      );
      loaded = true;
      afterLoad(body);
    } catch (error) {
      const retry = el("button", {
        type: "button",
        class: aer ? null : "eva-btn",
        ...(aer ? {} : { id: "eva-closed-retry" }),
        text: "Reintentar",
        onclick: load,
      });
      body.replaceChildren(
        node(
          "p",
          { class: aer ? null : "note" },
          aer
            ? "No se pudo cargar el historico. "
            : "No se pudo cargar el histórico. ",
          retry,
        ),
      );
    } finally {
      busy = false;
    }
  }
  box.addEventListener("toggle", () => {
    if (box.open) load();
  });
}
export { renderIxbHistory, renderAerHistory } from "./history_view.js";
