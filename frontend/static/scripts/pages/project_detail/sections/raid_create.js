// @ts-check
// Alta de Risk, Issue u Opportunity: abre la ventana, pide opciones y prompt a
// la API v1, sugiere con Claude y publica en Azure DevOps solo al pulsar Crear.
import { createdNotice, prepareCreate } from "./raid_create_model.js";
import { TYPES } from "./raid_model.js";
import { buildForm, createModal, message, refreshOptions } from "./raid_create_view.js";

const text = (/** @type {any} */ error) => (error && error.message) || String(error);
const $ = (/** @type {string} */ id) => document.getElementById(id);

/** @param {any} api */
export function createRaidCreator(api) {
  /** @type {any} */
  let session = null;
  const live = (/** @type {string} */ tipo) => !!session && session.tipo === tipo && !!$("ixs-raid-modal");

  function close() {
    $("ixs-raid-modal")?.remove();
    session = null;
  }

  /** @param {HTMLButtonElement} button @param {string} busy @param {string} idle @param {() => Promise<any>} call @param {(r: any) => void} done */
  async function withButton(button, busy, idle, call, done) {
    button.disabled = true;
    button.textContent = busy;
    try {
      done(await call());
    } catch (error) {
      message(text(error), true);
    }
    button.disabled = false;
    button.textContent = idle;
  }

  return {
    close,
    /**
     * @param {string} tipo @param {any} data proyecto abierto
     * @param {{current: () => boolean, created: () => void}} hooks
     */
    open(tipo, data, hooks) {
      if (!(/** @type {any} */ (TYPES)[tipo]) || !data) return;
      close();
      const project = data.proyecto.id;
      const ctx = { project, options: /** @type {any} */ (null), fieldTypes: /** @type {any} */ ({}) };
      session = { tipo, project, ctx, hooks };
      const stillHere = () => live(tipo) && hooks.current();
      const freeText = () => /** @type {HTMLTextAreaElement | null} */ ($("ixs-raid-free"));

      const handlers = {
        close,
        savePrompt: (/** @type {HTMLButtonElement} */ button) => {
          const box = /** @type {HTMLTextAreaElement | null} */ ($("ixs-raid-prompt"));
          if (!box) return;
          const label = button.textContent || "";
          withButton(button, "Guardando…", label, () => api.saveRaidPrompt(tipo, box.value), (r) => {
            if (r && r.ok) {
              if (tipo !== "Risk" && r.prompt) box.value = r.prompt;
              message(`✓ Prompt de ${/** @type {any} */ (TYPES)[tipo].label} guardado.`);
            } else message((r && r.error) || "No se pudo guardar.", true);
          });
        },
        restorePrompt: (/** @type {HTMLButtonElement} */ button) => {
          const box = /** @type {HTMLTextAreaElement | null} */ ($("ixs-raid-prompt"));
          if (!box || tipo === "Risk") return;
          withButton(button, "Restaurando…", "Restaurar estándar", () => api.saveRaidPrompt(tipo, ""), (r) => {
            if (r && r.ok) {
              box.value = r.prompt || "";
              message("✓ Prompt estándar restaurado.");
            } else message((r && r.error) || "No se pudo restaurar.", true);
          });
        },
        manual: () => {
          const form = $("ixs-raid-form-wrap");
          if (!form || form.style.display !== "none") return;
          const free = freeText();
          buildForm(tipo, { descripcion: free ? free.value.trim() : "" }, ctx);
          const intro = $("ixs-raid-ai-intro");
          if (intro) intro.style.display = "none";
          const manual = $("ixs-raid-manual");
          if (manual) manual.style.display = "none";
          message("Completa el formulario y revisa los datos antes de crear el registro en Azure DevOps.");
          form.scrollIntoView({ behavior: "smooth", block: "start" });
        },
        suggest: async (/** @type {HTMLButtonElement} */ button) => {
          const intro = $("ixs-raid-ai-intro");
          if (intro) intro.style.display = "";
          const free = freeText();
          if (!free) return;
          const description = free.value.trim();
          if (description.length < 12) return message("Describe la situación con al menos 12 caracteres.", true);
          button.disabled = true;
          button.textContent = "Consultando Claude…";
          message("");
          try {
            const r = await api.suggestRaid(tipo, description);
            if (!live(tipo)) return;
            button.disabled = false;
            button.textContent = "✨ Volver a sugerir";
            if (!r || !r.ok) {
              message((r && r.error) || "Claude no respondió. Puedes llenar el formulario manualmente.", true);
              buildForm(tipo, { descripcion: description }, ctx);
              return;
            }
            buildForm(tipo, { ...(r.sugerencia || r) }, ctx);
            message("Sugerencia generada. Revisa y modifica los campos antes de crear en Azure.");
          } catch (error) {
            button.disabled = false;
            button.textContent = "✨ Sugerir con IA";
            message(text(error), true);
            buildForm(tipo, { descripcion: description }, ctx);
          }
        },
        create: async (/** @type {HTMLButtonElement} */ button) => {
          /** @type {Record<string, string>} */
          const values = {};
          document.querySelectorAll("#ixs-raid-form-wrap [data-raid-key]").forEach((f) => {
            values[/** @type {HTMLElement} */ (f).dataset.raidKey || ""] = /** @type {HTMLInputElement} */ (f).value.trim();
          });
          const prepared = prepareCreate(tipo, values, ctx.options);
          if ("error" in prepared) return message(prepared.error, true);
          button.disabled = true;
          button.textContent = "Creando en Azure…";
          message(`Publicando el ${/** @type {any} */ (TYPES)[tipo].label} en ${project}…`);
          try {
            const r = await api.createRaid(project, tipo, prepared.data);
            button.disabled = false;
            button.textContent = "Crear en Azure DevOps";
            if (!r || !r.ok) return message((r && r.error) || "Error al crear el registro.", true);
            message(createdNotice(r), !r.vinculoConfirmado);
            setTimeout(() => {
              close();
              hooks.created();
            }, r.parentId ? 3500 : 1000);
          } catch (error) {
            button.disabled = false;
            button.textContent = "Crear en Azure DevOps";
            message(text(error), true);
          }
        },
      };

      document.body.append(createModal(tipo, project, handlers));

      api.raidPrompt(tipo).then(
        (/** @type {any} */ r) => {
          if (!live(tipo)) return;
          const state = $("ixs-raid-api-state");
          if (state) state.textContent = r && r.configurado ? "Claude configurado; la consulta solo se realiza al pulsar Sugerir con IA." : "Claude no está configurado; puedes completar el formulario manualmente.";
          const box = /** @type {HTMLTextAreaElement | null} */ ($("ixs-raid-prompt"));
          if (box && r && r.ok) box.value = r.prompt || "";
        },
        (/** @type {any} */ error) => {
          const state = $("ixs-raid-api-state");
          if (state) state.textContent = "Claude: " + text(error);
        },
      );
      api.raidFieldTypes(project, tipo).then(
        (/** @type {any} */ r) => {
          if (!live(tipo)) return;
          if (r && r.ok) {
            ctx.fieldTypes = r.campos || {};
            refreshOptions(ctx);
          } else message("Opciones Azure: " + ((r && r.error) || "No disponibles") + ". Puedes editar, pero comprueba los permisos del proyecto.", true);
        },
        (/** @type {any} */ error) => message("Opciones Azure: " + text(error), true),
      );
      api.raidCreationOptions(project, tipo).then(
        (/** @type {any} */ r) => {
          if (!stillHere()) return;
          if (!r || !r.ok) return message("Rutas y sugerencias: " + ((r && r.error) || "Azure no devolvió rutas del proyecto"), true);
          ctx.options = r;
          refreshOptions(ctx);
        },
        (/** @type {any} */ error) => {
          if (live(tipo)) message("Opciones Azure: " + text(error), true);
        },
      );
    },
  };
}
