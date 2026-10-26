# Integración de Christian y limpieza de frontend

Base de comparación: **3410e89**, sobre main, incluyendo `0de6c7d`,
`47d0364`, `834bbfa` y los bloques iniciales de fase 11. Se conserva el diseño
de esa base; la comparación no busca regresar al diseño previo de Christian.
La reorganización JS queda en `8be0dac`; la fusión CSS y este informe forman
el bloque siguiente del mismo trabajo.

## Cambios que se conservan

- Lectura de logos por `lib/account-logos.js`, caché compartida y API v1;
  búsqueda pura en `account-logo-lookup.js`, ambos en importmap. Sin lecturas
  fetch nuevas. La subida multipart/borrado de logos conserva su transporte.
- Comando `account_logos export|import`: sin tocar sus datos ni ejecutarlo
  sobre la base del usuario durante esta reorganización.
- Comercial: Previas al cierre muestra oportunidades abiertas; no volver a
  mostrar Pendiente ni la nota retirada. La plantilla anterior sigue igual.
- Capacidad diaria: Histórico Discovery→Deployment y respaldo Azure, con
  asignaciones fuera del mes ocultas. No se modifica Python ni su cálculo.

## Los 17 archivos revisados

Todos quedan con `// @ts-check`, JSDoc en funciones de entrada y formato
legible. Los puntos de importación existentes permanecen: los consumidores
no necesitan conocer la reorganización. No se introduce un framework.

| Entrada | Responsabilidad y separación |
| --- | --- |
| eva1/account_column.js | Control de logos; iniciales en modelo y celdas/imágenes en vista |
| eva1/history_table.js | Estado, filtros y CSV; modelo CSV y renderizador de página separado |
| eva1/main.js | Inicialización y eventos; conserva filtros y modelo existente |
| eva1/model.js | Fechas, filtros y CSV puros, ahora documentados |
| eva3/column_menu.js | Borrador/aplicación/cancelación; condiciones en modelo y color en vista |
| eva3/history_reference.js | Estado y controles; normalización/fechas/CSV en modelo, texto y tabla en vistas |
| eva3/main.js | Consultas y actualización; badge en main_view, cálculos en modelo existente |
| eva3/model.js | Reglas numéricas originales, sin cambiar redondeo ni datos ausentes |
| eva3/reference.js | Estado/filtros y exportación; CSV puro y renderizador separado |
| eva/history.js | Carga API y ciclo de vida; tablas IXB/AER en history_view |
| eva/table_columns.js | Estado de filtros y orden; lectura de celdas/encabezados en vista |
| eva4/report_table.js | Logos, controles y estado; CSV puro, iconos/banderas y tabla en vistas |
| executive/sections/card_visuals.js | Coordina vistas; valores mensuales puros y SVG separados |
| billability/reference.js | Estado de modo/selección y eventos; parseo/formato puro, iconos/sparkline y gráfica separados |
| operativa/sections/capacity.js | Entrada compatible; modelo de medidor/formatos y vista DOM |
| operativa/sections/eva.js | Entrada compatible; disponibilidad y vista de tarjetas separadas |
| dictionary/presentation.js | Entrada compatible; metadatos/textos puros e iconos SVG en vista |

Los renderizadores reciben estado vivo y callbacks mediante contratos de
contexto. El controlador conserva la propiedad de página, filtros, selección,
consultas y exportaciones. Los getters/setters evitan copiar un estado que
podría quedar desactualizado en un evento de una fila o botón. Los modelos
extraídos no importan DOM, vistas ni transporte; una prueba verifica esa frontera.

JSDoc describe los límites; no se afirma una compilación TypeScript de toda
la aplicación (el proyecto no tiene ese chequeo configurado). Las validaciones
de ejecución son Node, navegador y las suites Python indicadas en el plan.

## Hojas fusionadas

| Destino | Hojas integradas |
| --- | --- |
| operativa.css | operativa_reference, operativa_billing_reference, operativa_eva_reference, operativa_capacity_reference |
| executive.css | executive_cards, executive_monthly, executive_rankings, executive_glossary |
| all_accounts.css | all_accounts_reference |
| costs.css | costs_reference |
| delivery_manager.css | delivery_manager_reference |
| project_detail_ixs_ai.css | project_detail_ixs_ai_reference |

Se conservan los contenidos y el orden interno de las reglas; se eliminan
los enlaces redundantes y se actualiza la versión de caché. En Ejecutivo,
el glosario específico queda dentro de la hoja propia; la hoja compartida
de acuerdos conserva sus selectores delimitados y su enlace independiente.
`agreements_reference.css` sigue compartida por Cuenta y Business Overview.
No se mezcla CSS de distintas pantallas ni se fusionan las hojas anteriores
de portal con las activas de frontend. El ID de estilos IA base se conserva;
la prueba verifica que el enlace redundante retirado no reaparece.

## Comparación y pruebas

Pantallas de referencia: EVA 1 (incluido histórico), EVA 3 (incluido histórico),
EVA 4, Business Overview (tarjetas, ranking, gráfico mensual y glosario),
Operativa (incluidas EVA, capacidad y facturabilidad), Diccionario,
Facturabilidad (general y especialidad), Costos, Todas las cuentas y Delivery
Manager. Se usan 1450/900/390 px donde las referencias existentes lo contemplan.
IA IXB también conserva su prueba de estilos/estructura frente a la anterior.

Para comparar la base con los cambios pendientes sin cambiar el checkout,
`tmp/christian_reference_plugin.py` sirve plantillas y assets leídos mediante
`git show 3410e89:<ruta>`. Controla reloj y posición del ratón en las capturas.
Las pruebas mantienen los datos simulados y el bloqueo de red externa.
El arnés y las imágenes son diagnósticos locales ignorados, no producto.

La primera corrida amplia tuvo 193 aprobadas y un fallo de periodo en
Facturabilidad por recurso; la revalidación volvió a detectarlo. El test
interactuaba con el HTML recién navegado antes de terminar el módulo. Ahora
espera los controles de la tabla, que se montan después del selector de
periodo. No se altera producción, se oculta el fallo ni se omite el caso.
La base 3410e89 también se ejecutó como control (tres casos aprobados).

Ver los resultados definitivos y el siguiente bloque en el encabezado del
plan y del traspaso. La fase 11 sigue abierta: faltan otras referencias y
la certificación CSP completa. No se activa ACCESS_ENFORCED ni CSP global.

## Evidencia final

- **Servidor:** 1691 aprobadas con `pytest tests/portal tests/core tests/access
  tests/capacidad/test_history_range.py -q --no-cov --tb=short`. Incluye el
  comando nuevo de logos y los permisos/APIs existentes. Sin omisiones.
- **Node:** 505 aprobadas con `node --test tests/frontend/*.test.*`. La prueba
  de filtros ya importa el modelo puro, sin quitar imports mediante regex/vm.
  Siete casos nuevos cubren iniciales, importes numéricos como texto, márgenes
  negativos, ausencia de costos, decimales/comas, CSV protegido, definiciones,
  frontera de modelos y las 17 entradas sin fetch directo.
- **Navegador amplio:** 194 casos ejecutados (193 aprobados y el fallo de
  sincronización descrito). Revalidación de los tres archivos EVA/Facturabilidad:
  67 ejecutados (66 aprobados y el mismo fallo, antes de ajustar la espera).
  Tras ajustar SOLO la prueba, corrida final de 57 seleccionadas aprobadas,
  incluidos los tres casos de periodo. No se afirma una segunda corrida amplia
  íntegra ni se suman casos solapados como distintos.
- **Referencia:** 54 seleccionadas contra 3410e89 aprobadas con el arnés
  estable; 57 actuales aprobadas (las mismas 54 + los tres casos de periodo).
  De 53 PNG comparados, 42 son idénticos. Tres de Costos cambian únicamente
  los dígitos de «Última consulta», generados con Date del navegador. Ocho
  tienen diferencias pequeñas de pintado: siete con máximo 1–2 niveles RGB
  y EVA 3 escritorio con máximo 9 (media absoluta 0.0015/255). No se observan
  cambios de estructura/cifras/diseño; no describir estas 53 como idénticas
  píxel a píxel. Se inspeccionaron capturas de glosario, tarjetas EVA,
  Facturabilidad y Costos para clasificar las diferencias.
- Artefactos locales: `tmp/christian-3410e89-stable/`, `tmp/design/`,
  `tmp/christian-visual-results.json`, `tmp/christian-reference-stable-*.log`,
  `tmp/christian-after.log`, `tmp/christian-revalidation.log`,
  `tmp/christian-server.log`, `tmp/christian-node-final.log`.
- Ruff, formato (711 archivos) y mypy de páginas aprobados. Los temporales
  ajenos siguen intactos. No se hace push en este bloque.
