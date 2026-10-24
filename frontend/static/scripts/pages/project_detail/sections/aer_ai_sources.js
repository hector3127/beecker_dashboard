// Saved data and Drive only. Generation actions remain for the next block.
const message = (e) => e?.message || String(e);
export function createAerAiSources(api) {
  const bind = (env) => {
    const s = env.state,
      id = env.id;
    const current = () => env.current() && s.id === id;
    const paint = () => {
      if (env.active()) env.paint();
    };
    const source = (name, context) => api.aerAiSource(id, name, context);
    const methods = {
      async analysis() {
        if (s.cargandoAnalisis || s.analisis || s.analisisConsultado) return;
        s.cargandoAnalisis = true;
        try {
          const r = await source("analisis", env.context());
          if (!current()) return;
          s.cargandoAnalisis = false;
          s.analisisConsultado = true;
          if (r?.ok && r.resultado?.analisis && !s.analisis && !s.cargando)
            s.analisis = Object.assign({}, r.resultado, { restaurado: true });
          paint();
        } catch (e) {
          if (!current()) return;
          s.cargandoAnalisis = false;
          s.analisisConsultado = true;
          console.warn(
            "No se pudo recuperar el último análisis IA:",
            message(e),
          );
          paint();
        }
      },
      async summary() {
        if (s.cargandoResumen || s.resumenConsultado) return;
        s.cargandoResumen = true;
        try {
          const r = await source("resumen");
          if (!current()) return;
          s.cargandoResumen = false;
          s.resumenConsultado = true;
          if (r?.ok) {
            s.resumenEjecutivo = r.resumen || null;
            paint();
          } else
            env.toast(
              r?.error || "No se pudo leer el resumen guardado",
              "error",
            );
        } catch (e) {
          if (current()) {
            s.cargandoResumen = false;
            env.toast(message(e), "error");
          }
        }
      },
      async minutes() {
        if (s.cargandoMinutas || s.minutas !== null) return;
        s.cargandoMinutas = true;
        try {
          const r = await source("minutas");
          if (!current()) return;
          s.cargandoMinutas = false;
          if (r?.ok) {
            s.minutas = r.filas || [];
            paint();
          }
        } catch (e) {
          if (current()) {
            s.cargandoMinutas = false;
            console.warn("AER IA Minutas: " + message(e));
          }
        }
      },
      async config(open = false) {
        if (s.config !== null) {
          if (open) env.openConfig();
          return;
        }
        if (s.cargandoConfig) {
          if (open) env.toast("Cargando configuración de minutas…");
          return;
        }
        s.cargandoConfig = true;
        try {
          const r = await source("config");
          if (!current()) return;
          s.cargandoConfig = false;
          if (r?.ok) {
            s.config = r.config || {};
            paint();
            if (open) env.openConfig();
            if (
              env.active() &&
              s.config.folderUrl &&
              s.config.nombreFrecuente &&
              !s.archivos &&
              !s.buscando &&
              !s.archivosOcultos
            )
              methods.files();
          } else
            env.toast(
              r?.error || "No se pudo cargar la configuración.",
              "error",
            );
        } catch (e) {
          if (current()) {
            s.cargandoConfig = false;
            env.toast(message(e), "error");
          }
        }
      },
      async files() {
        if (s.buscando) return;
        if (!s.config?.folderUrl || !s.config?.nombreFrecuente) {
          env.toast(
            "Configura primero la carpeta y el nombre frecuente.",
            "error",
          );
          env.openConfig();
          return;
        }
        s.mostrarArchivos = true;
        s.archivosOcultos = false;
        s.errorBusqueda = "";
        s.buscando = true;
        paint();
        try {
          const r = await source("archivos");
          if (!current()) return;
          s.buscando = false;
          if (!r?.ok) {
            s.errorBusqueda = r?.error || "Error al buscar";
            paint();
            return;
          }
          s.archivos = r;
          s.seleccion = [];
          paint();
          env.toast(
            "Búsqueda terminada: " +
              r.totalEncontradas +
              " archivo(s) encontrados",
          );
        } catch (e) {
          if (current()) {
            s.buscando = false;
            s.errorBusqueda = message(e);
            paint();
          }
        }
      },
    };
    return methods;
  };
  return { bind };
}
