/* Progressive updates through the existing read-only portal routes. */
(function () {
  'use strict';
  const root = () => document.getElementById('ops-dashboard');
  if (!root()) return;
  const endpoint = root().dataset.endpoint;
  const summaryEndpoint = root().dataset.summaryEndpoint;
  const params = new URLSearchParams(location.search);
  params.delete('bloque');
  let refreshing = false;
  const controllers = new Set();

  // Keep the latest investment separately: EVA and investment finish independently.
  let investment = null;
  function updateManagerInvestment(doc) {
    const payload = doc && doc.getElementById('ops-investment-data');
    if (payload) {
      try { investment = JSON.parse(payload.textContent); } catch (_) { /* Keep current cut. */ }
    }
    if (!investment) return;
    document.querySelectorAll('[data-investment-projects]').forEach(node => {
      let ids;
      try { ids = JSON.parse(node.dataset.investmentProjects); } catch (_) { return; }
      const rows = ids.filter(id => Object.prototype.hasOwnProperty.call(investment.by_project || {}, id))
        .map(id => investment.by_project[id]);
      const ready = investment.complete && rows.length > 0;
      node.querySelectorAll('[data-investment]').forEach(value => {
        const hours = rows.reduce((sum, row) => sum + (Number(row[value.dataset.investment]) || 0), 0);
        value.textContent = ready ? hours.toLocaleString('es-MX', {maximumFractionDigits: 1}) + ' h' : '—';
      });
    });
  }

  function status(message) {
    const node = document.getElementById('ops-refresh-status');
    if (node) node.textContent = message;
    const button = document.getElementById('ops-refresh-button');
    if (button) button.title = message;
  }

  function busy(value) {
    const button = document.getElementById('ops-refresh-button');
    if (button) { button.hidden = false; button.disabled = value; button.textContent = value ? 'Actualizando…' : 'Actualizar datos'; }
  }

  async function read(url) {
    const controller = new AbortController();
    controllers.add(controller);
    const timer = setTimeout(() => controller.abort(), 120000);
    try {
      const response = await fetch(url, {
        credentials: 'same-origin', signal: controller.signal
      });
      if (!response.ok || response.redirected) throw new Error('Fuente no disponible');
      const text = await response.text();
      return new DOMParser().parseFromString(text, 'text/html');
    } finally {
      clearTimeout(timer);
      controllers.delete(controller);
    }
  }

  async function dashboard(block, force = false) {
    const query = new URLSearchParams(params);
    if (block) query.set('bloque', block);
    if (force) query.set('actualizar', '1');
    const doc = await read(endpoint + '?' + query);
    const next = doc.getElementById('ops-dashboard');
    if (!next) throw new Error('Respuesta incompleta');
    if (block && next.dataset.blockError) throw new Error('Datos parciales');
    return doc;
  }

  function replaceSections(doc, ids) {
    const pairs = ids.map(id => [document.getElementById(id), doc.getElementById(id)]);
    if (pairs.some(pair => !pair[0] || !pair[1])) throw new Error('Respuesta incompleta');
    pairs.forEach(([current, next]) => {
      if (current.id === 'ops-evas') {
        const liveCard = document.getElementById('ops-eva4-card');
        const placeholder = next.querySelector('#ops-eva4-card');
        if (liveCard && placeholder) placeholder.replaceWith(liveCard);
      }
      const oldTrack = current.querySelector('.dm-carousel-track');
      const scroll = oldTrack ? oldTrack.scrollLeft : 0;
      current.replaceWith(next);
      const newTrack = next.querySelector('.dm-carousel-track');
      if (newTrack) newTrack.scrollLeft = scroll;
    });
    updateManagerInvestment();
  }

  function replaceDashboard(doc) {
    const next = doc.getElementById('ops-dashboard');
    // Keep the live node: facturability may finish before or after this request.
    const summary = document.getElementById('facturability-summary');
    const placeholder = next.querySelector('#facturability-summary');
    if (!summary || !placeholder) throw new Error('Respuesta incompleta');
    const focus = document.activeElement;
    const focusId = focus && focus.id;
    const focusName = focus && focus.name;
    placeholder.replaceWith(summary);
    root().replaceWith(next);
    updateManagerInvestment(doc);
    if (focusId) {
      const target = document.getElementById(focusId);
      if (target) target.focus({preventScroll: true});
    } else if (focusName) {
      const target = Array.from(next.querySelectorAll('select')).find(node => node.name === focusName);
      if (target) target.focus({preventScroll: true});
    }
    const freshness = document.getElementById('portal-freshness-text');
    if (freshness && next.dataset.loadedAt) {
      freshness.textContent = 'Corte calculado al ' + next.dataset.loadedAt;
    }
  }

  async function refreshSummary(force = false) {
    const target = document.getElementById('facturability-summary');
    target.setAttribute('aria-busy', 'true');
    try {
      const doc = await read(summaryEndpoint + (force ? '?actualizar=1' : ''));
      const summary = doc.querySelector('[data-operations-summary]');
      if (!summary) throw new Error('Respuesta incompleta');
      target.replaceChildren(summary);
      if (summary.dataset.partial === 'true') throw new Error('Datos parciales');
    } catch (error) {
      if (!target.querySelector('[data-operations-summary]')) {
        target.textContent = 'No se pudo cargar facturabilidad. Consulta el detalle o vuelve a actualizar.';
      }
      throw error;
    } finally {
      target.setAttribute('aria-busy', 'false');
    }
  }

  async function refreshPortfolio(failures, force) {
    try {
      const pending = root().dataset.pendingBlocks;
      const needed = force || typeof pending !== 'string' ? null : pending.split(',');
      const doc = await dashboard('', force);
      const next = doc.getElementById('ops-dashboard');
      replaceDashboard(doc);
      busy(true);
      if (Number(next.dataset.sourceErrors) > 0) failures.push('fuentes del portafolio');
      status('Proyectos y estados disponibles. Actualizando consumo, inversión y capacidad…');
      const blocks = [
        ['eva4', 'EVA-04 Report', ['ops-eva4-card']],
        ['inversion', 'inversión', ['ops-investment-operational', 'ops-investment-commercial']],
        ['capacidad', 'capacidad', ['ops-capacity']],
        ['eva3', 'EVA 3', ['ops-metric-progress', 'ops-metric-paused', 'ops-metric-on-time', 'ops-health', 'ops-managers', 'ops-evas']]
      ];
      await Promise.all(blocks.filter(([block]) => !needed || needed.includes(block)).map(async ([block, label, ids]) => {
        try {
          const updated = await dashboard(block, force);
          replaceSections(updated, ids);
          if (block === 'inversion') updateManagerInvestment(updated);
        } catch (error) {
          failures.push(label);
        }
      }));
    } catch (error) {
      failures.push('portafolio');
    }
  }

  async function refresh(force = false) {
    if (refreshing) return;
    refreshing = true;
    busy(true);
    status('Actualizando indicadores. Puedes seguir consultando el corte disponible…');
    const failures = [];
    try {
      await Promise.all([
        refreshPortfolio(failures, force),
        (force || root().dataset.summaryFresh !== 'true'
          ? refreshSummary(force).catch(() => failures.push('facturabilidad'))
          : Promise.resolve())
      ]);
      status(failures.length
        ? 'Actualización parcial: no se pudo actualizar ' + failures.join(', ') + '. Se conserva la información disponible. Puedes reintentar.'
        : 'Consulta completada. Cada sección indica su período; los datos pueden proceder de caché.');
      const freshness = document.getElementById('portal-freshness');
      if (freshness) freshness.dataset.state = failures.length ? 'partial' : 'success';
    } finally {
      refreshing = false;
      busy(false);
    }
  }


  document.addEventListener('click', function (event) {
    const button = event.target.closest('#ops-refresh-button');
    if (button) { refresh(true); return; }
    const stepButton = event.target.closest('[data-dm-step]');
    if (!stepButton) return;
    const track = stepButton.closest('.dm-carousel').querySelector('.dm-carousel-track');
    const card = track.firstElementChild;
    if (!card) return;
    track.scrollBy({
      left: Number(stepButton.dataset.dmStep) * (card.getBoundingClientRect().width + 14),
      behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth'
    });
  });

  document.addEventListener('change', function (event) {
    const select = event.target.closest('select[data-account-navigation]');
    if (!select) return;
    if (!select.value) { select.form.submit(); return; }
    const slug = select.value.normalize('NFKD').replace(/[\u0300-\u036f]/g, '')
      .toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');
    location.assign(root().dataset.accountUrl.replace('account-placeholder', slug)
      + '?nombre=' + encodeURIComponent(select.value));
  });

  window.addEventListener('pagehide', () => controllers.forEach(controller => controller.abort()));
  updateManagerInvestment(document);
  busy(false);
  if (root().dataset.async === 'true') refresh();
  else if (root().dataset.summaryFresh !== 'true') {
    refreshSummary().catch(() => status('No se pudo completar facturabilidad. Consulta el detalle.'));
  }
})();
