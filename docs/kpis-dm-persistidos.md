# KPIs DM con almacenamiento propio — 29/10/2026

Por instrucción del usuario, la página KPI DM deja de reconstruir sus cifras
al consultar EVA. Solo se inicia el mes actual; los anteriores quedan pendientes
de conciliación. No se modifica el comportamiento de EVA ni su extracción.

## Datos y lectura

Migración aditiva `0013_dm_kpi_reports`, aplicada sobre SQLite con respaldo en
`tmp/backups/before-dm-kpi-reports-20261029.sqlite3`:

- `DmKpiPeriod`: mes único, último lunes–jueves, estado y última captura.
- `DmKpiObservation`: fecha de corte única, periodo y trazabilidad de fuente.
- `DmKpiMetric`: conteos por DM/captura, con unicidad y restricciones contables.

Se guardan TP, en tiempo, fuera de tiempo, sobrecosto y datos desconocidos.
T = desviación <= 0 / TP; C = avance > 100 / TP. Los pendientes permanecen en
el denominador. Los porcentajes se derivan de conteos para recalcular totales
del selector global sin promediar porcentajes entre DMs.

Tarjetas, tabla, tendencia e históricos leen exclusivamente estas tablas.
Consultar no escribe ni llama a Azure/Clockify o al inventario EVA. El corte
diario exige una captura exacta; no sustituye una fecha ausente por otra.
El corte inicial usa la última fecha guardada. Históricos conservan 12 meses,
trimestres y años independientes; futuros sin datos, anteriores sin captura
pendientes. Se retira el lector vivo `kpi_inventory_history.py`.

## Actualización

Después de actualizar las fuentes locales, ejecutar:

```powershell
.\.venv\Scripts\python.exe manage.py sync_kpi_dm
```

Si las fuentes todavía necesitan refrescarse, primero ejecutar el flujo existente:

```powershell
.\.venv\Scripts\python.exe manage.py sync_datastore --pasos eva
```

La captura KPI lee el inventario local publicado, con fuente fijada y sin usar
cierres EVA. No realiza peticiones externas. Solo admite el mes actual y una
observación real; una captura anterior al día actual no se sobrescribe.
El día actual puede refrescarse atómicamente. No rellena meses anteriores.

Queda preparado `sync_kpi_dm --automatic`, protegido por
`KPI_DM_AUTO_UPDATE_ENABLED=0` por defecto, hasta Genesis. No se instalaron ni
activaron tareas. Cuando se habilite, debe ejecutarse después de sincronizar
las fuentes y exige una observación de ese día. Después del último lunes–jueves
del mes se conserva el periodo: cerrado si existe captura de ese último día,
pendiente si falta. El siguiente mes crea su propio periodo. No inventa el
cierre faltante con datos posteriores.

## Inicio y evidencia

Se guardó únicamente octubre 2026, corte 29/10/2026, fuente local 19 observada
ese día: Alberto TP 7, en tiempo 7, sobrecosto 3; Brandon TP 2, en tiempo 2,
sobrecosto 0. Total TP 9, T 100%, C 33.3%. No se cargaron meses previos.
La automatización permanece desactivada y los cierres EVA siguen desactivados.

Validación: 1,875 pruebas servidor en portal/datastore/azure_devops aprobadas;
478 Node aprobadas. Validación final adicional: 12 pruebas servidor dirigidas
y 25 Chrome/CSP aprobadas (37 casos, con solapamiento con la corrida amplia).
Ruff, Django check y makemigrations --check aprobados. Capturas reproducibles en
`tmp/design/kpi-saved/saved-{1450,900,390}.png`; revisión móvil conserva
tarjetas, panel global, tablas con desplazamiento y gráfica con puntos del
único mes guardado. No se cambian fórmulas, permisos, CSP o conexión de base.
