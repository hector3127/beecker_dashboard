# 06 · Reevaluación tras las fases 1, 2, 3, 4 y 6

Fecha: 2026-10-20. Fase 5 (modo oscuro) **no se hizo**, por decisión del usuario.
Medido en la pantalla real (`/operativa/eva-4/?mes=2026-10`, datos de octubre
2026) con el navegador integrado, salvo lo marcado como no probado.

## Comparación de datos (pantalla anterior vs. nueva)

163 procesos en ambas. Las columnas de identidad, fechas y estado son idénticas, y
**todas las cifras (Average Limit, Invested Hours, Hours Balance) son iguales**.
Solo cambian los textos de los vacíos:

| Columna | Antes | Ahora | Filas |
|---|---|---|---|
| Average Limit | Sin dato | Sin límite para este servicio | 2 |
| Invested Hours | Sin dato | Sin coincidencia en Clockify | 35 |
| Hours Balance | Sin dato | — | 35 |
| Hours Package Limit y Available Hours Package | Sin dato | — | 163 y 163 |

## Mediciones

| Dato | Antes | Ahora |
|---|---|---|
| CSS en línea de la página | 5,218 bytes | 1,867 bytes (todo en `base.html`; el de EVA-04 está en `eva4.css`) |
| Tamaños de letra visibles | 12 | 7 (11.5 de `th` y 13 de `.crumb` vienen de `portal.css`) |
| Colores distintos (computados) | 42 | 15 |
| `<main>` | 2 | 1 |
| `th` con `scope` / `caption` | 0 de 33 / 0 | 15 de 15 / sí |
| "Sin dato" en la página | 399 | 0 |
| Orden del foco con teclado | — | saltar → logo → 3 enlaces del menú → regreso → mes → buscador → «Cómo se calcula» → tabla (enfocable para desplazarla) → «Por renovar» → «Servicios y estado por cliente» |
| Desbordamiento horizontal de la página | — | ninguno a 360, 768 y 1440 px |
| Columnas fijas en móvil | — | BOT ID (x=0) y Process Name (x=80) fijas; Service pasa por debajo |

Contrastes (texto normal ≥ 4.5:1): cuerpo 14.93, encabezados 7.45, notas 7.11,
«Sin …» 7.79, pastillas 5.46 / 6.17 / 5.58, saldo negativo 7.32, enlace de regreso
7.96, resúmenes 8.72. Banner (texto blanco sobre el degradado compartido): 5.94 en
el extremo morado, 5.09 a la mitad y 3.22 solo en el extremo rosa, donde no hay
texto; el título de 32 px es texto grande (mínimo 3:1).

Objetivos táctiles de EVA-04: 44 px o más (enlace de regreso 45, mes 44, buscador
44, resúmenes 44). El menú del portal mide 28 px; es del portal y no se tocó.

## Puntuación

| # | Principio | Antes | Ahora | Por qué |
|---|---|---|---|---|
| 1 | Innovador | 1 | 1 | Sigue siendo una tabla con filtro |
| 2 | Útil | 2 | 2 | En móvil la tabla queda debajo de encabezado, mes y buscador; empate → menor |
| 3 | Estético | 1 | 2 | Un solo sistema (`body.ds`); queda un par de colores documentado como excepción y 7 tamaños |
| 4 | Comprensible | 1 | 2 | Vacíos explicados y «Cómo se calcula»; «Hours Package Limit» y «Available Hours Package» solo se aclaran como «—» |
| 5 | Discreto | 1 | 2 | Notas reducidas a una plegable; el degradado compartido sigue |
| 6 | Honesto | 1 | 3 | Fuente por origen real; los conteos de «Sin …» coinciden con `unmatched_tasks` y `missing_limits` |
| 7 | Duradero | 2 | 2 | El degradado sigue (es el del portal) |
| 8 | Detalle | 1 | 2 | Estados, `scope`, `caption`, un `main` y foco ya están; **no se probó con lector de pantalla**, y por la regla de empate se queda en 2 |
| 9 | Recursos | 0 | 0 | Sin `prefers-color-scheme` (fase 5 no hecha) |
| 10 | Mínimo | 1 | 2 | Se quitaron las fichas duplicadas; queda la tabla de clientes plegada |

**Total: 18 / 30 (antes 11).**

## Veredicto sobre el objetivo del plan

El objetivo era ≥ 20/30 sin ceros en #2, #4 y #6: **no se alcanzó por 2 puntos**,
pero no hay ceros en esos tres. Quedan dos caminos:

1. **Fase 5 (modo oscuro solo en EVA-04)**: lleva #9 de 0 a 2 (el movimiento reducido
   ya se respeta y el JS inicial es de ≈ 6 KB) → **20/30**.
2. **Prueba con lector de pantalla** (la hace una persona): puede llevar #8 a 3 → 21/30.

## No probado

- Lector de pantalla.
- Pantalla con el estado de error visible (solo cubierto por tests).
- Rendimiento medido (tiempo hasta interactivo).
- Validación con Delivery Managers: el criterio de corte de la fase 6 sigue abierto.

## Corte de la pantalla anterior

Se puede ver con `?vista=anterior` **hasta el 2026-11-03** (14 días). Después el
parámetro se ignora. Para retirarla: borrar `ANTERIOR_HASTA` y `anterior_disponible()`
en `apps/portal/services/eva4.py`, la plantilla `eva4_anterior.html`, el parámetro en
`views.eva4` y las pruebas `test_anterior_*`.
Criterio: dos Delivery Managers confirman que encuentran sus procesos y su balance
sin ayuda.
