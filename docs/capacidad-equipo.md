# Capacidad instalada del equipo (30/10/2026)

Reglas que dio Christian; implementadas en
`apps/capacidad/services/team_capacity.py`. **La hoja Recursos ya no interviene**
en la pantalla `/capacidad-instalada/` ni en la tarjeta «Capacidad del equipo»
de Operativa (ambas leen este servicio).

## Fuentes y reglas

| Dato | Fuente |
|---|---|
| Personas | Hoja Bandas/rol: roles Dev, QA, ROC, Arq, BA y SM con banda vigente en el mes |
| Banda | Columna del mes; se excluyen vacía, Baja y NA |
| Cruce con Clockify | ID Clockify de Bandas/rol; sin ID, nombre normalizado |
| Horas | Registros de Clockify del mes guardados localmente (`ClockifyTimeEntry`): todos los proyectos, facturables o no y fines de semana; solo se excluye Comida (`61d5aa2596aafe5141cd7413`) |
| Delivery Manager y proyecto | Inventario Summary; respaldo MPB, Proyectos e Histórico; si falta, la pantalla dice «Sin Delivery Manager confirmado» |

Indicadores: capacidad base = personas × días hábiles (sin festivos de México)
× jornada (8 h, editable); saldo = base − registradas; utilización = registradas
÷ base. Las personas vigentes sin registros salen con 0 h.

## API y pantalla

- `GET /api/v1/screens/capacidad/diaria/?mes=AAAA-MM[&jornada=8]` devuelve en una
  sola lectura personas, filas persona × proyecto con horas por día, y resumen.
  Desaparece la lectura por proyecto (`.../diaria/proyecto/`).
- La jornada se recalcula en el navegador sin volver a leer. Filtros: texto,
  rol y banda; los indicadores son del mes completo. CSV de las filas visibles.
- Tarjeta de Operativa: `operational_sources.legacy_capacity` toma el mismo
  servicio (caché de 5 minutos). Ya no existe «Estimadas (Recursos)»; el
  medidor mide horas registradas ÷ capacidad base.

## Validación con datos locales (octubre 2026)

68 personas vigentes, 52 con horas, base 11,968 h (22 días × 8 h), 8,772.25 h
registradas, 3,195.75 h de saldo, 73.3 % de utilización y 14 personas sobre
jornada. La validación de Christian dio 68 y 52 (iguales) y 8,925.06 h: la
diferencia (152.81 h) es de sincronización; la base local de Clockify llegó
hasta el 28/10. No se ajustó nada para que coincidan.

## Pendiente

- `/operativa/capacidad-instalada/` (asignaciones mensuales) sigue leyendo
  Recursos; no se tocó. Decidir si también pasa a esta fuente.
- Las funciones RPC `capacidadInstaladaBase` y `...DatosProyecto` siguen
  registradas (la usan `/operativa/capacidad-instalada/` y pruebas).
- El texto del botón de proyecto y el rango por Histórico (834bbfa) quedaron
  obsoletos para esta pantalla.
