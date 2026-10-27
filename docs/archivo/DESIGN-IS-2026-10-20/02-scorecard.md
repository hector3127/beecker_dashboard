# 02 · Puntuación (Dieter Rams)

Reglas aplicadas: empate → el puntaje menor; se puntúa el peor caso, no el
promedio; sin pesos ni bonos.

1. **Innovador — 1/3**
   Evidencia: tablas y fichas estándar (`eva4.html:27-32`); copia el Excel con filtro de búsqueda.
   Justificación: imita un patrón común con pequeñas variaciones; no llega a «mejora clara».

2. **Útil — 2/3**
   Evidencia: la tabla de procesos da límite, horas y balance en una fila (`eva4.html:32`), pero hay que cruzar tres tablas y 15 columnas.
   Justificación: la tarea principal se cumple; las tablas adyacentes y las notas añaden pasos.

3. **Estético — 1/3**
   Evidencia: 12 tamaños de letra, 42 colores, más de 25 combinaciones de espaciado; degradado de tres colores en el banner.
   Justificación: no hay un sistema visible único (3 a 5 inconsistencias), aunque no hay ruido activo.

4. **Comprensible — 1/3**
   Evidencia: encabezados en inglés con títulos en español; «T M»; «Sin dato» (399 veces) sin distinguir el motivo; «Available Hours Package» sin explicación.
   Justificación: hay jerga y 2-3 elementos poco claros.

5. **Discreto — 1/3**
   Evidencia: banner con degradado y h1 de 36 px (`eva4.html:5,23`), cuatro fichas y 6 párrafos de notas antes del contenido.
   Justificación: la decoración y las notas compiten con los datos.

6. **Honesto — 1/3**
   Evidencia: «base Clockify del Sheet» y «08.Base Clockify 2026» (`eva4.html:32-33`) no describen de dónde salen hoy las horas; la nota de «coincidencia exacta de tarea» describe una regla ya cambiada.
   Justificación: dos o más textos no coinciden con el comportamiento; no hay patrones oscuros.

7. **Duradero — 2/3**
   Evidencia: degradado morado-rosa en el banner (`eva4.html:5`).
   Justificación: un marcador de moda; el resto (tabla, tipografía sobria) envejece bien.

8. **Cuidado hasta el último detalle — 1/3**
   Evidencia: sin estado de carga ni deshabilitado; 0 `scope` en 33 `th`; sin `<caption>`; 2 `<main>`; contraste 3.29:1 en el banner.
   Justificación: faltan estados y hay fallas de accesibilidad básicas; se puntúa el peor caso.

9. **Respetuoso con los recursos — 0/3**
   Evidencia: no hay `prefers-color-scheme` ni modo oscuro en ningún CSS del portal; carga fuentes externas. Sí respeta `prefers-reduced-motion` (`accessibility.css:31-37`), JS inicial ≈6 KB y 0 animaciones en reposo.
   Justificación: el anclaje da 0 cuando se ignora el modo oscuro; es una carencia de todo el portal, no solo de EVA-04.

10. **Lo menos diseño posible — 1/3**
    Evidencia: la ficha de totales, la tabla de clientes y la tarjeta de Operativa repiten los mismos conteos (`eva4.html:27-30`, `_eva4_card.html`); notas repetidas.
    Justificación: 3 a 5 elementos podrían quitarse sin romper la tarea.

## Total: **11 / 30**

| Principio | Puntaje |
|---|---|
| 1 Innovador | 1 |
| 2 Útil | 2 |
| 3 Estético | 1 |
| 4 Comprensible | 1 |
| 5 Discreto | 1 |
| 6 Honesto | 1 |
| 7 Duradero | 2 |
| 8 Detalle | 1 |
| 9 Recursos | 0 |
| 10 Mínimo | 1 |
