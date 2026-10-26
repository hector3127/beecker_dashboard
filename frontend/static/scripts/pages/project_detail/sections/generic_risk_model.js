// The manual-risk form only trims description; the service validates all fields.
export function riskPayload(values) {
  return {
    descripcion: values.descripcion.trim(),
    impacto: values.impacto,
    probabilidad: values.probabilidad,
    responsable: values.responsable,
  };
}
