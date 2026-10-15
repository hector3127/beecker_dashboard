# Actualización del 15 de octubre de 2026

Se integró el código nuevo de `beecker_dashboard-main (5).rar` sobre la
versión unificada del 14 de octubre.

## Funciones incorporadas

- Selector de fechas en Ejecutiva: año, trimestre, mes y rango personalizado.
  El periodo se conserva en los detalles financieros y separa sus resultados
  de caché. Las consultas en paralelo reciben el mismo periodo de la petición.
- Resumen comercial con ventas ganadas y oportunidades de Backlog_Proyectos,
  usando las conversiones de Comercial. El trabajo por entregar muestra
  «Sin dato» mientras no exista una fuente para el saldo pendiente.
- Acuerdos y pendientes con responsable, fecha, estado y notas. Se guardan
  en SQLite, son globales y se conservan al cambiar de periodo. Se mantienen
  la validación de formularios, CSRF y la política de acceso existente.
- Nuevos estilos de tarjetas, calendario y rankings financieros.
- El resumen comercial de Ejecutiva se añade a `python manage.py warm_cache`.

## Compatibilidad

Se conservaron las correcciones de AIN.002 CR y CCO.001 CR, fuentes históricas
de KPIs, Budget (Hrs) en J, GSE por área y páginas independientes de capacidad
y proyectos. No se restauraron los enlaces ni las vistas retiradas del
Panel anterior. No se sustituyeron credenciales, configuración local ni base
de datos por archivos del RAR.

Se corrigió la clave del resumen de Operations para separar los periodos,
y se reutilizan los resultados financieros ya preparados para cada rango.
La caché de archivos tolera los bloqueos de eliminación de Windows
(WinError 32/33): una entrada vencida sigue siendo una ausencia de caché;
otros errores de permisos se propagan. No es necesario borrar toda la caché.

## Base de datos y respaldo

La migración `portal.0001_initial` ya se aplicó en esta instalación.
Al llevar el código a otra instalación, ejecutar `python manage.py migrate`
antes de iniciar Django. Los acuerdos se guardan en la base de datos local,
por lo que debe incluirse en los respaldos.

Respaldos previos a la integración, dentro de `tmp/integracion-actualizacion-5/`:

- `antes-actualizacion.zip`: archivos versionados del proyecto anterior.
- `antes-actualizacion.sqlite3`: copia consistente de la base local anterior.

## Validación

- Suite completa de Python: 1,250 pruebas aprobadas.
- Frontend: 28 pruebas aprobadas.
- Comprobación de Django sin incidencias y sin migraciones pendientes de crear.
- Revisión en navegador de Ejecutiva, carga de datos y apertura del calendario.

Los costos pendientes y los datos parciales conservan su indicación en la
interfaz; integrar esta versión no completa los datos faltantes de origen.
