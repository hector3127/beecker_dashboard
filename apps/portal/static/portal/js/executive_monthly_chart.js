// Responsive rendering only: values and percentages come from the API.
function executiveMonthlyChartSvg(data, viewportWidth) {
  const rows = data.months || [];
  const viewport = Math.max(240, Number(viewportWidth) || 900);
  const width = rows.length > 6 ? Math.max(viewport, 120 + rows.length * 84) : viewport;
  const left = viewport < 500 ? 53 : 72;
  const right = viewport < 500 ? 43 : 55;
  const top = 32, baseline = 222;
  const plot = width - left - right;
  const step = plot / Math.max(1, rows.length);
  const barWidth = Math.max(6, Math.min(36, (step - 12) / 2));
  const fmt = n => typeof executiveMoney==='function'?executiveMoney(n):Number(n/1000).toLocaleString('en-US',{maximumFractionDigits:0})+'K';
  const escape = value => String(value).replace(/[&<>"']/g, ch => ({
    '&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;', "'":'&#39;',
  }[ch]));
  const values = rows.flatMap(row => [row.revenue, row.cost ?? 0]);
  const maximum = Math.max(1, ...values), minimum = Math.min(0, ...values);
  const range = maximum - minimum;
  const y = value => baseline - (value - minimum) * (baseline-top) / range;
  const zero = y(0);
  const margins = rows.filter(row => row.margin != null).map(row => row.margin);
  const marginMin = Math.min(0, ...margins), marginMax = Math.max(100, ...margins);
  const my = value => baseline - (value-marginMin)*(baseline-top)/(marginMax-marginMin);
  const text = (x, yy, value, color='#4A4D86', anchor='middle') =>
    '<text x="'+x+'" y="'+yy+'" text-anchor="'+anchor+'" fill="'+color+'" font-size="11">'+escape(value)+'</text>';
  let svg = '<svg width="'+width+'" style="min-width:'+width+'px" viewBox="0 0 '+width+' 275" role="img" aria-label="Ingresos, costos y margen mensual. Montos en USD; margen en el eje derecho.">';
  if (!rows.length) return svg+text(width/2, 140, 'Sin datos para este periodo')+'</svg>';
  for (let i=0;i<=3;i++) {
    const yy=baseline-i*(baseline-top)/3;
    svg+='<line x1="'+left+'" x2="'+(width-right)+'" y1="'+yy+'" y2="'+yy+'" stroke="#ECEEFA"/>';
    svg+=text(left-6, yy+4, fmt(minimum+range*i/3), '#4A4D86', 'end');
  }
  const segments=[];
  let segment=[];
  rows.forEach((row,i) => {
    const center=left+step*(i+.5), x=center-barWidth-2;
    const date=new Date(row.month+'-02T12:00:00');
    const label=date.toLocaleDateString('es-MX', rows.length>12 ?
      {month:'short',year:'2-digit'} : {month:'short'});
    function bar(xx, value, color, kind) {
      if (value==null) return text(xx+barWidth/2, baseline-8, step<70?'—':'Pendiente');
      const yy=Math.min(zero,y(value)), height=Math.abs(zero-y(value));
      return '<rect x="'+xx+'" y="'+yy+'" width="'+barWidth+'" height="'+height+'" rx="3" fill="'+color+'"><title>'+escape(row.month+' · '+kind+': '+fmt(value))+'</title></rect>'+
        (step>=105 ? text(xx+barWidth/2,Math.max(17,yy-7),fmt(value),'#2A2D7A') : '');
    }
    svg+=bar(x,row.revenue,'#8B5CF6','Facturación');
    svg+=bar(center+2,row.cost,'#C9BDF2','Costos');
    svg+=text(center,250,label);
    if(row.margin!=null) {
      segment.push({x:center,y:my(row.margin),value:row.margin,month:row.month});
    } else if(segment.length) {
      segments.push(segment); segment=[];
    }
  });
  if(segment.length) segments.push(segment);
  if(margins.length) {
    for(let i=0;i<=3;i++)svg+=text(width-right+6,baseline-i*(baseline-top)/3+4,
      Math.round(marginMin+(marginMax-marginMin)*i/3)+'%','#F0489E','start');
    segments.forEach(points=>{
      svg+='<polyline points="'+points.map(p=>p.x+','+p.y).join(' ')+'" fill="none" stroke="#F0489E" stroke-width="3"/>';
      points.forEach(p=>{
        svg+='<circle cx="'+p.x+'" cy="'+p.y+'" r="4" fill="#F0489E"><title>'+escape(p.month+' · Margen: '+p.value+'%'+(data.complete?'':' provisional'))+'</title></circle>';
        if(step>=70) svg+=text(p.x, p.y<baseline-25?p.y+20:Math.max(14,p.y-12),
          Number(p.value).toLocaleString('es-MX',{maximumFractionDigits:1})+'%'+(data.complete?'':'*'),'#C92C7E')
          .replace('<text ', '<text style="paint-order:stroke;stroke:#fff;stroke-width:4;stroke-linejoin:round" ');
      });
    });
  }
  return svg+'</svg>';
}

const executiveMonthlyCharts = new WeakMap();
function mountExecutiveMonthlyChart(container, data) {
  let chart=executiveMonthlyCharts.get(container);
  if(!chart) {
    chart={data, width:0};
    chart.render=()=>{
      const width=container.clientWidth||900;
      container.innerHTML=executiveMonthlyChartSvg(chart.data,width);
      chart.width=width;
    };
    if(typeof ResizeObserver!=='undefined') {
      chart.observer=new ResizeObserver(()=>{
        if(container.clientWidth && container.clientWidth!==chart.width)chart.render();
      });
      chart.observer.observe(container);
    }
    executiveMonthlyCharts.set(container,chart);
  }
  chart.data=data;
  chart.render();
}
if(typeof module!=='undefined')module.exports={executiveMonthlyChartSvg};
