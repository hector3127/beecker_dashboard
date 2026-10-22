(function () {
  const source = document.getElementById('kpi-chart-data');
  if (!source) return;
  const data = JSON.parse(source.textContent);
  const svg = document.getElementById('kpi-chart');
  const legend = document.getElementById('kpi-legend');
  const toggle = document.getElementById('kpi-chart-toggle');
  const scale = document.getElementById('kpi-chart-scale');
  const colors = ['#6347ed', '#18ad78', '#ed9c0a', '#e0457b', '#2a9fd6', '#8a7eae'];
  const ns = 'http://www.w3.org/2000/svg';
  const left = 45, right = 535, top = 16, bottom = 234;
  const count = data.labels.length;
  const step = count > 1 ? (right - left) / (count - 1) : 0;
  const x = i => count > 1 ? left + i * step : (left + right) / 2;
  const valid = v => typeof v === 'number' && Number.isFinite(v);
  let completeScale = false, selected = null;

  function node(tag, attrs, text) {
    const el = document.createElementNS(ns, tag);
    for (const [key, value] of Object.entries(attrs)) el.setAttribute(key, value);
    if (text !== undefined) el.textContent = text;
    svg.appendChild(el);
    return el;
  }

  function draw() {
    svg.replaceChildren();
    const series = data.series.filter((_, i) => selected === null || selected === i);
    const values = series.flatMap(s => s.values).filter(valid);
    const low = values.length ? Math.min(...values) : 0;
    const high = values.length ? Math.max(...values) : 100;
    const minimum = completeScale ? Math.min(0, Math.floor(low / 10) * 10) :
      (low >= 0 ? Math.max(0, Math.floor((low - 5) / 10) * 10) : Math.floor((low - 5) / 10) * 10);
    const maximum = completeScale ? Math.max(100, Math.ceil(high / 10) * 10) :
      Math.max(minimum + 10, Math.ceil((high + 5) / 10) * 10);
    const y = v => bottom - (v - minimum) / (maximum - minimum) * (bottom - top);
    scale.textContent = (completeScale ? 'Escala completa: ' : 'Escala ampliada: ') + minimum + '–' + maximum + '%';
    toggle.textContent = completeScale ? 'Ampliar diferencias' : 'Ver escala completa';
    toggle.setAttribute('aria-pressed', String(completeScale));
    const interval = completeScale && minimum === 0 && maximum === 100 ? 25 :
      (maximum - minimum <= 20 ? 5 : Math.ceil((maximum - minimum) / 5 / 10) * 10);
    const ticks = [];
    for (let value = minimum; value <= maximum; value += interval) ticks.push(value);
    if (ticks[ticks.length - 1] !== maximum) ticks.push(maximum);
    ticks.forEach(value => {
      node('line', {x1: left, x2: right, y1: y(value), y2: y(value), stroke: '#e4def4', 'stroke-dasharray': '3 4'});
      node('text', {x: left - 7, y: y(value) + 4, 'text-anchor': 'end', fill: '#8a7eae', 'font-size': 10}, value + '%');
    });
    data.labels.forEach((label, i) => {
      if ((data.highlight || []).includes(label)) {
        const width = count > 1 ? step : 80;
        const start = Math.max(left, x(i) - width / 2);
        node('rect', {x: start, y: top, width: Math.min(right, x(i) + width / 2) - start,
          height: bottom - top, fill: '#6347ed', 'fill-opacity': .07, rx: 4});
      }
      node('text', {x: x(i), y: 256, 'text-anchor': 'middle', fill: '#8a7eae', 'font-size': 11}, label);
    });
    data.series.forEach((serie, index) => {
      if (selected !== null && selected !== index) return;
      const color = colors[index % colors.length];
      let path = '', connected = false;
      serie.values.forEach((value, i) => {
        if (!valid(value)) { connected = false; return; }
        path += (connected ? 'L' : 'M') + x(i) + ' ' + y(value);
        connected = true;
      });
      node('path', {d: path, fill: 'none', stroke: color, 'stroke-width': 2.5, 'stroke-linejoin': 'round'});
      serie.values.forEach((value, i) => {
        if (!valid(value)) return;
        const point = node('circle', {cx: x(i), cy: y(value), r: 3.5, fill: color});
        const title = document.createElementNS(ns, 'title');
        title.textContent = serie.name + ' · ' + data.labels[i] + ': ' + value + '%';
        point.appendChild(title);
      });
    });
    if (!values.length) node('text', {x: 290, y: 125, 'text-anchor': 'middle', fill: '#8075a7'}, 'Sin valores para este periodo');
    Array.from(legend.children).forEach((button, i) => {
      button.setAttribute('aria-pressed', String(selected === i));
      button.style.opacity = selected === null || selected === i ? '1' : '.5';
    });
  }

  data.series.forEach((serie, index) => {
    const button = document.createElement('button');
    button.type = 'button';
    const dot = document.createElement('i');
    dot.style.background = colors[index % colors.length];
    dot.setAttribute('aria-hidden', 'true');
    button.append(dot, serie.name);
    button.onclick = () => { selected = selected === index ? null : index; draw(); };
    legend.appendChild(button);
  });
  toggle.onclick = () => { completeScale = !completeScale; draw(); };
  draw();
})();
