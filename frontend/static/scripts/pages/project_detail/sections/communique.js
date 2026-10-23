// @ts-check
// Comunicados del proyecto: elige el tipo, arma la vista previa, conecta Gmail
// y crea el borrador (o envía) en el hilo "Inicio de ...".
import { el } from "#app/lib/dom.js";
import { FILE_TYPE, KINDS, MAX_FILE, fmtDate, kindsFor, missingField, payload, previewBlocks, previewSubject } from "./communique_model.js";
import { createDialog, paintGmail } from "./communique_view.js";

const csrf = () => {
  const m = document.cookie.match(/(?:^|; )csrftoken=([^;]+)/);
  return m ? decodeURIComponent(m[1]) : "";
};
/** @param {string} url @param {RequestInit} [opts] */
const json = (url, opts) =>
  fetch(url, { credentials: "same-origin", headers: { "X-CSRFToken": csrf() }, ...(opts || {}) }).then((r) => r.json().catch(() => ({ ok: false, error: "Respuesta inválida del servidor." })));
const norm = (/** @type {any} */ t) => String(t || "").normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
const shortAddr = (/** @type {any} */ a) => {
  const m = String(a || "").match(/^\s*"?([^"<]*?)"?\s*<([^>]+)>/);
  return m ? m[1].trim() || m[2] : String(a || "").trim();
};
const dateText = (/** @type {string} */ iso) => {
  if (!iso) return "";
  const d = new Date(iso);
  return isNaN(+d) ? "" : d.toLocaleDateString("es-MX", { day: "2-digit", month: "short", year: "numeric" });
};
const todayIso = () => {
  const d = new Date();
  const z = (/** @type {number} */ n) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${z(d.getMonth() + 1)}-${z(d.getDate())}`;
};

/** Un solo diálogo a la vez; la sesión de Gmail se conserva entre aperturas. */
export function createCommuniqueController() {
  const gmail = { configured: true, connected: false, email: "", mode: "draft", threads: /** @type {any[]} */ ([]), selected: "", loading: false, error: "", result: /** @type {any} */ (null), query: "", sending: false, poll: 0 };
  /** @type {any} */
  let session = null;

  const live = () => session && session.dialog.overlay.isConnected;
  const paintMail = () => live() && paintGmail(session.dialog.gmail, gmail, mailHandlers);
  const paint = () => {
    if (!live()) return;
    const { kind, dialog } = session;
    const read = dialog.read();
    session.values[kind] = read.values;
    session.project = read.project;
    const thread = gmail.threads.find((t) => t.id === gmail.selected);
    const v = read.values;
    const dates = kind === "extension" ? (v.currentDate && v.newDate ? `${fmtDate(v.currentDate)} → ${fmtDate(v.newDate)}` : "") : fmtDate(v.resumeDate || v.closeDate);
    dialog.paint({
      values: v,
      project: read.project,
      files: session.files,
      thread,
      dates,
      kindLabel: KINDS[kind].label,
      blocks: previewBlocks(kind, v, { project: read.project.trim(), hasFiles: session.files.length > 0, hour: new Date().getHours(), today: todayIso() }),
    });
  };

  async function state() {
    try {
      const r = await json("/gmail/status/");
      if (!live()) return;
      if (r && r.ok) {
        const was = gmail.connected;
        Object.assign(gmail, r.result);
        gmail.error = "";
        if (gmail.connected && !was) search();
        else paintMail();
      } else {
        gmail.error = (r && r.error) || "No se pudo consultar el estado de Gmail.";
        paintMail();
      }
    } catch {
      gmail.error = "No se pudo contactar al servidor.";
      paintMail();
    }
  }

  /** @param {string} [query] */
  async function search(query) {
    if (!live()) return;
    if (query !== undefined) gmail.query = query.trim();
    Object.assign(gmail, { loading: true, error: "", result: null });
    paintMail();
    const qs = new URLSearchParams({ project: session.project.trim(), projectName: session.projectName || "", q: gmail.query });
    try {
      const r = await json("/gmail/threads/?" + qs);
      gmail.loading = false;
      if (r && r.ok) {
        gmail.threads = r.result.threads || [];
        gmail.email = r.result.email || gmail.email;
        const pre = gmail.threads.find((t) => t.remembered) || gmail.threads.find((t) => t.suggested);
        if (!gmail.threads.some((t) => t.id === gmail.selected)) gmail.selected = pre ? pre.id : "";
      } else {
        gmail.threads = [];
        gmail.error = (r && r.error) || "No se pudieron leer los hilos.";
        if (r && r.code === "ERR_GMAIL_NOT_CONNECTED") gmail.connected = false;
      }
    } catch {
      gmail.loading = false;
      gmail.error = "No se pudo contactar al servidor.";
    }
    paintMail();
    paint();
  }

  /** Oculta los hilos que no contienen todas las palabras escritas. @param {string} text */
  function filter(text) {
    if (!live()) return;
    const list = session.dialog.gmail.querySelector(".ixe-threads");
    if (!list) return;
    const words = norm(text).split(/\s+/).filter(Boolean);
    let shown = 0;
    list.querySelectorAll(".ixe-thread").forEach((node) => {
      const hay = node.getAttribute("data-s") || "";
      const ok = words.every((w) => hay.includes(w));
      /** @type {HTMLElement} */ (node).hidden = !ok;
      if (ok) shown++;
    });
    const none = list.querySelector("#ixe-nomatch");
    if (!shown && !none) list.append(el("div", { id: "ixe-nomatch", class: "ixe-empty", text: "Ningún hilo coincide. Pulsa Buscar para buscar en todo tu Gmail." }));
    else if (shown && none) none.remove();
  }

  function connect() {
    gmail.error = "";
    const w = window.open("/gmail/oauth/start/", "gmail-oauth", "width=520,height=680");
    if (!w) {
      gmail.error = "El navegador bloqueó la ventana. Permite ventanas emergentes para este sitio.";
      paintMail();
      return;
    }
    clearInterval(gmail.poll);
    let tries = 0;
    gmail.poll = /** @type {any} */ (
      setInterval(async () => {
        tries++;
        if (tries > 180 || !live()) return clearInterval(gmail.poll);
        const r = await json("/gmail/status/").catch(() => null);
        if (r && r.ok && r.result.connected) {
          clearInterval(gmail.poll);
          state();
        }
      }, 1500)
    );
  }
  async function disconnect() {
    await json("/gmail/disconnect/", { method: "POST" });
    Object.assign(gmail, { connected: false, email: "", threads: [], selected: "", result: null });
    paintMail();
    paint();
  }
  /** @param {any} d */
  function oauthDone(d) {
    if (!d || d.type !== "gmail-oauth") return;
    clearInterval(gmail.poll);
    if (!d.ok) gmail.error = d.message || "No se pudo conectar.";
    state();
  }
  window.addEventListener("message", (e) => e.origin === location.origin && oauthDone(e.data));
  try {
    new BroadcastChannel("gmail-oauth").onmessage = (e) => oauthDone(e.data);
  } catch {
    // Sin BroadcastChannel solo se usa postMessage.
  }
  window.addEventListener("focus", () => live() && !gmail.connected && state());

  const mailHandlers = {
    connect,
    disconnect,
    search,
    filter,
    short: shortAddr,
    norm,
    date: dateText,
    choose(/** @type {string} */ id) {
      gmail.selected = id;
      gmail.result = null;
      paintMail();
      paint();
    },
  };

  /** @param {string} text */
  function soon(text) {
    session.dialog.toast(/válido|archivo/.test(text) ? text : text + ": funcionalidad pendiente de conectar.");
  }

  /** @param {FileList | File[] | null} list */
  function addFiles(list) {
    let skipped = 0;
    for (const f of Array.from(list || [])) {
      if (!FILE_TYPE.test(f.name) || f.size > MAX_FILE) skipped++;
      else if (!session.files.some((/** @type {File} */ x) => x.name === f.name && x.size === f.size)) session.files.push(f);
    }
    if (skipped) soon(`${skipped} archivo(s) no válido(s): usa PDF, PNG, JPG, XLSX o DOCX de hasta 10 MB`);
    paint();
  }

  async function send() {
    const { kind, dialog } = session;
    if (gmail.sending) return;
    const read = dialog.read();
    if (!gmail.connected) return dialog.toast("Conecta tu cuenta de Google primero.");
    const missing = missingField(kind, read.values, read.project, session.files.length);
    if (missing) return dialog.toast(missing);
    if (!gmail.selected) return dialog.toast("Elige el hilo donde se va a responder.");
    const t = gmail.threads.find((x) => x.id === gmail.selected) || {};
    const people = (t.replyTo || []).length + (t.replyCc || []).length;
    if (gmail.mode === "send" && !(await dialog.confirm(`Se enviará un correo a ${people} ${people === 1 ? "destinatario" : "destinatarios"} del hilo. ¿Continuar?`))) return;
    const fd = new FormData();
    for (const [k, v] of payload(kind, read.values, read.project, gmail.selected)) fd.append(k, v);
    session.files.forEach((/** @type {File} */ f) => fd.append("files", f, f.name));
    gmail.sending = true;
    dialog.sendButton.disabled = true;
    try {
      const r = await json("/gmail/reply/", { method: "POST", body: fd });
      if (r && r.ok) {
        gmail.result = r.result;
        dialog.toast(r.result.mode === "send" ? "Correo enviado en el hilo." : "Borrador creado en tu Gmail.");
      } else {
        gmail.error = (r && r.error) || "No se pudo crear el correo.";
        if (r && r.code === "ERR_GMAIL_NOT_CONNECTED") gmail.connected = false;
        dialog.toast(gmail.error);
      }
    } catch {
      dialog.toast("No se pudo contactar al servidor.");
    }
    gmail.sending = false;
    dialog.sendButton.disabled = false;
    paintMail();
  }

  function copy() {
    const text = session.dialog.previewText();
    const done = () => session.dialog.toast("Texto copiado.");
    if (navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(text).then(done).catch(() => session.dialog.toast("No se pudo copiar; selecciona el texto manualmente."));
    else session.dialog.toast("No se pudo copiar.");
  }

  function applyAuto() {
    const { kind, dialog, auto } = session;
    if ((kind === "cierre_ixb" || kind === "cierre_aer") && !dialog.read().values.closeDate) dialog.setField("closeDate", todayIso());
    if (!auto) return;
    const v = dialog.read().values;
    if (KINDS[kind].fields.some((f) => f.key === "stage") && !v.stage && auto.stage) dialog.setField("stage", auto.stage);
    if (kind === "extension" && !dialog.read().values.currentDate) {
      const stage = dialog.read().values.stage;
      if (stage && auto.closes && auto.closes[stage]) dialog.setField("currentDate", auto.closes[stage]);
    }
  }

  function close() {
    if (session) session.dialog.overlay.remove();
    document.removeEventListener("keydown", onKey);
    session = null;
  }
  const onKey = (/** @type {KeyboardEvent} */ e) => e.key === "Escape" && close();

  /** @param {string} kind */
  function setKind(kind) {
    session.values[session.kind] = session.dialog.read().values;
    session.kind = kind;
    session.dialog.setKind(kind, session.values[kind] || {});
    applyAuto();
    paint();
  }

  return {
    close,
    /**
     * @param {{projectId: string, projectName?: string, family: string, auto?: {stage: string, closes: Record<string, string>}, kind?: string}} o
     */
    open(o) {
      close();
      const kinds = kindsFor(o.family);
      const kind = o.kind && kinds.includes(o.kind) ? o.kind : "extension";
      const handlers = {
        close,
        setKind,
        send,
        copy,
        soon,
        addFiles,
        removeFile: (/** @type {number} */ i) => {
          session.files.splice(i, 1);
          paint();
        },
        changed: (/** @type {Event} */ e) => {
          const t = /** @type {HTMLElement} */ (e.target);
          if (t.dataset && t.dataset.key === "stage" && session.kind === "extension" && session.auto) {
            const stage = /** @type {HTMLSelectElement} */ (t).value;
            if (stage && session.auto.closes[stage]) session.dialog.setField("currentDate", session.auto.closes[stage]);
          }
          paint();
        },
        clear: () => {
          session.dialog.clearFields();
          session.files = [];
          applyAuto();
          paint();
        },
        openLink: () => {
          const v = (session.dialog.read().values.link || "").trim();
          if (!/^https?:\/\//i.test(v)) return soon("Escribe un link válido que empiece con https://");
          window.open(v, "_blank", "noopener,noreferrer");
        },
      };
      const dialog = createDialog({ family: o.family, kinds, kind, project: o.projectId, values: {}, handlers });
      session = { dialog, kind, kinds, project: o.projectId, projectName: o.projectName || "", values: {}, files: [], auto: o.auto || null };
      document.body.append(dialog.overlay);
      dialog.setKind(kind, {});
      Object.assign(gmail, { threads: [], selected: "", error: "", result: null, loading: false, query: "", sending: false });
      document.addEventListener("keydown", onKey);
      paintMail();
      state();
      applyAuto();
      paint();
    },
  };
}

export { previewSubject };
