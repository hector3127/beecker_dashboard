// Original generic executive timeline rules, isolated without changing dates,
// suspension precedence, marker assignment or completion detection.
import {
  milestoneCategory as categoriaHito,
  cleanMilestone as nombreLimpioHito,
} from "./ixs_executive_model.js";

export function genericTimeline(data, ahoraMs = Date.now()) {
  const p = data.proyecto;
  const COLOR_TIPO = {
    plan: "#C9C9CD",
    real: "#4A2A94",
    suspendido: "#F2A900",
    completado: "#2E7D32",
  };
  const msDia = 24 * 60 * 60 * 1000;
  const historialCompleto = data.historialCompleto || [];
  const suspensiones = data.suspensiones || [];
  const hitosResumenCorregido = [];
  let proyectoCompletadoDetectado = false;
  const marcadoresAdicionales = (data.hitosAdicionales || [])
    .map((h) => {
      const partes = String(h.fecha || "").split("/");
      if (partes.length !== 3) return null;
      const d = new Date(
        Number(partes[2]),
        Number(partes[1]) - 1,
        Number(partes[0]),
      );
      if (isNaN(d.getTime())) return null;
      const cat = categoriaHito(h.tipo);
      return {
        tipo: h.tipo,
        tiempo: d.getTime(),
        icono: cat.icono,
        etiquetaCategoria: cat.etiqueta,
        indice: h.indice,
        observacion: h.observacion,
        fechaStr: h.fecha,
      };
    })
    .filter(Boolean);

  /**
   * Asigna cada marcador a la fila de EJECUCIÓN cuya fecha lo contenga
   * (entre inicio y fin, o hasta hoy si sigue en curso), para pintarlo
   * pegado a esa barra específica en vez de flotar sin relación visual.
   * Si no cae en ninguna fila, se asigna a la más cercana por fecha.
   */
  function marcadoresAdicionalesAsignar(filas, marcadores) {
    marcadores.forEach((m) => {
      let filaElegida = null;
      filas.forEach((f) => {
        if (f.tipo !== "real") return;
        const i0 = new Date(f.inicio).getTime();
        const i1 = f.enCurso ? ahoraMs : new Date(f.fin).getTime();
        if (m.tiempo >= i0 && m.tiempo <= i1) filaElegida = f;
      });
      if (!filaElegida) {
        // respaldo: la fila real mas cercana en el tiempo
        let mejorDist = Infinity;
        filas.forEach((f) => {
          if (f.tipo !== "real") return;
          const i0 = new Date(f.inicio).getTime();
          const dist = Math.abs(m.tiempo - i0);
          if (dist < mejorDist) {
            mejorDist = dist;
            filaElegida = f;
          }
        });
      }
      if (filaElegida) {
        if (!filaElegida.marcadores) filaElegida.marcadores = [];
        filaElegida.marcadores.push(m);
      }
    });
  }

  const filasPlan = data.hitos
    .filter((h) => h.fechaInicioPlan && h.fechaFinPlan)
    .map((h) => ({
      etiqueta: h.nombre + " EST",
      inicio: h.fechaInicioPlan,
      fin: h.fechaFinPlan,
      tipo: "plan",
    }));

  // --- Filas de EJECUCION REAL: cada registro tal cual viene, en orden
  // cronologico (Discovery OP, Discovery, Development, Suspendido, etc.) ---
  // Fusionar TODAS las ocurrencias reales de una misma fase (puede haber
  // más de un "Discovery" si hubo suspensiones y reanudaciones) en una
  // sola barra: fecha de inicio = la más temprana registrada (ej. la de
  // "Discovery OP"), fecha fin = la más tardía registrada para esa fase.
  const fasesUnicas = {};
  historialCompleto
    .filter((h) => h.fechaInicio)
    .forEach((h) => {
      const clave = h.fase.toLowerCase();
      if (!fasesUnicas[clave]) {
        fasesUnicas[clave] = {
          etiqueta: h.fase,
          inicio: h.fechaInicio,
          fin: h.fechaFin || h.fechaInicio,
          tipo: "real",
          enCurso: !!h.enCurso,
        };
      } else {
        const f = fasesUnicas[clave];
        if (new Date(h.fechaInicio) < new Date(f.inicio))
          f.inicio = h.fechaInicio;
        const finCandidato = h.fechaFin || h.fechaInicio;
        if (
          !f.enCurso &&
          (h.enCurso || new Date(finCandidato) > new Date(f.fin))
        ) {
          f.fin = finCandidato;
        }
        if (h.enCurso) f.enCurso = true;
      }
    });

  const filasReal = Object.values(fasesUnicas)
    .concat(
      suspensiones
        .filter((s) => s.fechaInicio)
        .map((s) => ({
          etiqueta: "Suspendido",
          inicio: s.fechaInicio,
          fin: s.fechaFin || s.fechaInicio,
          tipo: "suspendido",
        })),
    )
    .sort((a, b) => new Date(a.inicio) - new Date(b.inicio));

  // Asignar cada marcador adicional a la fila de EJECUCIÓN cuya fecha
  // lo contenga (para pintarlo pegado a esa barra, no flotando aparte).
  marcadoresAdicionalesAsignar(filasReal, marcadoresAdicionales);

  // Marcador de cierre (Completed): se infiere del estado general del
  // proyecto + la fecha real mas tardia, sin inventar una fecha nueva.
  if (p.estadoGeneral === "CERRADO" && filasReal.length) {
    const finesMs = filasReal
      .map((f) => new Date(f.fin).getTime())
      .filter((t) => !isNaN(t));
    if (finesMs.length) {
      const maxFin = new Date(Math.max.apply(null, finesMs)).toISOString();
      filasReal.push({
        etiqueta: "Completed (Cierre real)",
        inicio: maxFin,
        fin: maxFin,
        tipo: "completado",
      });
    }
  }

  // --- Escala de tiempo compartida por ambas secciones ---
  const todasFechas = [];
  filasPlan.concat(filasReal).forEach((f) => {
    [f.inicio, f.fin].forEach((v) => {
      const d = new Date(v);
      if (!isNaN(d.getTime())) todasFechas.push(d.getTime());
    });
  });

  /**
   * Estado real de una etapa de EJECUCIÓN:
   *  - 'Suspendida': el inicio de una suspensión cae DENTRO del rango
   *    de esta etapa Y esa suspensión termina DESPUÉS del fin de la
   *    etapa (la rebasa). Si la suspensión ya terminó antes/dentro del
   *    rango de la etapa, ya no cuenta como interrupción activa.
   *  - 'Pendiente': hoy todavía no llega a la fecha de inicio.
   *  - 'En curso': hoy cae dentro del rango [inicio, fin], o la etapa
   *    no tiene fin registrado (enCurso segun el backend).
   *  - 'Completado': hoy ya pasó el fin registrado.
   */
  function estadoEtapaReal(f) {
    const inicioMs = new Date(f.inicio).getTime();
    const finMs = f.enCurso ? null : new Date(f.fin).getTime();
    const finEfectivo = finMs != null && !isNaN(finMs) ? finMs : ahoraMs;

    // Caso A: la suspension EMPEZÓ mientras la etapa estaba en curso ->
    // la etapa sí arrancó y se interrumpió a medias.
    const suspendidaDurante = suspensiones.some((s) => {
      const sIni = new Date(s.fechaInicio).getTime();
      const sFin = s.fechaFin ? new Date(s.fechaFin).getTime() : sIni;
      if (isNaN(sIni)) return false;
      return sIni >= inicioMs && sIni <= finEfectivo && sFin > finEfectivo;
    });
    if (suspendidaDurante)
      return { texto: "Suspendida", color: COLOR_TIPO.suspendido };

    // Caso B: una suspension YA ESTABA ACTIVA antes de que la etapa
    // empezara y no se resolvió antes de su fin -> la etapa nunca
    // llegó a arrancar de verdad, aunque tenga fechas registradas.
    const cubiertaPorSuspension = suspensiones.some((s) => {
      const sIni = new Date(s.fechaInicio).getTime();
      const sFin = s.fechaFin ? new Date(s.fechaFin).getTime() : sIni;
      if (isNaN(sIni)) return false;
      return sIni <= inicioMs && sFin >= finEfectivo;
    });
    if (cubiertaPorSuspension) return { texto: "Pendiente", color: "#8D8D91" };

    if (f.enCurso) return { texto: "En curso", color: COLOR_TIPO.real };
    if (isNaN(finMs))
      return { texto: "Completado", color: COLOR_TIPO.completado };
    if (ahoraMs < inicioMs) return { texto: "Pendiente", color: "#8D8D91" };
    // Comparar por DÍA CALENDARIO, no por hora exacta: si la fecha fin
    // es hoy mismo, la etapa sigue "En curso" hasta que termine el día,
    // no se marca Completado apenas entra la fecha.
    const diaHoy = new Date(ahoraMs);
    diaHoy.setHours(0, 0, 0, 0);
    const diaFin = new Date(finMs);
    diaFin.setHours(0, 0, 0, 0);
    if (diaHoy.getTime() <= diaFin.getTime())
      return { texto: "En curso", color: COLOR_TIPO.real };
    return { texto: "Completado", color: COLOR_TIPO.completado };
  }

  // --- Resumen corregido para la tarjeta "HITOS DEL PROYECTO": usa la
  // MISMA lógica de estadoEtapaReal (fecha de hoy + suspensión que
  // rebasa) en vez del estado más simple que trae data.hitos[].estado ---
  const mapaUltimaOcurrencia = {};
  filasReal
    .filter((f) => f.tipo === "real")
    .forEach((f) => {
      mapaUltimaOcurrencia[f.etiqueta.toLowerCase()] = f;
    });

  data.hitos.forEach((h) => {
    const match = mapaUltimaOcurrencia[h.nombre.toLowerCase()];
    let estadoTexto = "Pendiente";
    if (match) estadoTexto = estadoEtapaReal(match).texto;

    // Si hay ejecución real registrada, mostrar SUS fechas (las mismas
    // que pinta el Gantt, ya fusionadas por si hubo reanudaciones), no
    // las fechas planeadas — evita la discrepancia entre esta tarjeta
    // y el Gantt cuando la ejecución real se corrió de las fechas plan.
    const fechaInicioMostrar = match ? match.inicio : h.fechaInicioPlan;
    const fechaFinMostrar = match
      ? match.enCurso
        ? new Date(ahoraMs).toISOString()
        : match.fin
      : h.fechaFinPlan;

    hitosResumenCorregido.push({
      nombre: h.nombre,
      fechaInicioPlan: fechaInicioMostrar,
      fechaFinPlan: fechaFinMostrar,
      estado: estadoTexto,
      esAdicional: false,
    });
  });

  // Hitos adicionales (Demo, QA, etc.) también entran al resumen:
  // Completado si su fecha ya pasó, Pendiente si es futura O si cae
  // dentro de un período de suspensión (aunque la fecha ya haya pasado).
  function fechaDentroDeSuspension(tiempoMs) {
    return suspensiones.some((s) => {
      const sIni = new Date(s.fechaInicio).getTime();
      const sFin = s.fechaFin ? new Date(s.fechaFin).getTime() : sIni;
      return !isNaN(sIni) && tiempoMs >= sIni && tiempoMs <= sFin;
    });
  }

  marcadoresAdicionales.forEach((m) => {
    const dentroDeSuspension = fechaDentroDeSuspension(m.tiempo);
    hitosResumenCorregido.push({
      nombre: m.icono + " " + nombreLimpioHito(m.tipo),
      fechaInicioPlan: null,
      fechaFinPlan: new Date(m.tiempo).toISOString(),
      estado: dentroDeSuspension
        ? "Pendiente"
        : m.tiempo <= ahoraMs
          ? "Completado"
          : "Pendiente",
      esAdicional: true,
      tipoOriginal: m.tipo,
      indice: m.indice,
      observacion: m.observacion,
    });
  });

  // Proyecto completado: la ÚLTIMA fase principal (Deployment, según
  // el orden cronológico de data.hitos) quedó Completada, y el
  // proyecto no está marcado como Suspendido/Cerrado en Proyectos.
  const fasesPrincipales = hitosResumenCorregido.filter((h) => !h.esAdicional);
  const ultimaFasePrincipal = fasesPrincipales.length
    ? fasesPrincipales[fasesPrincipales.length - 1]
    : null;
  proyectoCompletadoDetectado =
    !!ultimaFasePrincipal &&
    ultimaFasePrincipal.estado === "Completado" &&
    p.estadoGeneral !== "CERRADO" &&
    p.estadoGeneral !== "CANCELADO";

  marcadoresAdicionales.forEach((m) => todasFechas.push(m.tiempo));

  todasFechas.push(ahoraMs);
  const minT = Math.min.apply(null, todasFechas);
  const maxT = Math.max.apply(null, todasFechas);
  const rango = Math.max(maxT - minT, msDia);
  const PAD_IZQ = 230; // ancho fijo de la columna de etiquetas

  // Encabezado de meses agrupado por año
  const meses = [];
  let cursor = new Date(minT);
  cursor.setDate(1);
  const finEje = new Date(maxT);
  while (cursor <= finEje) {
    meses.push(new Date(cursor));
    cursor = new Date(cursor.getFullYear(), cursor.getMonth() + 1, 1);
  }

  return {
    filasPlan,
    filasReal,
    marcadoresAdicionales,
    estadoEtapaReal,
    minT,
    maxT,
    rango,
    PAD_IZQ,
    meses,
    hitosResumenCorregido,
    proyectoCompletadoDetectado,
  };
}
