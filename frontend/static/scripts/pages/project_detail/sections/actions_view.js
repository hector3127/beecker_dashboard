import { actionDistributionView, actionResponsibleView, actionWeeklyView } from "./actions_visuals.js";
import { el } from "#app/lib/dom.js";
import { icon } from "./ixs_icons.js";
import {
  STATES,
  PRIORITIES,
  actionDate,
  dateText,
  dependencies,
  normalize,
  progress,
  stateClass,
} from "./actions_model.js";

const h = (tag, cls, ...children) =>
  el(
    tag,
    cls ? { class: cls } : {},
    ...children.flat().filter((x) => x != null),
  );
const div = (cls, ...children) => h("div", cls, ...children);
const text = (value) => (value == null ? "" : String(value));
const fieldLabels = {
  accion: "Acción / Entregable",
  responsable: "Responsable",
  prioridad: "Prioridad",
  fechaInicio: "Fecha inicio",
  fechaLimite: "Fecha compromiso",
  fechaReal: "Próxima revisión",
  proximaRevision: "Próxima revisión",
  estado: "Estado",
  dependencia: "Dependencia",
};
const styled = (node, style) => {
  Object.assign(node.style, style);
  return node;
};
const button = (label, onclick, cls = "aer-btn", props = {}) =>
  el("button", { class: cls, onclick, ...props }, label);
const bar = (width, background) =>
  div("aer-bar", styled(h("i", ""), { width: width + "%", background }));
const red = "linear-gradient(90deg,#ff6773,#e4314e)",
  green = "linear-gradient(90deg,#25b36a,#67d78f)",
  actionPurple = "linear-gradient(90deg,#5b2ad8,#8d65ed)";

function input(value, props = {}) {
  const node = el("input", props);
  node.value = text(value);
  return node;
}
function area(value, props = {}) {
  const node = el("textarea", props);
  node.textContent = text(value);
  node.value = text(value);
  return node;
}
function select(options, value, props = {}, blank = false) {
  const node = el(
    "select",
    props,
    ...options.map((v) => el("option", { value: v }, v || (blank ? "—" : ""))),
  );
  if (options.includes(value)) node.value = value;
  return node;
}
const table = (headers, rows, props = {}) =>
  el(
    "table",
    { class: "aer-action-lite-table", ...props },
    h("thead", "", h("tr", "", ...headers)),
    ...rows,
  );
const heading = (label) => h("th", "", label);
const cell = (...body) => h("td", "", ...body);

function kpi(name, value, label, sub, tone = "purple", cls = "") {
  return div(
    `aer-action-kpi2 ${tone}` + (cls ? " " + cls : ""),
    div(
      "aer-action-metric-head",
      h("span", "icon", icon(name)),
      div("label", label),
    ),
    div("value", text(value)),
    div("sub", sub),
  );
}

export function filterActions(target, query) {
  const value=normalize(query);
  const selected=id=>target.querySelector('#'+id)?.value || '';
  const state=selected('action-filter-state'),person=selected('action-filter-person'),priority=selected('action-filter-priority');
  let visible=0;
  const rows=target.querySelectorAll('#aer-actions-table-body tr[data-action-filter]');
  rows.forEach(row=>{
    const match=(!value || String(row.dataset.actionFilter || '').includes(value)) &&
      (!state || row.dataset.actionState===state) && (!person || row.dataset.actionPerson===person) && (!priority || row.dataset.actionPriority===priority);
    row.style.display=match?'':'none';if(match)visible++;
  });
  const count=target.querySelector('#aer-actions-filter-count');
  if(count)count.textContent=`Mostrando ${visible} de ${rows.length} acciones`;
}

export function renderParts(parts, actions) {
  const rows = (parts || []).map((a) => {
    const edit = (field, value) => actions.partField(a.uid, field, value);
    const selectField = (field, values, value, props = {}) => {
      const node = select(values, value, {
        class: "aer-inline-edit",
        "aria-label": fieldLabels[field],
        ...props,
      });
      node.addEventListener("change", () => edit(field, node.value));
      return node;
    };
    const inputField = (field, props) => {
      const node = input(a[field] || "", {
        class: "aer-inline-edit",
        "aria-label": fieldLabels[field],
        ...props,
      });
      node.addEventListener("change", () => edit(field, node.value));
      return node;
    };
    const areaField = (field, label) => {
      const node = area(a[field] || "", {
        class: "aer-inline-edit aer-inline-textarea",
        "aria-label": label,
      });
      node.addEventListener("change", () => edit(field, node.value));
      return node;
    };
    return h(
      "tr",
      "",
      cell(areaField("accion", "Acción")),
      cell(
        selectField("responsable", ["Beecker", "Cliente"], a.responsable, {
          "aria-label": "Responsable Beecker o Cliente",
        }),
      ),
      cell(inputField("fechaLimite", { type: "date" })),
      cell(inputField("proximaRevision", { type: "date" })),
      cell(selectField("estado", STATES, a.estado || "Pendiente")),
      cell(areaField("notas", "Notas")),
      cell(
        button("✕", () => actions.removePart(a.uid), "aer-btn danger", {
          "aria-label": "Eliminar pendiente",
        }),
      ),
    );
  });
  if (!rows.length)
    rows.push(
      h(
        "tr",
        "",
        el(
          "td",
          { colspan: 7 },
          div('action-empty-state',icon('list'),h('strong','','Sin pendientes registrados.'),h('small','','Agrega un pendiente para iniciar el seguimiento.')),
        ),
      ),
    );
  return el(
    "div",
    {
      class: "aer-action-table-card",
      id: "aeri-partes-card",
      style: { marginTop: "14px" },
    },
    div(
      "aer-action-table-head",
      div(
        "",
        styled(h("h3", "", icon("people"), " Listado de acciones Beecker / Cliente"), {
          margin: "0",
        }),
        div(
          "aer-sub",
          "Compromisos y pendientes con Beecker y el cliente.",
        ),
      ),
      div(
        "aer-actions",
        button("＋ Agregar pendiente", actions.openPart, "aer-btn primary"),
      ),
    ),
    el(
      "div",
      {
        class: "aer-sub",
        id: "aeri-partes-status",
        "aria-live": "polite",
        style: { margin: "7px 0" },
      },
      parts === null
        ? "Cargando pendientes Beecker / Cliente…"
        : (parts || []).length + " pendiente(s) registrado(s)",
    ),
    styled(
      div(
        "",
        table(
          [
            styled(heading("Acción / Entregable"), { minWidth: "220px" }),
            styled(heading("Responsable"), { minWidth: "115px" }),
            heading("Fecha compromiso"),
            heading("Próxima revisión"),
            heading("Estado"),
            styled(heading("Notas"), { minWidth: "175px" }),
            heading("Eliminar"),
          ],
          [h("tbody", "", ...rows)],
          { style: { minWidth: "760px" } },
        ),
      ),
      { overflow: "auto" },
    ),
    styled(
      div(
        "aer-sub",
        "Edición directa: los cambios se guardan al salir del campo. Beecker / Cliente indica a quién corresponde el pendiente, no el nombre de una persona.",
      ),
      { marginTop: "8px" },
    ),
  );
}

export function renderActions(target, m, parts, actions) {
  const {
    filas,
    abiertas,
    vencidas,
    detenidas,
    proximas,
    urgente,
  } = m;
  const hero = div(
    "aer-vivid-card aer-action-overview",
    div(
      "aer-action-hero",
      div(
        "",
        h("h3", "", icon("target"), " Acciones y seguimiento"),
        div(
          "sub",
          "Control de acciones clave del proyecto y seguimiento de compromisos.",
        ),
      ),
      div(
        "aer-actions",
        el(
          "button",
          { class: "aer-btn", onclick: actions.clean },
          icon("layers"),
          "Limpiar duplicados",
        ),
        button("+ Agregar acción", () => actions.open(), "aer-btn primary"),
      ),
    ),
    div(
      "aer-action-kpi-grid",
      kpi("list", filas.length, "Total", "Acciones registradas"),
      kpi("flag", abiertas, "Abiertas", "Requieren seguimiento", "blue"),
      kpi(
        "warning",
        vencidas,
        "Vencidas",
        "Requieren atención inmediata",
        "red",
      ),
      kpi("clock", detenidas, "Detenidas", "Temporalmente en pausa", "slate"),
      kpi(
        "calendar",
        proximas ? dateText(actionDate(proximas)) : "—",
        "Próxima revisión",
        "Siguiente fecha de seguimiento",
        "purple",
        "aer-action-date",
      ),
    ),
  );
  const meta = (label, value) =>
    div("aer-action-meta-block", div("lbl", label), div("val", value));
  const alert = div(
    "aer-action-alert" + (vencidas ? " is-overdue" : " is-clear"),
    div(
      "head",
      div(
        "",
        div(
          "title",
          styled(h("span", "aer-vivid-icon red", vencidas ? "!" : "✓"), {
            width: "46px",
            height: "46px",
            fontSize: "20px",
          }),
          vencidas ? "Atención inmediata" : "Seguimiento al día",
        ),
        div(
          "desc",
          vencidas
            ? `Tienes ${vencidas} acción${vencidas === 1 ? "" : "es"} vencida${vencidas === 1 ? "" : "s"} que requiere${vencidas === 1 ? "" : "n"} seguimiento para evitar impacto en el proyecto.`
            : "No hay acciones vencidas en este momento.",
        ),
      ),
      button("Ver todas las acciones →", () => {
        target.querySelectorAll('.action-filter-panel select,.aer-action-search').forEach(node=>node.value='');
        filterActions(target,'');
        target.querySelector('.action-main-listing')?.scrollIntoView({behavior:'smooth',block:'start'});
      }),
    ),
    ...(urgente && (vencidas || detenidas || abiertas)
      ? [
          h('details', 'action-priority-disclosure', h('summary','','Ver acción prioritaria'), div(
            "aer-action-alert-item",
            div(
              "main",
              h("b", "", text(urgente.accion || "Acción prioritaria")),
              h(
                "small",
                "",
                text(
                  urgente.comentarios ||
                    urgente.notas ||
                    "Esta acción está fuera de la fecha compromiso. Es necesario dar seguimiento y definir próximas acciones.",
                ),
              ),
            ),
            meta("Responsable", text(urgente.responsable || "—")),
            meta("Fecha compromiso", dateText(urgente.fechaLimite)),
            meta(
              "Estado",
              h("span", "aer-pill purple", text(urgente.estado || "Pendiente")),
            ),
            meta(
              "Prioridad",
              h("span", "aer-pill red", text(urgente.prioridad || "Alta")),
            ),
          )),
        ]
      : []),
  );
  const distribution=actionDistributionView(m);
  const responsible=actionResponsibleView(m);
  const weekly=actionWeeklyView(m);
  const rows = filas.map((x, index) => {
    const edit = (field, value) => actions.field(x.uid, field, value);
    const inputField = (field, type) => {
      const node = input(x[field] || "", {
        class: "aer-inline-edit",
        "aria-label": fieldLabels[field],
        ...(type ? { type } : {}),
      });
      node.addEventListener("change", () => edit(field, node.value));
      return node;
    };
    const selectField = (field, values, value, blank) => {
      const node = select(
        values,
        value,
        {
          class: "aer-inline-edit",
          "aria-label": fieldLabels[field],
        },
        blank,
      );
      if (field === 'estado') node.classList.add('action-status-edit',stateClass(value));
      if (field === 'prioridad') node.classList.add('action-priority-edit',normalize(value));
      node.addEventListener("change", () => edit(field, node.value));
      return node;
    };
    const action = area(x.accion || "", {
      class: "aer-inline-edit aer-inline-textarea",
      "aria-label": fieldLabels.accion,
    });
    action.addEventListener("change", () => edit("accion", action.value));
    const cls = stateClass(x.estado),
      pct = progress(x.estado);
    return el(
      "tr",
      {
        dataset: {
          actionState: text(x.estado), actionPerson:text(x.responsable), actionPriority:text(x.prioridad),
          actionFilter: (
            normalize(x.accion) +
            " " +
            normalize(x.responsable) +
            " " +
            normalize(x.estado)
          ).trim(),
        },
      },
      cell(String(index + 1)),
      cell(action),
      cell(div('action-inline-person',h('span','action-avatar',String(x.responsable||'?').split(/\s+/).filter(Boolean).slice(0,2).map(n=>n[0]).join('').toUpperCase()),inputField("responsable"))),
      cell(selectField("prioridad", PRIORITIES, x.prioridad || "Media")),
      cell(inputField("fechaInicio", "date")),
      cell(inputField("fechaLimite", "date")),
      cell(inputField("fechaReal", "date")),
      cell(selectField("estado", STATES, x.estado || "Pendiente")),
      cell(
        selectField(
          "dependencia",
          dependencies(x.dependencia),
          x.dependencia || "",
          true,
        ),
      ),
      cell(
        styled(
          div(
            "",
            bar(pct, cls === "bad" ? red : cls === "ok" ? green : actionPurple),
            h("b", "", pct + "%"),
          ),
          {
            display: "grid",
            gridTemplateColumns: "minmax(0,1fr) 40px",
            gap: "10px",
            alignItems: "center",
          },
        ),
      ),
      cell(
        button("✕", () => actions.remove(x.uid), "aer-btn danger", {
          "aria-label": "Eliminar acción",
        }),
      ),
    );
  });
  if (!rows.length)
    rows.push(
      h("tr", "", el("td", { colspan: 11 }, "Sin acciones registradas.")),
    );
  const search = input("", {
    class: "aer-action-search",
    type: "text",
    placeholder: "Buscar acción, responsable...",
    "aria-label": "Buscar acción o responsable",
  });
  search.addEventListener("input", () => filterActions(target, search.value));
  const filterPanel=el('div',{class:'action-filter-panel',hidden:true,role:'group','aria-label':'Filtros de acciones'});
  for(const [id,label,values] of [
    ['action-filter-state','Estado',[...new Set(filas.map(x=>text(x.estado)).filter(Boolean))]],
    ['action-filter-person','Responsable',[...new Set(filas.map(x=>text(x.responsable)).filter(Boolean))]],
    ['action-filter-priority','Prioridad',[...new Set(filas.map(x=>text(x.prioridad)).filter(Boolean))]]
  ]) {
    const node=el('select',{id,'aria-label':label},el('option',{value:'',text:'Todos'}),...values.map(value=>el('option',{value,text:value})));
    node.addEventListener('change',()=>filterActions(target,search.value));
    filterPanel.append(el('label',{},label,node));
  }
  const toggleFilters=button('Filtros',()=>{
    filterPanel.hidden=!filterPanel.hidden;
    toggleFilters.setAttribute('aria-expanded',String(!filterPanel.hidden));
  },'aer-btn',{'aria-expanded':'false'});
  const listing = div(
    "aer-action-table-card action-main-listing",
    div(
      "aer-action-table-head",
      div("", styled(h("h3", "", icon("list"), " Listado de acciones"), { margin: "0" })),
      div(
        "tools",
        search,
        toggleFilters,
      ),
    ),
    filterPanel,
    styled(
      div(
        "",
        table(
          [
            heading("#"),
            styled(heading("Acción / Entregable"), { minWidth: "260px" }),
            ...[
              "Responsable",
              "Prioridad",
              "Fecha inicio",
              "Fecha compromiso",
              "Próxima revisión",
              "Estado",
              "Dependencia",
              "Avance",
              "Eliminar",
            ].map(heading),
          ],
          [el("tbody", { id: "aer-actions-table-body" }, ...rows)],
        ),
      ),
      { overflow: "auto" },
    ),
    styled(
      el("div", {class:"aer-sub",id:"aer-actions-filter-count",role:"status",text:`Mostrando ${filas.length} de ${filas.length} acciones`}),
      { marginTop: "10px" },
    ),
  );
  hero.append(alert);
  target.replaceChildren(
    div(
      "aer-action-shell",
      hero,
      div("aer-action-mid", distribution, responsible, weekly),
      listing,
      renderParts(parts, actions),
    ),
  );
}

let editorReturnFocus = null;
function closeActionEditor() {
  document.getElementById('aer-modal-back')?.remove();
  if (editorReturnFocus?.isConnected) editorReturnFocus.focus();
  editorReturnFocus = null;
}
function modal(...body) {
  document.getElementById('aer-modal-back')?.remove();
  editorReturnFocus = document.activeElement;
  const panel = el('div', {class:'aer-modal action-editor-modal',role:'dialog','aria-modal':'true','aria-labelledby':'action-editor-title'},...body);
  const back=el('div',{class:'aer-modal-back action-editor-overlay',id:'aer-modal-back'},panel);
  back.addEventListener('click',event=>{if(event.target===back)closeActionEditor();});
  back.addEventListener('keydown',event=>{
    if(event.key==='Escape'){event.preventDefault();closeActionEditor();}
    if(event.key==='Tab'){
      const nodes=[...panel.querySelectorAll('button,input,textarea,select,a[href]')].filter(n=>!n.disabled);
      const first=nodes[0],last=nodes.at(-1);
      if(event.shiftKey&&document.activeElement===first){event.preventDefault();last?.focus();}
      else if(!event.shiftKey&&document.activeElement===last){event.preventDefault();first?.focus();}
    }
  });
  document.body.append(back);
  panel.querySelector('textarea,input,select')?.focus();
  return back;
}
function editorHeader(title, subtitle, name) {
  return div('action-editor-header',div('action-editor-heading',h('span','action-editor-icon',icon(name)),div('',el('h3',{id:'action-editor-title',text:title}),h('p','',subtitle))),
    button('✕',closeActionEditor,'aer-btn action-editor-close',{'aria-label':'Cerrar',title:'Cerrar'}));
}
function editorField(title, field, name, wide=false, required=false) {
  field.setAttribute('aria-label',title);
  if(required)field.setAttribute('aria-required','true');
  return h('label','action-editor-field'+(wide?' aer-span2':''),
    h('span','action-editor-label',icon(name),title,required?h('span','action-required','*'):null),field);
}
function countedText(value, id, placeholder) {
  const field=area(value,{id,placeholder,rows:3});
  const counter=el('span',{class:'action-editor-counter',id:id+'-counter','aria-live':'polite'});
  const update=()=>{counter.textContent=`${field.value.length} caracteres`;};
  field.addEventListener('input',update);update();
  field.setAttribute('aria-describedby',counter.id);
  const box=div('action-editor-text',field,counter);
  // The original field stays free of new length limits, preserving existing text.
  return {field,box};
}
function textField(title,value,id,placeholder,name,required=false) {
  const counted=countedText(value,id,placeholder);
  counted.field.setAttribute('aria-label',title);
  if(required)counted.field.setAttribute('aria-required','true');
  return h('label','action-editor-field aer-span2',h('span','action-editor-label',icon(name),title,required?h('span','action-required','*'):null),counted.box);
}
function editorSelect(options,value,id,kind) {
  const field=select(options,value,{id,class:'action-editor-select '+(kind||'')});
  const paint=()=>{field.dataset.tone=normalize(field.value);};
  field.addEventListener('change',paint);paint();return field;
}
function editorSave(text,onclick,props={}) {
  return el('button',{type:'button',class:'aer-btn primary',onclick,...props},icon('check'),text);
}
export function openAction(data, uid, actions) {
  const x=(data.acciones?.filas||[]).find(row=>row.uid===uid)||{};
  const owners=[...new Set([
    ...(data.filasRecursosCompleto||[]).map(row=>row.nombre),
    ...(data.acciones?.filas||[]).map(row=>row.responsable),
    data.proyecto?.pm,data.proyecto?.deliveryManager
  ].filter(Boolean).map(String))];
  const ownerInput=input(x.responsable||'',{id:'aa-r',list:'action-editor-owners',placeholder:'Escribe o selecciona un responsable'});
  return modal(
    editorHeader((uid?'Editar':'Agregar')+' acción','Registra una acción, su seguimiento y control.','sparkles'),
    div('aer-formgrid action-editor-grid',
      textField('Acción / Entregable',x.accion||'','aa-a','Describe la acción o entregable…','list',true),
      editorField('Responsable',ownerInput,'user'),
      editorField('Estado',editorSelect(STATES,x.estado||'Pendiente','aa-e','state'),'target'),
      editorField('Fecha inicio',input(x.fechaInicio||'',{type:'date',id:'aa-fi'}),'calendar'),
      editorField('Fecha compromiso',input(x.fechaLimite||'',{type:'date',id:'aa-f'}),'calendar'),
      editorField('Fecha real',input(x.fechaReal||'',{type:'date',id:'aa-fr'}),'calendar'),
      editorField('Dependencia',select(dependencies(x.dependencia),x.dependencia||'',{id:'aa-d'},true),'link'),
      editorField('Prioridad',editorSelect(PRIORITIES,x.prioridad||'Media','aa-p','priority'),'flag'),
      textField('Comentarios',x.comentarios||x.notas||'','aa-n','Agrega comentarios o contexto de la acción…','megaphone')),
    el('datalist',{id:'action-editor-owners'},...owners.map(name=>el('option',{value:name}))),
    div('aer-actions action-editor-footer',
      ...(uid?[button('Eliminar',()=>actions.remove(uid,true),'aer-btn danger')]:[]),
      button('Cancelar',closeActionEditor),editorSave('Guardar',()=>actions.save(uid))))
}
export function openPart(actions) {
  return modal(
    editorHeader('Agregar pendiente Beecker / Cliente','Registra un compromiso o pendiente con Beecker o el cliente.','list'),
    div('aer-formgrid action-editor-grid',
      textField('Acción / entregable','','aerp-new-accion','Describe el compromiso pendiente…','list',true),
      editorField('Responsable',select(['Beecker','Cliente'],'Beecker',{id:'aerp-new-parte'}),'user'),
      editorField('Estado',editorSelect(STATES,'Pendiente','aerp-new-estado','state'),'target'),
      editorField('Fecha compromiso',input('',{type:'date',id:'aerp-new-fecha'}),'calendar'),
      editorField('Próxima revisión',input('',{type:'date',id:'aerp-new-revision'}),'calendar'),
      textField('Notas','','aerp-new-notas','Agrega información adicional…','layers')),
    div('aer-actions action-editor-footer',button('Cancelar',closeActionEditor),editorSave('Guardar pendiente',actions.savePart,{id:'aerp-new-save'})));
}
