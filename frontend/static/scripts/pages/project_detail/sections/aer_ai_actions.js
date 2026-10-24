import { notice } from "./aer_ai_dom.js";
import { isSummaryQuestion, summaryPayload } from "./aer_ai_actions_model.js";
import { minuteActions } from "./aer_ai_minutes_actions.js";
const node = (id) => document.getElementById(id);
const message = (e) => e?.message || String(e);
const button = (btn, label, disabled) => {
  if (btn?.isConnected) {
    btn.textContent = label;
    btn.disabled = disabled;
  }
};

export function createAerAiActions(api) {
  return {
    bind(env) {
      const s = env.state,
        live = env.current;
      const paint = () => {
        if (env.active()) env.paint();
      };
      return {
        ...minuteActions(api, env),
        async analyze(force) {
          if (s.cargando) return;
          const btn = node("aeri-analyze"),
            ctx = env.context();
          s.cargando = true;
          button(btn, "Analizando…", true);
          try {
            const r = await api.aerAiAction(env.id, "analizar", {
              contexto: ctx,
              forzar: !!force,
            });
            if (!live()) return;
            s.cargando = false;
            if (!r?.ok) {
              button(btn, "Reintentar análisis", false);
              env.error(r?.error || "Error al analizar");
              return;
            }
            s.analisis = Object.assign({}, r, { restaurado: false });
            s.analisisConsultado = true;
            paint();
            env.toast(
              (r.cache
                ? "Análisis recuperado del caché"
                : "Análisis generado") +
                (r.persistido ? " y guardado" : "") +
                " · costo est. $" +
                (r.uso?.usd || 0) +
                " USD",
            );
            if (r.aviso)
              console.warn("Persistencia del análisis IA: " + r.aviso);
          } catch (e) {
            if (live()) {
              s.cargando = false;
              button(btn, "Reintentar análisis", false);
              env.error(e);
            }
          }
        },
        async generateSummary() {
          if (s.generandoResumen) return;
          const btn = node("aeri-generate-summary");
          s.generandoResumen = true;
          button(btn, "Generando resumen…", true);
          try {
            const r = await api.aerAiAction(env.id, "generar-resumen", {
              contexto: env.context(),
              datos: summaryPayload(
                s,
                "Estado actual, semana próxima, pendientes del cliente, pendientes Beecker y riesgos.",
              ),
            });
            if (!live()) return;
            s.generandoResumen = false;
            if (!r?.ok) {
              button(btn, "Reintentar resumen", false);
              env.toast(r?.error || "No se pudo generar el resumen", "error");
              return;
            }
            if (r.resumen) {
              s.resumenEjecutivo = r.resumen;
              s.resumenConsultado = true;
            }
            paint();
            env.toast(
              r.persistido
                ? "Resumen generado y guardado en Sheets"
                : r.aviso || "Resumen generado pero no guardado",
              r.persistido ? "success" : "error",
            );
          } catch (e) {
            if (live()) {
              s.generandoResumen = false;
              button(btn, "Reintentar resumen", false);
              env.toast(message(e), "error");
            }
          }
        },
        async ask() {
          const input = node("aeri-question"),
            question = input?.value || "",
            box = node("aeri-response"),
            btn = node("aeri-ask");
          if (btn?.disabled) return;
          if (question.trim().length < 5)
            return notice(
              box,
              "Escribe una pregunta antes de consultar a Claude.",
              true,
            );
          const summary = isSummaryQuestion(question);
          button(btn, "…", true);
          notice(
            box,
            summary
              ? "Preparando resumen ejecutivo…"
              : "Consultando Claude Haiku 4.5…",
          );
          try {
            const r = await api.aerAiAction(
              env.id,
              summary ? "generar-resumen" : "preguntar",
              {
                contexto: env.context(),
                ...(summary
                  ? { datos: summaryPayload(s, question) }
                  : { texto: question }),
              },
            );
            if (!live()) return;
            button(btn, "➤", false);
            if (!r?.ok) {
              notice(
                node("aeri-response"),
                r?.error || "No hubo respuesta",
                true,
              );
              return;
            }
            if (summary) {
              if (r.resumen) {
                s.resumenEjecutivo = r.resumen;
                s.resumenConsultado = true;
              }
              s.respuestaChatResumen = {
                texto: String(r.texto || r.resumen?.contenido || ""),
                persistido: !!r.persistido,
                guardado: r.resumen?.guardado || "",
              };
              paint();
              if (!r.persistido)
                env.toast(
                  r.aviso ||
                    "Claude respondió, pero no se guardó el resumen en Sheets.",
                  "error",
                );
            } else
              notice(
                node("aeri-response"),
                r.texto +
                  "\n\n" +
                  (r.cache
                    ? "♻ Respuesta en caché"
                    : "Costo est. $" + (r.uso?.usd || 0) + " USD"),
              );
            const current = node("aeri-question");
            if (current && current.value === question) current.value = "";
          } catch (e) {
            if (live()) {
              button(btn, "➤", false);
              notice(node("aeri-response"), message(e), true);
            }
          }
        },
        async generateMail() {
          const q = node("aeri-mail-in")?.value || "",
            btn = node("aeri-mail-btn"),
            modal = node("aer-modal-back"),
            out = node("aeri-mail-out");
          if (btn?.disabled || q.trim().length < 5) return;
          button(btn, "Redactando…", true);
          try {
            const r = await api.aerAiAction(env.id, "correo", {
              contexto: env.context(),
              texto: q,
            });
            if (!live() || !modal?.isConnected) return;
            button(btn, "Generar borrador", false);
            notice(out, r?.ok ? r.texto : r?.error || "Error", !r?.ok);
          } catch (e) {
            if (live() && modal?.isConnected) {
              button(btn, "Reintentar", false);
              notice(out, message(e), true);
            }
          }
        },
      };
    },
  };
}
