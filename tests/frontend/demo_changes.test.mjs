import test from 'node:test';
import assert from 'node:assert/strict';
import { computed, resourceDetail } from '../../frontend/static/scripts/pages/capacity_daily/model.js';
import { workPlanDocuments } from '../../frontend/static/scripts/pages/project_detail/sections/work_plan_model.js';

test('resource drilldown retains all projects, pending data and the original totals', () => {
  const st = { mes: '2026-10', jornada: 8,
    base: { filas: [
      { recurso: 'Ána', idProyecto: 'P1', iteration: '', concepto: 'Proyecto', regla: { afecta: true } },
      { recurso: 'Ana', idProyecto: 'P2', iteration: '', concepto: 'Proyecto', regla: { afecta: true } },
      { recurso: 'Luis', idProyecto: 'P3', iteration: '', concepto: 'Proyecto', regla: { afecta: true } },
    ] }, meta: new Map([['P1|', { ok: true, daily: { ana: { '2026-10-01': 3 } } }], ['P3|', { ok: true, daily: { luis: { '2026-10-01': 6 } } }]]) };
  const data = computed(st), before = JSON.stringify(data);
  const detail = resourceDetail(data, 'Ana');
  assert.deepEqual(detail.rows.map(r => r.idProyecto), ['P1', 'P2']);
  assert.equal(detail.pending, true);
  assert.equal(detail.rows[0].total, 3);
  assert.equal(detail.rows[1].values[0], null);
  assert.equal(data.people.find(p => p.nombre === 'Ána').total, 3);
  assert.equal(JSON.stringify(data), before);
});

test('work plans allow external web links and reject executable or invalid URLs', () => {
  const docs = [
    { tipo: 'Roadmap', nombre: 'Entrega', url: 'https://example.com/plan?a=1' },
    { tipo: 'Plan de trabajo', url: 'example.com/plan' },
    { tipo: 'Referencia', nombre: 'Hoja de ruta', url: 'https://example.com/ruta' },
    { tipo: 'Documento', nombre: 'Contrato', url: 'https://example.com/contrato' },
    ...['javascript:alert(1)', 'data:text/html,test', 'file:///tmp/plan', 'https://', ''].map(url => ({ tipo: 'Roadmap', url })),
  ];
  assert.equal(workPlanDocuments(docs).length, 3);
  assert.equal(workPlanDocuments(docs)[1].url, 'https://example.com/plan');
  assert.deepEqual(workPlanDocuments([]), []);
});
