import { el } from "#app/lib/dom.js";

export function workItemProgress(dev, qa) {
  return Math.round((Number(dev) || 0) * 0.8 + (qa ? 20 : 0));
}

function renderProgress(cell, row) {
  const value = workItemProgress(
    row.querySelector("td:nth-child(5) input")?.value,
    row.querySelector("td:nth-child(6) input")?.checked,
  );
  const fill = el("div", { class: "progress-bar-fill ixs-plan-saved-fill" });
  fill.style.width = value + "%";
  cell.replaceChildren(
    el("div", { class: "progress-bar-bg ixs-plan-saved-progress" }, fill),
    value + "%",
  );
}

export function createWorkItemActions(api) {
  let session;
  const busyComments = new WeakSet(),
    timers = new WeakMap();
  return {
    bind(project, azure, guards, paint, options = {}) {
      const owner = {};
      session = owner;
      const current = (row) =>
        session === owner &&
        guards.current(project) &&
        guards.active() &&
        row.isConnected;
      return {
        async update(id, field, value) {
          const row = document.getElementById("wi-row-" + id);
          if (!row || !current(row)) return;
          try {
            const result = await api.saveWorkItem(id, field, value);
            if (!current(row)) return;
            if (!result || !result.ok) {
              window.alert(
                "Error al guardar: " + (result ? result.error : "desconocido"),
              );
              return;
            }
            const cell = document.getElementById("wi-avance-" + id);
            if (cell) renderProgress(cell, row);
            if (
              field === "fechaLimiteDev" &&
              options.refreshDeadline !== false
            ) {
              const item = azure.items.find((x) => Number(x.id) === Number(id));
              if (item) item.fechaLimiteDev = value || "";
              paint();
            }
          } catch (error) {
            if (current(row)) window.alert("Error: " + error.message);
          }
        },
        async comment(id) {
          const row = document.getElementById("wi-row-" + id),
            input = document.getElementById("wi-comentario-" + id),
            status = document.getElementById("wi-comentario-status-" + id);
          if (!row || !input || !current(row) || busyComments.has(row)) return;
          const text = input.value.trim();
          if (!text) {
            window.alert("Escribe un comentario antes de enviar.");
            return;
          }
          const button = row.querySelector(".ixs-azure-comment button");
          busyComments.add(row);
          if (button) button.disabled = true;
          if (status) {
            clearTimeout(timers.get(status));
            status.textContent = "Enviando...";
          }
          try {
            const result = await api.commentWorkItem(id, text);
            if (!current(row)) return;
            if (!result || !result.ok) {
              if (status) status.textContent = "";
              window.alert(
                "Error al enviar comentario: " +
                  (result ? result.error : "desconocido"),
              );
              return;
            }
            input.value = "";
            if (status) {
              status.textContent = "✓ Publicado en Azure DevOps";
              timers.set(
                status,
                setTimeout(() => {
                  if (current(row)) status.textContent = "";
                }, 3000),
              );
            }
          } catch (error) {
            if (current(row)) {
              if (status) status.textContent = "";
              window.alert("Error: " + error.message);
            }
          } finally {
            busyComments.delete(row);
            if (button) button.disabled = false;
          }
        },
      };
    },
  };
}
