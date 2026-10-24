import {
  el,
  h,
  div,
  styled,
  button,
  text,
  muted,
  title,
  chip,
  notice,
} from "./aer_ai_dom.js";
import { table, cell } from "./aer_planning_dom.js";

export function minutesTable(mins, actions) {
  return styled(
    div(
      "",
      table(
        "aeri-table",
        ["Fecha", "Reunión / Tema", "Contenido", "Ver"],
        mins.map((x, i) => {
          const open = () => actions.minute(i);
          return el(
            "tr",
            {
              class: "aeri-minuta-row",
              role: "button",
              tabindex: 0,
              "aria-label": "Ver minuta: " + text(x.tema),
              onclick: open,
              onkeydown: (e) => {
                if (e.key === "Enter" || e.key === " ") {
                  e.preventDefault();
                  open();
                }
              },
            },
            cell(text(x.fecha)),
            cell(h("b", "", text(x.tema))),
            el(
              "td",
              {
                class: "aeri-minuta-preview",
                title: "Haz clic para ver el contenido completo",
              },
              (x.contenido || "").slice(0, 110) +
                (String(x.contenido || "").length > 110 ? "…" : ""),
            ),
            cell(
              button(
                "Ver minuta ↗",
                (e) => {
                  e.stopPropagation();
                  open();
                },
                "aer-btn aeri-minuta-open",
                { type: "button" },
              ),
            ),
          );
        }),
        "Sin minutas guardadas en IA.",
      ),
    ),
    { overflow: "auto" },
  );
}
const href = (value) =>
  /^https?:\/\//i.test(String(value || "")) ? value : "#";
export function documents(s, actions) {
  const cfg = s.config || {},
    files = s.archivos,
    list = files?.filas || [],
    hidden = !!s.archivosOcultos;
  const summary = cfg.folderUrl
    ? `Carpeta configurada · Proyecto: ${cfg.nombreBusqueda || "—"} · Nombre frecuente: ${cfg.nombreFrecuente || "Sin configurar"}`
    : "Sin carpeta configurada. Usa «Configuración minuta» para guardar la URL y el nombre frecuente de los archivos.";
  const status = el("div", { id: "aeri-folder-status" });
  if (s.errorBusqueda) notice(status, s.errorBusqueda, true);
  else if (s.buscando) notice(status, "Buscando archivos en Google Drive…");
  return el(
    "div",
    { class: "aeri-card", id: "aeri-archivos-en-ia" },
    title(
      "▤ Documentos encontrados",
      div(
        "aer-actions",
        chip(
          files
            ? list.length + " de " + files.totalEncontradas
            : "Sin búsqueda",
        ),
        button(
          s.buscando ? "Buscando…" : "⌕ Buscar de nuevo",
          actions.files,
          "aer-btn primary",
          { id: "aeri-folder-scan", disabled: !!s.buscando },
        ),
        button(
          hidden ? "Mostrar resultados ▾" : "Ocultar resultados ×",
          actions.hideFiles,
        ),
      ),
    ),
    styled(muted(summary), { overflowWrap: "anywhere" }),
    status,
    ...(hidden
      ? [
          styled(
            muted(
              "Listado contraído. Pulsa «Mostrar resultados» para ver los documentos.",
            ),
            { marginTop: "8px" },
          ),
        ]
      : [
          ...(files
            ? [
                styled(
                  muted(
                    `Carpeta: ${files.carpeta || ""} · Búsqueda: ${files.busqueda || ""} · Archivos: ${files.patron || ""}${files.limitado ? " · Límite de escaneo alcanzado" : ""}`,
                  ),
                  { margin: "8px 0" },
                ),
              ]
            : []),
          div(
            "aeri-drivefiles",
            ...(list.length
              ? list.map((x) =>
                  div(
                    "aeri-driveitem",
                    el("input", {
                      type: "checkbox",
                      disabled: !x.legible,
                      title: x.legible
                        ? null
                        : "Solo vínculo: para extraer texto usa Google Docs o TXT",
                      checked: s.seleccion.includes(x.id),
                      onchange: (e) =>
                        actions.selectFile(x.id, e.target.checked),
                    }),
                    styled(
                      div(
                        "",
                        h("b", "", text(x.nombre)),
                        h(
                          "small",
                          "",
                          `${text(x.fecha)} · ${x.legible ? "Disponible para Claude" : "Solo vínculo · convierte a Google Docs/TXT"}`,
                        ),
                      ),
                      { minWidth: 0, overflowWrap: "anywhere" },
                    ),
                    el(
                      "a",
                      {
                        target: "_blank",
                        rel: "noopener noreferrer",
                        href: href(x.url),
                      },
                      "Abrir ↗",
                    ),
                  ),
                )
              : [
                  styled(
                    muted(
                      files
                        ? "No se encontraron documentos que coincidan con el proyecto y el nombre frecuente. Revisa Configuración minuta."
                        : "Configura la carpeta y pulsa «Buscar minutas».",
                    ),
                    { padding: "12px" },
                  ),
                ]),
          ),
          div(
            "aeri-mutedfoot",
            `Selecciona hasta 5 archivos. Claude solo recibirá fragmentos de los seleccionados cuando pulses «Generar borrador». ${s.seleccion.length} seleccionado(s). `,
            button("✦ Generar borrador", actions.openMinute),
          ),
        ]),
  );
}
