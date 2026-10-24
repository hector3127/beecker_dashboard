import { el, h, div, styled, button, text } from "./aer_planning_dom.js";
import { summaryMarkup } from "./aer_ai_presentation_model.js";
export { el, h, div, styled, button, text };
export const muted = (value) => div("aeri-muted", value);
export const card = (...nodes) => div("aeri-card", ...nodes);
export const title = (label, ...nodes) =>
  div("aeri-cardtitle", h("h3", "", label), ...nodes);
export const chip = (value) => h("span", "aeri-chip", text(value));
export const br = () => h("br", "");

// Only these three generated tags become nodes. Escaped content stays text.
export function formatted(value) {
  const root = document.createDocumentFragment(),
    stack = [root];
  const entities = {
    "&amp;": "&",
    "&lt;": "<",
    "&gt;": ">",
    "&quot;": '"',
    "&#039;": "'",
    "&bull;": "•",
  };
  for (const part of summaryMarkup(value).split(/(<strong>|<\/strong>|<br>)/)) {
    const parent = stack.at(-1);
    if (part === "<strong>") {
      const node = h("strong", "");
      parent.append(node);
      stack.push(node);
    } else if (part === "</strong>") {
      if (stack.length > 1) stack.pop();
    } else if (part === "<br>") parent.append(br());
    else
      parent.append(
        document.createTextNode(
          part.replace(/&(?:amp|lt|gt|quot|#039|bull);/g, (x) => entities[x]),
        ),
      );
  }
  return root;
}
export function notice(node, message, fail = false) {
  if (node)
    node.replaceChildren(
      styled(
        div("aeri-answer", text(message)),
        fail ? { color: "#b62843", background: "#fff2f4" } : {},
      ),
    );
}
export function modal(content, width) {
  document.getElementById("aer-modal-back")?.remove();
  const back = el("div", { class: "aer-modal-back", id: "aer-modal-back" });
  const box = div("aer-modal", content);
  if (width) box.style.width = width;
  back.append(box);
  back.addEventListener("click", (event) => {
    if (event.target === back) back.remove();
  });
  document.body.append(back);
  return back;
}
export const close = () => document.getElementById("aer-modal-back")?.remove();
export function chat(state) {
  const r = state.respuestaChatResumen;
  if (!r?.texto) return null;
  return el(
    "div",
    { class: "aeri-answer aeri-chat-summary", role: "status" },
    div("aeri-chat-summary-content", formatted(r.texto)),
    div(
      "aeri-chat-summary-status",
      r.persistido
        ? "✓ Resumen guardado en Google Sheets · " + (r.guardado || "")
        : "⚠ Resumen generado, pero no se pudo guardar en Sheets.",
    ),
  );
}
