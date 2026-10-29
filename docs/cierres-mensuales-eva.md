# Cierres mensuales fijos de EVA — 29/10/2026

**Estado vigente: desactivado hasta Genesis por instrucción posterior del
usuario.** `EVA_MONTHLY_CLOSES_ENABLED=0` por defecto. Las dos tareas Windows
están deshabilitadas. Los comandos salen sin capturar/sellar y EVA/KPIs usan
consultas actualizables, incluso si existen copias en la base. No se borraron
tablas ni respaldos. La descripción siguiente documenta la función preparada,
no una activación vigente.

Antes de activarla en Genesis: validar el primer mes de `EvaMonthlyClosePolicy`
según la fecha acordada, aplicar migraciones y configurar el programador de
ese entorno; luego habilitar explícitamente `EVA_MONTHLY_CLOSES_ENABLED=1`.
Los datos oficiales anteriores se conciliarán cuando el usuario los entregue.

El último día de lunes a jueves de cada mes es el corte. El día permanece
abierto hasta terminar en la zona America/Mexico_City. Después se conserva
una fotografía completa de las filas de EVA: identidad, DM, servicio, fechas
de etapas, estado, presupuesto, horas, avance, tareas, riesgos y notas de
atribución. No se vuelven a leer fuentes para recalcular un cierre guardado.
Los filtros de DM/servicio y los totales operan sobre esa misma fotografía.

La migración aditiva 0012 crea `EvaMonthlyClosePolicy` y `EvaMonthlyClose`.
El encabezado conserva corte, momento de cierre, observación y extracción
de origen protegida contra borrado. El JSON es evidencia del reporte, no una
segunda contabilidad de horas. La clave única por mes/corte y get_or_create
impiden duplicar/sobrescribir automáticamente; save rechaza modificar un
cierre ya creado. No se elimina ninguna extracción ni se cambia SQLite.
Respaldo previo: tmp/backups/before-eva-monthly-closes-20261029.sqlite3.

La política local empieza en octubre de 2026. No se rellenan meses anteriores
con el Summary actual. Se incorporarán cuando el usuario proporcione y valide
su información oficial. Un cierre vencido sin fotografía muestra pendiente,
no cero proyectos. Los KPIs mensuales/trimestrales y la tendencia usan estos
cierres; el mes abierto sigue siendo provisional. Noviembre/diciembre futuros
continúan sin datos. Este cambio conserva las fórmulas y el rango de proyectos;
no corrige retrospectivamente T ni establece aún una fecha base original frente
a reprogramaciones. Esa conciliación espera los datos del usuario.

## Operación

`manage.py close_eva_month --capture` solo consulta fuentes el día de cierre.
Primero captura Summary/Clockify y luego actualiza revisiones Azure. Cualquier
otro día sale sin llamadas externas. `manage.py close_eva_month` sella desde
la última extracción publicada/enriquecida observada realmente ese día, con
timestamp válido; nunca usa una extracción posterior ni un reproceso de una
observación antigua. Guarda faltantes/observaciones parciales tal como estaban.
Las lecturas GET no crean cierres. La sincronización Summary también intenta
sellar pendientes antes de consultar fuentes nuevas, bajo el mismo candado.
Los cierres vencidos sin observación válida hacen fallar el comando de sellado
con un mensaje explícito; los reintentos no cambian fuentes ni fabrican datos.
La copia fija se usa para la fecha exacta de cierre mensual; las consultas de
otros días no se presentan como cierres mensuales validados.

Instaladas en este Windows, sin modificar otras tareas:

- Beecker-EVA-CapturaCierre: 23:40, con guarda de fecha de cierre.
- Beecker-EVA-CerrarMes: desde 00:20, cada hora; solo lecturas locales y cierre.

Ambas usan PowerShell oculto y el script local scripts/run_eva_close.ps1.
La excepción de política de ejecución es solo del proceso; no cambia la política
de Windows. Scripts: scripts/schedule_eva_closes.ps1 -Action Status/Install/Remove;
admite -DryRun. Logs: logs/eva-captura-cierre.log y eva-cierre-mensual.log.
El cierre local programado se ejecutó correctamente; la captura nocturna real
todavía no ha ocurrido. El equipo debe estar encendido y la sesión disponible.
Si se pierde el día y no hay evidencia, queda pendiente sin fabricar un cierre.

En Linux/Genesis se pueden programar scripts/run_job.sh eva-captura y eva-cierre
en esa zona horaria. No se instaló allí ningún proceso ni se migró PostgreSQL.

## Validación

Pruebas verifican cierre solo después de terminar el día, selección de la última
observación válida, idempotencia, protección de origen, rechazo de timestamps
inválidos/incompletos, meses previos pendientes, filtros sobre la copia y
persistencia frente a cambios posteriores de DM/fechas/horas. El comando de
captura no consulta fuentes en otros días. Chrome comprueba fijo/pendiente,
conservación de fecha y DM, actualización de fechas abiertas y estado mensual
sin asterisco provisional después del cierre. Ver plan para recuentos finales.
Regresión portal/datastore/Azure: 1,863 aprobadas; 12 dirigidas finales con
solapamiento. Conjunto Chrome EVA/Summary/KPIs: 32 aprobadas con CSP/rutas
reales. Node: 478. Check, mypy y makemigrations --check aprobados.
