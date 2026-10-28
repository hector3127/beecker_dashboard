// @ts-check
/** Solo vínculos HTTP(S) del plan; no interpreta esquemas ejecutables.
 * @param {any[]} documents */
export function workPlanDocuments(documents) {
  return (Array.isArray(documents) ? documents : []).flatMap(doc => {
    if (!doc || typeof doc !== 'object') return [];
    if (!/roadmap|plan\s+de\s+trabajo|hoja\s+de\s+ruta/i.test(String(doc.tipo || '') + ' ' + String(doc.nombre || ''))) return [];
    const raw = String(doc.url || '').trim();
    if (!raw || (/^[a-z][a-z\d+.-]*:/i.test(raw) && !/^https?:/i.test(raw))) return [];
    try {
      const url = new URL(/^https?:\/\//i.test(raw) ? raw : 'https://' + raw);
      return ['https:', 'http:'].includes(url.protocol) ? [{ name: doc.nombre || 'Plan de trabajo', url: url.href }] : [];
    } catch { return []; }
  });
}
