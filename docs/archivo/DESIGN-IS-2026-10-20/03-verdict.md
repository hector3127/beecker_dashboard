# 03 · Veredicto

## REDESIGN (11/30)

La capa de presentación de EVA-04 no pasa la auditoría (11 de 30; el umbral de
REFINE es 20), con 0 en «recursos» y 1 en «comprensible» y «honesto».

**Alcance honesto:** es el rediseño de **esta pantalla** (HTML, CSS y textos),
no del cálculo ni de la base de datos, que funcionan y se conservan. La pantalla
sirve para su tarea (puntaje 2 en «útil»); lo que falla es cómo se presenta y
lo que dice de sí misma.

Anti-patrón revisado: no se recomienda REDESIGN por «verse fea», sino porque
el total queda por debajo de 20 aplicando el criterio mecánico.

## Las 5 jugadas de mayor palanca

1. **Honesto (#6) y comprensible (#4): decir la verdad sobre la fuente y el motivo del vacío.**
   Cambiar «base Clockify del Sheet», «08.Base Clockify 2026» y la nota de «coincidencia exacta de tarea» por lo que ocurre hoy (horas de Clockify por ROC ID + número del BOT), y distinguir en la celda «0 horas», «servicio sin límite» y «sin coincidencia» en vez de 399 «Sin dato».
   Evidencia: `eva4.html:32-33`, `eva4.py:198`, 399 «Sin dato» en el render.
2. **Detalle (#8) y útil (#2): una tabla principal bien construida.**
   Poner la tabla de procesos primero, con `<caption>`, `scope="col"`, un solo `<main>`, encabezado fijo que funcione, un diseño móvil definido (por ejemplo, columnas clave fijas o tarjetas) y los estados de carga y deshabilitado.
   Evidencia: 0 de 33 `th` con `scope`, 2 `<main>` (`eva4.html:22`, `base.html:44`).
3. **Mínimo (#10) y discreto (#5): quitar lo repetido y reutilizar lo compartido.**
   Eliminar las fichas de totales duplicadas, reducir las 6 notas a un solo «Cómo se calcula» plegable y sustituir el banner propio `.eva4-banner` por el componente compartido `.pgh` del portal.
   Evidencia: `eva4.html:5,23,27-33`, `_eva4_card.html`.
4. **Estético (#3): usar el sistema de diseño que ya existe.**
   Reemplazar el CSS propio por las clases de `portal.css` (`body.ds`: tokens, `.card`, `.note`, `.err`, `.vacio`, tablas) y limitar lo que falte a 6 tamaños de letra.
   Evidencia: 12 tamaños, 42 colores, más de 25 espaciados.
5. **Recursos (#9): respetar el modo oscuro.**
   Añadir `prefers-color-scheme` (el movimiento reducido ya se respeta) y evaluar servir la fuente desde el propio sitio en vez de Google Fonts. Es una carencia de todo el portal.
   Evidencia: sin `prefers-color-scheme` en ningún CSS; `base.html:8-9`.

Corrección pendiente aunque no se rediseñe: el contraste del texto blanco sobre
el rosa del degradado (3.29:1) y la etiqueta «T M».
