// Interacciones de la maqueta: ninguna consulta ni escritura de negocio.
(() => {
  const months = [
    {name:'Abril', short:'Abr', revenue:504000, cost:228000},
    {name:'Mayo', short:'May', revenue:660000, cost:276000},
    {name:'Junio', short:'Jun', revenue:600000, cost:252000},
    {name:'Julio', short:'Jul', revenue:810000, cost:342000},
    {name:'Agosto', short:'Ago', revenue:696000, cost:312000},
    {name:'Septiembre', short:'Sep', revenue:870000, cost:372000},
  ];
  const host = document.getElementById('expressive-chart');
  const readout = document.getElementById('chart-readout');
  const enabled = {revenue:true,cost:true,margin:true};
  let selected = 5;
  const format = value => 'USD '+value.toLocaleString('es-MX');
  const margin = row => (row.revenue-row.cost)/row.revenue*100;
  function describe(index) {
    const row = months[index];
    readout.innerHTML = '<span class="readout-month">'+row.name+'</span>'+
      (enabled.revenue?'<span>Ingresos <b>'+format(row.revenue)+'</b></span>':'')+
      (enabled.cost?'<span>Costos <b>'+format(row.cost)+'</b></span>':'')+
      (enabled.margin?'<span>Margen <b>'+margin(row).toFixed(1)+'%</b></span>':'');
  }
  function render() {
    const mobile = matchMedia('(max-width:700px)').matches;
    const w = mobile?360:680, left = mobile?38:53, right = mobile?30:35;
    const top = 22, bottom = 183, step = (w-left-right)/6;
    const bar = Math.min(mobile?14:24,(step-12)/2);
    const y = n => bottom - n/1000000*(bottom-top);
    const ym = n => bottom - n/100*(bottom-top);
    let svg = '<svg viewBox="0 0 '+w+' 232" role="group" aria-label="Gráfica interactiva de ejemplo: ingresos, costos y margen. Selecciona un mes con el teclado, el cursor o un toque.">';
    for(let i=0;i<=3;i++){
      const amount=i*300000, yy=y(amount);
      svg+='<path class="plot-grid" d="M'+left+' '+yy+'H'+(w-right)+'"/>'+
        '<text x="'+(left-7)+'" y="'+(yy+4)+'" text-anchor="end" style="font-size:10px">'+(i?i*300+' mil':'0')+'</text>';
    }
    months.forEach((row,i)=>{
      const center=left+step*(i+.5), x=center-bar-2;
      svg+='<g class="month-group '+(selected===i?'selected':'')+'" role="button" tabindex="0" aria-label="'+row.name+': ingresos '+row.revenue+' dólares, costos '+row.cost+' dólares, margen '+margin(row).toFixed(1)+' por ciento; serie ilustrativa" data-month="'+i+'">'+
        '<rect class="month-hit" x="'+(left+step*i+1)+'" y="12" width="'+(step-2)+'" height="195" rx="7"/>';
      if(enabled.revenue)svg+='<rect class="rev-bar" x="'+x+'" y="'+y(row.revenue)+'" width="'+bar+'" height="'+(bottom-y(row.revenue))+'" rx="3"/>';
      if(enabled.cost)svg+='<rect class="cost-bar" x="'+(center+2)+'" y="'+y(row.cost)+'" width="'+bar+'" height="'+(bottom-y(row.cost))+'" rx="3"/>';
      svg+='<text x="'+center+'" y="207" text-anchor="middle">'+row.short+'</text></g>';
    });
    if(enabled.margin){
      svg+='<path class="margin-path" pointer-events="none" d="'+months.map((row,i)=>(i?'L':'M')+(left+step*(i+.5))+' '+ym(margin(row))).join(' ')+'"/>';
      months.forEach((row,i)=>svg+='<circle class="margin-point" pointer-events="none" cx="'+(left+step*(i+.5))+'" cy="'+ym(margin(row))+'" r="3.5"/>');
      [0,50,100].forEach(n=>svg+='<text x="'+(w-right+6)+'" y="'+(ym(n)+4)+'" style="font-size:10px">'+n+'%</text>');
    }
    host.innerHTML=svg+'</svg>';
    describe(selected);
    host.querySelectorAll('[data-month]').forEach(group=>{
      const select=()=>{
        selected=Number(group.dataset.month);
        host.querySelectorAll('[data-month]').forEach(g=>g.classList.toggle('selected',g===group));
        describe(selected);
      };
      group.addEventListener('pointermove',select);
      group.addEventListener('focus',select);
      group.addEventListener('click',select);
      group.addEventListener('keydown',event=>{
        if(event.key==='Enter'||event.key===' '){event.preventDefault();select();}
      });
    });
  }
  document.querySelectorAll('.series-toggle').forEach(button=>button.addEventListener('click',()=>{
    const series=button.dataset.series;
    if(enabled[series]&&Object.values(enabled).filter(Boolean).length===1)return;
    enabled[series]=!enabled[series];
    button.setAttribute('aria-pressed',String(enabled[series]));
    render();
  }));
  matchMedia('(max-width:700px)').addEventListener('change',render);
  render();
  document.querySelectorAll('[data-preview-action]').forEach(button=>button.addEventListener('click',event=>{
    event.preventDefault();
    const feedback=document.getElementById('decision-feedback');
    feedback.textContent='En el panel final, esta acción abrirá el detalle del proyecto '+button.dataset.previewAction+'. Esta maqueta no modifica datos.';
    feedback.hidden=false;
  }));
})();
