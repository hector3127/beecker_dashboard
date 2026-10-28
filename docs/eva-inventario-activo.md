# EVA 1 con la lógica del inventario aprobado

28/10/2026. El usuario pide que los datos/filtros desarrollados en el
inventario sean la fuente de EVA, conservando la apariencia de las imágenes:
dos tarjetas por DM, tabla con logos, etiquetas de servicio/etapa y alertas.

`views.eva1` usa `load_inventory_eva`: adaptador de las mismas filas que
`inventory_rows(cut=...)`. No usa `load_native_cut` para esta pantalla.
Start/Finish provienen de iteraciones, inicio ≤ corte ≤ fin, etapa calculada
al corte; horas facturables guardadas y métricas históricas Azure locales.
No se filtra nuevamente por servicio/cierre ni se alteran sus identidades.
Las tablas DM usan `dm_totals` sobre los mismos bloques seleccionados por
DM/servicio; incluyen Pendiente/otros servicios para conservar la suma.

Se conserva el shell/CSS EVA, colores, cuenta/logos, etiquetas, menús de
columna, ordenamiento, CSV protegido, filtros GET y navegación de regreso.
Se retira de esta página el listado antiguo de cerrados para no mezclar otra
fuente/regla con el rango solicitado. Su endpoint permanece para consumidores
existentes. El inventario de revisión sigue disponible por enlace.

El botón Actualizar fuentes refresca histórico incremental y luego el
inventario Summary/iteraciones/Clockify, usando los candados existentes.
Su estado consulta las corridas de esta fuente. Sin nuevas extracciones
necesarias para la integración ni cambios en los KPI mensuales.

Verificación real 30/09/2026: once bloques, tres DM, mismas filas que el
inventario. Página local Chrome sin errores JS, logos y estilos conservados;
captura `tmp/eva-native/eva-inventory-real.png`. Siete Chrome con rutas reales
y CSP aprueban escritorio/tablet/móvil, filtros, CSV, refresco exitoso/fallido,
consulta sin JS y estado API 503. 478 Node aprobados. Pruebas dirigidas de
adaptador, fuente local y reglas del corte; no se regeneran referencias para
imponer otro diseño. Regresión final completa de tests/portal: 1691 aprobadas
en 89.13 s (advertencias conocidas de estáticos y librerías). Ruff, mypy de
pages.py y manage.py check aprobados. Módulo EVA versionado para evitar
controladores de caché anteriores. Sin push.
