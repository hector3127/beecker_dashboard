// @ts-check
// view: eva3/column_menu. Original data, ordering and interactions are preserved.
/**
 * @param {HTMLTableCellElement} cell
 */
export function columnColor(cell) {
  for (const [selector, key, label] of [
    [
      ".hm .cr,.bad,.over,.pd,.critical,.eva4-pill.suspended,.st.sus,.st.dep",
      "red",
      "Rojo",
    ],
    [".hm .cg,.ok,.finished,.eva4-pill.active", "green", "Verde"],
    [".cancelled", "red", "Rojo"],
    [".service-aer,.service-pill.raas,.st.dev", "blue", "Azul"],
    [
      ".service-tym,.service-pill:not(.raas),.st:not(.sus):not(.dep):not(.dev)",
      "purple",
      "Morado",
    ],
    [".hm .cy,.eva4-pill.warning", "yellow", "Amarillo"],
  ])
    if (cell.matches(selector) || cell.querySelector(selector))
      return { key, label };
  return { key: "none", label: "Sin color" };
}
