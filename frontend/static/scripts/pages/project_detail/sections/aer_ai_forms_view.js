import {
  el,
  h,
  div,
  styled,
  button,
  text,
  muted,
  title,
  formatted,
  modal,
  close,
} from "./aer_ai_dom.js";
import { input } from "./aer_planning_dom.js";
import { today } from "./aer_ai_model.js";

const promptArea = (value, props) => {
  const node = el("textarea", props);
  node.value = text(value || "");
  return node;
};

export function readMinute(x, a) {
  return modal(
    div(
      "aeri",
      div(
        "aeri-minuta-modal-header",
        div(
          "",
          h("h3", "", "▤ " + (x.tema || "Minuta")),
          styled(
            muted(
              "Fecha de reunión: " +
                (x.fecha || "—") +
                (x.guardado ? " · Guardada: " + x.guardado : ""),
            ),
            { marginTop: "5px" },
          ),
        ),
        button("✕", close, "aer-btn", { "aria-label": "Cerrar minuta" }),
      ),
      el(
        "div",
        { class: "aeri-minuta-read", id: "aeri-minuta-read", role: "document" },
        x.contenido || "Sin contenido registrado.",
      ),
      div(
        "aeri-minuta-modal-actions",
        button("▣ Copiar contenido", a.copySavedMinute),
        button("Cerrar", close, "aer-btn primary"),
      ),
    ),
    "min(860px,96vw)",
  );
}
export function readSummary(r, a) {
  return modal(
    div(
      "aeri",
      div(
        "aeri-cardtitle",
        div(
          "",
          h("h3", "", "▤ Resumen ejecutivo automático"),
          muted("Último resumen guardado: " + (r.guardado || "—")),
        ),
        button("✕", close),
      ),
      styled(
        el(
          "div",
          { class: "aeri-minuta-read", id: "aeri-resumen-lectura" },
          formatted(r.contenido),
        ),
        { whiteSpace: "normal" },
      ),
      div(
        "aeri-minuta-modal-actions",
        button("Copiar texto", a.copySummary),
        button("Cerrar", close, "aer-btn primary"),
      ),
    ),
    "min(850px,96vw)",
  );
}
export function mailForm(a) {
  return modal(
    div(
      "aeri",
      title("✉ Borrador de correo con Claude", button("✕", close)),
      h(
        "label",
        "",
        "¿Qué debe comunicar el correo?",
        styled(
          el("textarea", {
            id: "aeri-mail-in",
            maxlength: 380,
            placeholder:
              "Describe lo que quieres comunicar sin agregar datos sensibles…",
          }),
          { width: "100%", minHeight: "90px" },
        ),
      ),
      el("div", { id: "aeri-mail-out" }),
      button("Generar borrador", a.generateMail, "aer-btn primary", {
        id: "aeri-mail-btn",
      }),
    ),
  );
}
export function minuteForm(s, a) {
  return modal(
    div(
      "aeri",
      title("▤ Generar minuta con Claude", button("✕", close)),
      muted(
        ((s.seleccion || []).length
          ? "Se usarán " +
            s.seleccion.length +
            " minuta(s) seleccionada(s) de Drive."
          : "Sin archivos seleccionados: se redactará a partir de tus apuntes. Para elegir documentos, pulsa «Buscar minutas» en IA y selecciona los archivos.") +
          " Se usará el prompt de «Configuración minuta» guardado para este proyecto. Claude no inventa asistentes, acuerdos ni fechas.",
      ),
      div(
        "aer-formgrid",
        h(
          "label",
          "",
          "Tema",
          el("input", {
            id: "aeri-minute-topic",
            placeholder: "Seguimiento semanal",
          }),
        ),
        h(
          "label",
          "",
          "Fecha",
          input(today(), { id: "aeri-minute-date", type: "date" }),
        ),
        h(
          "label",
          "aer-span2",
          "Apuntes o instrucciones complementarias",
          styled(
            el("textarea", {
              id: "aeri-minute-notes",
              maxlength: 2400,
              placeholder:
                "Opcional si seleccionaste minutas de Drive. Escribe acuerdos o instrucciones reales…",
            }),
            { minHeight: "120px" },
          ),
        ),
      ),
      div(
        "aer-actions",
        button("✦ Generar borrador", a.generateMinute, "aer-btn primary", {
          id: "aeri-minute-generate",
        }),
      ),
      el("div", { id: "aeri-minute-result" }),
    ),
  );
}
export function draft(result, a) {
  const target = document.getElementById("aeri-minute-result");
  if (!target) return;
  target.replaceChildren(
    styled(
      muted(
        "Borrador editable · " +
          (result.cache
            ? "respuesta en caché"
            : "costo est. $" + (result.uso?.usd || 0) + " USD"),
      ),
      { marginTop: "8px" },
    ),
    styled(el("textarea", { id: "aeri-minute-text" }, text(result.texto)), {
      width: "100%",
      minHeight: "240px",
      border: "1px solid #dcd4f0",
      borderRadius: "10px",
      padding: "10px",
    }),
    styled(
      div(
        "aer-actions",
        button("Copiar", a.copyMinute),
        button("Guardar minuta", a.saveMinute, "aer-btn primary", {
          id: "aeri-minute-save",
        }),
      ),
      { marginTop: "7px" },
    ),
  );
}
export function configForm(d, s, a) {
  const c = s.config || {},
    p = d.proyecto || {};
  const fields = el("div", {
    class: "aeri-config-fields",
    id: "aeri-config-fields",
  });
  const field = (id, label, value, placeholder, type = "text") => {
    const node = input(value || "", {
      id,
      name: id,
      type,
      autocomplete: "off",
      placeholder,
    });
    fields.append(
      el(
        "label",
        { for: id },
        label,
        styled(node, {
          display: "block",
          width: "100%",
          boxSizing: "border-box",
        }),
      ),
    );
  };
  field(
    "aeri-folder-url",
    "Link crudo de la carpeta de Google Drive",
    c.folderUrl,
    "Pega aquí el enlace completo de la carpeta",
    "url",
  );
  field(
    "aeri-folder-name",
    "Nombre o clave del proyecto",
    c.nombreBusqueda || p.nombre || p.id,
    "Ej. Macro - Célula",
  );
  field(
    "aeri-file-pattern",
    "Nombre frecuente de los archivos",
    c.nombreFrecuente,
    "Ej. Daily Scrum OXXO, Seguimiento, Comité",
  );
  fields.append(
    muted(
      "Puedes indicar varias frases frecuentes separadas por comas. La búsqueda usa la carpeta y el nombre frecuente guardados para este proyecto.",
    ),
    styled(
      el(
        "label",
        { for: "aeri-minute-prompt" },
        "Prompt para generar la minuta",
        styled(
          promptArea(c.promptMinuta, {
            id: "aeri-minute-prompt",
            name: "aeri-minute-prompt",
            maxlength: 3000,
            rows: 12,
          }),
          {
            display: "block",
            boxSizing: "border-box",
            width: "100%",
            minHeight: "210px",
            maxHeight: "370px",
            resize: "vertical",
            lineHeight: 1.5,
            marginTop: "6px",
            background: "#fff",
            border: "1px solid #dcd5f0",
            borderRadius: "9px",
            padding: "10px",
            color: "#251f53",
            fontSize: "11px",
            fontFamily: "inherit",
          },
        ),
      ),
      { marginTop: "5px" },
    ),
    muted(
      "El prompt se guarda por proyecto en Sheets. Claude lo usará al generar borradores nuevos; no cambia minutas ya guardadas.",
    ),
    button("↺ Restablecer prompt predeterminado", a.resetPrompt, "aer-btn", {
      type: "button",
    }),
  );
  return modal(
    div(
      "aeri aeri-config-modal",
      title("⚙ Configuración minuta", button("✕", close)),
      muted(
        `Configuración exclusiva de ${p.id || "este proyecto"}. Aquí puedes editar también el prompt que Claude usará para las minutas.`,
      ),
      fields,
      el("div", { id: "aeri-config-status", "aria-live": "polite" }),
      styled(
        div(
          "aer-actions",
          button("Cancelar", close),
          button(
            "Guardar configuración",
            () => a.saveConfig(false),
            "aer-btn",
            { id: "aeri-folder-save" },
          ),
          button(
            "⌕ Guardar y buscar",
            () => a.saveConfig(true),
            "aer-btn primary",
            { id: "aeri-folder-save-scan" },
          ),
        ),
        { justifyContent: "flex-end", marginTop: "12px" },
      ),
    ),
  );
}
