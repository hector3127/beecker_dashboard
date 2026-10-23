// @ts-check
// Textos de importes, horas y margenes de una fila de costos.
import { formatMoney } from '#app/lib/format.js';

/** Numero con hasta dos decimales; vacio es «Pendiente». @param {number | null | undefined} v */
export const fmt = (v) => (v === null || v === undefined ? 'Pendiente' : Number(v).toLocaleString('es-MX', { maximumFractionDigits: 2 }));
/** Tarifa por hora con dos decimales. @param {number | null | undefined} v */
export const moneyRate = (v) =>
  v === null || v === undefined ? 'Pendiente' : `$${Number(v).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
export const money = formatMoney;

/** Texto del margen de un proyecto: porcentaje, perdida en USD o la razon de que falte. @param {any} p */
export function marginText(p) {
  if (p.margin !== null && p.margin !== undefined) return `${fmt(p.margin)}%${p.margin_provisional ? '*' : ''}`;
  if (p.revenue === null || p.revenue === undefined) return 'Sin datos';
  if (p.revenue <= 0 && p.gross_profit !== null && p.gross_profit !== undefined) return money(p.gross_profit) + (p.margin_provisional ? '*' : '');
  return p.revenue <= 0 ? 'No aplica' : 'Pendiente';
}

/** Color del margen: rojo si es perdida o menor a 30%, gris sin dato, verde en lo demas. @param {any} p */
export function marginColor(p) {
  if (p.gross_profit < 0) return '#d83259';
  if (p.margin === null || p.margin === undefined) return '#8a80a6';
  return p.margin < 30 ? '#d83259' : '#168b67';
}
