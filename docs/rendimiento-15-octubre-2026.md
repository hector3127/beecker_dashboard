# Primera etapa de rendimiento — 15/10/2026

## Cambios

- La precarga financiera consulta qué costos faltan antes de preparar bandas
  y tarifas. Si todos están guardados, omite esa preparación y el cálculo
  individual. Los resúmenes conservan su marca de datos incompletos.
- Operations utiliza los proyectos ya resueltos para preparar sus consumos.
  La población se consulta una vez para planificar y otra para resumir, en
  lugar de volver a buscar cada ID en la población completa.
- Se conserva la caché mensual compartida de Clockify y sus filtros de CR,
  fechas y deduplicación. Los meses anteriores al mes previo se reutilizan
  hasta siete días; el mes previo conserva 24 horas. El mes actual mantiene
  las reglas existentes: seis horas con registros o 30 minutos sin registros
  para consultas hasta hoy. Las descargas forzadas omiten la caché mensual.
- Ejecutiva con un corte guardado responde con ese corte mientras se
  prepara otro. La actualización automática usa POST con CSRF y consulta
  un estado ligero, sin descargar repetidamente toda la página.
- El navegador no lanza cálculos individuales de costos/Operations cuando
  está trabajando la actualización en segundo plano. Se conservan fechas,
  filtros y la confirmación «Mostrar datos actualizados»; los cortes
  parciales se identifican expresamente.
- Se registra el tiempo de actualización y la cantidad de costos reutilizados
  y pendientes para facilitar las siguientes mediciones.

## Uso y límites

Reiniciar Django para activar el código nuevo. No hace falta borrar la caché
ni ejecutar migraciones adicionales. `python manage.py warm_cache` conserva
su funcionamiento; los cálculos y meses presentes se reutilizan.

Si se corrigen horas antiguas de Clockify, usar la actualización forzada de
horas del proyecto o `python manage.py warm_cache --refresh`. Este último
borra toda la caché y vuelve a preparar las fuentes: reservarlo para cuando
sea necesario, porque será más lento.

La actualización en segundo plano usa un hilo por proceso de Django y admite
como máximo dos periodos pendientes en ese proceso. Las solicitudes del mismo
periodo se agrupan dentro del proceso. No es una cola persistente ni garantiza
exclusión entre varios procesos: al reiniciar el servidor se debe reintentar.
La caché guardada permanece disponible. Una futura instalación con varios
workers debería usar una cola compartida para coordinar las actualizaciones.

La primera consulta de un rango sin datos preparados todavía necesita
consultar las fuentes. Estas mejoras reducen trabajo repetido; no se ha
medido todavía una reducción porcentual con una descarga real completa.

## Validación

Suite completa: 1,263 pruebas Python y 31 pruebas frontend aprobadas.
Cobertura Python: 90.29%. Comprobación de Django sin incidencias.

Se comprueba la reutilización sin lecturas de tarifas, la cantidad constante
de consultas a la población, los tiempos de retención mensual, el recorte de
rangos, las reglas CR y la actualización forzada. Las pruebas de actualización
comprueban cola limitada, deduplicación, aislamiento del periodo, fallos,
autenticación y CSRF. Las pruebas de navegador simuladas verifican que no se
dupliquen cálculos ni se sustituyan automáticamente los datos visibles.
