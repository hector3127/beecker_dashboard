# 01 · Evidencia

Todo lo marcado INFERIDO sale de leer el código, no de ver la pantalla.

> **Corrección (descubierta al planear):** la primera pasada solo midió el CSS
> en línea del HTML. La página también carga `portal.css`, `accessibility.css`
> y `navigation.css`. Con eso: (a) `prefers-reduced-motion` **sí** se respeta en
> toda la página (`accessibility.css:31-37`); (b) `prefers-color-scheme` no
> existe en ningún CSS del portal; (c) el banner con degradado **no es propio de
> EVA-04**: es el componente compartido `.pgh` (`portal.css:46-58`) que usan
> Ejecutiva, Operativa, Comercial y EVA 1, y EVA-04 lo duplica con
> `.eva4-banner`; (d) `portal.css` ya define el sistema de diseño (`body.ds`:
> tokens `--ink`, `--brand`, `--line`…, y las clases `.card`, `.note`, `.err`,
> `.vacio`, `.kp/.kc`, tablas), que EVA-04 no usa y reimplementa; (e) el
> `<main>` anidado también ocurre en EVA 1 (`eva1.html:82`): es del portal, no
> solo de EVA-04.

## Estructura (renderizado real, `/operativa/eva-4/?mes=2026-10`)

| Dato | Valor | Fuente |
|---|---|---|
| Tamaño del HTML | 78,038 bytes | render con datos reales |
| Elementos interactivos | 6 enlaces, 1 botón, 2 inputs (búsqueda y mes), 1 formulario | HTML renderizado |
| Tablas / filas / celdas | 3 tablas, 210 filas, 2,828 celdas | `eva4.html:29-32` |
| Columnas de la tabla de procesos | 15 | `eva4.html:32` |
| Filas de procesos | 164 (163 de datos) | render |
| Encabezados `<th>` con `scope` | 0 de 33 | render |
| `<caption>` en las tablas | 0 de 3 | render |
| Elementos `<main>` | **2** (`eva4.html:22` y `base.html:44`) | render |
| Párrafos `eva4-note` | 6 | `eva4.html:29,30,32,33` |
| Estilos en línea (`style="…"`) | 1 | render |
| Contadores duplicados | Activos, suspendidos y renovaciones aparecen en las fichas (`eva4.html:27`) y otra vez en las tablas y en la tarjeta de Operativa (`_eva4_card.html`) | `eva4.html:27-30` |

## Visual

| Dato | Valor |
|---|---|
| Tamaños de letra | 12 distintos: 11, 11.5, 12, 13, 14, 14.5, 15, 17, 20, 23, 28, 36 px |
| Colores distintos | 42 (hex) en la página renderizada |
| Valores de espaciado | 25+ combinaciones (`20px 28px`, `10px 16px`, `12px 18px`, `4px 0 0 4px`…) |
| CSS en línea | 5,218 bytes, dentro de `{% block css %}` (`eva4.html:4-20`) |
| Contraste más bajo | **3.29:1** texto blanco sobre el rosa `#ff3ba1` del degradado del banner (`eva4.html:5`); pasa 4.5:1 en el morado (4.93:1) |
| Otros contrastes | nota 6.35:1, encabezado de tabla 10.52:1, «crítico» 5.33:1, botón 7.67:1, cuerpo 15.19:1 |
| Fondo del banner | degradado de tres colores (`#603aff → #ab28ed → #ff3ba1`) |

### Estados

| Estado | Presente |
|---|---|
| Vacío | Sí: «No hay procesos activos o suspendidos» (`eva4.html:32`) |
| Error | Sí: `.err` con aviso y «Se conserva el último corte» (`eva4.html:25`) |
| Foco | Sí: contorno de 3 px compartido (`accessibility.css:13-16`) y uno propio para el mes |
| Cargando | **No** (la página es de servidor; no hay indicador) |
| Éxito | No aplica |
| Deshabilitado | **No** (el botón del mes no tiene estilo deshabilitado) |
| Encabezado fijo | `position: sticky; top: 0` en `th`, dentro de un contenedor con desplazamiento (`eva4-scroll`): INFERIDO que solo fija dentro del contenedor |
| Responsivo | 4 reglas `@media` (450, 700, 800 y 1050 px); la tabla de 15 columnas solo se desplaza en horizontal: INFERIDO |

## Copia y honestidad

| Texto | Problema | Fuente |
|---|---|---|
| «Consumo mensual de la base Clockify del Sheet» | Ya no es cierto: las horas salen de Clockify, por la base de datos cuando está encendida, y se agrupan por ROC ID y número del BOT | `eva4.html:32` |
| «Fuentes: ROC y 08.Base Clockify 2026» | El nombre de la hoja se muestra aunque la lectura sea de la base de datos | `eva4.html:33`, `eva4.py:198` |
| «N procesos no tienen coincidencia exacta de tarea… para evitar asignar horas de otro proceso» | Describe la regla anterior; hoy se cruza por ROC ID + número de BOT | `eva4.html:32` |
| «Sin dato» | 399 veces en la página; no distingue «0 horas», «sin límite» y «sin coincidencia» | render |
| «T M» | Etiqueta del servicio T&M mal formada | `eva4.py:105` (`norm()` convierte «T&M» en «t m») |
| Idioma | Encabezados de la tabla en inglés (pedido del usuario), títulos, notas y KPI en español | `eva4.html:22-33` |
| Patrones oscuros | Ninguno detectado | — |

## Peso y fricción

| Dato | Valor |
|---|---|
| JS inicial | `return_navigation.js` 1.9 KB + `page_capture.js` 3.9 KB + 2 scripts en línea. `html2canvas.min.js` (198.7 KB) se declara en `data-library`: INFERIDO que se carga solo al usarse |
| CSS externo | `portal.css` 7.7 KB, `accessibility.css` 1.1 KB, `navigation.css` 2.8 KB |
| Solicitudes externas | Google Fonts (5 pesos de Plus Jakarta Sans) |
| Animaciones en reposo | 0; 2 reglas `transition` |
| `prefers-reduced-motion` | Sí, global (`accessibility.css:31-37`) |
| `prefers-color-scheme` / modo oscuro | No existe en ningún CSS del portal |
| Notificaciones o modales al cargar | 0 |
| Tiempo de carga | No medido |

## Accesibilidad

| Dato | Valor |
|---|---|
| `lang` y viewport | `lang="es"`, `width=device-width` |
| Enlace para saltar al contenido | Sí (`accessibility.css:2-12`) |
| Puntos de referencia | 1 `nav`, 2 `main` (duplicado), 2 `header`, 0 `footer`; 8 atributos `aria-*` |
| Teclado | Todos los controles son enlaces, botón o campos nativos: alcanzables |
| Encabezados de tabla | sin `scope` ni `<caption>`; el lector de pantalla no asocia 15 columnas con cada celda |
| Contraste del texto principal | pasa en todo menos el blanco sobre rosa del banner (3.29:1) |

## Huecos conocidos

- No se midió tiempo hasta interactivo ni número real de solicitudes.
- No se vio la pantalla en un navegador ni en móvil.
- No se probó con lector de pantalla.
