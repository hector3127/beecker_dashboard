import { el } from "#app/lib/dom.js";
import {
  PLAN_STATES,
  DEPENDENCY_STATES,
  resources,
  capacity,
  parsePlanText,
  today,
} from "./aer_planning_model.js";

const node = (tag, cls, ...children) =>
  el(tag, cls ? { class: cls } : {}, ...children);
const div = (cls, ...children) => node("div", cls, ...children);
const styled = (element, css) => {
  Object.assign(element.style, css);
  return element;
};
const label = (title, field, cls = "") => node("label", cls, title, field);
const text = (value) => String(value ?? "");
function input(value, props = {}) {
  const field = el("input", props);
  field.value = text(value);
  return field;
}
function area(value, props = {}) {
  const field = el("textarea", props);
  field.textContent = text(value);
  field.value = text(value);
  return field;
}
function select(options, value, props = {}) {
  const field = el(
    "select",
    props,
    ...options.map((x) => el("option", { value: x }, text(x))),
  );
  if (options.map(String).includes(String(value))) field.value = String(value);
  return field;
}
const button = (title, fn, cls = "aer-btn", props = {}) =>
  el("button", { class: cls, onclick: fn, ...props }, title);
function modal(...body) {
  document.getElementById("aer-modal-back")?.remove();
  const back = el(
    "div",
    { class: "aer-modal-back", id: "aer-modal-back" },
    div("aer-modal", ...body),
  );
  back.addEventListener("click", (e) => {
    if (e.target === back) back.remove();
  });
  document.body.append(back);
  return back;
}
const close = () => document.getElementById("aer-modal-back")?.remove();
const header = (title) =>
  styled(div("", node("h3", "", title), button("✕", close)), {
    display: "flex",
    justifyContent: "space-between",
  });
const actions = (...children) =>
  styled(div("aer-actions", ...children), { marginTop: "12px" });

export function openVacation(dashboard, uid, handlers) {
  const x =
    (dashboard.vacaciones?.filas || []).find((row) => row.uid === uid) || {};
  return modal(
    header((uid ? "Editar" : "Registrar") + " vacaciones"),
    div(
      "aer-formgrid",
      label(
        "Recurso",
        select(resources(dashboard), x.recurso, { id: "av-rec" }),
      ),
      label(
        "Estado",
        select(["Aprobada", "Pendiente", "Cancelada"], x.estado, {
          id: "av-est",
        }),
      ),
      label("Inicio", input(x.inicio || "", { id: "av-ini", type: "date" })),
      label("Fin", input(x.fin || "", { id: "av-fin", type: "date" })),
      label("Registrado por", input(x.registradoPor || "", { id: "av-reg" })),
      label(
        "Comentarios",
        area(x.comentarios || "", { id: "av-com" }),
        "aer-span2",
      ),
    ),
    actions(
      ...(uid
        ? [
            button(
              "Eliminar",
              () => handlers.removeVacation(uid),
              "aer-btn danger",
            ),
          ]
        : []),
      button("Guardar", () => handlers.saveVacation(uid), "aer-btn primary"),
    ),
  );
}

export function capacityWarning(dashboard, uid = "") {
  const box = document.getElementById("ap-cap-warning");
  if (!box) return;
  const v = (id) => document.getElementById(id)?.value || "";
  const responsable = v("ap-resp"),
    esfuerzo = Number(v("ap-ord") || 0),
    estado = v("ap-est") || "Por iniciar",
    tipo = v("ap-tipo") || "Actividad";
  const cap = capacity(
    dashboard,
    responsable,
    v("ap-ip"),
    v("ap-fp"),
    uid,
    esfuerzo,
    estado,
    tipo,
  );
  const bold = (t) => node("b", "", t);
  if (
    !responsable ||
    /^pendiente$/i.test(responsable) ||
    tipo === "Hito" ||
    esfuerzo <= 0 ||
    /complet|por validar|detenido/i.test(estado)
  ) {
    box.className = "aer-cap-modal ok";
    box.replaceChildren(
      bold("Capacidad:"),
      " esta asignación no consume capacidad activa.",
    );
  } else if (cap.max > 6) {
    box.className = "aer-cap-modal bad";
    box.replaceChildren(
      bold("⚠ Sobreasignación:"),
      ` ${responsable} alcanzaría `,
      bold(`${cap.max}/6 puntos`),
      " en el periodo seleccionado. El recurso supera su capacidad.",
    );
  } else if (cap.max === 6) {
    box.className = "aer-cap-modal warn";
    box.replaceChildren(
      bold("Ocupado al 100%:"),
      ` ${responsable} llegará a `,
      bold("6/6 puntos"),
      ". No debería recibir otra actividad concurrente.",
    );
  } else {
    box.className = "aer-cap-modal ok";
    box.replaceChildren(
      bold("Capacidad disponible:"),
      " máximo previsto ",
      bold(`${cap.max}/6 puntos`),
      ".",
    );
  }
}

export function openPlan(dashboard, uid, handlers) {
  const x = (dashboard.plan?.filas || []).find((row) => row.uid === uid) || {},
    estado = x.estado || "Por iniciar",
    esfuerzo = x.esfuerzo != null ? x.esfuerzo : x.orden || 0;
  const back = modal(
    header(uid ? "Editar actividad / hito" : "Agregar actividad / hito"),
    div(
      "aer-formgrid",
      label("Tipo", select(["Actividad", "Hito"], x.tipo, { id: "ap-tipo" })),
      label("Responsable", input(x.responsable || "", { id: "ap-resp" })),
      label(
        "Actividad / Hito",
        input(x.actividad || "", { id: "ap-act" }),
        "aer-span2",
      ),
      label(
        "Inicio compromiso",
        input(x.inicioPlan || "", { type: "date", id: "ap-ip" }),
      ),
      label(
        "Fin compromiso",
        input(x.finPlan || "", { type: "date", id: "ap-fp" }),
      ),
      label("Estado", select(PLAN_STATES, estado, { id: "ap-est" })),
      label(
        "Fecha de cierre",
        input(x.finReal || "", {
          type: "date",
          id: "ap-fr",
          disabled: estado !== "Completado",
        }),
      ),
      label(
        "Esfuerzo (0 a 6)",
        select([0, 1, 2, 3, 4, 5, 6], Number(esfuerzo || 0), { id: "ap-ord" }),
      ),
      label("Dependencia", input(x.dependencia || "", { id: "ap-dep" })),
      label(
        "Estado dependencia",
        el(
          "select",
          { id: "ap-dep-est" },
          el("option", { value: "" }, "Sin dependencia"),
          ...DEPENDENCY_STATES.map((v) =>
            el(
              "option",
              { value: v, selected: v === (x.estadoDependencia || "Abierta") },
              v,
            ),
          ),
        ),
      ),
      label("Notas", area(x.notas || "", { id: "ap-not" }), "aer-span2"),
    ),
    styled(
      div(
        "aer-callout purple",
        node("b", "", "Esfuerzo:"),
        " escala de 0 a 6. Un valor 6 representa el 100% de capacidad de una persona.",
      ),
      { marginTop: "10px" },
    ),
    el("div", { id: "ap-cap-warning", class: "aer-cap-modal ok" }),
    actions(
      ...(uid
        ? [button("Eliminar", () => handlers.removePlan(uid), "aer-btn danger")]
        : []),
      button(
        "Guardar cambios",
        () => handlers.savePlan(uid),
        "aer-btn primary",
      ),
    ),
  );
  const get = (id) => back.querySelector("#" + id);
  const state = get("ap-est"),
    end = get("ap-fr");
  const sync = () => {
    if (state.value === "Completado") {
      end.disabled = false;
      if (!end.value) end.value = x.finReal || today();
    } else {
      end.value = "";
      end.disabled = true;
    }
  };
  state.addEventListener("change", sync);
  sync();
  const dep = get("ap-dep"),
    depState = get("ap-dep-est");
  const syncDep = () => {
    depState.disabled = !String(dep.value || "").trim();
    if (depState.disabled) depState.value = "";
    else if (!depState.value) depState.value = x.estadoDependencia || "Abierta";
  };
  dep.addEventListener("input", syncDep);
  syncDep();
  for (const id of [
    "ap-resp",
    "ap-ord",
    "ap-ip",
    "ap-fp",
    "ap-est",
    "ap-tipo",
  ]) {
    for (const event of ["change", "input"])
      get(id).addEventListener(event, () => capacityWarning(dashboard, uid));
  }
  capacityWarning(dashboard, uid);
  return back;
}

export function previewImport(dashboard) {
  const status = document.getElementById("aer-plan-import-status");
  if (!status) return;
  const parsed = parsePlanText(
    document.getElementById("aer-plan-text")?.value || "",
    dashboard.proyecto || {},
  );
  if (!parsed.ok) {
    status.style.color = "#c3273e";
    status.textContent = parsed.error;
    return;
  }
  status.style.color = "#16864e";
  status.textContent = `Listo: ${parsed.items.length} actividad(es) detectada(s)${parsed.errores.length ? ` · ${parsed.errores.length} fila(s) omitida(s)` : ""}.`;
}

export function openImport(dashboard, handlers) {
  const file = input("", {
    type: "file",
    id: "aer-plan-file",
    accept: ".csv,.tsv,.txt",
    "aria-label": "Archivo de planeación",
  });
  const areaText = area("", {
    id: "aer-plan-text",
    placeholder: "También puedes pegar aquí los datos tabulados",
    "aria-label": "Datos de planeación",
  });
  const back = modal(
    styled(
      div(
        "",
        div(
          "",
          node("h3", "", "Cargar planeación / hitos"),
          div(
            "aer-sub",
            "Pega una tabla de Excel/Sheets (TSV) o un CSV con: Tipo, Actividad, Responsable, Inicio_Plan, Fin_Plan, Inicio_Real, Fin_Real, Avance, Estado, Dependencia, Notas",
          ),
        ),
        button("✕", close),
      ),
      { display: "flex", justifyContent: "space-between", gap: "16px" },
    ),
    styled(file, { margin: "12px 0" }),
    styled(areaText, {
      width: "100%",
      minHeight: "250px",
      boxSizing: "border-box",
      fontFamily: "monospace",
    }),
    el(
      "div",
      {
        id: "aer-plan-import-status",
        style: { fontSize: "11px", color: "var(--gris)", marginTop: "8px" },
      },
      "Esperando datos…",
    ),
    styled(
      div(
        "aer-actions",
        button("Importar", handlers.importPlan, "aer-btn primary", {
          id: "aer-plan-import-btn",
        }),
      ),
      { marginTop: "10px" },
    ),
  );
  areaText.addEventListener("input", () => previewImport(dashboard));
  file.addEventListener("change", () => {
    const selected = file.files?.[0];
    if (!selected) return;
    const reader = new FileReader();
    reader.onload = () => {
      if (!back.isConnected) return;
      areaText.value = reader.result || "";
      previewImport(dashboard);
    };
    reader.readAsText(selected);
  });
  return back;
}
