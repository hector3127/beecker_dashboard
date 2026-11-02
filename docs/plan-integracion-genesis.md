# Plan de integración de Dashboard Management en Genesis

Actualizado: 02/11/2026. Documento de entrada y traspaso entre desarrolladores.
Describe el estado observado y el trabajo pendiente; no autoriza despliegues,
cambios de reglas de negocio ni uso de datos de producción.

## Objetivo y alcance actual

Integrar Dashboard Management como módulo de Genesis conservando cifras,
filtros, exportaciones, permisos y trazabilidad. La aplicación independiente
seguirá siendo la referencia funcional mientras se trasladan las pantallas.

El usuario autorizó preparar y limpiar la versión estable del dashboard,
documentar el plan y publicar sus cambios confirmados en `origin/main`.
Todavía no se está implementando la integración en Genesis. El usuario
levantó Genesis localmente con datos de demostración para conocerlo primero.

Este documento prevalece sobre notas históricas que describan Genesis como
un repositorio todavía inaccesible o C de KPIs como sobrecosto. No sustituye
los AGENTS.md de cada repositorio ni cambia fórmulas aprobadas.

## Repositorios y flujo de trabajo

| Repositorio | Ruta local observada | Rama | Regla |
|---|---|---|---|
| Dashboard Management | `C:/beecker_dashboard` | `main` | Commits pequeños; push solo autorizado por usuario |
| Genesis | `C:/Genesis/genesis` | `Integracion_Dashboard_Management` | Rama creada desde UAT según Talin; PR hacia UAT |

Genesis se revisó en el commit `70299ea`. Antes de implementar se deben leer
sus `AGENTS.md`, `GOLDEN_PATH.md`, `docs/sdd.md` y `AZURE.md` y comprobar la
rama nuevamente. Su guía general menciona `features`; la reunión autorizó
la rama específica desde UAT. Confirmar con el equipo la política del PR.
Revisores indicados en la reunión: Talin y Ulises/Martín. No hacer push
directo a UAT/main de Genesis ni desplegar producción.

Los cambios locales de otro desarrollador no se revierten, reformatean ni
incluyen por accidente. No usar `git add .` ni publicar una mezcla sin revisión.

## Arquitectura comprobada

| Tema | Dashboard actual | Genesis | Trabajo necesario |
|---|---|---|---|
| Backend | Django 5.2.3, DRF 3.16.0, Python 3.12 | Mismas versiones de Django/DRF; Python 3.12 | Reutilizar servicios con adaptadores de configuración y errores |
| Frontend | Plantillas Django y módulos JS, sin compilación | React/Vite, Tailwind, Recharts, React Router | Adaptar vistas y eventos; conservar modelos puros de cálculo cuando proceda |
| HTTP | Cliente `apiGet` y `/api/v1/` | `frontend/src/services/apiClient.js`, sesión y CSRF | Servicio propio de módulo usando el cliente de Genesis |
| Módulos | 14 apps; servicios de dominio en apps/core | `ai_hub` y `lin` como apps separadas | Acordar paquete propio y prefijos, sin pegar otro proyecto settings/urls completo |
| Usuarios | Proveedor de capacidades y alcance intercambiable | Usuarios Django y roles específicos de Lin | Mapeo explícito; autenticación no equivale a autorización financiera |
| Datos | SQLite local y ORM con soporte PostgreSQL | PostgreSQL documentado en Azure; SQLite de desarrollo | Ensayar importación a PostgreSQL local antes de UAT |
| Trabajos | Comandos de sync, candados DB y algunos hilos locales | Runner `Job` con lease y reintentos | Adaptar extracciones; no depender solo de memoria/hilos del proceso web |
| IA | Adaptadores Claude propios | Proveedores centralizados en `ai_hub/llm/` | Usar esa frontera, preservar evidencia y medir tokens/tiempos |
| Apariencia | Diseño actual aprobado, CSP | Layout, navegación y ThemeProvider claro/oscuro | Usar tokens de Genesis sin modificar las reglas del producto |

Fuentes: `pyproject.toml`, `apps/portal/pages.py`, `apps/portal/api/`,
`apps/access/providers.py` y `apps/portal/services/executive_refresh.py`;
en Genesis, `Genesis/Genesis/urls.py`, `Genesis/Genesis/settings.py`,
`frontend/src/routes/LayoutRoutes.jsx`, `frontend/src/services/apiClient.js`,
`frontend/src/context/ThemeContext.jsx` y `Genesis/ai_hub/jobs/`.

El inventario estático completo de páginas y API está en
[inventario-integracion-genesis.md](inventario-integracion-genesis.md).
26 plantillas y 284 módulos JS fueron observados el 02/11; son una medida
del alcance, no una equivalencia entre archivos y pantallas por reescribir.

## Fuentes e integraciones que siguen siendo necesarias

| Integración | Uso vigente | Tratamiento para Genesis |
|---|---|---|
| Azure DevOps | Summary, S#/CR#, iteraciones, WI, riesgos, revisiones históricas | Conservar descarga/persistencia y contrato de IDs; configurar acceso de servicio |
| Clockify | Horas facturables/no facturables, tareas/tags, catálogos y control mensual | Conservar sync incremental e IDs; lectura local donde exista cobertura |
| Google Sheets | DataRevenue, bandas/tarifas, MPB, ROC y otros datos de módulos no sustituidos | Sigue siendo fuente; no borrar SDK ni hojas por haber migrado EVA1 |
| Google Drive | Archivos/carpetas/minutas en pestañas IA | Adaptar credenciales y almacenamiento solo al integrar esas funciones |
| Gmail | Funciones de correo vigentes | Conservar; pruebas sin envíos a destinatarios reales |
| Proveedor IA | Análisis, preguntas y sugerencias | Adaptador al proveedor de Genesis; no cambiar prompts ni modelos sin validación |
| Registro RPC interno | Funciones de dominio registradas y `warm_cache` | Conservar mientras haya consumidores; transporte HTTP de pruebas no se publica |

El módulo nuevo debe distinguir lecturas locales de refrescos externos.
No prometer funcionamiento completamente offline: hay rutas y operaciones
que todavía consultan o escriben en fuentes. Inventariar cada endpoint antes
de cambiar su mecanismo de carga.

## Datos actuales y destino

Medición de solo lectura, 02/11/2026. SQLite del dashboard:
`C:/beecker_dashboard/db.sqlite3`, aproximadamente 4.22 GB. Hay 31 tablas
propias datastore/portal, además de tablas administrativas Django.

| Grupo | Datos observados |
|---|---|
| Catálogos | 250 clientes, 293 personas, 1,614 proyectos |
| Clockify | 536,344 entradas; 28 registros mensuales entre 2024-08 y 2026-11 |
| Azure | 451 proyectos, 227,782 WI y 781,913 revisiones |
| Sheets | 14 copias locales de hojas |
| Extracciones | 17 corridas EVA |
| KPI DM | 10 periodos, 10 observaciones, 43 métricas por DM |

Estos conteos pueden aumentar al sincronizar; no son constantes del código.
El rango de meses no acredita por sí solo cobertura completa de cada mes.
La estructura combina relaciones normales con JSON de origen/cortes: no es
una base completamente normalizada ni se debe rediseñar toda al migrar.

Genesis separa usuarios/sesiones, procesos/chat/artefactos/trabajos en
`ai_hub`, y equipos/perfiles/bandas/evaluaciones/formación en `lin`.
Su documentación describe `genesis_uat_db` y `genesis_prod_db` en PostgreSQL
Azure. No se consultó su base remota ni se verificó su capacidad real.
Su SQLite local de demostración no contiene los datos productivos.

Propuesta pendiente de aprobación del equipo: tablas propias del dashboard
con prefijos y relaciones claras, usuarios compartidos de Genesis. No forzar
nuestros proyectos a ProcessAnalysis ni mezclar bandas de costos con las de
carrera de Lin sin acordar autoridad y vigencia.

La importación debe:

1. Partir de respaldo consistente y registrar fuente, fecha y versión.
2. Crear esquema en una base de prueba aislada, sin sobrescribir tablas de Genesis.
3. Importar por lotes preservando PK/FK, JSON, fechas, IDs y secuencias.
4. Comparar conteos, duplicados, integridad referencial, horas por mes/proyecto
   y facturabilidad; comprobar tipos, índices y planes de consultas grandes.
5. Preservar todos los periodos KPI cerrados y el enlace a su captura original.
6. Definir reversión con respaldo y versión de código antes de UAT.
7. No importar usuarios, sesiones ni cuentas demo encima de los de Genesis.

No copiar SQLite, .env, key.json, caché o respaldos dentro del repositorio
Genesis. No arrancar migraciones apuntando por accidente a una URL remota.

## Reglas funcionales que se conservan

- EVA1 activo usa inventario Summary Azure/Clockify local, con bloques S#/CR#
  independientes. Fechas desde iteraciones; Finish usa la última etapa fechada.
- Etapas activas por rango inclusivo al corte. Solapamientos muestran sus nombres.
  Suspendido requiere evidencia explícita Azure: RSP activo o RCP con situación
  Suspended; no inferir suspensión de huecos del calendario.
- Burn: horas facturables atribuidas al bloque según sus reglas. ETC=Budget−Burn;
  Desv. Hrs=min(ETC,0); avance=Burn/Budget×100 con faltantes explícitos.
- Horas sin tarea/tag de alcance: se atribuyen una sola vez al bloque que inició
  primero entre los elegibles. Empate queda pendiente. Nota visible en el receptor.
- T de EVA1/KPI: proyectos con desviación <=0 / TP. C de KPI DM es cumplimiento:
  proyectos con avance <=100 / TP; no volver a tratarlo como sobrecosto. Las
  tarjetas EVA conservan su regla propia vigente; verificar su contrato, no asumir
  que todos los contenedores llamados C comparten semántica.
- KPI DM lee sus tablas DmKpiPeriod/Observation/Metric, no recalcula al consultar.
  DMs globales, meses fijos, trimestres por promedio mensual, futuros sin dato.
- Enero–septiembre 2026 importados del reporte aprobado. Octubre cerrado con la
  captura existente del 29/10: TP9, T100%, C cumplimiento66.7%; dos filas DM
  intactas. No reconstruir esos meses con Azure actual.
- Automatización KPI y cierres EVA permanecen desactivados hasta acuerdo Genesis.
- EVA4 excluye AER y consulta el mes actual; conserva búsqueda, filtros y CSV.
  Paquete no aplicable se muestra N/A, nunca se inventan horas.
- Financiera sigue dependiendo de Sheets. Bandas: si falta la actual, usar por
  persona la última válida con tarifa positiva entre los meses anteriores del
  mismo año; no tomar futuros. Sin banda válida queda pendiente. Esta es la
  implementación actual; no afirmar cruce de año que todavía no está implementado.
- Conservar Horas por mes, exportaciones, regreso a cuenta, CSP y alcance limitado.

Fuentes adicionales: [EVA vigente](eva-inventario-activo.md),
[horas e histórico](historico-azure.md), [fuentes persistentes](fuentes-persistentes.md),
[KPIs persistidos](kpis-dm-persistidos.md), [reglas KPI](kpis-dm-reglas.md),
[cierre de fase 11](cierre-fase-11.md).

## Trabajo compartido y orden de ejecución

Asignar un responsable antes de empezar una fila. Estados válidos: pendiente,
en curso, bloqueado, revisión, terminado. No confundir planificación con evidencia.

| ID | Bloque | Estado inicial | Responsable | Depende de | Evidencia para terminar |
|---|---|---|---|---|---|
| G00 | Referencia funcional dashboard y limpieza | Terminado | Preparación 02/11 | — | Código 6b10ea0; pruebas abajo, CI global pendiente en G12 |
| G01 | Revisión de Genesis y arquitectura | Terminado, lectura | Revisión del 02/11 | — | Archivos y commit revisados descritos arriba |
| G02 | Arranque local Genesis | Confirmado por usuario | Usuario | G01 | Pantalla local con seed_demo; no equivale a gate aprobado |
| G03 | Definir permisos, destino DB y credenciales | Pendiente | Sin asignar | Equipo Genesis | Respuestas escritas, sin secretos en el documento |
| G04 | Piloto módulo y tabla EVA1 en React | Pendiente | Sin asignar | G00, G03 | Sesión, permisos, corte/filtros, cifras y error/reintento verificados |
| G05 | PostgreSQL local e importación de muestra | Pendiente | Sin asignar | G03 | Integridad y conteos comparados; sin tablas ajenas sobrescritas |
| G06 | Extracciones y refrescos como trabajos | Pendiente | Sin asignar | G04, G05 | Reintento, idempotencia, lease, reinicio y tiempos |
| G07 | EVA1/KPI DM y demás vistas operativas | Pendiente | Sin asignar | G04–G06 | Cortes/cierres, CSV, DMs globales, faltantes y carga móvil |
| G08 | Business Overview/Comercial/Financiera | Pendiente | Sin asignar | G04–G06 | Cifras por periodo/cuenta, costos, permisos y estados parciales |
| G09 | Detalle de proyecto y pestañas | Pendiente | Sin asignar | G04–G06 | Ejecutivo, Planeación, Esfuerzo, Recursos, RAID, Acciones, Cliente, Comunicación, Azure e IA por familia |
| G10 | Importación completa y ensayo de UAT | Pendiente | Sin asignar | G05, G07–G09 | Cierres intactos, conciliación, capacidad, carga y reversión |
| G11 | Gates Genesis y PR a UAT | Pendiente | Sin asignar | G10 | Gates sin bajar cobertura; revisores y evidencia |
| G12 | Consolidar CI legado del dashboard | Pendiente | Sin asignar | Dueños de tools/scripts | Corregir alcance de módulos y herramientas sin relajar reglas |

No trabajar simultáneamente sobre los mismos settings, rutas, modelos o
migraciones. Antes de empezar: revisar git status/log, el último PR y este
registro. Si dos personas trabajan a la vez, usar ramas de trabajo coordinadas
desde la integración y PRs pequeños según lo acuerde el equipo. No alternar
dos instalaciones con copias manuales de carpetas ni subir archivos de entorno.

Al finalizar cada turno, rellenar este bloque y actualizar la fila correspondiente:

| Campo de traspaso | Valor actual |
|---|---|
| Bloque realizado | Referencia funcional G00 validada; limpieza y plan compartido listos para publicación autorizada |
| Rama/repo | Dashboard main; Genesis sin implementación |
| Commit inicial de esta preparación | c68a256 |
| Referencia de código / limpieza | 6b10ea0 / 412b6b3; documentación y publicación identificadas por el commit de este archivo |
| Archivos/contratos modificados | Documentación, inventario y limpieza de archivos generados |
| Datos o migraciones aplicados | Ninguno en esta preparación |
| Pruebas ejecutadas | Ver registro de validación al finalizar G00 |
| Riesgos/bloqueos | Respuestas del equipo, CI legado G12 y cambios locales ajenos fuera de la publicación |
| Siguiente paso | Asignar G03; no comenzar la integración sin acordar su alcance |

## Información que debe confirmar el equipo Genesis

- Usuario de aplicación UAT y configuración de desarrollo, distintos del acceso a Repos.
- Destino de tablas y autorización de migraciones/importación, backup y reversión.
- Matriz de roles y alcance: financiera, tarifas, todo el portafolio o proyectos propios.
- Identidades de servicio y mecanismo de secretos para Azure, Clockify, Google e IA.
- Worker/programación de sync, salida de red, límites de API y capacidad de PostgreSQL.
- Revisores, política para esta rama y ventana de pruebas en UAT.

No se necesita acceso de escritura a producción para el piloto local.

## Limpieza y publicación de la referencia

Retirar únicamente exportaciones/logs generados comprobados sin consumidores.
Los archivos de tmp ya estaban ignorados pero algunos habían sido versionados:
se retiran del índice, conservando copias locales. No se borra la base, datos de
usuario, .cache, logs locales, graphify-out ni tmp/backups. Los fixtures de
pruebas y JSON de cálculos son código de verificación, no residuos.

El transporte RPC de pruebas y utilidades de migración con consumidores se
conservan; no se publican como API productiva ni se copian automáticamente a
Genesis. Cualquier retiro posterior exige rastrear consumidores y preservar
las pruebas funcionales. Ver [limpieza](limpieza-pre-genesis-2026-11-02.md).

Un push transmite código/documentación, no los datos SQLite ni el cierre de
octubre realizado localmente. Al importar datos se debe llevar ese cierre.
No confundir archivos ignorados presentes en el equipo con archivos publicados.

## Verificación y límites

Validar el SHA a publicar en copia aislada para no depender de cambios locales
sin commit de otro desarrollador. No afirmar suite completa por sumar corridas
parciales ni regenerar JSON/snapshots para hacer pasar diferencias.

Dashboard: pytest por capas, Node, Django check/makemigrations --check, Ruff y
mypy dirigidos, más navegador con rutas reales/CSP para flujos representativos.
No lanzar dos pytest con base al mismo tiempo ni activar sincronizaciones reales
durante pruebas. El entorno aislado usa configuración de prueba, sin secretos.

Genesis al implementar: gestores uv/pnpm y lockfiles propios, `make gate` y
`make verify` según su AGENTS.md; ningún gate de Genesis se ejecutó como parte
de esta revisión. No copiar nuestro venv ni sustituir sus settings globales.

Estimación orientativa, no compromiso: piloto 2–4 días hábiles; versión útil en
UAT 2–3 semanas; alcance completo 5–8 semanas con una persona dedicada, sujeto
a accesos, decisiones y resultados del piloto. Reestimar tras G04/G05.

### Registro de validación de G00

Validación realizada sobre una copia aislada del commit inicial, con las dos
correcciones de 6b10ea0. Se comprobó con git diff que apps/core/config/frontend/tests
coinciden con main; no se usan cambios pendientes ni credenciales del equipo.
Limpieza de salidas en 412b6b3, con copias locales y staged ajeno preservados.

| Comprobación | Resultado |
|---|---|
| `pytest tests --ignore=tests/e2e -q --no-cov` | 2,947 aprobadas en la repetición final de 60.44 s; primera corrida detectó un doble de prueba que construía el cliente real de Sheets; corregido sin cambiar el cálculo |
| `node --test tests/frontend/*.test.*` | 482 aprobadas en el código confirmado; el árbol local con bajas ajenas tiene un recuento distinto |
| `ruff check apps core config tests --exclude test_zz_*.py` | Aprobado |
| `ruff format --check` de los dos Python modificados | Aprobado |
| `mypy apps/portal/pages.py` | Aprobado; anotados los argumentos del guardado y su cobertura histórica no nula |
| Django `check`, `makemigrations --check --dry-run` | Aprobado; sin cambios de esquema, entorno aislado sin secretos |
| Chrome, 11 archivos e2e seleccionados | 176 aprobadas, un aviso staticfiles; no es toda la suite e2e. Incluye CSP y 18 pestañas × cinco tamaños |
| Enlaces de los tres documentos nuevos | Destinos relativos comprobados |
| collectstatic --dry-run --noinput | Aprobado en el entorno aislado, sin publicar archivos |

Límites conocidos: la corrida servidor reporta avisos existentes (directorio
staticfiles ausente y avisos de caché, entre otros); no se afirma cero avisos.
No se ejecutó toda la suite e2e ni se validó despliegue real en Azure.
No se mide cobertura nueva con --no-cov ni se afirma aprobado el piso de CI.

Auditoría adicional de los comandos globales del pipeline histórico:
`ruff check .` encuentra 52 errores en tools/migracion; `ruff format --check .`
encuentra seis herramientas antiguas sin formato. `mypy .` se detiene por
scripts/check_load.py descubierto como check_load y scripts.check_load. Los
comandos dirigidos de la aplicación sí pasan. No se relajan reglas ni se
modifican herramientas con cambios ajenos. Por tanto, esta publicación es una
referencia funcional verificada, no una declaración de CI global o fase 11
completos. La consolidación del pipeline legado queda explícitamente pendiente.

La publicación autorizada de esta preparación se identifica por el commit
que contiene este documento y se comprueba contra origin/main al finalizar.
El código funcional corresponde a 6b10ea0 y la limpieza a 412b6b3. Las bases
y sus cierres no viajan por Git. Logs locales de validación: tmp/stable-server-publish.txt,
tmp/stable-node.txt, tmp/stable-browser.txt, tmp/stable-ruff.txt y tmp/stable-mypy.txt.
El último contiene el primer diagnóstico de tipado; el reintento final de mypy
pages.py aprobó tras 6b10ea0. No trasladar esos logs a Genesis como datos.
