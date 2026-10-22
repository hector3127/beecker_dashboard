# Conciliación de KPIs DMs — 22/10/2026

## Conclusión

No se está comparando el mismo indicador ni la misma población. Esto se confirma antes de revisar horas: para septiembre de 2026, el Excel reporta 9 proyectos y la reconstrucción con las hojas guardadas produce 30. Excluir AER/T&M reduce a 14, no a 9. No basta cambiar un formato o retirar un servicio para cuadrar.

No se han importado valores del Excel como reemplazo de las fuentes. No se han cambiado umbrales de cumplimiento T/C para forzar resultados.

## Evidencia del Excel

Archivo: `Copia de [Interno] GSE_OP_25-26.xlsx`, hoja `Indicadores PPT C-suite`.

- El encabezado de fechas B4=2025-12-01 y K4=2026-01-01 da el contexto dic-2025 / ene-sep-2026.
- El bloque mensual es A69:AE77; el trimestral es A81:J89.
- TP mensual está escrito como dato: por ejemplo AC71=2 (Brandon), AC72=5 (Alberto), AC73=2 (Patricio). No hay una fórmula COUNTIFS ni un enlace a IDs de proyectos que identifique esos nueve proyectos.
- T y C son ratios, no promedios de días ni consumo de horas. Por ejemplo AD72=2/AC72 y AE72=2/AC72, ambos 40%. El numerador 2 está escrito dentro de la fórmula; el archivo no identifica qué proyectos cumplen ni el criterio de cumplimiento.
- El total de septiembre AC77=SUM(AC71:AC75)=9, AD77=5/AC77 y AE77=5/AC77: 55.555...%, mostrado como 56%.
- El total de diciembre es 25, C=77%. Por eso la lámina muestra 25→9 y 77%→56%. Son extremos dic-2025/sept-2026, no el año actual hasta octubre.
- La suma de TP de enero E77=SUM(E71:E75) excluye a Miguel A. de la fila 76. Los seis DM suman 20, pero el total mostrado es 19. En febrero ocurre 20 frente a 19. Hay que confirmar si esa exclusión es intencional.
- Los trimestres usan AVERAGE por indicador, por ejemplo B83=AVERAGE(E71,H71,K71) y D83=AVERAGE(G71,J71,M71). El TP trimestral de Brandon es 6 en Q1, no su TP de marzo (4).
- El TP total Q1 es 18.333..., Q2 14.666... y Q3 10.333..., mostrados como 18, 15 y 10. No son sumas ni cantidad de proyectos únicos del trimestre.
- Algunas celdas están vacías intencionalmente (por ejemplo T/C de Enrique en Q3). No equivalen a cero.

## Evidencia de la aplicación

- KPIs usa MPB para contratos AER/T&M y Historico_Proyectos para los demás servicios; no utiliza la tabla reportada del Excel ni su pestaña Proyectos.
- Las fechas y estados determinan qué proyectos estaban vigentes al cierre de cada mes. Los contratos suspendidos se excluyen según el estado disponible, y el DM procede del catálogo actual, no de una historia de asignaciones por mes.
- TP cuenta esa población reconstruida.
- T es desviación promedio en días.
- C es promedio de consumo de horas facturables / presupuesto por proyecto, acotado a 100% antes del promedio. No es la proporción de proyectos que cumplen el costo.
- Las tarjetas de mejor/menor cumplimiento se elegían por proporción de proyectos con salud en tiempo, no por C. Se aclararon sus etiquetas sin cambiar los valores.
- El gráfico pinta ese C y comienza en enero. La lámina incluye diciembre del año anterior y porcentajes de cumplimiento distintos. Cambiar la escala del gráfico no resuelve la diferencia.
- Hay variantes de nombres (por ejemplo Gutiérrez/Gutierréz, Eduardo/Edhuardo) que separan filas de un mismo posible responsable. Las coincidencias de personas deben validarse antes de fusionar registros.

### TP: mismo mes, distinta población

| Mes | Excel (fila 77) | Web reconstruida | AER/T&M incluidos | Web sin AER/T&M |
|---|---:|---:|---:|---:|
| 2026-01 | 19 | 41 | 22 | 19 |
| 2026-02 | 19 | 32 | 17 | 15 |
| 2026-03 | 17 | 35 | 17 | 18 |
| 2026-04 | 17 | 32 | 17 | 15 |
| 2026-05 | 15 | 24 | 11 | 13 |
| 2026-06 | 12 | 25 | 12 | 13 |
| 2026-07 | 12 | 28 | 13 | 15 |
| 2026-08 | 10 | 26 | 12 | 14 |
| 2026-09 | 9 | 30 | 16 | 14 |

### Septiembre: población de la web por DM

| DM | TP |
|---|---:|
| Alberto Carlos Rodriguez Veloz | 13 |
| Brandon Daniel Sotelo Moreno | 10 |
| Enrique Yael Badillo Gutierréz | 1 |
| Jose Patricio Ochoa Garza | 6 |

El Excel muestra Brandon=2, Alberto=5 y Patricio=2. La diferencia no se limita a un responsable.

## Actualidad de las fuentes

La copia entregada no contiene las pestañas MPB ni Historico_Proyectos, que son las entradas de esta pantalla. Su pestaña Proyectos tiene 509 filas de datos y 501 IDs únicos (8 IDs repetidos); el catálogo Proyectos guardado por la aplicación tiene 176 filas incluyendo encabezado y otra estructura de columnas. Son catálogos de distinto alcance y no prueban por sí solos qué proyectos se usaron en el reporte guardado. Para confirmar igualdad de las fuentes de KPIs falta comparar las pestañas MPB/Histórico que alimentaron el reporte original.

Las hojas locales MPB e Historico_Proyectos estaban sincronizadas el 21/10/2026 a las 14:32 UTC al ejecutar esta auditoría. El Excel entregado es una copia del 22/10/2026. No se ha verificado que el contenido actual de Google Sheets sea idéntico a esa copia; la fecha de sincronización tampoco demuestra por sí sola la causa de las diferencias históricas.

## Ajustes realizados sin cambiar las reglas T/C

- KPIs DMs abre con periodo anual si no existe un periodo explícito en la URL.
- Histórico mensual y trimestral presentan subcolumnas TP/T/C.
- El histórico trimestral promedia los cortes mensuales y conserva la precisión antes de redondear TP para mostrarlo. Los meses sin fila no se convierten en ceros.
- Las unidades actuales T=días y C=consumo% quedan explícitas. Las tarjetas y el gráfico no se cambian por valores de la lámina.

## Información necesaria para cerrar la diferencia de negocio

1. Lista de IDs de los nueve proyectos considerados en septiembre en la lámina/Excel.
2. Regla que determina el numerador T y el numerador C para cada proyecto, incluyendo umbrales, estados, servicios y tratamiento de datos faltantes.
3. Confirmación de si los totales deben incluir a Miguel A. y qué nombres son alias de una misma persona.

Con eso se puede comparar inclusión/exclusión por ID y aplicar la fórmula correcta sin copiar valores reportados ni inventar criterios.

## Comparación de septiembre en las unidades actuales

| Indicador | Excel | Aplicación |
|---|---:|---:|
| TP | 9 | 30 |
| T | 55.6% | 5.9 días |
| C | 55.6% | 59.2% de consumo |

Que una celda contenga un valor fijo o un numerador literal no demuestra que una persona lo haya capturado manualmente: pudo provenir de otro cálculo o proceso. Lo comprobable es que esta copia no conserva la lista de IDs ni el criterio que generó los numeradores.
