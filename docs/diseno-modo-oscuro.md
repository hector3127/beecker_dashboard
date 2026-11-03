# Modo oscuro del módulo en Genesis (tarea D6)

Medido el 02/11/2026 sobre `frontend/static/styles/` del dashboard. Este
documento define los tokens de color del módulo `dashboard_management` en
Genesis y cómo traducir cada color fijo al portar una pantalla. El diseño
claro actual es la referencia; el oscuro se deriva sin cambiar significados.

## Diagnóstico

- 68 hojas CSS, **5,885 usos de color y 3,339 valores distintos**. Casi todos
  son variantes mínimas de los mismos lilas y morados (`#eee8ff`, `#eee7ff`,
  `#ece8fa`…), escritos a mano en `pages/*.css`.
- `tokens.css` ya tiene unos 50 tokens, pero las páginas casi no los usan.
- Hojas con más colores: `project_detail_aer.css` (648 usos),
  `executive.css` (521), `project_detail_ixs.css` (477),
  `billability_area.css` (330), `commercial.css` (261).

Agrupados por función (mismo criterio que la tabla de traducción de abajo):

| Función | Usos | Distintos | Más usados |
|---|---|---|---|
| Tinte fuerte / borde suave | 1,245 | 662 | `#eee8ff`, `#eee7ff`, `#ece8fa`, `#eeeafa` |
| Marca (violeta) | 950 | 654 | `#4b25c9`, `#5925df`, `#6025e8`, `#5b3cff` |
| Tinte suave (fondo lila) | 722 | 221 | `#faf8ff`, `#faf7ff`, `#f0eaff`, `#f4f0ff` |
| Superficie (blanco) | 634 | 37 | `#fff`, `#fcfaff`, `#fbfaff` |
| Texto secundario | 598 | 428 | `#55537f`, `#4a4d86`, `#4a4872` |
| Texto fuerte | 412 | 285 | `#1b1a6b`, `#1b1a4a`, `#17134a`, `#14125e` |
| Marca suave | 253 | 192 | `#ded7ef`, `#7a4df0`, `#cfc4ff` |
| Sombra / overlay | 253 | 220 | `rgba(27,26,107,.05)`, `#5b36b00a` |
| Crítico / negativo | 247 | 186 | `#a31b33`, `#f23b54`, `#c0233e` |
| Positivo / verde | 230 | 181 | `#13693b`, `#17924b`, `#05ae7d` |
| Advertencia / ámbar | 190 | 159 | `#8a5600`, `#f3a800`, `#f2a900` |
| Borde / texto tenue | 102 | 81 | `#8a81b8`, `#8a80b3` |
| Acento rosa | 49 | 33 | `#ff3fa6`, `#f0489e` |

Conclusión: no se portan 3,339 colores. Cada pantalla se reescribe con
**unos 30 tokens semánticos**; las diferencias mínimas entre lilas se
unifican al token de su función.

## Cómo funciona el tema en Genesis

- `ThemeProvider` (`frontend/src/context/ThemeContext.jsx`) guarda `light`,
  `dark` o `system` en `genesis-theme` y pone la clase `.dark` y
  `data-theme` en `<html>`.
- `frontend/src/styles/theme.css` define las variables de Genesis para
  `:root` y `.dark` (`--background`, `--surface`, `--surface-2`,
  `--foreground`, `--muted-foreground`, `--border`, `--primary`, `--success`,
  `--warning`, `--destructive`, `--info`, `--chart-1..5`, `--shadow-*`) y las
  expone a Tailwind. Su regla: ningún componente declara hex.
- El módulo define sus propios tokens `--mg-*` en un CSS del módulo, bajo la
  clase raíz `.mg-root`, y los redefine bajo `.dark .mg-root`. Donde el
  significado coincide, apuntan a la variable de Genesis. No se toca
  `theme.css` ni el tema de Lin u otras pantallas.

## Tokens del módulo

Valor claro: el del diseño aprobado. Valor oscuro: alineado con `.dark` de
Genesis. `mix(x, n%)` significa `color-mix(in oklab, x n%, var(--surface))`.

| Token | Uso | Claro | Oscuro |
|---|---|---|---|
| `--mg-bg` | Fondo de página | `#f3f4fd` | `var(--background)` |
| `--mg-surface` | Tarjetas, tablas, paneles | `#ffffff` | `var(--surface)` |
| `--mg-surface-tint` | Fondos lila suaves (filas alternas, tarjetas suaves) | `#faf8ff` | `mix(var(--primary), 6%)` |
| `--mg-surface-tint-strong` | Chips, filtros, celdas destacadas | `#eee8ff` | `mix(var(--primary), 14%)` |
| `--mg-hover` | Fila o control en hover | `#f3eeff` | `mix(var(--primary), 18%)` |
| `--mg-th-bg` | Encabezado de tabla | `#f4f0ff` | `mix(var(--primary), 10%)` |
| `--mg-th-ink` | Texto de encabezado de tabla | `#4b3fa0` | `#c3b5ff` |
| `--mg-total-bg` | Fila de totales | `#efebff` | `mix(var(--primary), 16%)` |
| `--mg-border` | Bordes y divisores | `#e4e6f8` | `var(--border)` |
| `--mg-border-strong` | Bordes de controles | `#ded7ef` | `#343a58` |
| `--mg-ink-strong` | Cifras grandes, títulos fuertes | `#14125e` | `var(--foreground)` |
| `--mg-ink` | Texto normal | `#1b1a6b` | `#dfe1f0` |
| `--mg-title` | Títulos de sección | `#1b1a9e` | `#b9a8ff` |
| `--mg-muted` | Texto secundario | `#55537f` | `var(--muted-foreground)` |
| `--mg-soft` | Texto tenue, ayudas | `#8a81b8` | `#7a8099` |
| `--mg-brand` | Marca, enlaces, botones | `#4b25c9` | `var(--primary)` |
| `--mg-brand-strong` | Activo, foco, selección | `#6027ef` | `#a28bff` |
| `--mg-brand-soft` | Fondos de marca | `#ede7ff` | `mix(var(--primary), 22%)` |
| `--mg-good` | Texto positivo / cumplimiento | `#13693b` | `var(--success)` |
| `--mg-good-soft` | Fondo positivo | `#e3f6ec` | `mix(var(--success), 16%)` |
| `--mg-bad` | Texto negativo / sobrecosto | `#a31b33` | `var(--destructive)` |
| `--mg-bad-soft` | Fondo negativo | `#fbe3e7` | `mix(var(--destructive), 16%)` |
| `--mg-warn` | Texto de advertencia | `#8a5600` | `var(--warning)` |
| `--mg-warn-soft` | Fondo de advertencia | `#fff3d6` | `mix(var(--warning), 16%)` |
| `--mg-state-ok` | Semáforo en tiempo | `#1fa866` | `#3dd68c` |
| `--mg-state-risk` | Semáforo en riesgo | `#f5b31c` | `#f5b759` |
| `--mg-state-critical` | Semáforo crítico | `#f0455e` | `#ff6b6b` |
| `--mg-accent-pink` | Acento rosa (dona crítica, degradado) | `#ff3fa6` | `#ff6fbf` |
| `--mg-chart-1..5` | Series de gráfica en orden | `#6534df`, `#2d6be8`, `#1fa866`, `#f5b31c`, `#f0455e` | `#8b6bff`, `#6e9bff`, `#3dd68c`, `#f5b759`, `#ff6b6b` |
| `--mg-hero` | Degradado del encabezado | `linear-gradient(90deg, #5b3cff, #a02df0 55%, #ff3fa6)` | El mismo, con texto blanco |
| `--mg-shadow` | Sombra de tarjeta | `0 1px 3px rgba(27,26,107,.05)` | `var(--shadow-sm)` |

Los valores oscuros sin variable de Genesis son propuestas: se validan con
contraste AA (4.5:1 en texto normal, 3:1 en texto grande y semáforos) al
portar la primera pantalla (G6) y se corrigen aquí si no cumplen.

## Tabla de traducción al portar

Para cada color fijo de la hoja de la pantalla:

| Si el color es… | Usar |
|---|---|
| Blanco o casi blanco (luminosidad ≥ 99 %) | `--mg-surface` |
| Lila muy claro (≥ 95.5 %) | `--mg-surface-tint` (fondos) o `--mg-th-bg` (encabezados) |
| Lila claro (90–95.5 %) | `--mg-surface-tint-strong`, `--mg-border` o `--mg-hover` según dónde se use |
| Gris lila oscuro | `--mg-ink-strong` / `--mg-ink` (texto) |
| Gris lila medio | `--mg-muted` (texto) o `--mg-border-strong` (borde) |
| Gris lila claro | `--mg-soft` |
| Violeta saturado | `--mg-brand` o `--mg-brand-strong` |
| Violeta claro | `--mg-brand-soft` |
| Rojo | `--mg-bad` (texto), `--mg-bad-soft` (fondo), `--mg-state-critical` (semáforo) |
| Verde | `--mg-good`, `--mg-good-soft`, `--mg-state-ok` |
| Ámbar | `--mg-warn`, `--mg-warn-soft`, `--mg-state-risk` |
| Rosa | `--mg-accent-pink` |
| Transparencias (alfa < 0.6) | `--mg-shadow` o un `color-mix` del token de fondo |

Si un color no encaja, no se inventa un token nuevo en la pantalla: se agrega
aquí con su uso y sus dos valores.

## Reglas

- El modo claro debe verse igual que el diseño aprobado; las diferencias
  mínimas entre lilas desaparecen al unificar.
- Rojo, verde y ámbar conservan su significado (sobrecosto, cumplimiento,
  riesgo). Solo cambia el tono para que se lea en fondo oscuro.
- Gráficas: ejes, rejilla, leyendas y tooltips también usan tokens
  (`--mg-muted`, `--mg-border`, `--mg-surface`).
- Cubrir carga, vacío, error, hover, foco, diálogos y encabezados fijos.
- Las capturas o exportaciones PNG se generan en el tema activo y deben
  seguir legibles.
- Cambiar de tema no reinicia filtros ni cambia cifras.

## Aceptación por pantalla

Claro igual al aprobado; oscuro y sistema legibles con contraste AA; cuatro
anchos (1450, 1000, 768, 390) sin desborde horizontal; prueba Vitest que
monte la pantalla con `.dark` y compruebe que no quedan colores fijos en sus
estilos.
