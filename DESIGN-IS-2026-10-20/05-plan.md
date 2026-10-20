# 05 · Plan: rediseño de la pantalla EVA-04

**Estado (2026-10-20):** fases 1, 2, 3, 4 y 6 hechas; fase 5 (modo oscuro) no
hecha; verificación final en [06-reevaluacion.md](06-reevaluacion.md): 18/30.

Plan por fases, pensado para ejecutarse en sesiones separadas. Cada fase se
puede hacer sola y trae sus referencias, su verificación y lo que no se debe
hacer. **No se cambia el cálculo** (`eva4.py`, `eva4_hours.py`), los
encabezados de la tabla ni los límites por servicio.

## Decisiones abiertas (responder antes de la fase 2)

1. **Tabla «Servicios y estado por cliente».** La auditoría marca duplicada la
   ficha de totales y la tarjeta de Operativa. Propuesta: quitar solo la fila de
   fichas y dejar esa tabla y «Por renovar» como secciones plegadas debajo de
   la tabla principal. ¿Se conserva la tabla de clientes o se retira?
2. **Móvil.** Opción A: la tabla se desplaza en horizontal con las columnas
   BOT ID y Process Name fijas. Opción B: cada proceso se convierte en una
   tarjeta bajo 700 px. El plan asume A (menos código, mismos datos).
3. **Fuente.** Servir Plus Jakarta Sans desde el propio sitio exige descargar
   los archivos de la fuente; no se hará sin tu aprobación. Por defecto se
   mantiene Google Fonts.

## Fase 0 · Descubrimiento (hecho)

### Hallazgos que cambian el plan

- El sistema de diseño **ya existe**: `apps/portal/static/portal/css/portal.css`
  (`body.ds`, líneas 7-24 tokens; `.crumb` 42; `.pgh` 46; `.fbar` 63; `.card` 68;
  `.err` 73; `.vacio` 74; `.kp/.kc`; tablas 89-107; `.pill` 110). EVA-04 ya usa
  `{% block body_class %}ds{% endblock %}` pero reimplementa todo en su propio
  `{% block css %}` (`eva4.html:4-20`).
- El banner con degradado es el componente **compartido** `.pgh`
  (`data-tone="operations"`), igual que en EVA 1 (`eva1.html:85`). Se sustituye
  `.eva4-banner` por `.pgh`, no por un diseño nuevo.
- `prefers-reduced-motion` ya se respeta en todo el portal
  (`accessibility.css:31-37`). `prefers-color-scheme` no existe en ningún CSS.
- El `<main>` anidado es del portal: `base.html:44` ya abre
  `<main id="main-content">` y las páginas abren otro (`eva4.html:22`,
  `eva1.html:82`).
- `accessibility.css` ya trae el enlace para saltar (2-12) y el foco de 3 px
  (13-16).

### Referencia a copiar (no a reinventar)

- Estructura de página: `apps/portal/templates/portal/eva1.html:82-90`
  (`crumb`, `pgh data-tone="operations"`, `card`, `note`, `err`).
- Tablas: reglas `.ds table/th/td/.n/.pill` de `portal.css:89-111`.
- Datos disponibles para la plantilla (`apps/portal/services/eva4.py`):
  `processes` (claves `manager`, `country`, `client`, `bot_id`, `bot_label`,
  `service`, `process`, `status`, `status_code`, `start`, `finish`,
  `average_limit`, `invested_hours`, `hours_balance`, `package_limit`,
  `package_available`, `risk`), `clients`, `renewals`, `renewal_count`,
  `total`, `active`, `suspended`, `missing_limits`, `unmatched_tasks`,
  `month`, `loaded_at`, `hours_source`, `available`, `error`.

### Anti-patrones del código actual

- CSS y script por página en la plantilla (`eva4.html:4-20`, `:36`).
- Texto fijo sobre la fuente de datos (`eva4.html:32-33`).
- `Sin dato` para tres causas distintas.

## Fase 1 · Estilos con el sistema de diseño

**Qué hacer**
- Crear `apps/portal/static/portal/css/eva4.css` y enlazarlo desde
  `{% block extra_head %}`; vaciar `{% block css %}` de la plantilla.
- Usar solo variables de `body.ds` (`--ink`, `--brand`, `--line`, `--th-bg`,
  `--bad`…). Cero colores nuevos; cualquier excepción se documenta en el CSS.
- Tamaños de letra permitidos: **12, 13.5, 16, 19, 21, 32 px** (los que ya usa
  `portal.css`).
- Contenedor de la tabla con `max-height` y `overflow:auto` para que el
  encabezado fijo (`position: sticky`) funcione dentro de él.

**Referencias:** `portal.css:7-24, 89-111`; `eva4.html:4-20` (lo que se retira).

**Verificación**
- `grep -c "font-size" eva4.css` y lista de tamaños distintos ≤ 6.
- Ningún `#rrggbb` en `eva4.css` fuera de variables.
- La pantalla se ve igual en datos y orden de columnas.

**No hacer:** copiar las reglas viejas con otro nombre; tocar `portal.css`
(salvo la fase 5).

## Fase 2 · Estructura de la pantalla

**Qué hacer** (copiar el patrón de `eva1.html:82-90`)
1. `<div class="page">` en lugar de `<main class="eva4-page">`: un solo `<main>`.
2. `crumb` con el enlace de regreso y `.pgh data-tone="operations"` con el
   título «EVA-04 Report» (sustituye a `.eva4-banner`).
3. Barra de filtros `.fbar`: selector de mes y buscador, en la misma fila.
4. **Primero** la tarjeta «Procesos y consumo por servicio» con la tabla de
   15 columnas: `<caption class="eva4-sr-only">` (esa clase no existe en el portal: se define en `eva4.css`), `scope="col"` en los 15 `th`,
   `aria-label` en el buscador y `aria-live="polite"` en el contador de filas
   visibles.
5. Debajo, «Por renovar» y (según la decisión 1) «Servicios y estado por
   cliente» dentro de `<details>`.
6. Quitar la fila de fichas de totales (`eva4.html:27`) y poner los tres
   números dentro del resumen del `.pgh` (como texto, no como fichas).

**Verificación**
- Una sola etiqueta `<main>` en el HTML renderizado.
- `th` con `scope`: 15 de 15 en la tabla de procesos; `<caption>` presente.
- Los ids `eva4-processes`, `eva4-renewals` y `eva4-clients` se conservan
  (los usan tests y el script del buscador).

**No hacer:** cambiar el orden ni el texto de los 15 encabezados; mover la
lógica a JavaScript nuevo (el buscador actual de 1 línea se conserva).

## Fase 3 · Textos honestos y estados

**Qué hacer**
- Reemplazar la nota de la fuente por un texto que dependa del dato real:
  «Horas de Clockify del mes {{ month }}, por ROC ID y número del BOT»; mostrar
  `hours_source` solo si la lectura fue de la hoja (no con la base de datos).
- Distinguir en la tabla (mismas columnas, solo el contenido de la celda):
  - `invested_hours == 0` → `0`.
  - `invested_hours is None` → «Sin horas en Clockify».
  - `average_limit is None` → «Sin límite para este servicio».
  - Columnas de paquete vacías → «—» con una leyenda única.
- Una sola nota plegable «Cómo se calcula» (`<details>`) con: balance =
  límite − horas, límites por servicio y qué significa cada vacío.
- Estados: **error** (`.err` existente), **vacío** (`.vacio`), **cargando**
  (`aria-busy="true"` en la tabla y el botón del mes con estilo deshabilitado
  mientras se envía el formulario), **foco** (ya compartido).
- Corregir la etiqueta «T M» → «T&M»: `norm()` convierte «T&M» en «t m» y
  `SERVICES`/`LABELS` (`eva4.py:21-22`) no lo contemplan; agregar `"T M": "T&M"`
  a `LABELS` y `"T M"` a `SERVICES`, sin tocar `SERVICE_LIMITS`.

**Referencias:** `eva4.html:32-33`; `eva4.py:21-22,105`; `.err`/`.vacio` en
`portal.css:73-74`.

**Verificación**
- `grep -c "Sin dato" ` en el render = 0.
- `grep "08.Base Clockify"` en el render solo aparece cuando la hoja fue la
  fuente.
- La suma de celdas «Sin horas en Clockify» coincide con `unmatched_tasks`.

**No hacer:** cambiar `enrich_hours`, `SERVICE_LIMITS` ni el cruce por ROC ID.

## Fase 4 · Móvil y escritorio

**Qué hacer** (opción A de la decisión 2)
- Ancho: tabla con `min-width` y desplazamiento horizontal en `.tw`.
- Bajo 900 px (`portal.css` ya cambia ahí): BOT ID y Process Name fijas a la
  izquierda con `position: sticky` y fondo opaco.
- Objetivos táctiles ≥ 44 px en el selector de mes y el buscador.
- Revisar 360, 768 y 1440 px.

**Verificación:** capturas a 360/768/1440 px con el navegador integrado;
ninguna página con desplazamiento horizontal fuera del contenedor de la tabla.

**No hacer:** ocultar columnas (se perdería lo que pide el Excel).

## Fase 5 · Modo oscuro (opcional, solo EVA-04)

**Qué hacer**
- Añadir a `eva4.css` un `@media (prefers-color-scheme: dark)` que redefina las
  variables de `body.ds` **solo dentro de `.eva4-scope`** (clase en el `.page`).
  No tocar `portal.css` global: otras pantallas tienen colores fijos y se
  romperían.
- Verificar contraste ≥ 4.5:1 con el mismo script de la auditoría.

**No hacer:** modo oscuro global del portal en este plan.

## Fase 6 · Migración y corte

- Mientras se valida con los Delivery Managers: conservar la plantilla actual
  como `eva4_anterior.html`, accesible con `?vista=anterior`, **máximo 14 días**.
- Criterio de corte: dos Delivery Managers confirman que encuentran sus
  procesos y su balance sin ayuda y no hay errores nuevos.
- Al cortar: borrar `eva4_anterior.html`, el parámetro y su prueba. Reversión:
  `git revert` del commit del rediseño.

## Fase final · Verificación

1. `python -m pytest`, `ruff check`, `ruff format --check`, `mypy .`.
2. Actualizar y ampliar las pruebas:
   - Existentes que dependen del HTML: `tests/portal/test_eva4.py` (ids de las
     tablas, «EVA-04 Report»), `tests/portal/test_eva4_hours.py`
     (orden de los 15 encabezados, «Sin dato»), `tests/portal/test_views.py`.
   - Nuevas: un solo `<main>`; 15 `scope="col"`; `<caption>`; ausencia de
     «Sin dato»; textos de vacío distintos; fuente correcta en la nota.
3. Render con datos reales de octubre 2026 y comparar contra la pantalla
   actual: mismos 164 procesos, mismas cifras en las columnas numéricas.
4. Contraste ≥ 4.5:1 (texto normal) y 3:1 (texto grande) calculado sobre los
   colores finales.
5. Teclado: Tab recorre enlace de saltar → regreso → mes → buscador → tabla;
   el foco siempre es visible.
6. Lector de pantalla (prueba manual de una persona): se anuncian el título de
   la tabla, el encabezado de cada columna y el contador de resultados.
7. Volver a puntuar con `design-is`; objetivo ≥ 20/30 sin ningún 0 en #2, #4 ni
   #6 (el #9 depende del modo oscuro de la fase 5).

## Guardas generales

- No inventar clases: usar las de `portal.css` o declarar las nuevas en
  `eva4.css` con prefijo `eva4-`.
- No cambiar `apps/portal/services/eva4*.py` salvo la etiqueta de la fase 3.
- No dejar dos pantallas detrás de una bandera sin fecha de retiro.
