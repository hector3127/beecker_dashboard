// @ts-check
// Reglas del editor de hitos: validación, nombre del tipo nuevo y fechas.

export const NEW_TYPE = "__nuevo__";
export const ICONS = ["🎥", "🧪", "🚀", "✅", "🎓", "🔍", "🏁", "📦", "📌", "📝", "🔔", "⭐"];

/** @param {string} text dd/mm/yyyy @returns {string} yyyy-mm-dd o vacío */
export function dmyToIso(text) {
  const parts = String(text || "").split("/");
  if (parts.length !== 3) return "";
  return `${parts[2]}-${parts[1].padStart(2, "0")}-${parts[0].padStart(2, "0")}`;
}

/**
 * Convierte las filas del formulario en altas y ediciones, o devuelve el
 * primer error con el mismo texto de la pantalla anterior.
 * @param {{tipo: string, nuevoNombre: string, icono: string, fecha: string, obs: string, editTipo?: string, editIndice?: number}[]} rows
 */
export function collectRows(rows) {
  /** @type {{tipo: string, fechaISO: string, observacion: string}[]} */
  const nuevos = [];
  /** @type {{tipo: string, indice: number, fechaISO: string, observacion: string}[]} */
  const ediciones = [];
  for (const row of rows) {
    let tipo = row.tipo;
    if (tipo === NEW_TYPE) {
      const name = row.nuevoNombre.trim();
      if (!name) return { error: "Falta el nombre de un tipo de hito nuevo." };
      tipo = `${row.icono || "📌"} ${name}`;
    }
    if (!row.fecha) return { error: "Falta la fecha en uno de los hitos." };
    if (row.editTipo && row.editIndice !== undefined) {
      ediciones.push({ tipo: row.editTipo, indice: Number(row.editIndice), fechaISO: row.fecha, observacion: row.obs });
    } else {
      nuevos.push({ tipo, fechaISO: row.fecha, observacion: row.obs });
    }
  }
  if (!nuevos.length && !ediciones.length) return { error: "Agrega al menos un hito." };
  return { nuevos, ediciones };
}
