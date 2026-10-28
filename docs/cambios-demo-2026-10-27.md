# Seguimiento de acuerdos de la demo del 27 de octubre

Base de implementación: a187954. El usuario autoriza aplicar cambios de la
demo y después indica expresamente que PostgreSQL espere a Genesis y que
la importación de evaluaciones espere la plantilla oficial.

## Implementación del bloque

- Capacidad diaria: el nombre del recurso abre un desglose del mismo corte
  por proyecto/concepto y día. Disponible desde matriz y tarjetas; vuelve al
  mismo listado con filtros conservados. No modifica las fuentes, el rango
  Histórico/Azure de 834bbfa, jornada, totales, CSV ni permisos.
- Facturabilidad por recurso: filtro servidor por activos confirmados, bajas,
  sin confirmar o todo el histórico. La confirmación usa exclusivamente
  Bandas/rol del mes de corte. Ausencia de banda no equivale a baja ni a activo.
  Se mantienen porcentajes individuales y fórmulas; el promedio del equipo
  utiliza la población seleccionada. Los filtros de áreas repetidos se conservan.
- Plan de trabajo: tipos Plan de trabajo/Roadmap en la documentación de Cliente;
  enlaces visibles desde Planeación en AER/T&M e IXB/SaaS/RaaS. Solo HTTP(S),
  nueva pestaña y permisos de lectura/escritura existentes. IXS carga por apiGet,
  con consulta compartida y protección frente a lecturas posteriores a un guardado;
  AER utiliza sus documentos existentes, sin consultar el almacén de IXS.
- Manual: docs/manual-usuario.md es un borrador funcional para Wendy/Christian,
  con la separación entre horas planeadas y registradas, filtros, navegación,
  datos parciales, accesos y vínculos del plan.
- Carga concurrente: scripts/check_load.py permite solicitudes GET JSON locales
  acotadas, sin compartir cookies, seguir redirecciones ni usar proxies. Reporta
  éxito, errores, mediana y p95. No envía escrituras ni mensajes.

## Dependencias y asuntos que no se dan por completados

- PostgreSQL: diferido explícitamente hasta Genesis. Se conserva SQLite y
  la configuración de PostgreSQL existente; no se cambian .env ni conexiones.
- Plantillas de evaluaciones: diferidas explícitamente hasta recibir el formato
  oficial. No se crean importadores con columnas inventadas.
- Costos definitivos: requieren bandas/tarifas de RH. Se conservan los avisos
  parciales; no se inventan tarifas ni se ocultan proyectos incompletos.
- Fecha de paso a ROC: no se infiere de otra etapa. Hay que identificar una
  fuente histórica válida antes de incorporar el campo.
- Etiquetas Clockify: Alberto debe confirmar el catálogo. No se renombran
  actividades remotas ni se alteran agrupaciones para imponer categorías.
- Azure: sigue pendiente la credencial corporativa con acceso a los proyectos.
  No se sustituyen credenciales personales automáticamente.
- Listado completo de cuentas: ya existía; no se duplica.
- Manual: pendiente revisión de Wendy/Christian y validación de usuarios finales.
- Prueba concurrente con dobles: no sustituye una prueba de producción con
  usuarios reales ni valida capacidad de Genesis/PostgreSQL.

No se hace push ni se instala una programación de tareas. La incidencia #REF!
del histórico de Sheets sigue siendo un problema de origen independiente.

## Validación del 28/10/2026

- Servidor: `pytest tests/portal tests/core tests/access tests/datastore
  tests/clockify tests/capacidad -q --no-cov --tb=short`: 2101 aprobadas.
  Después, 38 dirigidas de herramienta de carga, plantilla y páginas de
  facturabilidad aprobadas; tienen solapamiento con la corrida anterior.
- `node --test tests/frontend/*.test.*`: 478 aprobadas.
- Chrome con rutas reales y CSP: `pytest tests/e2e/test_demo_requests.py
  tests/e2e/test_capacidad_diaria.py -k 'demo_requests or
  matrix_filters_resources_csv_and_refresh' --browser chromium
  --browser-channel chrome -q --no-cov --tb=short`: 15 aprobadas,
  10 deseleccionadas. Incluye 390, 900 y 1450 px, navegación de regreso,
  porcentajes individuales, filtros, CSV y enlaces de ambas familias.
- Capturas locales reproducibles en `tmp/demo-requests/`: capacity,
  personnel, aer-plan e ixs-plan por ancho. Inspección visual representativa:
  móvil de recurso/plantilla, tableta de capacidad, escritorio de plantilla
  y enlace de Planeación móvil. Línea base del diseño vigente: a187954.
  Las adiciones solicitadas cambian controles y geometría; no se regeneran
  referencias anteriores para ocultar diferencias. Se aplicó ui-ux-pro-max.
- Carga sintética del endpoint local de capacidad: 64/64 respuestas correctas,
  ocho conexiones, 17.34 s total, mediana 2.09 s y p95 2.285 s.
  Artefacto: `tmp/demo-requests/load.json`. Usa fuentes de prueba, sin
  escrituras ni consultas a proveedores reales; no mide producción.
- Ruff, mypy de pages.py y `manage.py check` aprobados. Los avisos de
  staticfiles corresponden a la preparación de pruebas sin collectstatic.

No se declara terminada la fase 11 por este bloque funcional.
