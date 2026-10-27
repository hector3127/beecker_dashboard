# Documentación del proyecto

## Entrada vigente

- [AGENTS.md](../AGENTS.md): reglas y siguiente bloque de trabajo.
- [Estado de traspaso](estado-traspaso.md): estado actual al principio;
  los bloques siguientes son históricos.
- [Plan de migración](plan-migracion-frontend.md): objetivos y evidencia;
  su apartado vigente prevalece sobre los avances históricos.
- [Auditoría del 27/10](auditoria-fase11-2026-10-27.md): comprobaciones
  independientes de main, CSP, archivos retirados y límites de cobertura.
- [CSP](estado-csp.md) y [permisos/Genesis](permisos.md).
- [Congelación de referencias](congelacion-referencias.md): piloto integrado,
  modelos ya independientes del original y siguiente bloque.

## Operación y datos

Conservar los manuales de base de datos, sincronización y ejecución programada,
el reporte de horas mensuales y la navegación al origen. Las conciliaciones
de KPIs/horas y cambios solicitados por negocio no son temporales de migración.

## Evidencia histórica

Los documentos `retiro-*.md`, `integracion-*.md`, `preparacion-fase-11.md` y
`limpieza-por-lotes.md` conservan resultados y decisiones por commit. Sus
recuentos describen el momento de cada bloque, no el estado actual.
`archivo/` conserva notas y análisis anteriores que siguen teniendo contenido.

## Limpieza de documentación

El 27/10 se retiró `prompt-continuacion.md`: duplicaba AGENTS y el traspaso,
con instrucciones obsoletas sobre CSP y presentaciones que ya no existen.
Su función está cubierta por las entradas vigentes de esta página.

Antes de borrar otro documento, revisar contenido único, consumidores y
enlaces. No eliminar evidencias de prueba, reglas de negocio, conciliaciones
o manuales solo porque correspondan a un bloque terminado.
