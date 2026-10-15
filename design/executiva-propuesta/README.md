# Propuesta visual de Ejecutiva

Maqueta independiente para revisión. No modifica los templates del portal,
las consultas, fórmulas, rutas, base de datos ni cachés. Los valores son de
referencia de la interfaz anterior; la gráfica es una serie ilustrativa.

## Dirección visual

Se revisó https://beecker.ai/ el 15/10/2026. Los estilos visibles del sitio
incluyen estos colores, tomados de sus estilos calculados:

| Color del sitio | Hex | Uso propuesto |
|---|---|---|
| Azul oscuro | #00092A | Navegación y títulos |
| Índigo | #180191 | Acciones principales y serie de ingresos |
| Violeta | #803FE0 | Acentos secundarios |
| Naranja | #FF9933 | Selección de navegación y foco de teclado |
| Blanco | #FFFFFF | Superficies de lectura |
| Texto oscuro | #0F172A | Referencia para textos con contraste |

Para facilitar la lectura se añaden neutros de interfaz: texto #17233B,
secundario #526078, fondo #F4F6FA y bordes #DFE4ED. No se presentan como
colores oficiales de un manual de marca. Los estados usan verde y rojo
oscuros con etiquetas, además del color. El naranja brillante no se usa
como texto pequeño sobre blanco.

Tipografía: Poppins, usada en elementos del sitio oficial, con Arial como
respaldo. Alineación izquierda para contenido y derecha para cantidades.
Los datos usan cifras tabulares. Se reduce la decoración para concentrar
la atención en métricas, excepciones y acciones.

## Distribución

```text
Escritorio
Navegación azul oscuro
Ejecutiva                           Periodo y actualización
[ Financiera ] [ Operations ] [ Comercial ]
[ Rentabilidad mensual, fuentes y avisos dentro del bloque ]
[ Cuentas con margen alto ] [ Cuentas con margen bajo ]
[ Requieren decisión ]
[ Acuerdos y pendientes ]

Tablet de 701–900 px
[ Financiera ] [ Operations ]
[ Comercial                  ]
[ Gráfica, cuentas y seguimiento en bloques completos ]

Móvil hasta 700 px
[ Navegación en dos filas ]
[ Título ]
[ Periodo y actualización ]
[ Financiera ]
[ Operations ]
[ Comercial ]
[ Gráfica adaptada al ancho ]
[ Cuentas ]
[ Decisiones como fichas ]
[ Acuerdos ]
```

Los avisos de cobertura, costos pendientes y fuentes viven dentro del
componente al que pertenecen. Los cálculos ampliados usan desplegables.
El control de actualización permanece arriba a la derecha en escritorio,
junto al periodo, y ocupa el ancho disponible en móvil.

## Revisión

Abrir `index.html` o servir esta carpeta con un servidor HTTP estático.
Se puede cambiar el periodo de muestra, desplegar explicaciones y alternar
las series de la gráfica. Los accesos de navegación son enlaces internos
de la maqueta. No se guardan acuerdos ni se consultan datos externos.

Se revisó en navegador a ancho de escritorio, 820 px y 390 px. No se detectó
desbordamiento horizontal de la página; las decisiones cambian de tabla a
fichas en móvil. Capturas adjuntas en esta carpeta.

La implementación en Django queda pendiente de la revisión del usuario.

## Dos variantes adicionales

`comparativa.html` permite comparar:

- **A / Logo Beecker** (`index.html?tema=logo`): azul #1B0096 y violeta
  #6200D0 extraídos del logo local, con coral #FA3541 de su extremo derecho.
  Cabecera blanca, logo en sus colores originales y acentos pequeños.
- **B / Plataforma QA** (`index.html?tema=qa`): colores declarados en
  `C:/qa_automation_platform/apps/test_cases/static/test_cases/css/test_cases.css`
  y compartidos por PEP: #1B0096, #6200D0, #B53A99 y #E5365C. Fondo #F6F7FB,
  texto #1F2330, secundario #667085 y Segoe UI, como en esa plataforma.
  Se retoman la cabecera con tinte suave, bordes redondeados y controles
  degradados, concentrando la decoración para facilitar la lectura.

Ambas usan la misma información y distribución. La variante B cambia también
la tipografía para mantener continuidad con QA. El rojo coral/rosa de marca
se usa en acentos; los estados críticos siguen llevando texto e indicadores
específicos. Los controles con texto blanco usan tonos oscuros para mantener
el contraste, en lugar de situar texto pequeño sobre el rosa más brillante.

El proyecto QA se consultó solo para leer estilos. No se modificó.
Se verificaron anchos de 320, 390, 820 y 1280 px en ambas variantes:
sin desbordamiento horizontal y con una, dos o tres columnas según el ancho.
El selector superior permite cambiar entre las dos variantes y Web oficial.

## Propuesta A más visual

`expresiva.html` conserva A original y ofrece una alternativa más expresiva:

- Operations es el acento principal: fondo violeta y un indicador circular
  del avance en horas. El círculo redondea la etiqueta a 87%; el dato principal
  conserva 87.39% y la marca de resultado parcial. No significa salud ni éxito.
- Financiera y Comercial conservan superficies claras, cifras protagonistas
  y mensajes de datos pendientes dentro de cada componente.
- Las prioridades aparecen junto a rentabilidad, con acciones explícitas.
- La gráfica se puede explorar con cursor, teclado o toque, y sus series se
  activan/desactivan. Sus cifras son ilustrativas y se identifican como tales.
  No se inventan tendencias históricas de los indicadores principales.
- Las cuentas incorporan barras de margen con las cifras de referencia ya
  presentes en A; los acuerdos conservan su lugar y sus estados de muestra.

Es una maqueta estática, sin cambios en el portal ni en sus datos o caché.
Se verificó la distribución a 320, 390 y 820 px, además de escritorio.
