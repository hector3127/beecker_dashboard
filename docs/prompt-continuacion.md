# Mensaje para continuar la migración

Pega el texto que sigue en la sesión nueva:

---

Continúa en `C:\beecker_dashboard`. Lee primero `AGENTS.md`, el primer bloque
de `docs/estado-traspaso.md` y `docs/plan-migracion-frontend.md`. Revisa Git,
los últimos commits y los cambios pendientes antes de editar. Trabajamos
directamente en `main`, con commits pequeños y archivos añadidos por nombre.
No hagas push sin petición expresa del usuario.

**Actualización 26/10 posterior al rediseño:** lee también
`docs/preparacion-fase-11.md`. El usuario autorizó preparar la fase 11.
La migración local de logos está aplicada; en otros entornos ejecutar migrate.
Se corrigió una regresión de rangos MPB repetidos respecto al cierre anterior
y se probó CSP de la vista previa del logo en navegador, sin activar bloqueo
global. Pasan 388 servidor, 498 Node y 74 Chrome; revalidación logos/CSP 15
casos solapados. Los apartados de evidencia que siguen son históricos.
Continuar por limpieza de referencias y auditoría CSP del diseño vigente,
conservando servicios JSON/cálculos y pruebas actuales. Fase 11 no terminada.

**Estado vigente: la fase 10 está completada.** El detalle de AER/T&M e
IXB/SaaS/RaaS y el Ejecutivo genérico usan HTML, CSS y JS de `frontend/`, con
estado/controladores propios. La plantilla activa no carga
`proyecto_detalle.js`, `gas_shim.js` ni CSS de portal. No hay RPC en el grafo
activo ni al recorrer las pestañas. Los nombres públicos restantes delegan a
módulos en `project_commands.js`; no son renderizadores anteriores.

El código del cierre independiente está en `fa4bf11`; consulta los commits
posteriores para el cierre de pruebas/documentación. La ruta del proyecto
siempre recibe ID desde Django. Cuenta tiene su propia ruta: las ramas del
dashboard antiguo sin proyecto/cuenta ya no son dependencias del detalle.
Las anotaciones «fase 10 parcial» en bloques históricos no son tareas vigentes.
No reabras pestañas, modelos, editores o proveedores ya migrados.

**Validación realizada:** 478 pruebas Node aprobadas. La corrida general de
3862 casos Python dio 3853 aprobadas, ocho fallos de pruebas y una lista de
parámetros vacía omitida. Se corrigieron expectativas/referencias y el origen
de rectángulos nulos de elementos ocultos; las capturas de las gráficas
afectadas son idénticas byte por byte. La lista vacía ahora tiene tres casos
reales de rechazo anónimo antes de consultar datos. La revalidación de todos
los archivos afectados dio 55 aprobadas, sin fallos ni omisiones. Son 3864
casos Python verificados en conjunto, incluidas 1264 pruebas de navegador;
no se afirma una segunda corrida general. Ruff/formato, Django y mypy pasan.
El traspaso conserva los comandos y el desglose de evidencia.

**Si el usuario pide seguir, lo siguiente es fase 11:** auditar y retirar
archivos anteriores que ya no tengan consumidores, las rutas de comparación
y sus pruebas, y preparar CSP. Conserva diseño, cifras, filtros, exportaciones,
permisos y regreso. Retirar los originales exige retirar a la vez sus pruebas
de referencia: `project_reference.py` solo existe para esos contrastes.
La ruta nueva ya es independiente; no dupliques el megabyte ni crees otra API.
Genesis/ACCESS_ENFORCED es decisión de despliegue; no lo actives sin accesos
configurados. Horas por mes se conserva tal cual.

**Archivos ajenos que debes conservar y no comitear:**

- `tools/migracion/inline2css.py`
- `tools/migracion/migrate_page.py`
- `shots_tmp/`
- `tests/e2e/test_zz_dom.py`, `test_zz_pages.py`, `test_zz_seq.py`,
  `test_zz_styles.py`

No uses `git add tests` ni `git add .`. No subas `.env`, `key.json`,
`db.sqlite3` o credenciales. El `.env` local tiene `GMAIL_DELIVERY_MODE=send`:
las operaciones reales de Comunicados pueden enviar correos. Las pruebas
usan proveedores simulados, borradores y red externa bloqueada.

**Pruebas en Windows / PowerShell:**

```powershell
.venv/Scripts/python.exe -m pytest tests -q --no-cov --browser-channel chrome --ignore=tests/e2e/test_zz_dom.py --ignore=tests/e2e/test_zz_pages.py --ignore=tests/e2e/test_zz_seq.py --ignore=tests/e2e/test_zz_styles.py
.venv/Scripts/ruff.exe check apps tests --exclude 'test_zz_*.py'
.venv/Scripts/ruff.exe format --check apps tests --exclude 'test_zz_*.py'
.venv/Scripts/mypy.exe apps/portal/pages.py
node --test tests/frontend/*.test.*
```

Solo se excluyen los diagnósticos ajenos no versionados. No añadas marcas de
omisión para hacer pasar una revisión. Compara siempre con datos simulados y
sin enviar correos ni consultar Azure/Sheets/Clockify reales. Antes de editar,
explica brevemente qué encontraste y qué bloque vas a tomar.
