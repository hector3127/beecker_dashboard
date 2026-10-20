# Revisión de comentarios de pantallas

## Conservado

El encabezado comercial y la metodología de facturabilidad se mantienen. Los montos de etapas y cuentas ya usaban el formateador sin US/USD por importe; no se modificó ese comportamiento. Los filtros, las fuentes y las fórmulas financieras no se alteraron.

## Cambios

- Cuentas con más oportunidades abiertas: orden por cantidad de registros abiertos, no por importe.
- Carga comercial prevista por mes: horas agrupadas por fecha de cierre de Backlog_Proyectos.
- Oportunidades de alta probabilidad: 70% o más, sin firma; oportunidades en desarrollo: probabilidad menor a 70%. Los nombres reemplazan los títulos repetidos Pipeline.
- La matriz Servicio / cuentas se despliega por servicio y conserva todas sus cuentas. Las cifras son horas, no toneladas ni importes monetarios. Ya no se abrevia la capacidad con el formateador monetario K/M. El total incluye todos los servicios y cuentas, aunque los desplegables estén cerrados; antes solo se veían diez filas paginadas mientras el total abarcaba todas.
- Resumen operativo pasa a Resumen; Por Delivery Manager a Delivery manager. Se elimina el contador redundante de managers.
- Etiquetas principales de operaciones, margen bruto y cobranza en español. Los códigos de origen y términos técnicos como ETC, FTE, booking y Delivery manager no se cambian.

## Salud del portafolio: trazabilidad

La población proviene de load_eva2 (IxB/RaaS/SaaS, Histórico_Proyectos) y load_eva1 (AER/TYM, MPB). views.py convierte sus resultados con operational_sources.eva_projects y aplica filter_projects por servicio y cuenta antes de resumir. No es una constante ni depende de cuántas tarjetas se ven en el carrusel.

portfolio_summary.select_in_progress selecciona status_category=Activo; summarize_portfolio cuenta esos activos como denominador y count_health los de health=A tiempo como numerador. Se calcula 100 × en tiempo / activos, redondeado al entero. Los suspendidos (En Pausa) se cuentan aparte y no entran al denominador. Sí cambia al cambiar la población y los filtros.

eva_projects marca Crítica si hay sobreconsumo (burn>budget, con presupuesto positivo) o fecha vencida (días restantes<0); En Riesgo si faltan fechas o quedan hasta 30 días y como máximo 10% de horas disponibles; A tiempo en los demás casos. Mientras faltan consumos, las plantillas ocultan el porcentaje definitivo. Los presupuestos, horas y fechas se toman de los cargadores EVA y Clockify; no se sustituyen por los números ilustrativos de los comentarios.

La pregunta abierta sobre facturabilidad no constituye una solicitud de cambiar su fórmula, por lo que se conserva.
