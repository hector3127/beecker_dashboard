// Form fields and defaults from the original planning editor.
export function planningEditorModel(type, uid, initialType, state) {
  const vacation = type === "vacacion";
  const source =
    (vacation ? state.vacaciones : state.compromisos).find(
      (row) => row.uid === uid,
    ) || {};
  const row = { ...source };
  if (!uid && initialType) row.tipo = initialType;
  const input = (label, name, inputType = "text") => ({
    label,
    name,
    inputType,
    value: row[name] || "",
    required: ["recurso", "actividad", "inicio", "fin", "fecha"].includes(name),
  });
  const select = (name, label, options) => ({
    name,
    label,
    options,
    value: row[name],
  });
  return {
    title: `${uid ? "Editar" : "Registrar"} ${vacation ? "vacaciones" : "actividad / hito"}`,
    fields: vacation
      ? [
          input("Recurso", "recurso"),
          input("Inicio", "inicio", "date"),
          input("Fin", "fin", "date"),
          select("estado", "Estado", ["Pendiente", "Aprobada", "Cancelada"]),
          input("Comentarios", "comentarios"),
          input("Registrado por", "registradoPor"),
        ]
      : [
          input("Actividad / hito", "actividad"),
          input("Responsable", "responsable"),
          input("Fecha", "fecha", "date"),
          select("tipo", "Tipo", ["Actividad", "Hito"]),
          select("estado", "Estado", [
            "Pendiente",
            "En progreso",
            "Por validar",
            "Completado",
            "Detenido",
            "Cancelado",
          ]),
        ],
  };
}
