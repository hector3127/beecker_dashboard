# Revisión del dashboard y primera mejora

Fecha: 13 de octubre de 2026. Alcance: análisis del código disponible y
primera implementación sobre Operativa y la base común del portal.
Se conservaron los cambios locales que ya existían al comenzar.

## 1. Cómo funciona el proyecto

- `config/urls.py` expone Ejecutiva, Operativa y Comercial en la raíz,
  el panel anterior en `/legacy/`, los RPC en `/api/`, Gmail y Django admin.
- `apps/portal/views.py` coordina los servicios y renderiza las páginas.
  Las vistas de detalle conservan enlaces a proyectos, cuentas y managers.
- Google Sheets contiene los datos de negocio: Proyectos, MPB,
  Recursos, Bandas/rol, históricos y Backlog_Proyectos, entre otras hojas.
- Clockify aporta registros de horas; Azure DevOps aporta etapas,
  tareas y riesgos. Los servicios ya usan caché y pruebas de paridad.
- SQLite guarda usuarios y sesiones. No se encontró evidencia de que
  índices de SQLite o `select_related()` aceleren los indicadores de negocio.
- Operativa abre un corte en caché sin esperar integraciones. El navegador
  consulta `/operativa/datos/`, luego inversión, capacidad y EVA 3 mediante
  la misma ruta y el parámetro `bloque`. Facturabilidad carga de forma
  independiente desde `/operations/resumen/`.
- Ejecutiva utiliza el portafolio calculado para decisiones, horas y cuentas.
  Aún contiene cifras financieras y comerciales estáticas marcadas
  «Ejemplo». Comercial sí lee Backlog_Proyectos: la tabla del README que
  la describe como ejemplo está desactualizada.

No se modificaron modelos, autenticación, rutas, RPC, escrituras a Sheets,
reglas de facturabilidad ni cálculos de horas. La comprobación del navegador
utilizó exclusivamente fixtures locales, nunca credenciales del negocio.

## 2. Problemas, prioridad y riesgo

| Prioridad | Evidencia e impacto | Acción | Riesgo |
| --- | --- | --- | --- |
| Alta | La sustitución de `.pg` descartaba facturabilidad si su petición terminaba antes. | Conservar el nodo vivo al renovar el portafolio. Implementado. | Medio: JavaScript |
| Alta | HTTP 200 con errores de fuentes se anunciaba como «Datos actualizados». El corte guardado ocultaba el motivo del fallo. | Señalizar fuentes y bloques incompletos, conservar el corte y permitir reintento. Implementado. | Medio: vistas/caché |
| Alta | EVA 3 renovaba managers, pero dejaba totales y dona del corte inicial. Además, reemplazar todas las tarjetas podía deshacer la inversión recién cargada. | Actualizar las tres métricas, salud, managers y EVA por sus IDs, manteniendo inversión independiente. Implementado. | Medio: JavaScript |
| Alta | «Totales operados» mostraba activos; «En costo» era consumo de horas; el trimestre parecía un filtro aunque no recortaba la población. | Etiquetas, fórmulas, ámbito de filtros y trimestre de referencia. Implementado en Operativa. | Bajo |
| Alta | La caché del portafolio reconstruía `loaded_at` en cada lectura, simulando una actualización. | Guardar el resultado con su fecha de cálculo. Implementado; los valores antiguos de caché se recalculan una vez. | Medio: formato interno de caché |
| Alta | La población EVA convierte fechas, avance y horas ausentes a cero; `delay_days` representa días restantes en esta población. | Se corrigió su etiqueta en Operativa. Preservar nulos y armonizar reglas entre vistas requiere otra etapa con pruebas de paridad. | Medio/alto: semántica de negocio |
| Alta | Ejecutiva presenta ejemplos antes de decisiones reales. | Priorizar decisiones y separar visualmente ejemplos hasta disponer de fuentes financieras validadas. Pendiente; no se inventaron importes ni comparativos. | Bajo en presentación; medio al conectar datos |
| Media | Cada bloque devuelve una página completa y repite renderizado. | Reutilizar estas mismas rutas para devolver fragmentos delimitados, después de medir bytes y tiempo por fase. Pendiente. | Medio: contrato de respuesta |
| Media | El resumen de Operativa comparte un diccionario de caché entre peticiones; leer-modificar-escribir no es atómico. Inversión y capacidad usan claves globales durante 24 h. | Separar almacenamiento por bloque y período, con procedencia/fecha. Pendiente; no se introdujo Redis sin mediciones. | Medio |
| Media | Los filtros navegan y recargan la página; seleccionar cuenta abre un detalle en lugar de filtrar. | Se hizo explícita la navegación y se añadió limpiar filtros. La actualización asíncrona de filtros sigue pendiente. | Medio |
| Media | CSS repetido, HTML en líneas extensas y estilos fijos complican mantenimiento y móvil. | Se extrajo JavaScript y se añadieron estilos acotados para navegación, tarjetas, EVA, salud y facturabilidad. Unificar los demás templates requiere revisión por pantalla. | Bajo/medio |
| Media | Falta trazabilidad visual de cuándo se leyó cada integración; un corte calculado puede incluir fuentes en caché. | El mensaje final lo aclara. Añadir fecha por fuente requiere soporte de los loaders. Pendiente. | Medio |
| Baja | SVG y tablas de otras vistas necesitan revisión de teclado, descripciones y datos equivalentes. | Añadidos foco visible, enlace de salto, landmark principal y títulos a barras del resumen. Auditoría completa pendiente. | Bajo |

## 3. Datos, métricas y KPIs

| Elemento actual | Clasificación | Interpretación y acción |
| --- | --- | --- |
| Nombre, cuenta, manager, servicio y fechas | Datos | Describen el proyecto; permiten abrir su detalle. |
| Proyectos activos/suspendidos | Métricas de volumen/estado | Muestran carga operativa; no evalúan por sí solos un objetivo. |
| Horas de inversión operativa/comercial | Métricas de consumo | No son dinero ni una variación contra el trimestre anterior. Las tarjetas cubren los proyectos IXB/RaaS activos consultados. |
| Consumo ÷ presupuesto de horas | Métrica de consumo del presupuesto | No equivale a entregables completados, cumplimiento de costo financiero o margen. Un aumento no es automáticamente positivo. |
| Días restantes hasta término/renovación | Métrica temporal | Negativos indican fecha vencida. En EVA 1/2 la tarjeta usa la desviación de su fuente; EVA 3 usa renovación. Los nulos convertidos a cero en la población operativa siguen pendientes de corregir. |
| Proyectos en tiempo ÷ activos | Indicador de desempeño del portafolio | Puede ser KPI con objetivo y reglas de salud acordadas; no se añadió una meta inexistente. Sin proyectos activos se muestra «—». |
| Facturabilidad global contra meta existente de 70% | KPI de utilización facturable | La comparación está en puntos porcentuales contra la meta, no es tendencia. Permite consultar especialidad/recurso para investigar el desvío. |
| Históricos de KPIs de managers | Indicadores reconstruidos | El responsable y riesgos disponibles pueden corresponder al presente; no deben presentarse como snapshots históricos exactos. |
| Finanzas de ejemplo de Ejecutiva | Datos demostrativos | No permiten decisiones financieras ni tendencias reales. |

La salud de Operativa usa las reglas existentes: crítico si excede horas
o fecha; en riesgo si falta fecha o si quedan como máximo 30 días y
como máximo 10% del presupuesto de horas; excluye suspendidos.
No se cambió esta regla para armonizarla con el panel anterior.

## 4. Archivos de esta implementación

| Archivo | Cambio | Motivo |
| --- | --- | --- |
| `apps/portal/views.py` | Errores de fuentes y bloques se comunican sin reemplazar cortes válidos; respuesta EVA 3 conserva el estado previo si falla. | Evitar falso éxito y pérdida de datos disponibles. |
| `apps/portal/services/portfolio_loader.py` | La caché conserva `PortfolioLoad`, incluida la fecha de cálculo. | Evitar fechas engañosas y mantener una lectura sin consultas adicionales. |
| `apps/portal/templates/portal/base.html` | Landmark, salto al contenido, navegación activa accesible y estado de actualización. | Acceso por teclado y claridad sobre disponibilidad. |
| `apps/portal/templates/portal/operativa.html` | Contenedores estables, botón de actualización, advertencias, etiquetas y contexto; fallback sin JavaScript. | Actualizaciones independientes y comprensión de las cifras. |
| `apps/portal/templates/portal/_operations_summary.html` | Marcador de estado parcial y títulos SVG por barra. | Comunicar errores y valores del gráfico. |
| `apps/portal/static/portal/js/operativa.js` | Coordinación modular, validación de respuesta, timeout, preservación de facturabilidad y reintentos. | Evitar condiciones de carrera en la interfaz sin añadir dependencias. |
| `apps/portal/static/portal/css/accessibility.css` | Foco, navegación móvil y movimiento reducido. | Accesibilidad común. |
| `apps/portal/static/portal/css/operativa.css` | Reorganización por ancho de pantalla y estilos de estados. | Mantener legibilidad en móvil. |
| `tests/portal/test_dashboard_refresh.py` | Regresiones de fuentes, cortes, estado inicial y fecha. | Proteger comportamiento de riesgo medio. |
| `tests/frontend/operativa.test.cjs` | Orden de respuestas, errores, redirección y reintentos con Node nativo. | Proteger condiciones de carrera sin instalar librerías. |
| `tests/portal/test_views.py` | Ajuste de la comprobación de carga diferida al script externo. | Preservar la verificación del contrato existente. |

## 5. Validación y límites

- La suite completa final pasó con **1,080 pruebas y 90.91% de cobertura**,
  por encima del mínimo de 80%, incluidos los casos de inversión y
  capacidad incompletas.
- Cinco pruebas Node cubren la respuesta de facturabilidad antes y después
  del portafolio, inversión independiente de EVA, errores parciales,
  redirección a login y protección contra clics repetidos.
- Comprobación visual de Operativa con fixtures locales en escritorio,
  tablet y móvil; medición de ancho del DOM para detectar overflow.
- Ruff y mypy pasan sobre los tres archivos Python de esta etapa.
  `manage.py check --settings=config.settings.test` no reporta problemas.
- No se midieron tiempos ni volumen reales de Sheets, Clockify o Azure;
  no se afirma una reducción numérica del tiempo de carga. La apertura
  conserva el comportamiento de caché sin integraciones y el beneficio
  inmediato es evitar pérdida de componentes y mensajes incorrectos.
- Continúan las advertencias existentes de pruebas porque `staticfiles/`
  no se ha generado en este checkout. El servidor local de revisión sirve
  los assets desde las aplicaciones. El despliegue necesita su paso normal
  de `collectstatic` para los archivos nuevos.
- No se desplegó ni se creó un commit.

Siguiente etapa técnica: medir por integración, resolver nulos y períodos
de caché, revisar la consistencia de indicadores entre páginas y mejorar
la jerarquía de Ejecutiva sobre fuentes reales.
