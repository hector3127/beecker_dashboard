# Vista de proyectos: dirección visual y validación

Solicitud del 27/10/2026: rediseñar todas las pestañas del detalle de proyecto.
Esta autorización sustituye la conservación estricta del aspecto anterior
**solo en esta vista**. Se conservan datos, cálculos, controles, permisos,
exportaciones, navegación y operaciones de edición.

## Ajuste posterior del resumen de Acciones

Petición sobre la captura del usuario, base `4d520ce`: encabezado sin el
doble recuadro, cinco métricas con el mismo orden icono/etiqueta, valor y
ayuda. La clase `.top` heredaba reglas de otra presentación; se sustituye
por `.aer-action-metric-head`. Se usan SVG del catálogo existente, colores
por categoría y una composición de cinco/tres/dos/una columnas. La fecha
ocupa una fila completa en móvil. Se mantienen clases de compatibilidad,
valores y operaciones; se retira solo el emoji del texto del botón Limpiar
duplicados, reemplazado por un SVG decorativo.

24 Chrome aprobadas: 16 casos vacío/con datos en AER/IXS y
1450/900/390/320, y ocho operaciones/guardas del transporte. Se comprobó
alineación de valores, iconos, ausencia de desbordamiento y apertura del
editor. Las pruebas funcionales incluyen guardar/reintentar, editar,
eliminar/confirmar y limpiar duplicados. 476 Node, Ruff y sintaxis JS
aprobados. Capturas inspeccionadas en `tmp/actions-overview/`; logs
`tmp/actions-overview-final.log` y `tmp/actions-overview-node-final.log`.
No se ejecutan seis comparaciones del diseño old, que sigue sin ser el
criterio visual del rediseño autorizado. Sin llamadas a proveedores reales.

## Segunda revisión: Business Overview como referencia (delivery-v2)

Base de comparación: `ce68f0e`. El usuario pide recorrer cada pestaña a
detalle y acercarla a Business Overview. Se revisan las dos familias con
fuentes simuladas pobladas, sin escrituras externas. No se cambia Business
Overview: se toman de su CSS/captura el ancho 1520, fondo lavanda, títulos
azules, bordes suaves, superficies claras y acciones moradas.

| Apartado | Revisión y ajuste |
| --- | --- |
| Ejecutivo | Escala común de métricas, lectura de alertas/resumen y leyendas con tamaños legibles. |
| Planeación | Métricas adaptables, cronología con desplazamiento propio, filtros/acciones separados y selección con etiqueta legible. |
| Esfuerzo | Cinco métricas que pasan a tres/dos/una según el ancho; leyenda y resumen se apilan; fechas y registros mantienen espacio. |
| Recursos | Roles y nombres no se parten letra por letra; historial/evaluaciones conservan contexto y controles. |
| Gestión RAID / Riesgos | Conteos y etiquetas coherentes, detalle y formulario con límites de pantalla. |
| Acciones | Encabezado, estados y formularios al mismo tamaño; columnas y operaciones conservadas. |
| Cliente | Tarjetas de contactos, matriz, ficha y directorio con espaciado común; editor móvil en una columna. |
| Comunicación | Métricas/controles legibles, barra de filtros adaptable, lista y contexto separados; detalle/editor responsivos. |
| Azure DevOps | Distribución y leyenda dejan de comprimirse en tablet; grupos y tabla conservan columnas y controles. |
| IA | Indicadores adaptables, informes/evidencias legibles, acciones que se distribuyen y editores dentro del dispositivo. |

Hallazgos concretos de la revisión: las métricas de Esfuerzo podían caber
sin desbordar y aun así resultar ilegibles; se añade una comprobación de
ancho mínimo de tarjeta. Los roles también podían cortarse carácter por
carácter: las columnas de detalle tienen ahora un ancho de lectura mínimo.
El SVG de evaluaciones AER usaba `preserveAspectRatio=none`, deformando
marcadores y texto: se adapta su viewBox al contenedor con ResizeObserver,
conservando las posiciones normalizadas del modelo y sus cinco valores.
Las leyendas de Azure usan una composición propia para tablet.

Evidencia visual local: `tmp/design-review-baseline/` conserva las capturas
anteriores; `tmp/design-review/` contiene la revisión por familia/pestaña/
ancho y `editors/` sus formularios. Se comprueban 1450/900/600/390/320 para
las pestañas y 1450/900/390/320 para los once editores. El navegador integrado
estaba deshabilitado; la revisión se realizó en Chrome mediante las pruebas.

Las referencias de AER se actualizan expresamente a
`project_redesign_delivery_v2`; no se intenta igualar el old ni se declara
aprobación posterior del usuario. El transporte y todas las operaciones
siguen en sus módulos existentes.

### Validación de delivery-v2

- 476 Node completas aprobadas (`tmp/design-review-node-release.log`).
- Las 32 pruebas específicas de diseño aprobaron dentro de la corrida de
  cierre: 18 pestañas en cinco anchos (90 vistas), 11 editores en cuatro
  anchos (44 formularios), referencia visual de Business Overview,
  redimensionado del SVG y desplazamiento de la tabla conservando nombres.
  Comprueban contención, ayudas/textos nativos de al menos 12 px, tarjetas
  de al menos 128 px, cifras sin truncar y campos de tamaño utilizable.
- La corrida de cierre registró 70 aprobadas y una referencia desactualizada
  en Recursos/full/390. Tres mediciones reprodujeron la disposición final
  con todos los textos iguales: aquella captura precedía al último ajuste
  de métricas móviles. Se actualizó solo ese caso, sin tolerancias nuevas.
  Después pasaron las 31 de Ejecutivo/Recursos AER, incluidas sus 24
  comparaciones exactas, teclado, CRUD, reintento y respuestas tardías.
  Logs: `tmp/design-review-release.log`, `tmp/design-review-aer-release.log`.
- La regresión amplia anterior de controles registró 114 aprobadas y dos
  fallos de diseño a 320 px (Azure/IA). Se corrigieron y seis dirigidas
  aprobaron antes de la corrida de cierre. No se cuenta como una suite
  completa de e2e ni se suman corridas solapadas.
- Ruff de los seis Python propios, sintaxis JS, `git diff --check` y
  `manage.py check` aprobados. Se conserva el aviso del entorno de pruebas
  sobre `staticfiles/` ausente; los estáticos fuente sí se sirvieron.

No se repitió toda la suite de servidor: no hay cambios en `apps/`, `core/`
ni `config/`. No se hicieron envíos ni escrituras a proveedores reales.
Las antiguas comparaciones de aspecto contra el old siguen pendientes de
clasificación en fase 11; este bloque no las borra ni declara cerrada esa fase.

## Dirección: centro de seguimiento de entregas

Mantener Beecker reconocible y dar prioridad a la lectura de decisiones.
El único gesto de marca dominante es la cabecera morado/fucsia; el área de
trabajo usa superficies blancas, texto oscuro y color semántico en estados.
La navegación presenta todas las pestañas existentes de cada familia.

- Tinta: #1b1a6b; títulos: #1b1a9e; secundario: #5b5e85; superficie: #ffffff.
- Fondo: #f3f4fd; borde: #e5dcff; marca: #6429d8.
- Estados: verde #147d5c, ámbar #9b650d y rojo #c62d50.
- Tipografía: familia del portal con respaldo del sistema. Título 26–34 px,
  sección 20 px, texto/datos 14 px, ayudas 12–13 px; texto/campos móviles
  16 px. Números tabulares.
- Espaciado de 4/8 px; paneles 20–24 px; separaciones 16–24 px.
- Contenido centrado hasta 1520 px, como Business Overview; rejillas adaptadas al contenido y a
  escritorio/tablet/móvil. Navegación horizontal desplazable en móvil.
- Tablas completas con desplazamiento propio y columna de contexto fija;
  no esconder columnas ni encoger texto para forzarlas dentro del móvil.
- Gráficas con proporción conservada y leyendas que fluyen; ejes y barras
  no cambian de valores. Cronogramas con su propio espacio de lectura.
- Formularios y ventanas con controles táctiles, foco visible y altura
  limitada al dispositivo. No se dispara ninguna escritura en pruebas visuales.

Esquema de lectura:

    Regreso
    Proyecto / contexto                              Estado / Actualizar
    Ejecutivo · Planeación · Esfuerzo · Recursos · RAID · …
    Indicadores con valor y contexto
    Zona principal de trabajo              Atención / distribución
    Detalles, tablas o registros de seguimiento

La búsqueda de sistema visual de ui-ux-pro-max devolvió patrones de marketing
que no corresponden al panel; se usan las pautas generales de diseño de la
skill y la identidad existente. La consulta específica de tablas responsivas
sí recomendó desplazamiento contenido, aplicado aquí. frontend-design guía
la jerarquía y la revisión visual; no se añaden fuentes ni servicios externos.

## Cobertura aplicada

IXB/SaaS/RaaS: Ejecutivo, Planeación, Esfuerzo, Recursos, Gestión RAID,
Acciones, Cliente, Comunicación, Azure DevOps e IA. AER/T&M: las ocho pestañas
existentes, con el mismo sistema visual; no se inventan servicios nuevos.

Cada pestaña se revisa con datos de prueba, estados vacíos, tablas y controles
en 1450/900/390/320 px. Se conservan pruebas funcionales y expectativas de
cálculos; las referencias visuales de esta vista deben reflejar el rediseño
solicitado, nunca forzar su aspecto anterior.

## Evidencia del bloque (base 007d76c)

- 476 pruebas Node completas aprobadas; ningún modelo ni cálculo cambiado.
- 85 Chrome aprobadas con `config.urls`, sin recursos/rutas de referencia y
  con CSP: controles de recursos, filtros/CSV de esfuerzo, hitos, RAID,
  comunicación, escrituras/CSV de Cliente, planeación AER, esfuerzo AER,
  acciones de IA de ambas familias y transporte Azure. Incluye seis casos
  de recorrido responsivo (54 combinaciones pestaña/tamaño).
- Revisión ampliada final: ocho casos Chrome aprobados, 72 combinaciones de
  pestaña/tamaño. Cliente, Acciones y RAID usan datos poblados; los estados
  vacíos de otras fuentes usan dobles explícitos. Comprueba contención,
  selección visible de pestaña, tipografía y errores JS. El caso 320 px
  detectó un texto de IA desbordado; se corrigió el encogimiento del texto
  y se repitió satisfactoriamente.
- 24 referencias de Ejecutivo/Recursos AER capturadas para el rediseño
  solicitado (mismas entradas, variantes y formularios). Se distinguen por
  `source=project_redesign_delivery_v1`; las anteriores siguen en Git.
  En la corrida posterior, las 31 pruebas permanentes de ambos archivos
  pasaron, incluidas las 24 comparaciones y sus interacciones.
- Ruff de los seis archivos Python propios y `manage.py check` aprobados.
  Se conserva el aviso del entorno de pruebas por `staticfiles/` ausente;
  los estáticos del navegador sí se sirvieron desde sus fuentes.

Capturas y métricas locales: `tmp/design/projects/<familia>/<ancho>/`.
Se inspeccionaron Ejecutivo, Planeación, Esfuerzo, Recursos, RAID, Cliente,
Comunicación, Azure e IA; los cuatro tamaños se recorren automáticamente.
Registros de ejecución locales: `tmp/project-design-regression.log`,
`tmp/project-design-final-tabs.log`, `tmp/project-design-visual-final.log`,
`tmp/project-design-node.log`. Las corridas se solapan: no sumar sus casos
como si fueran una suite completa.

## Límites y continuación de fase 11

El diseño queda implementado para revisión del usuario; no se afirma una
aprobación visual posterior. Las pruebas antiguas que exigen igualdad de
apariencia con `?vista=anterior` ya no describen este encargo. No se borraron
ni se regeneraron masivamente: falta clasificar/reemplazar esas comparaciones
con la nueva referencia conservando sus casos funcionales. Esta entrega no
declara cerrada la fase 11 ni una corrida completa de e2e.

Las pruebas usan servicios simulados y no envían Gmail ni escriben Azure,
Sheets o Drive reales. No se modificó `apps/`, CSP, ACCESS_ENFORCED, fuentes,
cálculos ni otras páginas del portal. Sin push.
