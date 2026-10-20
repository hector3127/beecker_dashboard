# 04 · Prompt para `/make-plan`

````
/make-plan Redesign la pantalla EVA-04 Report (/operativa/eva-4/). El diseño actual falló la auditoría de Dieter Rams con 11/30, con puntajes críticos en los principios #9 (0), #4 (1), #6 (1), #8 (1), #3 (1), #5 (1) y #10 (1).

Veredicto (citado de 03-verdict.md):
> La capa de presentación de EVA-04 no pasa la auditoría (11/30; el umbral para refinar es 20); se rediseña la pantalla (HTML, CSS y textos), no el cálculo ni la base de datos.

Por qué rediseñar y no refinar: el total queda por debajo de 20 y la pantalla dice cosas falsas sobre su fuente (#6) y no se entiende por sí sola (#4); las correcciones tocan estructura, jerarquía y sistema visual a la vez.

Conservar del diseño actual:
- Los 15 encabezados de la tabla de procesos, en este orden y en inglés, igual que el Excel: Delivery Manager, Country, Client, BOT ID, Service, Process Name, Status ROC, Start, Finish, Average Limit, Invested Hours, Hours Balance, Hours Package Limit, Available Hours Package, Risk (apps/portal/templates/portal/eva4.html:32).
- La lógica de datos: Average Limit por servicio (ROC 30, AER 160, RaaS 40, SaaS 80, T&M 160), Invested Hours por ROC ID + número del BOT, BOT ID mostrado solo como número y Process Name con el nombre completo (apps/portal/services/eva4.py, eva4_hours.py).
- El selector de mes, el filtro de búsqueda, el enlace de regreso a Operativa y el enlace para saltar al contenido (apps/portal/static/portal/css/accessibility.css:2-12) con su contorno de foco de 3 px (líneas 13-16).
- Los tokens de marca: morado #5827dc, #241568 para texto y la fuente Plus Jakarta Sans.

Descartar:
- El banner propio `.eva4-banner` con h1 de 36 px (eva4.html:5,23), duplicado del componente compartido `.pgh` de portal.css. Se sustituye por `.pgh data-tone="operations"` (como EVA 1).
- Las fichas de totales y la tabla de clientes duplicadas con la tarjeta de Operativa (eva4.html:27-30, _eva4_card.html). Falló #10.
- La pila de 6 párrafos de notas antes de los datos (eva4.html:29-33). Falló #5 y #6.
- El CSS por página en {% block css %} con 12 tamaños de letra, 42 colores y más de 25 espaciados (eva4.html:4-20). Falló #3.
- Los textos «base Clockify del Sheet», «08.Base Clockify 2026» y «coincidencia exacta de tarea», que ya no describen el comportamiento (eva4.html:32-33, eva4.py:198). Falló #6.

Las 5 jugadas de la auditoría (verbatim):
1. Honesto (#6) y comprensible (#4): decir la verdad sobre la fuente y distinguir «0 horas», «servicio sin límite» y «sin coincidencia» en vez de 399 «Sin dato». Evidencia: eva4.html:32-33, eva4.py:198.
2. Detalle (#8) y útil (#2): tabla principal primero, con <caption>, scope="col", un solo <main>, encabezado fijo que funcione, diseño móvil definido y estados de carga y deshabilitado. Evidencia: 0 de 33 th con scope; 2 <main> (eva4.html:22, base.html:44).
3. Mínimo (#10) y discreto (#5): quitar fichas duplicadas, reducir las notas a un «Cómo se calcula» plegable y reemplazar el banner por un encabezado sobrio. Evidencia: eva4.html:5,23,27-33.
4. Estético (#3): usar el sistema de diseño de portal.css (body.ds) en vez de CSS propio; máximo 6 tamaños de letra. Evidencia: 12 tamaños, 42 colores, 25+ espaciados.
5. Recursos (#9): respetar prefers-color-scheme (reduced-motion ya existe en accessibility.css:31-37); evaluar servir la fuente desde el propio sitio. Evidencia: sin prefers-color-scheme en ningún CSS; base.html:8-9.

Principios de rediseño, en orden de prioridad:
1. Honesto (#6) — cada texto, etiqueta y celda vacía corresponde 1:1 con lo que hace el sistema.
2. Comprensible (#4) — un usuario nuevo nombra cada control y cada columna sin ayuda; un solo idioma coherente salvo los encabezados del Excel.
3. Lo menos diseño posible (#10) — si se quita un elemento, la tarea se rompe.

Entregables del plan:
- Nueva arquitectura de la pantalla (no derivada de la anterior): qué va primero y qué se pliega.
- Flujo principal en baja fidelidad, comparado lado a lado con el actual.
- Lista de estados: vacío, cargando, error, éxito, foco, deshabilitado.
- Tokens: escala de letra (máx. 6), espaciado y paleta; reglas de modo oscuro y movimiento reducido.
- Diseño para móvil y escritorio de la tabla de 15 columnas.
- Ruta de migración: cómo se despliega sin perder la pantalla actual hasta validarla con Delivery Managers.
- Criterios de corte: cuándo se retira la pantalla anterior.
- Verificación: render con datos reales de octubre 2026, comprobación de contraste ≥ 4.5:1, prueba con teclado y con lector de pantalla.

Antipatrones a evitar (propios de REDESIGN):
- Portar la estructura anterior con otro estilo.
- Mantener las dos pantallas detrás de una bandera indefinidamente.
- Rediseñar siguiendo una moda y no estos principios.
- Cambiar los encabezados, el cálculo de horas o los límites por servicio.
````
