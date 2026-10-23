import { el } from "#app/lib/dom.js";
import { renderTranscripts } from "./ixs_ai_view.js";

const node = (tag, props = {}, ...children) => el(tag, props, ...children);
const note = (text) => node("p", { class: "ixai-muted", text });
const button = (text, onclick, primary = false, props = {}) =>
  node("button", {
    class: "ixai-btn" + (primary ? " primary" : ""),
    type: "button",
    text,
    onclick,
    ...props,
  });
const field = (label, name, type = "text", value = "", props = {}) => {
  const input = node(type === "textarea" ? "textarea" : "input", {
    name,
    ...(type === "textarea" ? {} : { type }),
    ...props,
  });
  if (type === "textarea") input.textContent = value;
  input.value = value;
  return node("label", {}, label, input);
};
const content = (value, scroll = false) =>
  node("div", {
    text: value,
    style: {
      whiteSpace: "pre-wrap",
      lineHeight: "1.6",
      ...(scroll ? { maxHeight: "50vh", overflow: "auto" } : {}),
    },
  });
const msg = (color = true) =>
  node("div", {
    id: "ixai-form-error",
    ...(color ? { style: { color: "#bf2550" } } : {}),
  });
const fail = (error) => error?.message || String(error);
const today = () => new Date().toISOString().slice(0, 10);

export function createAiController(api) {
  return {
    actions(s, deps) {
      const current = () => deps.current(s);
      const paint = () => {
        if (current()) deps.paint();
      };
      const close = () => document.getElementById("ixai-modal")?.remove();
      const modal = (title, ...body) => {
        close();
        const box = node("div", { id: "ixai-modal", class: "ixai-detail" });
        box.append(
          node(
            "div",
            { class: "ixai-dialog", role: "dialog", "aria-modal": "true" },
            node(
              "div",
              { class: "ixai-head" },
              node("h3", { text: title }),
              button("✕", close),
            ),
            ...body,
          ),
        );
        box.addEventListener("click", (e) => {
          if (e.target === box) box.remove();
        });
        document.body.append(box);
        return box;
      };
      const alive = (box) => current() && box.isConnected;
      const checked = async (task, fallback) => {
        const result = await task;
        if (!result?.ok) {
          const error = new Error(result?.error || fallback);
          error.serviceResponse = true;
          throw error;
        }
        return result;
      };
      const runForm = async (box, submit, message, busy, retry, task, done) => {
        if (submit.disabled) return;
        submit.disabled = true;
        submit.textContent = busy;
        try {
          const result = await checked(
            task(),
            retry === "Agregar carpeta"
              ? "No se pudo conectar."
              : retry === "Reintentar"
                ? "No se pudo generar."
                : "No se pudo guardar.",
          );
          if (alive(box)) done(result);
        } catch (error) {
          if (alive(box)) {
            submit.disabled = false;
            submit.textContent =
              retry === "Reintentar" && error.serviceResponse
                ? "✦ Regenerar borrador"
                : retry;
            message.textContent = fail(error);
          }
        }
      };
      const a = {
        tab: deps.tab,
        loadDrive: deps.loadDrive,
        setQuestion(q) {
          const input = document.getElementById("ixai-question");
          if (input) {
            input.value = q;
            s.question = q;
            input.focus();
          }
        },
        async analyze() {
          if (s.loading) return;
          s.loading = true;
          s.error = "";
          paint();
          try {
            const r = await api.aiAnalyze(s.id, deps.context(), true);
            if (!current()) return;
            s.loading = false;
            if (r?.ok) {
              s.analisis = r;
              if (r.avisoGuardado) s.error = r.avisoGuardado;
            } else s.error = r?.error || "No se pudo analizar el proyecto.";
          } catch (e) {
            if (!current()) return;
            s.loading = false;
            s.error = fail(e);
          }
          paint();
        },
        async ask(e) {
          e?.preventDefault();
          const input = document.getElementById("ixai-question"),
            q = input ? input.value.trim() : s.question;
          if (q.length < 5) {
            s.respuesta = "Escribe al menos 5 caracteres.";
            paint();
            return;
          }
          s.question = "";
          if (input) input.value = "";
          s.respuesta = "Consultando Claude Haiku…";
          paint();
          document.getElementById("ixai-question")?.focus();
          try {
            const r = await api.aiAsk(s.id, deps.context(), q);
            if (!current()) return;
            s.question = document.getElementById("ixai-question")?.value || "";
            s.respuesta = r?.ok ? r.texto : r?.error || "No hubo respuesta.";
          } catch (error) {
            if (!current()) return;
            s.question = document.getElementById("ixai-question")?.value || "";
            s.respuesta = fail(error);
          }
          paint();
        },
        async memory() {
          if (!s.azure || !s.clockify) {
            s.error =
              "Para guardar un corte comparable espera a que carguen Azure DevOps y Clockify.";
            paint();
            return;
          }
          const btn = document.querySelector(
            ".ixai-head-actions button:first-child",
          );
          if (btn?.disabled) return;
          if (btn) {
            btn.disabled = true;
            btn.textContent = "Guardando…";
          }
          try {
            const r = await api.aiSaveMemory(
              s.id,
              deps.snapshot(),
              s.analisis?.analisis || {},
            );
            if (!current()) return;
            if (r?.ok) {
              s.memoria = r;
              s.error = "";
            } else s.error = r?.error || "No se pudo actualizar la memoria.";
          } catch (error) {
            if (!current()) return;
            s.error = fail(error);
          }
          paint();
        },
        evidence(kind, index) {
          const analysis = s.analisis?.analisis || {},
            item = (
              kind === "recomendacion"
                ? analysis.recomendaciones
                : kind === "alertas"
                  ? analysis.alertas
                  : kind === "hallazgos"
                    ? analysis.hallazgos
                    : analysis.resumen || []
            )?.[index];
          const evidence = s.analisis?.evidencias || [],
            refs = item?.evidencias || [];
          const rows = refs.length
            ? evidence.filter((x) => refs.includes(x.id))
            : evidence
                .filter((x) => /^(PR-|ET-|AZ-RES|CL-RES|FIN-)/.test(x.id))
                .slice(0, 12);
          modal(
            "Evidencias del proyecto",
            node("p", {
              text:
                (item &&
                  [item.texto, item.titulo, item.detalle]
                    .filter(Boolean)
                    .join(" · ")) ||
                "Registros de origen consultados.",
            }),
            ...(rows.length
              ? rows.map((x) =>
                  node(
                    "div",
                    { class: "ixai-line" },
                    node("strong", { text: x.id + " · " + x.fuente }),
                    node("span", { text: x.texto }),
                  ),
                )
              : [note("Actualiza el análisis para vincular evidencias.")]),
            note(
              "Confirma el registro vigente en su pestaña de origen antes de tomar una decisión.",
            ),
          );
        },
        minute(i) {
          const m = s.minutas?.[i];
          if (m)
            modal(m.tema, node("p", { text: m.fecha }), content(m.contenido));
        },
        createMinute() {
          const form = node("form"),
            message = msg(),
            submit = button("Guardar minuta", null, true, { type: "submit" });
          const draft = button("Preparar borrador con IA", async () => {
            message.textContent = "Preparando borrador…";
            try {
              const r = await api.aiAsk(
                s.id,
                deps.context(),
                "Prepara un borrador de minuta de seguimiento con asuntos verificables. Deja sin completar los acuerdos de una reunión que no estén documentados.",
              );
              if (!alive(box)) return;
              message.textContent = r?.ok
                ? "Revisa y edita antes de guardar."
                : r?.error || "Error";
              if (r?.ok) form.elements.contenido.value = r.texto;
            } catch (e) {
              if (alive(box)) message.textContent = fail(e);
            }
          });
          form.append(
            field("Reunión / tema", "tema", "text", "Seguimiento · " + s.id, {
              required: true,
            }),
            field("Fecha", "fecha", "date", today(), { required: true }),
            field("Contenido editable", "contenido", "textarea", "", {
              required: true,
              placeholder:
                "Acuerdos, decisiones y pendientes respaldados por la reunión…",
            }),
            draft,
            message,
            submit,
          );
          const box = modal("Preparar minuta", form);
          form.addEventListener("submit", (e) => {
            e.preventDefault();
            runForm(
              box,
              submit,
              message,
              "Guardando…",
              "Guardar minuta",
              () =>
                api.aiSaveMinute(
                  s.id,
                  form.elements.tema.value,
                  form.elements.fecha.value,
                  form.elements.contenido.value,
                ),
              (r) => {
                s.minutas = r.filas;
                close();
                paint();
              },
            );
          });
        },
        report(audience) {
          const select = node(
            "select",
            { id: "ixai-audience" },
            ...["CEO", "COO", "CTO", "Delivery Manager", "Cliente"].map((x) =>
              node("option", { text: x }),
            ),
          );
          select.value = audience || "Delivery Manager";
          const draft = node("textarea", {
              id: "ixai-draft",
              placeholder: "Aquí aparecerá el borrador editable…",
            }),
            message = msg();
          const generate = button(
            "Generar borrador con IA",
            () =>
              generateText(
                box,
                message,
                draft,
                "Generando…",
                "Borrador editable listo.",
                "Prepara un reporte ejecutivo breve para " +
                  select.value +
                  ". Usa hechos respaldados y fuentes disponibles, con estado, cambios, bloqueos, decisiones y siguientes hitos.",
              ),
            true,
          );
          const box = modal(
            "Reporte ejecutivo editable",
            node("label", {}, "Destinatario", select),
            generate,
            note("El borrador no se publica ni se envía."),
            draft,
            message,
          );
        },
        communique() {
          const draft = node("textarea", {
              id: "ixai-draft",
              placeholder: "Borrador editable…",
            }),
            message = msg();
          const generate = button(
            "Preparar borrador",
            () =>
              generateText(
                box,
                message,
                draft,
                "Redactando…",
                "Borrador editable listo.",
                "Redacta un comunicado para el equipo sobre novedades verificadas del proyecto. Evita inventar anuncios, decisiones y compromisos.",
              ),
            true,
          );
          const box = modal(
            "Comunicado editable",
            note("Revisa el texto antes de publicarlo en Comunicación."),
            generate,
            draft,
            message,
          );
        },
        summarize() {
          const indices = [
            ...document.querySelectorAll(".ixai-minute-select:checked"),
          ]
            .map((x) => Number(x.value))
            .slice(0, 5);
          if (!indices.length) {
            s.error = "Selecciona al menos una minuta.";
            paint();
            return;
          }
          const picked = indices.map((i) => s.minutas[i]).filter(Boolean),
            ctx = {
              ...deps.context(),
              minutas: picked.map((m) => ({
                fecha: m.fecha,
                tema: m.tema,
                contenido: m.contenido.slice(0, 3500),
              })),
            };
          const draft = node("textarea", {
              id: "ixai-draft",
              placeholder: "Preparando resumen…",
            }),
            message = msg(false);
          const box = modal(
            "Resumen consolidado de minutas",
            note(
              picked.length +
                " minuta(s) seleccionada(s). El texto se puede editar.",
            ),
            draft,
            message,
          );
          api
            .aiAsk(
              s.id,
              ctx,
              "Resume únicamente los acuerdos y pendientes de las minutas seleccionadas; identifica de cuáles proviene cada punto.",
            )
            .then((r) => {
              if (alive(box))
                draft.value = r?.ok
                  ? r.texto
                  : r?.error || "No se pudo resumir.";
            })
            .catch((e) => {
              if (alive(box)) draft.value = fail(e);
            });
        },
        action(i) {
          const r = s.analisis?.analisis?.recomendaciones?.[i];
          if (!r) return;
          const form = node("form"),
            message = msg(),
            submit = button("Guardar acción", null, true, { type: "submit" });
          form.append(
            field("Acción", "accion", "text", r.titulo || "", {
              required: true,
            }),
            field(
              "Descripción / evidencia",
              "notas",
              "textarea",
              (r.detalle || "") + "\nFuente: " + (r.fuente || ""),
            ),
            field("Responsable", "responsable", "text", "", {
              placeholder: "Asignar responsable",
            }),
            field("Fecha compromiso", "fecha", "date"),
            message,
            submit,
          );
          const box = modal("Revisar acción sugerida", form);
          form.addEventListener("submit", (e) => {
            e.preventDefault();
            runForm(
              box,
              submit,
              message,
              "Guardar acción",
              "Guardar acción",
              () =>
                api.aiSaveAction(s.id, {
                  ID_Proyecto: s.id,
                  Accion: form.elements.accion.value,
                  Notas: form.elements.notas.value,
                  Responsable: form.elements.responsable.value,
                  Fecha_Limite: form.elements.fecha.value,
                }),
              () => {
                close();
                s.error = "Acción guardada en este proyecto.";
                paint();
              },
            );
          });
        },
        raid(type, i) {
          const rec = s.analisis?.analisis?.recomendaciones?.[i];
          if (rec)
            deps.raid(
              type,
              [rec.titulo, rec.detalle].filter(Boolean).join(" — "),
            );
        },
        configureDrive(type) {
          type = type === "transcripciones" ? type : "documentos";
          const form = node("form"),
            message = msg(),
            submit = button("Agregar carpeta", null, true, { type: "submit" });
          form.append(
            note(
              "Puedes agregar varias carpetas a este proyecto sin afectar a otros. Deben ser accesibles para la cuenta que ejecuta la aplicación.",
            ),
            field("Vínculo de carpeta", "url", "url", "", {
              required: true,
              placeholder: "https://drive.google.com/drive/folders/…",
            }),
            message,
            submit,
          );
          const box = modal("Agregar carpeta de " + type, form);
          form.addEventListener("submit", (e) => {
            e.preventDefault();
            runForm(
              box,
              submit,
              message,
              "Conectando…",
              "Agregar carpeta",
              () => api.aiSaveFolder(s.id, form.elements.url.value, type),
              () => {
                close();
                deps.loadDrive();
              },
            );
          });
        },
        async removeFolder(id, type) {
          try {
            const r = await api.aiRemoveFolder(s.id, id, type);
            if (!current()) return;
            if (r?.ok) deps.loadDrive();
            else {
              s.driveError = r?.error || "No se pudo quitar la carpeta.";
              paint();
            }
          } catch (e) {
            if (current()) {
              s.driveError = fail(e);
              paint();
            }
          }
        },
        toggleTranscript(id, input) {
          const selected = s.driveSelected || [];
          if (input.checked && selected.length >= 5) {
            input.checked = false;
            s.driveError = "Selecciona hasta cinco transcripciones.";
            return;
          }
          s.driveSelected = input.checked
            ? [...selected, id]
            : selected.filter((x) => x !== id);
          const out = document.getElementById("ixai-transcript-results");
          if (out) renderTranscripts(out, s, a);
        },
        prepareDriveMinute() {
          const count = (s.driveSelected || []).length,
            form = node("form"),
            message = msg(),
            submit = button("✦ Generar borrador", null, true, {
              type: "submit",
            });
          const draft = node("textarea", {
            id: "ixai-minute-draft",
            placeholder: "Borrador editable",
            style: { display: "none", minHeight: "200px" },
          });
          const save = button(
            "Guardar minuta",
            () =>
              draft.value.trim() &&
              runForm(
                box,
                save,
                message,
                "Guardando…",
                "Guardar minuta",
                () =>
                  api.aiSaveMinute(
                    s.id,
                    form.elements.tema.value,
                    form.elements.fecha.value,
                    draft.value,
                  ),
                (r) => {
                  s.minutas = r.filas;
                  close();
                  paint();
                },
              ),
            true,
            { id: "ixai-minute-save", style: { display: "none" } },
          );
          form.append(
            note(
              count +
                " transcripción(es) seleccionada(s). Puedes añadir apuntes reales y revisar el borrador antes de guardarlo.",
            ),
            field("Tema", "tema", "text", "Seguimiento · " + s.id, {
              required: true,
            }),
            field("Fecha", "fecha", "date", today(), { required: true }),
            field("Apuntes complementarios", "notas", "textarea", "", {
              maxlength: 2400,
              placeholder: "Acuerdos o puntos reales de la reunión…",
            }),
            submit,
            message,
            draft,
            save,
          );
          const box = modal("Preparar minuta desde transcripciones", form);
          form.addEventListener("submit", (e) => {
            e.preventDefault();
            const ids = [...(s.driveSelected || [])];
            if (!ids.length && form.elements.notas.value.trim().length < 15) {
              message.textContent =
                "Selecciona un archivo o escribe al menos 15 caracteres de apuntes.";
              return;
            }
            runForm(
              box,
              submit,
              message,
              "Generando…",
              "Reintentar",
              () =>
                api.aiGenerateMinute(
                  s.id,
                  ids,
                  form.elements.tema.value,
                  form.elements.fecha.value,
                  form.elements.notas.value,
                ),
              (r) => {
                submit.disabled = false;
                submit.textContent = "✦ Regenerar borrador";
                draft.value = r.texto;
                draft.style.display = "block";
                save.style.display = "inline-block";
                message.textContent =
                  "Revisa y edita el borrador antes de guardarlo.";
              },
            );
          });
        },
        async document(id) {
          const message = node("p", {
              id: "ixai-drive-message",
              text: "Leyendo documento…",
            }),
            out = node("div", { id: "ixai-drive-content" });
          const box = modal("Documento de Drive", message, out);
          try {
            const r = await api.aiReadDocument(s.id, id);
            if (!alive(box)) return;
            message.textContent = r?.ok
              ? r.nombre +
                (r.truncado ? " · Vista limitada a 18 000 caracteres" : "")
              : r?.error || "No se pudo leer el documento.";
            if (r?.ok)
              out.replaceChildren(
                content(r.contenido, true),
                button(
                  "Preparar minuta con este contenido",
                  () => {
                    a.createMinute();
                    const f = document.querySelector("#ixai-modal form");
                    if (f) {
                      f.elements.tema.value = r.nombre;
                      f.elements.fecha.value = r.fecha;
                      f.elements.contenido.value = r.contenido;
                    }
                  },
                  true,
                  { id: "ixai-import-drive" },
                ),
              );
          } catch (e) {
            if (alive(box)) message.textContent = fail(e);
          }
        },
      };
      async function generateText(box, message, draft, busy, ready, question) {
        message.textContent = busy;
        try {
          const r = await api.aiAsk(s.id, deps.context(), question);
          if (!alive(box)) return;
          message.textContent = r?.ok ? ready : r?.error || "Error";
          if (r?.ok) draft.value = r.texto;
        } catch (e) {
          if (alive(box)) message.textContent = fail(e);
        }
      }
      return a;
    },
  };
}
