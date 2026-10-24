// View, forms and writes are modular; filter/range state still comes from the bridge.
import {
  capacity,
  parsePlanText,
  planningModel,
} from "./aer_planning_model.js";
import { renderPlanning } from "./aer_planning_view.js";
import {
  openPlan,
  openVacation,
  openImport,
  previewImport,
} from "./aer_planning_forms.js";
const value = (id) => document.getElementById(id)?.value ?? "";
const today = () => new Date().toISOString().slice(0, 10);
const message = (e) => e?.message || String(e || "Error desconocido");

export function createAerPlanning(api) {
  return {
    mount(target, env) {
      const actions = { ...this.bind(env), ...env.controls };
      renderPlanning(
        target,
        planningModel(env.dashboard, env.range),
        env.filters,
        actions,
      );
    },
    bind(env) {
      const live = () => env.current();
      const send = (operation, body) =>
        api.saveAerPlan(env.id, operation, body);
      const box = () => document.getElementById("aer-modal-back");
      const close = (modal) => {
        if (modal?.isConnected) modal.remove();
      };
      const publish = (result, vacation = false) => {
        if (vacation)
          env.dashboard.vacaciones = result.vacaciones || { filas: [] };
        else if (result.plan) env.dashboard.plan = result.plan;
        if (env.active()) env.paint();
      };
      async function save(operation, payload, vacation = false) {
        const modal = box(),
          button = modal?.querySelector(".aer-actions .aer-btn.primary");
        if (button?.disabled) return;
        const saver = env.saving(
          button,
          vacation ? "Guardando vacaciones..." : "Guardando actividad...",
        );
        try {
          const r = await send(operation, payload);
          if (!live()) return;
          if (!r?.ok) {
            if (modal?.isConnected)
              saver.error(
                r?.error ||
                  (vacation
                    ? "No se pudo guardar."
                    : "No se pudo guardar la actividad."),
              );
            return;
          }
          saver.ok(vacation ? "Vacaciones guardadas" : "Actividad guardada");
          close(modal);
          publish(r, vacation);
        } catch (e) {
          if (live() && modal?.isConnected) saver.error(message(e));
        }
      }
      const methods = {
        openPlan(uid = "") {
          return openPlan(env.dashboard, uid, methods);
        },
        openVacation(uid = "") {
          return openVacation(env.dashboard, uid, methods);
        },
        openImport() {
          return openImport(env.dashboard, methods);
        },
        previewImport() {
          return previewImport(env.dashboard);
        },
        saveVacation(uid) {
          return save(
            "vacacion-guardar",
            {
              UID: uid,
              ID_Proyecto: env.id,
              Recurso: value("av-rec"),
              Inicio: value("av-ini"),
              Fin: value("av-fin"),
              Estado: value("av-est"),
              Comentarios: value("av-com"),
              Registrado_Por: value("av-reg"),
            },
            true,
          );
        },
        async removeVacation(uid) {
          if (!confirm("¿Eliminar este registro de vacaciones?")) return;
          const modal = box();
          try {
            const r = await send("vacacion-eliminar", { uid });
            if (!live()) return;
            if (!r?.ok) {
              env.error(r?.error);
              return;
            }
            close(modal);
            publish(r, true);
          } catch (e) {
            if (live()) env.error(e);
          }
        },
        savePlan(uid) {
          const estado = value("ap-est") || "Por iniciar";
          const cap = capacity(
            env.dashboard,
            value("ap-resp"),
            value("ap-ip"),
            value("ap-fp"),
            uid,
            Number(value("ap-ord") || 0),
            estado,
            value("ap-tipo") || "Actividad",
          );
          if (
            cap.max > 6 &&
            !confirm(
              `${value("ap-resp") || "El recurso"} quedará sobreasignado con ${cap.max}/6 puntos en parte del periodo. ¿Guardar de todos modos?`,
            )
          )
            return;
          const row =
            (env.dashboard.plan?.filas || []).find((x) => x.uid === uid) || {};
          return save("guardar", {
            UID: uid,
            ID_Proyecto: env.id,
            Tipo: value("ap-tipo"),
            Actividad: value("ap-act"),
            Responsable: value("ap-resp"),
            Inicio_Plan: value("ap-ip"),
            Fin_Plan: value("ap-fp"),
            Fin_Real:
              estado === "Completado"
                ? value("ap-fr") || row.finReal || today()
                : "",
            Estado: estado,
            Dependencia: value("ap-dep"),
            Estado_Dependencia: value("ap-dep-est"),
            Orden: value("ap-ord"),
            Notas: value("ap-not"),
          });
        },
        async removePlan(uid) {
          if (!confirm("¿Eliminar este elemento?")) return;
          const modal = box();
          try {
            // Original success callback reloads even if the service returns ok:false.
            await send("eliminar", { uid });
            if (!live()) return;
            close(modal);
            env.reload();
          } catch (e) {
            if (live()) env.error(e);
          }
        },
        async mark(uid, cerrado, checkbox) {
          if (!env.id || !uid) {
            if (checkbox) checkbox.checked = !cerrado;
            return;
          }
          if (checkbox) checkbox.disabled = true;
          const fail = (e) => {
            if (checkbox) {
              checkbox.checked = !cerrado;
              checkbox.disabled = false;
            }
            env.error(e);
          };
          try {
            const r = await send("cerrar", { uid, cerrado });
            if (!live()) return;
            if (!r?.ok) {
              fail(r?.error || "No se pudo guardar el cierre.");
              return;
            }
            env.reload();
          } catch (e) {
            if (live()) fail(e);
          }
        },
        async modalState(uid) {
          const estado = value("ap-est") || "Por iniciar",
            modal = box();
          const cierre =
            estado === "Completado" ? value("ap-fr") || today() : "";
          try {
            const r = await send("estado", { uid, estado, cierre });
            if (!live()) return;
            if (!r?.ok) {
              env.error(r?.error);
              return;
            }
            close(modal);
            publish(r);
          } catch (e) {
            if (live()) env.error(e);
          }
        },
        async inlineState(uid) {
          const row = (env.dashboard.plan?.filas || []).find(
            (x) => x.uid === uid,
          );
          if (!row) return;
          const sel = document.getElementById(`apt-est-${uid}`),
            date = document.getElementById(`apt-close-${uid}`),
            status = document.getElementById(`apt-save-${uid}`);
          const estado = sel ? sel.value : row.estado || "Por iniciar";
          let cierre = date ? date.value : row.finReal || "";
          if (date) {
            if (estado === "Completado") {
              date.disabled = false;
              if (!cierre) {
                cierre = row.finReal || today();
                date.value = cierre;
              }
            } else {
              cierre = "";
              date.value = "";
              date.disabled = true;
            }
          }
          if (status) {
            status.textContent = "Guardando…";
            status.className = "aer-autosave-state saving";
          }
          if (sel) sel.disabled = true;
          if (date) date.disabled = true;
          const fail = (e) => {
            if (status) {
              status.textContent = "Error";
              status.className = "aer-autosave-state error";
            }
            if (sel) sel.disabled = false;
            if (date) date.disabled = estado !== "Completado";
            env.error(e);
          };
          try {
            const r = await send("estado", { uid, estado, cierre });
            if (!live()) return;
            if (!r?.ok) {
              fail(r?.error || "No se pudo guardar.");
              return;
            }
            if (status) {
              status.textContent = "Guardado ✓";
              status.className = "aer-autosave-state saved";
              status.style.display = "inline-block";
            }
            publish(r);
          } catch (e) {
            if (live()) fail(e);
          }
        },
        async removeSelected() {
          const uids = [
            ...document.querySelectorAll(".aer-plan-row-check:checked"),
          ]
            .map((cb) => String(cb.value || "").trim())
            .filter(Boolean);
          const n = uids.length;
          if (!n) return;
          if (
            !confirm(
              `¿Eliminar ${n} actividad${n === 1 ? "" : "es"} / hito${n === 1 ? "" : "s"} seleccionado${n === 1 ? "" : "s"}?\n\nEsta acción elimina las filas de AER_Planeacion.`,
            )
          )
            return;
          const button = document.getElementById("aer-plan-delete-selected");
          if (button) {
            button.disabled = true;
            button.textContent = "Eliminando…";
          }
          const restore = () => {
            if (button) {
              button.disabled = false;
              button.textContent = "🗑 Eliminar seleccionadas";
            }
          };
          try {
            const r = await send("eliminar-lote", { uids });
            if (!live()) return;
            if (!r?.ok) {
              restore();
              env.error(r?.error || "No se pudieron eliminar las actividades.");
              return;
            }
            const count = Number(
              r.eliminadosFisicos != null
                ? r.eliminadosFisicos
                : r.eliminados || 0,
            );
            if (!count) {
              restore();
              alert(
                r.mensaje ||
                  "El servidor no encontró las filas seleccionadas en AER_Planeacion.",
              );
              return;
            }
            env.reload();
          } catch (e) {
            if (live()) {
              restore();
              env.error(e);
            }
          }
        },
        async importPlan() {
          const status = document.getElementById("aer-plan-import-status"),
            button = document.getElementById("aer-plan-import-btn"),
            modal = box();
          const statusText = (text, color) => {
            if (status) {
              status.style.color = color;
              status.textContent = text;
            }
          };
          const restore = () => {
            if (button) {
              button.disabled = false;
              button.textContent = "Importar";
            }
          };
          try {
            const parsed = parsePlanText(
              value("aer-plan-text"),
              env.dashboard.proyecto || {},
            );
            if (!parsed.ok) {
              statusText(parsed.error, "#c3273e");
              return;
            }
            if (!env.id) {
              statusText(
                "No encuentro el proyecto seleccionado. Cierra y vuelve a abrir el proyecto.",
                "#c3273e",
              );
              return;
            }
            if (button?.disabled) return;
            if (button) {
              button.disabled = true;
              button.textContent = "Importando…";
            }
            statusText(
              `Enviando ${parsed.items.length} actividad(es)…`,
              "var(--gris)",
            );
            let r;
            try {
              r = await send("importar", { items: parsed.items });
            } catch (e) {
              if (live()) {
                restore();
                const msg = "Error del servidor: " + message(e);
                if (status) statusText(msg, "#c3273e");
                else alert(msg);
              }
              return;
            }
            if (!live()) return;
            if (!r?.ok) {
              restore();
              const msg =
                "Error: " +
                (r?.error || "El servidor no confirmó la importación.");
              if (status) statusText(msg, "#c3273e");
              else alert(msg);
              return;
            }
            statusText(
              `Importación completa: ${r.guardados || 0} guardado(s)` +
                (r.nuevos != null ? ` · ${r.nuevos} nuevo(s)` : "") +
                (r.actualizados != null
                  ? ` · ${r.actualizados} actualizado(s)`
                  : "") +
                (r.duplicadosEliminados
                  ? ` · ${r.duplicadosEliminados} duplicado(s) eliminado(s)`
                  : "") +
                ".",
              "#16864e",
            );
            setTimeout(() => {
              if (live()) {
                close(modal);
                env.reload();
              }
            }, 650);
          } catch (e) {
            restore();
            statusText(
              "Error al preparar importación: " + message(e),
              "#c3273e",
            );
          }
        },
      };
      return methods;
    },
  };
}
