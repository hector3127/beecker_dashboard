/* Selection uses the monthly values already loaded; no source requests. */
(function () {
  'use strict';
  function selectBillingMonth(button) {
    const root = button.closest('[data-operations-summary]');
    if (!root) return;
    const number = value => value === '' || value == null ? null : Number(value);
    const fmt = (value, digits=2) => value == null || !Number.isFinite(value) ? '—' : value.toLocaleString('es-MX', {maximumFractionDigits:digits})+'%';
    const percent=number(button.dataset.percent), fixed=number(button.dataset.fixed), variable=number(button.dataset.variable);
    root.querySelector('[data-billing-value]').textContent=fmt(percent);
    root.querySelector('[data-billing-fixed]').textContent='AER '+fmt(fixed,0);
    root.querySelector('[data-billing-variable]').textContent='PRJ '+fmt(variable,0);
    const gap=root.querySelector('[data-billing-gap]');
    const difference=percent==null?null:Math.round((percent-Number(root.dataset.target))*100)/100;
    gap.textContent=difference==null?'Sin datos para comparar con la meta':
      (difference>=0?'↑ ':'↓ ')+Math.abs(difference).toLocaleString('es-MX',{maximumFractionDigits:1})+' puntos '+(difference>=0?'arriba':'abajo')+' de la meta';
    gap.style.color=difference==null?'#625780':difference>=0?'#17924B':'#C0233E';
    const latest=button.dataset.billingMonth===root.dataset.latestMonth;
    root.querySelector('[data-billing-label]').textContent=button.dataset.label+' · '+(latest?(root.dataset.monthClosed==='true'?'último mes cerrado':'mes en curso'):'mes seleccionado');
    root.querySelectorAll('[data-billing-month]').forEach(bar=>{
      const selected=bar===button;
      bar.setAttribute('aria-pressed',String(selected));
      bar.querySelector('rect').setAttribute('fill',selected?'#4B25C9':'#C9B8F7');
    });
  }
  if(typeof module!=='undefined')module.exports={selectBillingMonth};
  if(typeof document==='undefined')return;
  document.addEventListener('click',event=>{
    const button=event.target.closest('[data-billing-month]');
    if(button)selectBillingMonth(button);
  });
  document.addEventListener('keydown',event=>{
    const button=event.target.closest('[data-billing-month]');
    if(button&&(event.key==='Enter'||event.key===' ')){event.preventDefault();selectBillingMonth(button);}
  });
})();
