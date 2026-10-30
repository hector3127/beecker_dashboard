import test from 'node:test';
import assert from 'node:assert/strict';
import { workPlanDocuments } from '../../frontend/static/scripts/pages/project_detail/sections/work_plan_model.js';

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
