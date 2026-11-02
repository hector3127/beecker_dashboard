# Integración de la copia del compañero — 02/11/2026

Origen revisado: carpeta entregada por el usuario en Downloads,
`beecker_dashboard-main (3)/beecker_dashboard-main`. La copia no tiene
historial Git; la atribución personal no puede verificarse. El usuario
autorizó integrar los cambios identificados tras la comparación.

## Alcance

- Capacidad: plantilla operativa de Bandas/rol y registros Clockify locales,
  exclusión del ID Comida, control de mes sincronizado, ID Clockify visible,
  fechas de sincronización y exportación detallada individual.
- Facturabilidad: capacidad individual para bajas explícitas y cortes de
  plantilla. Conserva conceptos/NYB y matriz aprobados del destino.
- Operativa: capacidad desde el servicio común; lectura consistente y avisos
  de falta de datos. Inversión usa la población vigente de EVA 1 y EVA 3.
- Inversión: acumulado por INV_OPERATIVA/INV_COMERCIAL, desglose por recurso,
  área y proyecto, gráficas y detalle. Cambia la fuente anterior mensual.
- Comercial: gráficas mensuales de pipeline, cuentas, importes y probabilidades
  ponderadas por horas, con estilos y filtros del origen.
- EVA 1: proyectos vencidos permanecen abiertos hasta evidencia terminal de
  épicas; Resolved se admite terminal. No basta Summary/General cerrado si
  hay épicas abiertas. Horas al corte pueden leerse de meses locales completos.
  Histórico materializado versionado para renovar reglas.
  Incluye las exclusiones puntuales recibidas AZR.001.PRUEBA y CFC.001
  para EVA 1; no elimina esos proyectos de las fuentes.
- KPIs: detección de tablas ausentes con aviso; conserva cumplimiento en C,
  selector de año y datos históricos ya existentes en el destino.
- Proyectos: ajustes visuales y funcionales de Ejecutivo, Planeación,
  Esfuerzo, RAID, Acciones, Cliente, Azure e IA. Las hojas llamadas
  `*_reference.css` son estilos del diseño recibido, no comparaciones con el old.
- IA IXS: priorización de evidencias por intención de pregunta, fuentes
  visibles y respuesta contextualizada. Límite de respuesta aumenta de
  800 a 1800 tokens; puede aumentar consumo del proveedor por consulta.

## Preservación

No se copian .env, env, key.json, SQLite, logs, cachés, entornos, binarios ni
dependencias. No se ejecuta código de inicialización del origen. No se aplican
migraciones ni sincronizaciones, imports históricos, cierre o programación.
PostgreSQL, accesos y cierres continúan sin activarse. EVA4 conserva exclusión
AER, buscador, N/A y consulta del mes actual.

No se restauran archivos retirados ni comparaciones/generadores/snapshots
anteriores. Se excluye el lector antiguo kpi_inventory_history sin consumidor.
Los cambios locales preexistentes (incluidas bajas staged, pruebas y tools)
permanecen sin modificar ni incluir en los commits de integración.

Respaldo por archivo sustituido: `tmp/backups/colleague-code-20261102/`.
Manifiesto técnico local: `tmp/colleague-applied.json` (125 archivos inicialmente
incorporados, incluidas pruebas). Se añadieron correcciones de tipado sin
alterar resultados y adaptaciones de pruebas a los contratos nuevos; no se
regeneran JSON de cálculos para hacer coincidir resultados.

## Validación

Primera corrida amplia: 2,387 aprobadas y cinco fallos en 2,392 pruebas de
portal/capacidad/GSE/core/daily/Azure/access. Se diagnosticaron: contrato antiguo
mensual de inversión, fixture de inventario ausente, regex de imports con
huella y query versionada, dos expectativas de respuesta IA antigua.
Las verificaciones actuales de calidad IA se conservan junto con el resto de
paridad no afectada. Validación final y navegador se registran en el plan.

Node: 471 aprobadas (las bajas locales de pruebas retiradas explican el
recuento menor frente a registros históricos). Ruff dirigido y mypy de
pages.py aprobados. Django check y makemigrations --check aprobados.
No se hizo push. La fase 11 no se declara cerrada por esta integración.

Navegador: primera corrida 141 aprobadas y siete fallos; repetición final
33 aprobadas, con solapamiento (no sumar como suite completa). Incluye las
18 pestañas IXS/AER a 1450/900/600/390/320 y editores. Corregidos textos de
9–11 px a 12 px en las cinco hojas nuevas, tarjetas IA y fecha AER a 320 px.
La navegación de capacidad valida ahora ruta y parámetro mensual. Capturas
locales en tmp/design-review y tmp/migration/commercial; revisión visual de
Ejecutivo y Acciones móviles, Comercial escritorio y detalle de inversión.
Ruff y formato final: 73 archivos propios aprobados. No se cambian umbrales
de legibilidad ni se regeneran expectativas de cálculos.

Repetición final de los cinco archivos de servidor afectados: 103 aprobadas
(alcance dirigido, con solapamiento con la corrida amplia). Commits locales:
9f0c421 servicios y pruebas; 4a055d4 interfaz y navegador. Sin push.
