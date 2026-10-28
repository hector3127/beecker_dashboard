// @ts-check
// Pestaña Cliente de AER/T&M e IXB/SaaS/RaaS: filtros, ventanas y guardado por
// API v1. El dato vive en `dashboard.cliente` (el mismo objeto que usa la
// caché de la pantalla), así que se actualiza en el lugar tras cada guardado.
import { EMPTY_FILTERS, clientData, clientModel, contactsCsv, governanceRows, linkTarget } from "./client_model.js";
import { contactModal, documentModal, governanceModal, infoModal, renderClient, toast } from "./client_view.js";
import { updateWorkPlanDocuments } from "./work_plan_links.js";

const closeModal = () => document.getElementById("aer-modal-back")?.remove();
const value = (/** @type {string} */ id) => /** @type {HTMLInputElement | null} */ (document.getElementById(id))?.value ?? "";
const checked = (/** @type {string} */ id) => !!(/** @type {HTMLInputElement | null} */ (document.getElementById(id))?.checked);
const message = (/** @type {any} */ error) => (error && error.message ? error.message : String(error || ""));

/** Botón principal de la ventana abierta, como en la pantalla anterior. */
const primaryButton = () =>
  /** @type {HTMLButtonElement | null} */ (
    document.querySelector("#aer-modal-back .aer-actions .aer-btn.primary") || document.querySelector("#aer-modal-back .aer-gov-actions .aer-btn.primary") || document.querySelector("#aer-modal-back .aer-btn.primary")
  );

/** @param {HTMLButtonElement | null} button @param {string} label */
function startSaving(button, label) {
  if (!button) return { ok() {}, error() {} };
  const original = button.textContent;
  button.disabled = true;
  button.classList.add("saving");
  button.textContent = label;
  return {
    ok: (/** @type {string} */ done = "Guardado correctamente") => toast(done, "success"),
    error: (/** @type {string} */ text) => {
      button.disabled = false;
      button.classList.remove("saving");
      button.textContent = original;
      if (text) toast(text, "error");
    },
  };
}

/** @param {{saveClient: (id: string, operation: string, body: any) => Promise<any>}} api */
export function createClientController(api) {
  let filters = { ...EMPTY_FILTERS };
  let showFilters = false;
  /** @type {HTMLElement | null} */
  let target = null;
  /** @type {any} */
  let dashboard = null;
  let family = "aer";
  /** @type {{current: () => boolean, active: () => boolean} | null} */
  let guards = null;

  const live = () => !!target && target.isConnected && !!guards && guards.current() && guards.active();
  const send = (/** @type {string} */ operation, /** @type {any} */ body) => api.saveClient(dashboard.proyecto.id, operation, { ...body, servicio: family });
  const cliente = () => (dashboard.cliente = dashboard.cliente || {});

  function paint() {
    if (target) renderClient(target, clientModel(dashboard, filters, family), { filters, showFilters }, handlers);
  }

  /** Guarda, actualiza el dato y vuelve a pintar; los errores avisan sin cerrar la ventana. */
  async function save(/** @type {string} */ operation, /** @type {any} */ body, /** @type {string} */ busy, /** @type {string} */ done, /** @type {string} */ fallback, /** @type {(r: any) => void} */ apply, /** @type {() => void} [enable] */ enable = () => {}) {
    const saver = startSaving(primaryButton(), busy);
    try {
      const r = await send(operation, body);
      if (!r || !r.ok) {
        enable();
        saver.error((r && r.error) || fallback);
        return;
      }
      apply(r);
      if (operation === 'documento-guardar') updateWorkPlanDocuments(dashboard.proyecto.id, cliente().documentos || []);
      saver.ok(done);
      closeModal();
      if (live()) paint();
    } catch (error) {
      enable();
      saver.error(message(error) || "Error al guardar.");
    }
  }

  const handlers = {
    contact(/** @type {string} */ uid = "") {
      const x = clientData(dashboard).contactos.find((c) => c.uid === uid) || {};
      closeModal();
      document.body.append(contactModal(x, uid, { close: closeModal, save: () => saveContact(uid), remove: removeContact }));
    },
    info() {
      closeModal();
      document.body.append(infoModal(clientData(dashboard).info || {}, { close: closeModal, save: saveInfo }));
    },
    governance() {
      closeModal();
      document.body.append(governanceModal(governanceRows(clientData(dashboard), family), { close: closeModal, save: saveGovernance }));
    },
    document(/** @type {string} */ uid = "") {
      const x = clientData(dashboard).documentos.find((v) => String(v.uid) === String(uid)) || {};
      closeModal();
      document.body.append(documentModal(x, uid, { close: closeModal, save: () => saveDocument(uid), remove: removeDocument }));
    },
    openLink(/** @type {any} */ url) {
      const href = linkTarget(url);
      if (!href) return toast("No hay vínculo configurado.", "error");
      window.open(href, "_blank", "noopener");
    },
    exportContacts() {
      const blob = new Blob([contactsCsv(clientData(dashboard).contactos)], { type: "text/csv;charset=utf-8" });
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `${dashboard.proyecto.id}_contactos_cliente.csv`;
      document.body.append(link);
      link.click();
      link.remove();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    },
    search(/** @type {string} */ text) {
      filters.q = text;
      paint();
    },
    filter(/** @type {string} */ key, /** @type {string} */ text) {
      /** @type {any} */ (filters)[key] = text;
      paint();
    },
    clearFilters() {
      filters = { ...EMPTY_FILTERS };
      paint();
    },
    toggleFilters() {
      showFilters = !showFilters;
      paint();
    },
  };

  function saveContact(/** @type {string} */ uid) {
    const body = {
      UID: uid,
      Nombre: value("acc-nom"), Cargo: value("acc-cargo"), Rol: value("acc-rol"), Area: value("acc-area"),
      Correo: value("acc-mail"), Telefono: value("acc-tel"), Nivel_Decision: value("acc-nivel"), Estado: value("acc-est"),
      Canal: value("acc-canal"), Alcance: value("acc-alc"), Notas: value("acc-notas"),
      Requerimientos: checked("acc-req"), Aprueba: checked("acc-apr"), Valida: checked("acc-val"),
      Decide: checked("acc-dec"), Informado: checked("acc-inf"), Es_Decisor: checked("acc-decidor"),
    };
    const others = document.querySelectorAll("#aer-modal-back .aer-btn:not(.primary)");
    others.forEach((b) => (/** @type {HTMLButtonElement} */ (b).disabled = true));
    save("contacto-guardar", body, "Guardando contacto...", "Contacto guardado", "No se pudo guardar el contacto.", (r) => (cliente().contactos = (r.cliente && r.cliente.contactos) || []), () => others.forEach((b) => (/** @type {HTMLButtonElement} */ (b).disabled = false)));
  }

  async function removeContact(/** @type {string} */ uid) {
    if (!window.confirm("¿Eliminar este contacto?")) return;
    try {
      const r = await send("contacto-eliminar", { uid });
      if (!r || !r.ok) return toast((r && r.error) || "No se pudo eliminar.", "error");
      cliente().contactos = (r.cliente && r.cliente.contactos) || [];
      closeModal();
      if (live()) paint();
    } catch (error) {
      toast(message(error), "error");
    }
  }

  function saveInfo() {
    const old = clientData(dashboard).info || {};
    const body = { UID: old.uid || "", Area_Principal: value("aci-area"), Sponsor: value("aci-sponsor"), Product_Owner: value("aci-po"), Correo_Distribucion: value("aci-mail"), Ruta_Escalamiento: value("aci-ruta"), Canales: value("aci-canales"), Proxima_Reunion: old.proximaReunion || "", Tipo_Reunion: old.tipoReunion || "" };
    save("info-guardar", body, "Guardando información...", "Información guardada", "No se pudo guardar.", (r) => {
      cliente().info = { uid: r.uid || old.uid || "", areaPrincipal: body.Area_Principal, sponsor: body.Sponsor, productOwner: body.Product_Owner, correoDistribucion: body.Correo_Distribucion, rutaEscalamiento: body.Ruta_Escalamiento, canales: body.Canales, proximaReunion: body.Proxima_Reunion, tipoReunion: body.Tipo_Reunion, cliente: dashboard.proyecto.cliente || "", deliveryManager: dashboard.proyecto.deliveryManager || "" };
    });
  }

  function saveGovernance() {
    const rows = [...document.querySelectorAll("#aer-gov-editor .aer-gov-edit-row")]
      .map((row) => {
        const get = (/** @type {string} */ key) => /** @type {HTMLInputElement | null} */ (row.querySelector(`[data-gov="${key}"]`))?.value || "";
        return { Reunion: get("reunion"), Frecuencia: get("frecuencia"), Participantes: get("participantes"), Canal: get("canal") };
      })
      .filter((x) => String(x.Reunion || "").trim());
    save("gobierno-guardar", { filas: rows }, "Guardando reuniones...", "Gobierno y comunicación guardados", "No se pudo guardar gobierno y comunicación.", (r) => (cliente().gobierno = r.gobierno || []));
  }

  function saveDocument(/** @type {string} */ uid) {
    const body = { UID: uid, Nombre: value("acd-nom"), Tipo: value("acd-tipo"), URL: value("acd-url"), Accion: value("acd-accion") || "Abrir", Notas: value("acd-notas") };
    save("documento-guardar", body, "Guardando link...", "Link guardado", "No se pudo guardar el link.", (r) => (cliente().documentos = r.documentos || []));
  }

  async function removeDocument(/** @type {string} */ uid) {
    if (!window.confirm("¿Eliminar este registro de documentación?")) return;
    try {
      const r = await send("documento-eliminar", { uid });
      if (!r || !r.ok) return toast((r && r.error) || "No se pudo eliminar.", "error");
      cliente().documentos = r.documentos || [];
      updateWorkPlanDocuments(dashboard.proyecto.id, cliente().documentos);
      toast("Link eliminado", "success");
      closeModal();
      if (live()) paint();
    } catch (error) {
      toast(message(error) || "Error al eliminar.", "error");
    }
  }

  return {
    /** @param {HTMLElement} el @param {any} data @param {{family: string, current: () => boolean, active: () => boolean}} options */
    mount(el, data, options) {
      closeModal();
      target = el;
      dashboard = data;
      family = options.family;
      guards = { current: options.current, active: options.active };
      paint();
    },
  };
}
