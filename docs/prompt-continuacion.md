# Mensaje para continuar la migración

Pega esto tal cual en la sesión nueva (Codex o Claude Code):

---

Continúa la migración del frontend de Beecker en `C:\beecker_dashboard`.

**Antes de tocar nada**
1. Lee `AGENTS.md`, `docs/estado-traspaso.md` y `docs/plan-migracion-frontend.md`.
2. Revisa Git: debes estar en `main`; comprueba los últimos commits y la
   diferencia con `origin/main`. El último bloque local separa las operaciones
   por API de Planeación AER; el anterior completó Acciones AER/IXS.
   Claude completó Cliente y el Centro
   de Comunicación IXB/SaaS/RaaS (posterior al glosario
   `b1ca4b4`). No hagas push
   salvo que te lo pida expresamente.
3. Conserva sin comitear ni modificar lo que no es tuyo:
   `tools/migracion/inline2css.py`, `tools/migracion/migrate_page.py`,
   `shots_tmp/` y los cuatro `tests/e2e/test_zz_*.py`. Al comitear agrega
   archivos por nombre, nunca `git add tests` ni `git add .`.

**Reglas que no se negocian** (están en `AGENTS.md`)
- Diseño idéntico al anterior; compara cada cambio contra `?vista=anterior`
  (cajas y estilos calculados a 1450/900/390 px) y no cambies cálculos ni reglas
  de negocio.
- No actives `ACCESS_ENFORCED`; no toques Horas por mes (`cuenta/<slug>/horas/`).
- Commits pequeños directo en `main`, con pruebas y plan/traspaso actualizados con
  evidencia real. La fase 10 (detalle del proyecto) sigue **parcial**: no la
  marques terminada, no retires `gas_shim.js` ni `proyecto_detalle.js`.

**Patrón ya establecido para una pestaña del detalle** (mira
`sections/raid*.js`, `milestones*.js` y `communique*.js` como ejemplo)
1. Endpoints en `apps/portal/api/project_detail.py` y `urls.py` que llaman, sin
   cambiarlos, a los servicios del RPC; lecturas con `view_operations`,
   escrituras con `edit_operations` + alcance total + CSRF (o la capacidad que
   marque `apps/access/rpc_policy.py`). Importa el módulo (`from apps.x import y`)
   para poder hacer monkeypatch en las pruebas.
2. Métodos en `project_detail/data.js`, y modelo / vista (DOM con `el()`, nunca
   `innerHTML` con datos) / controlador en `project_detail/sections/`, registrado
   en `main.js` como `window.bee…`. El script anterior delega si el módulo existe
   y conserva su código para `?vista=anterior`.
3. CSS externo en `frontend/static/styles/pages/` y enlazado en
   `frontend/templates/pages/project_detail.html` (sube la versión `?v=` del script).
4. Pruebas: API en `tests/portal/`, comparación vieja-vs-nueva en `tests/e2e/`
   (copia el estilo de `test_ixs_raid.py` / `test_ixs_raid_create.py`), Node en
   `tests/frontend/` contrastando contra las funciones originales.

**Avance posterior:** Azure DevOps ya carga y actualiza por API v1, con
`sections/ixs_azure{,_model,_loading}.js`. Las agrupaciones por persona/iteración
y etapa, búsqueda y ventanas de detalle también son modulares en
`ixs_azure_groups{,_model,_view}.js`. El resumen, indicadores, atención,
carga y fechas usan `ixs_azure_summary{,_model,_view}.js`. La pestaña completa
usa `ixs_azure_tab*.js`, el modelo de filtros `ixs_azure_table_model.js` y los
controles/acciones compartidos con Planeación. Azure sí está migrada; la fase
10 sigue parcial. Los seis errores antiguos de mypy los corrigió Claude en
`c82b6d0`; la revisión posterior pasó sin errores de tipos.

**IA completada:** `project_ai.py` conserva servicios y permisos originales;
fuentes/historial/Drive y las acciones usan API. `ixs_ai_model.js` conserva
contexto/snapshot/cambios/capacidad; `ixs_ai_view.js`, `ixs_ai_panels_view.js`
y `ixs_ai_controller.js` presentan la pestaña y sus formularios con DOM seguro
y eventos externos. Comparados con la anterior en tres tamaños. No consultar
modelos o servicios reales durante las pruebas. Fase 10 todavía parcial.

**Cliente completo:** `client{,_model,_view}.js` y API `project_client.py` en
ambas familias. **Centro de Comunicación completo:** `bee_com{,_model,_view}.js`
y API v1 para IXS. Revisión directa: 94 e2e, 26 API y siete Node aprobadas.
`ixs_client_actions.js` mantiene la caché compartida de IXB.

**Acciones completada (ambas familias):** `actions_model.js` separa el resumen; `actions.js` usa
lecturas y siete mutaciones de API v1 (`project_actions.py`) para ambas familias.
`actions_view.js` presenta tablas, búsqueda y formularios con DOM seguro/eventos
externos. Las comparaciones cubren estados y formularios a 1450/900/390 px.
Conserva los puentes de entrada/estado y el fallback anterior.

**Planeación AER parcial:** `project_aer_planning.py` expone ocho POST explícitos
en `screens/proyectos/<id>/planeacion-aer/<operacion>/`; `aer_planning.js` separa
guardado, cierre/estado, vacaciones, importación y borrado simple/por lote.
Conserva confirmación de sobreasignación, confirmación física del borrado por
lote, borradores al reintentar y protección frente a respuestas antiguas.
La vista/formularios/filtros/parser/capacidad siguen anteriores; no contar la
pestaña como terminada.

**Siguiente bloque sugerido:** modelo, vista y formularios de Planeación AER;
reutilizar las operaciones nuevas. Después Esfuerzo, Riesgos,
Recursos e IA de AER. Quedan también
encabezados/navegación/estado y los auxiliares de Planeación IXB que aún viven
en el archivo anterior (`ixsEditarHitoTimeline`, `_ixsCargarEstadosRecursos`,
`_ixeAuto`). Al final: limpieza de archivos anteriores y CSP. Genesis/accesos
es decisión de despliegue: no activar ACCESS_ENFORCED.

**Cómo probar (Windows, Git Bash)**
```bash
export MSYS_NO_PATHCONV=1
.venv/Scripts/python -m pytest tests/portal tests/gmail tests/ejecutivo tests/aer tests/clockify tests/e2e -q --no-cov
.venv/Scripts/ruff check apps tests && .venv/Scripts/ruff format apps tests
node --test tests/frontend/*.test.*
```
- Fallos conocidos y anteriores: 3 de Node (`cost_sprint_details`,
  `executive_report`, `financial`); `test_ixs_effort::test_modals_match_previous`
  (activity, por hover) y `test_late_response_does_not_modify_reentered_view` de
  Work Items; el 403 intermitente de Acuerdos.
- Al escribir archivos con comandos de shell evita heredocs con comillas o
  barras invertidas (se pierden); usa el editor de archivos.
- `ruff format` de todo `tests/` también toca los `test_zz_*`; formatea archivos
  concretos.

**Cosas a tener presentes**
- El `.env` local tiene `GMAIL_DELIVERY_MODE=send`: la ventana de comunicados
  envía correos de verdad (con confirmación). Las pruebas fijan `draft`.
- `.env`, `key.json` y `db.sqlite3` no se suben nunca a Git.
- Presupuesto vs. consumo (cuenta) usa un rango por fila de MPB y puede no
  coincidir con el detalle del proyecto; está documentado, no lo "arregles".

**Antes de empezar, dime en pocas líneas** qué encontraste en Git y en el
traspaso, y qué bloque vas a tomar.
