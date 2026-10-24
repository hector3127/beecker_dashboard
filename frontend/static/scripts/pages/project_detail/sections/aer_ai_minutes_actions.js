import { notice } from "./aer_ai_dom.js";
import { today } from "./aer_ai_model.js";

const node = (id) => document.getElementById(id);
const value = (id) => node(id)?.value || "";
const message = (e) => e?.message || String(e);
const button = (btn, label, disabled) => {
  if (btn?.isConnected) {
    btn.textContent = label;
    btn.disabled = disabled;
  }
};

export function minuteActions(api, env) {
  const s = env.state,
    live = env.current;
  const paint = () => {
    if (env.active()) env.paint();
  };
  const actions = {
    async generateMinute() {
      const notes = value("aeri-minute-notes"),
        topic = value("aeri-minute-topic"),
        date = value("aeri-minute-date") || today(),
        ids = (s.seleccion || []).slice();
      const btn = node("aeri-minute-generate"),
        modal = node("aer-modal-back"),
        out = node("aeri-minute-result");
      if (btn?.disabled) return;
      if (!ids.length && notes.trim().length < 15) {
        env.toast(
          "Escribe al menos 15 caracteres de notas o selecciona minutas de Drive.",
          "error",
        );
        return;
      }
      button(btn, "Generando…", true);
      try {
        const result = await api.aerAiAction(
          env.id,
          ids.length ? "minuta-drive" : "minuta-borrador",
          {
            contexto: env.context(),
            ...(ids.length
              ? { datos: { ids, tema: topic, fecha: date, notas: notes } }
              : {
                  texto:
                    "Tema: " + topic + "; Fecha: " + date + "; Notas: " + notes,
                }),
          },
        );
        if (!live() || !modal?.isConnected) return;
        button(btn, "✦ Generar borrador", false);
        if (!result?.ok) {
          notice(out, result?.error || "Error generando minuta", true);
          return;
        }
        env.presentation().draft(result);
      } catch (e) {
        if (live() && modal?.isConnected) {
          button(btn, "Reintentar", false);
          notice(out, message(e), true);
        }
      }
    },
    async saveMinute() {
      const data = {
          tema: value("aeri-minute-topic"),
          fecha: value("aeri-minute-date"),
          contenido: value("aeri-minute-text"),
        },
        btn = node("aeri-minute-save"),
        modal = node("aer-modal-back");
      if (btn?.disabled) return;
      if (!data.tema.trim() || !data.contenido.trim()) {
        env.toast("Captura tema y minuta.", "error");
        return;
      }
      button(btn, "Guardando…", true);
      try {
        const r = await api.aerAiAction(env.id, "minuta-guardar", {
          datos: data,
        });
        if (!live()) return;
        if (!r?.ok) {
          button(btn, "Reintentar", false);
          env.error(r?.error || "No se pudo guardar");
          return;
        }
        env.toast("Minuta guardada");
        s.minutas = null;
        if (modal?.isConnected) modal.remove();
        env.sources().minutes();
      } catch (e) {
        if (live()) {
          button(btn, "Reintentar", false);
          env.error(e);
        }
      }
    },
    async resetPrompt() {
      const area = node("aeri-minute-prompt");
      if (!area || s.cargandoPromptDefecto) return;
      s.cargandoPromptDefecto = true;
      try {
        const r = await api.aerAiSource(env.id, "prompt");
        if (!live()) return;
        s.cargandoPromptDefecto = false;
        if (!r?.ok) {
          env.toast(
            r?.error || "No se pudo cargar el prompt predeterminado.",
            "error",
          );
          return;
        }
        if (area.isConnected) {
          area.value = r.prompt || "";
          env.toast(
            "Prompt predeterminado cargado. Pulsa Guardar configuración para conservarlo.",
          );
        }
      } catch (e) {
        if (live()) {
          s.cargandoPromptDefecto = false;
          env.toast(message(e), "error");
        }
      }
    },
    async saveConfig(search) {
      const ids = [
        "aeri-folder-url",
        "aeri-folder-name",
        "aeri-file-pattern",
        "aeri-minute-prompt",
      ];
      if (ids.some((id) => !node(id))) {
        env.toast(
          "No se mostraron todos los campos. Cierra y abre Configuración minuta.",
          "error",
        );
        return;
      }
      const config = {
        folderUrl: value(ids[0]).trim(),
        nombreBusqueda: value(ids[1]).trim(),
        nombreFrecuente: value(ids[2]).trim(),
        promptMinuta: value(ids[3]).trim(),
      };
      const status = node("aeri-config-status"),
        btn = node(search ? "aeri-folder-save-scan" : "aeri-folder-save"),
        modal = node("aer-modal-back");
      if (btn?.disabled) return;
      if (
        !config.folderUrl ||
        !config.nombreBusqueda ||
        !config.nombreFrecuente
      ) {
        notice(
          status,
          "Completa los tres campos: link de carpeta, nombre del proyecto y nombre frecuente de los archivos.",
          true,
        );
        return;
      }
      button(btn, search ? "Guardando y buscando…" : "Guardando…", true);
      try {
        const r = await api.aerAiAction(env.id, "config-guardar", {
          datos: config,
        });
        if (!live()) return;
        if (!r?.ok) {
          button(btn, "Reintentar", false);
          if (status?.isConnected)
            notice(status, r?.error || "Error guardando", true);
          return;
        }
        s.config = r.config || {};
        s.archivos = null;
        s.seleccion = [];
        env.toast("Configuración de minuta guardada");
        if (modal?.isConnected) modal.remove();
        if (search) {
          s.mostrarArchivos = true;
          s.archivosOcultos = false;
          if (!env.active()) env.tab();
          env.sources().files();
        } else if (s.mostrarArchivos) paint();
      } catch (e) {
        if (live()) {
          button(btn, "Reintentar", false);
          if (status?.isConnected) notice(status, message(e), true);
        }
      }
    },
    copyMinute() {
      const t = node("aeri-minute-text");
      if (!t) return;
      t.select();
      document.execCommand("copy");
      env.toast("Texto copiado.");
    },
    copySavedMinute() {
      const box = node("aeri-minuta-read");
      if (!box) return;
      const ok = copy(box.textContent || "", true);
      env.toast(
        ok
          ? "Contenido de la minuta copiado"
          : "No se pudo copiar. Selecciona el texto manualmente.",
        ok ? "success" : "error",
      );
    },
    copySummary() {
      const ok = copy(s.resumenEjecutivo?.contenido || "", false);
      env.toast(
        ok ? "Resumen copiado" : "No se pudo copiar el resumen",
        ok ? "success" : "error",
      );
    },
  };
  return actions;
}

function copy(text, top) {
  const area = document.createElement("textarea");
  area.value = text;
  Object.assign(area.style, {
    position: "fixed",
    left: "-9999px",
    opacity: 0,
    ...(top ? { top: 0 } : {}),
  });
  document.body.append(area);
  area.select();
  let ok = false;
  try {
    ok = document.execCommand("copy");
  } catch {
    ok = false;
  }
  area.remove();
  return ok;
}
