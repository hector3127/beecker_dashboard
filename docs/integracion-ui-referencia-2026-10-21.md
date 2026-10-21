# Integración visual y seguimiento por cuenta

Referencia: `beecker_dashboard-main (1).rar`, recibida el 21/10/2026.

Se comparó el código del portal antes de incorporar los cambios. La extracción
de referencia quedó en `tmp/referencia-rar-20261021/`, ignorado por Git.

## Cambios incorporados

- `portal_loading.js` y su CSS: indicadores de consulta, skeletons y regiones
  con `aria-busy`. Las consultas superpuestas mantienen el indicador hasta
  finalizar la última. Se respeta la preferencia de movimiento reducido.
- Operativa activa y libera esas regiones durante cada petición.
- Ejecutiva diferencia un bloque que aún se está consultando de un valor
  realmente pendiente. El estado de actualización informa de la disponibilidad
  de Financiera, Operaciones y Comercial. Los indicadores de consulta terminan
  también cuando la preparación falla.
- Una plantilla compartida presenta Decisiones y seguimiento en Business
  Overview y en Cuenta. El primero conserva el historial global; la cuenta
  muestra acuerdos abiertos o en curso de esa cuenta.
- El formulario de cuenta ya selecciona la cuenta correspondiente. El endpoint
  aplica el mismo alcance y rechaza cambios de registros de otra cuenta.
- Cada fila permite cambiar el estado o completar el acuerdo con Cerrar.
  Completar conserva el registro en SQL y en el historial global.
- Se mantienen las equivalencias de nombres de Heineken y Oxxo de la referencia.

## Integración con las mejoras locales

Se conservaron el diccionario con buscador y los modales de pendientes con
cierre visible. Las tarjetas incorporan SVG por indicador, avisos contextuales
y una sola acción de detalle al pie. Fuentes y cálculo abre un panel lateral
común a las tres tarjetas, sin modificar sus alturas.

Las fórmulas del panel explicativo corresponden al motor de cálculo local.
No se importaron los cambios financieros adicionales que contiene el RAR.
Tampoco se copiaron su base SQLite, caché, entorno ni credenciales. No se
necesitan migraciones nuevas: los acuerdos utilizan `ExecutiveAgreement`.

## Verificación

- Pruebas de alcance por cuenta, alias, creación y cambio de estado; los
  completados siguen visibles en el historial global.
- Pruebas frontend que diferencian consultas en curso de valores faltantes,
  liberan indicadores al terminar y conservan cifras válidas ante fallos.
- Revisión en navegador de las tres tarjetas, el panel lateral y el formulario
  contextual de una cuenta. La comprobación del formulario no guardó registros
  de prueba en la base de uso diario.

Los tres fallos frontend ya documentados antes de esta integración son
independientes de estas funciones: extracción del script de costos por sprint
y dos expectativas antiguas sobre textos/cifras comerciales.

Resultado final: 1,538 pruebas Python aprobadas, cobertura 90.82%; 56 de 59
pruebas JavaScript aprobadas, con esos tres fallos previos. Ruff y Mypy pasan
(355 archivos fuente revisados por Mypy). El navegador confirmó que abrir el
panel explicativo no cambia la altura de ninguna tarjeta y que cabe en un
viewport móvil de 390 píxeles sin desbordamiento horizontal.
