import { renderAi } from "./aer_ai_view.js";
import * as forms from "./aer_ai_forms_view.js";
import { notice } from "./aer_ai_dom.js";

export function createAerAiPresentation() {
  const bind = (env) => {
    const s = env.state,
      call = env.actions;
    const paint = () => {
      if (env.active()) env.paint();
    };
    const a = {
      ...call,
      history() {
        s.historialCompleto = !s.historialCompleto;
        paint();
      },
      hideFiles() {
        s.archivosOcultos = !s.archivosOcultos;
        paint();
      },
      selectFile(id, checked) {
        const selected = s.seleccion || [];
        if (checked) {
          if (selected.length >= 5) {
            env.toast(
              "Máximo 5 minutas por consulta para ahorrar tokens.",
              "error",
            );
            paint();
            return;
          }
          if (!selected.includes(id)) selected.push(id);
        } else s.seleccion = selected.filter((x) => x !== id);
        if (checked) s.seleccion = selected;
        paint();
      },
      question(q) {
        const node = document.getElementById("aeri-question");
        if (node) {
          node.value = q;
          node.focus();
        }
      },
      recommendation(index) {
        const r = s.analisis?.analisis?.recomendaciones?.[index];
        if (!r) return;
        call.action();
        setTimeout(() => {
          if (!env.current()) return;
          const action = document.getElementById("aa-a"),
            notes = document.getElementById("aa-n");
          if (action) action.value = r.titulo;
          if (notes) notes.value = r.detalle;
        }, 0);
      },
      minute(index) {
        const x = (s.minutas || [])[Number(index)];
        if (!x) {
          env.toast(
            "No se encontró la minuta. Actualiza el historial.",
            "error",
          );
          return;
        }
        forms.readMinute(x, a);
      },
      summary() {
        const r = s.resumenEjecutivo || {};
        if (!r.contenido) {
          env.toast("Primero genera un resumen ejecutivo.", "error");
          return;
        }
        forms.readSummary(r, a);
      },
      openMinute() {
        return forms.minuteForm(s, a);
      },
      mail() {
        return forms.mailForm(a);
      },
      config() {
        if (s.config === null) {
          if (s.cargandoConfig) {
            env.toast("Cargando configuración de minutas…");
            return;
          }
          call.loadConfig(true);
          return;
        }
        return forms.configForm(env.dashboard, s, a);
      },
      draft(result) {
        forms.draft(result, a);
      },
    };
    return a;
  };
  return {
    bind,
    notice,
    mount(target, env) {
      renderAi(target, env.dashboard, env.state, bind(env));
    },
  };
}
