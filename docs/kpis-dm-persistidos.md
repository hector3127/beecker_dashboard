# KPIs DM con almacenamiento propio — 29/10/2026

El filtro principal permite seleccionar mes y año, con `mes=YYYY-MM`.
Consulta la última captura del periodo, dejando visible la fecha real de esa
captura. No sustituye meses sin datos. El filtro global de DMs y los años de
tendencia e históricos se conservan. Los enlaces anteriores con `corte` siguen
admitidos, aunque el formulario ahora envía solo el mes.

## Histórico aprobado importado después del inicio

El usuario autorizó cargar enero–septiembre 2026 desde la imagen
`codex-clipboard-140f2b84-a386-46e4-80d1-be774a3d64b2.png` y confirmó que
C de origen significa proyectos dentro del presupuesto. El comando
`import_kpi_dm_2026` guarda nueve periodos cerrados, 41 filas DM y el origen
`user_report_20261029`. Es transaccional, repetible y rechaza sobrescribir
periodos de otro origen. Octubre se conserva.

Cada TP y porcentaje original queda en los metadatos. Todos los porcentajes
mensuales tienen un único conteo entero compatible con el redondeo a unidades;
se valida antes de guardar. C pasa a conteo de sobrecosto como TP menos los
proyectos dentro del presupuesto. Por ello 63% de 8 se guarda como 5 en costo,
3 con sobrecosto (37.5%); no como un conteo fraccionario derivado de 37%.
Vacíos no generan filas ni ceros. Fechas de corte asignadas al último
lunes–jueves del mes; no se afirma conocer la fecha original de observación:
source_observed_at registra la recepción/importación, sin fuente Azure.

Discrepancias del origen: enero y febrero suman 20 proyectos en filas DM,
aunque la imagen muestra Total 19. Se conservan las filas y se recalculan
totales ponderados, sin forzar el total impreso. La columna «12» es el
acumulado según aclaración del usuario, no diciembre; se excluye del eje
mensual. Los trimestres se calculan desde meses con la regla vigente y no se
copian los totales ni promedios impresos que no coinciden con esas filas.

Respaldo previo: `tmp/backups/before-kpi-history-import-20261029.sqlite3`.
15 pruebas dirigidas aprobadas (incluidas tres nuevas de importación), Ruff
aprobado. No cambia diseño, fórmulas, EVA, conexión o automatización.

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
