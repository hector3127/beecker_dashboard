export function isSummaryQuestion(question) {
  const normalized = question
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .trim();
  return (
    normalized.includes("resume el proyecto para comite") ||
    normalized.includes("resumen ejecutivo")
  );
}
export const summaryPayload = (state, instructions) => ({
  ids: (state.seleccion || []).slice(0, 5),
  instrucciones: instructions,
});
