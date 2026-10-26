# Fase 11: retiro de la presentación anterior de Costos

26/10/2026. Se retira `portal/costos_detalle.html` y el parámetro
`?anterior=1`. La ruta `/ejecutiva/costos/detalle/?vista=proyectos` siempre
sirve `pages/costs.html`; `views.costos_detalle` conserva el cálculo y los
permisos y ahora usa esa plantilla por defecto. `vista=` sigue eligiendo entre
proyectos y márgenes. No se tocan cifras, fuentes ni diseño.

Las tres pruebas Node que ejecutaban el script en línea de la plantilla
anterior se sustituyen por dos pruebas de navegador sobre el módulo vigente
(`tests/e2e/test_costos.py`): desglose parcial que actualiza fila y detalle, y
desglose por sprint preparado que se abre sin pedir nada a la API. La cobertura
de enlaces con regreso y de proyectos no disponibles ya existía en ese archivo.

Verificación: 1735 pruebas de portal, core, costos y ejecutiva aprobadas;
498 Node aprobadas; ruff aprobado.
