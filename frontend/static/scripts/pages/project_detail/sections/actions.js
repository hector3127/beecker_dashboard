import { actionsModel } from "./actions_model.js";
import { renderActions, openAction, openPart } from "./actions_view.js";

const value = (id) => document.getElementById(id)?.value ?? "";
const message = (error) => error?.message || String(error || "");

export function createActionsController(api) {
  return {
    mount(target, env) {
      renderActions(
        target,
        actionsModel(env.dashboard),
        env.parts(),
        this.bind(env),
      );
    },
    bind(env) {
      const live = () => env.current();
      const send = (operation, body) =>
        api.saveAction(env.id, operation, { ...body, servicio: env.family });
      const publish = (result) => {
        if (result.acciones) env.actions(result.acciones);
      };
      const saving = (button) => {
        if (!button)
          return { done() {}, error: (text) => env.toast(text, "error") };
        const original = button.textContent;
        button.disabled = true;
        button.classList.add("saving");
        button.textContent = "Guardando acción...";
        return {
          done: () => env.toast("Acción guardada", "success"),
          error: (text) => {
            button.disabled = false;
            button.classList.remove("saving");
            button.textContent = original;
            if (text) env.toast(text, "error");
          },
        };
      };
      const methods = {
        open(uid = "") {
          return openAction(env.dashboard, uid, methods);
        },
        openPart() {
          return openPart(methods);
        },
        async save(uid) {
          const box = document.getElementById("aer-modal-back"),
            button = box?.querySelector(".aer-actions .aer-btn.primary");
          if (button?.disabled) return;
          const saver = saving(button);
          try {
            const r = await send("guardar", {
              UID: uid,
              ID_Proyecto: env.id,
              Accion: value("aa-a"),
              Responsable: value("aa-r"),
              Fecha_Inicio: value("aa-fi"),
              Fecha_Limite: value("aa-f"),
              Fecha_Real: value("aa-fr"),
              Estado: value("aa-e"),
              Dependencia: value("aa-d"),
              Prioridad: value("aa-p"),
              Notas: value("aa-n"),
            });
            if (!live()) return;
            if (!r?.ok) {
              if (box?.isConnected)
                saver.error(r?.error || "No se pudo guardar.");
              return;
            }
            saver.done();
            if (box?.isConnected) box.remove();
            publish(r);
          } catch (error) {
            if (live() && box?.isConnected) saver.error(message(error));
          }
        },
        async field(uid, campo, valor) {
          const status = document.getElementById(`aer-action-save-${uid}`);
          if (status) {
            status.textContent = "Guardando…";
            status.className = "aer-action-save-state saving";
          }
          try {
            const r = await send("actualizar", { uid, campo, valor });
            if (!live()) return;
            if (!r?.ok) {
              if (status) {
                status.textContent = "Error";
                status.className = "aer-action-save-state error";
              }
              env.error(r?.error);
              return;
            }
            if (status) {
              status.textContent = "✓ Guardado";
              status.className = "aer-action-save-state saved";
            }
            if (r.acciones) {
              env.storeActions(r.acciones);
              setTimeout(() => {
                if (live() && env.active()) env.paint();
              }, 350);
            }
          } catch (error) {
            if (live()) {
              if (status) {
                status.textContent = "Error";
                status.className = "aer-action-save-state error";
              }
              env.error(error);
            }
          }
        },
        async clean() {
          try {
            const r = await send("limpiar-duplicados", {});
            if (!live()) return;
            if (!r?.ok) {
              env.error(r?.error);
              return;
            }
            publish(r);
            alert(
              Number(r.eliminados || 0) > 0
                ? `Se eliminaron ${r.eliminados} acción(es) duplicada(s).`
                : "No se encontraron duplicados.",
            );
          } catch (error) {
            if (live()) env.error(error);
          }
        },
        async remove(uid, close = false) {
          if (!confirm("¿Eliminar esta acción?")) return;
          const box = document.getElementById("aer-modal-back");
          try {
            const r = await send("eliminar", { uid });
            if (!live()) return;
            if (!r?.ok) {
              env.error(r?.error);
              return;
            }
            if (close && box?.isConnected) box.remove();
            const rows = await api.actions(env.id, env.family);
            if (live() && rows?.ok) publish(rows);
          } catch (error) {
            if (live()) env.error(error);
          }
        },
        async loadParts(force) {
          if (env.partsLoading() || (!force && env.parts() !== null)) return;
          env.loadingParts(true);
          try {
            const r = await api.actions(env.id, env.family, true);
            if (!live()) return;
            env.loadingParts(false);
            if (!r?.ok) {
              env.toast(
                r?.error || "Error cargando pendientes Beecker/Cliente",
                "error",
              );
              return;
            }
            env.setParts(r.filas || []);
            env.paintParts();
          } catch (error) {
            if (live()) {
              env.loadingParts(false);
              env.toast(message(error), "error");
            }
          }
        },
        async savePart() {
          const button = document.getElementById("aerp-new-save"),
            box = document.getElementById("aer-modal-back");
          const datos = {
            accion: value("aerp-new-accion"),
            responsable: value("aerp-new-parte"),
            estado: value("aerp-new-estado"),
            fechaLimite: value("aerp-new-fecha"),
            proximaRevision: value("aerp-new-revision"),
            notas: value("aerp-new-notas"),
          };
          if (!datos.accion.trim()) {
            env.toast("Escribe el pendiente.", "error");
            return;
          }
          if (button?.disabled) return;
          if (button) {
            button.disabled = true;
            button.textContent = "Guardando…";
          }
          try {
            const r = await send("parte-guardar", { datos });
            if (!live()) return;
            if (!r?.ok) {
              if (button?.isConnected) {
                button.disabled = false;
                button.textContent = "Reintentar";
              }
              env.toast(r?.error || "No se pudo guardar", "error");
              return;
            }
            env.setParts(r.filas || []);
            if (box?.isConnected) box.remove();
            if (env.active()) env.paint();
            env.toast("Pendiente guardado", "success");
          } catch (error) {
            if (live()) {
              if (button?.isConnected) {
                button.disabled = false;
                button.textContent = "Reintentar";
              }
              env.toast(message(error), "error");
            }
          }
        },
        async partField(uid, campo, valor) {
          const status = document.getElementById("aeri-partes-status");
          if (status) status.textContent = "Guardando cambios…";
          try {
            const r = await send("parte-actualizar", { uid, campo, valor });
            if (!live()) return;
            if (!r?.ok) {
              if (status) status.textContent = "Error al guardar";
              env.toast(r?.error || "Error guardando pendiente", "error");
              return;
            }
            env.setParts(r.filas || []);
            if (status) status.textContent = "✓ Guardado";
          } catch (error) {
            if (live()) {
              if (status) status.textContent = "Error al guardar";
              env.toast(message(error), "error");
            }
          }
        },
        async removePart(uid) {
          if (!confirm("¿Eliminar este pendiente Beecker / Cliente?")) return;
          try {
            const r = await send("parte-eliminar", { uid });
            if (!live()) return;
            if (!r?.ok) {
              env.toast(r?.error || "No se pudo eliminar", "error");
              return;
            }
            env.setParts(r.filas || []);
            if (env.active()) env.paint();
            env.toast("Pendiente eliminado", "success");
          } catch (error) {
            if (live()) env.toast(message(error), "error");
          }
        },
      };
      return methods;
    },
  };
}
