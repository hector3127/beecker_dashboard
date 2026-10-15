# Regreso al origen de los detalles

Las cuentas, costos y proyectos aceptan un destino local explícito en `volver`. El destino se valida contra las rutas de páginas del portal; no admite URLs externas ni endpoints RPC. No depende de la pestaña del navegador ni de `history.back()`.

- Todas las cuentas → Ver costos → Todas las cuentas.
- Todas las cuentas → Cuenta → Todas las cuentas.
- Todas las cuentas → Cuenta → Costos → Cuenta → Todas las cuentas.
- Business Overview → Cuenta → Business Overview.
- Operativa → Cuenta → Operativa.

El enlace de salida conserva el periodo y la URL completa de su origen, incluido su propio regreso. La lista guarda búsqueda y clasificación en la URL y los restaura al regresar. El enlace de regreso nunca se reescribe como un nuevo avance.

No cambian las fuentes, cálculos ni claves de caché de negocio. La validación cubre destinos, filtros, periodos, navegación anidada y regresos con rutas directas.
