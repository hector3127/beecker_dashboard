# Vista de proyectos: dirección visual y validación

Solicitud del 27/10/2026: rediseñar todas las pestañas del detalle de proyecto.
Esta autorización sustituye la conservación estricta del aspecto anterior
**solo en esta vista**. Se conservan datos, cálculos, controles, permisos,
exportaciones, navegación y operaciones de edición.

## Dirección: centro de seguimiento de entregas

Mantener Beecker reconocible y dar prioridad a la lectura de decisiones.
El único gesto de marca dominante es la cabecera morado/fucsia; el área de
trabajo usa superficies blancas, texto oscuro y color semántico en estados.
La navegación presenta todas las pestañas existentes de cada familia.

- Tinta: #211b4b; secundario: #676b82; superficie: #ffffff.
- Fondo: #f5f6fb; borde: #e4e6ef; marca: #6429d8.
- Estados: verde #147d5c, ámbar #9b650d y rojo #c62d50.
- Tipografía: familia del portal con respaldo del sistema. Título 26–32 px,
  sección 17–20 px, texto/datos 13–14 px, ayudas 12 px. Números tabulares.
- Espaciado de 4/8 px; paneles 20–24 px; separaciones 16–24 px.
- Contenido centrado hasta 1680 px; rejillas adaptadas al contenido y a
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
