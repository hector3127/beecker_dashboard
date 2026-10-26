// Available capacity and its existing billable/base meter, presentation only.
import { el } from '#app/lib/dom.js';
import { formatNumber } from '#app/lib/format.js';
import { icon } from '#app/ui/icons.js';
const NO_VALUE='—';
const RESTRICTED='Cifras del equipo completo: no disponibles con tu acceso.';
const known=value=>typeof value==='number'&&Number.isFinite(value);
const hours=(value,digits=2)=>known(value)?`${formatNumber(value,digits)} h`:NO_VALUE;
/** Existing meter: billable hours / base capacity, clamped to 0–100. */
export function meterPercent(billable, base) {
  return base ? Math.min(100, Math.max(0, Math.round((billable / base) * 100))) : 0;
}
function ratio(value,base){return known(value)&&known(base)&&base>0?`${formatNumber(value/base*100,1)}% de la capacidad`:'';}
function stat(label,value,note,tone){
  return el('div',{class:`capacity-stat ${tone}`},el('span',{class:'capacity-stat-label',text:label}),el('strong',{text:hours(value)}),el('small',{text:note}));
}
function detail(label,value,note,glyph){
  return el('div',{class:'capacity-detail-row'},el('span',{class:'capacity-detail-icon'},icon(glyph,20)),el('span',{text:label}),el('div',{},el('strong',{text:hours(value)}),el('small',{text:note})));
}
export function renderCapacity(root,capacity){
  const section=root.closest('.ops-capacity-section');
  const details=section?.querySelector('#ops-capacity-details');
  const period=section?.querySelector('#ops-capacity-month');
  details?.replaceChildren();
  if(capacity===null){root.replaceChildren(el('p',{class:'ops-muted capacity-message',text:RESTRICTED}));if(period)period.textContent='Acceso limitado';return;}
  if(period){
    const valid=/^\d{4}-\d{2}$/.test(capacity.month||'');
    const date=valid?new Date(Number(capacity.month.slice(0,4)),Number(capacity.month.slice(5,7))-1,1):null;
    const text=date?date.toLocaleDateString('es-MX',{month:'long',year:'numeric'}):'Periodo pendiente';
    period.textContent=text[0].toUpperCase()+text.slice(1);
  }
  const available=!capacity.error&&known(capacity.available);
  const left=el('div',{class:'capacity-main'},
    el('div',{class:'capacity-main-heading'},el('span',{class:'capacity-main-icon'},icon('team',25)),el('h3',{text:'Capacidad instalada'}),el('span',{class:'capacity-info',title:'Disponibilidad calculada por recurso y día en el corte operativo.',text:'ⓘ'})),
    el('strong',{class:'capacity-main-value',text:available?formatNumber(capacity.available,0):NO_VALUE}),
    el('p',{class:'capacity-main-caption',text:capacity.loading?'Calculando…':'horas disponibles'}),
    el('p',{class:'capacity-main-period',text:capacity.loading?'':`${capacity.month||'Periodo pendiente'} · ${capacity.registered_people??'—'} recursos con registros`})
  );
  if(capacity.loading||capacity.error){root.replaceChildren(left,el('p',{class:'ops-muted capacity-message',text:capacity.loading?'Calculando capacidad y horas registradas…':capacity.error}));return;}
  const usageKnown=known(capacity.billable)&&known(capacity.base)&&capacity.base>0;
  const percent=usageKnown?meterPercent(capacity.billable,capacity.base):0;
  const meter=el('div',{class:'ops-meter',role:'img','aria-label':usageKnown?`Horas facturables respecto a capacidad base: ${percent}%`:'Uso de capacidad pendiente'},el('i'));
  meter.firstElementChild.style.width=`${percent}%`;
  const baseText=`Capacidad base del mes: ${hours(capacity.base,0)} (${capacity.days??'—'} días × 8 h). ${capacity.over??'—'} personas sobre jornada.`+(capacity.pending?` ${capacity.pending} asignaciones pendientes; horas parciales.`:'');
  const center=el('div',{class:'capacity-usage'},
    el('h3',{},'Uso de la capacidad del equipo ',el('span',{class:'capacity-info',title:'Horas facturables divididas entre la capacidad base del mes. El medidor se limita a 0–100%.',text:'ⓘ'})),
    el('div',{class:'capacity-meter-row'},meter,el('div',{class:'capacity-meter-value'},el('strong',{text:usageKnown?`${percent}%`:NO_VALUE}),el('span',{text:'utilizado'}))),
    el('div',{class:'capacity-stats'},stat('Horas facturables',capacity.billable,ratio(capacity.billable,capacity.base),'capacity-stat-billable'),stat('Horas disponibles',capacity.available,ratio(capacity.available,capacity.base),'capacity-stat-available'),stat('Estimadas (Recursos)',capacity.estimated,'Estimadas en el mes','capacity-stat-estimated')),
    el('div',{class:'capacity-notes'},el('span',{'aria-hidden':'true',text:'ⓘ'}),el('div',{},el('p',{text:'Estimaciones de las asignaciones de recursos con registros en el mes seleccionado.'}),el('p',{text:baseText})))
  );
  details?.replaceChildren(detail('Consumo actual (Clockify)',capacity.consumed,ratio(capacity.consumed,capacity.base),'pause'),detail('Estimadas (Recursos)',capacity.estimated,ratio(capacity.estimated,capacity.base),'chart'),detail('Capacidad base del mes',capacity.base,`${capacity.days??'—'} días × 8 h`,'target'));
  root.replaceChildren(left,center);
}
