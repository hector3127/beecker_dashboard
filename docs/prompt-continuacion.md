# Mensaje para continuar la migración

Pega el texto que sigue en la sesión nueva:

---

Continúa en `C:\beecker_dashboard`. Lee primero `AGENTS.md`, el primer bloque
de `docs/estado-traspaso.md` y `docs/plan-migracion-frontend.md`. Revisa Git,
los últimos commits y los cambios pendientes antes de editar. Trabajamos
directamente en `main`, con commits pequeños y archivos añadidos por nombre.
No hagas push sin petición expresa del usuario.

**Más reciente: Facturabilidad sobre 18e69a1.** Leer
`docs/retiro-facturabilidad.md`. Retiradas las tres plantillas anteriores de
general/especialidad/recurso; datos y permisos intactos. Nueve snapshots del
diseño vigente registrados antes del retiro se revalidan con CSP de prueba.
1724 servidor, 504 Node y 36 Chrome pasan; detalle en el informe. Área sigue con su
comparación. Quedan 20 HTML/35 estáticos portal; continuar otras referencias
y CSP sin retirar servicios/componentes aún usados. Sin push de este bloque.

**Último bloque: EVA 2 y Capacidad mensual sobre 7420d17.** Leer
`docs/retiro-capacidad-eva2.md`. Solo frontend en esas rutas; dos plantillas
anteriores retiradas. Datos/permisos/CSV sin cambios. Seis snapshots vigentes
guardados antes de borrar se revalidan con CSP de prueba; 1715 servidor y
504 Node y 34 Chrome pasan. No recrear plantillas ni modificar Capacidad diaria.
Quedan 23 HTML/35 estáticos portal; continuar referencias restantes y CSP.

**Último bloque: limpieza agrupada sobre 1e17d99.** Leer
`docs/limpieza-por-lotes.md`. 21 archivos/1.42 MB retirados: comparaciones de
Inversión, Proyecto simple y Todas las cuentas; cuatro huérfanos y el árbol
del panel original, porque /legacy/ solo redirige. No recrearlos. Siete snapshots
vigentes versionados ANTES del borrado mantienen diseño con CSP de prueba.
1711 servidor, 504 Node, 28 Chrome pasan. Quedan 25 HTML/35 estáticos portal;
otras comparaciones siguen usando motor/shim. No borrarlos ni tocar servicios,
fórmulas o permisos. Fase 11 abierta, nuevos cambios sin push.

**Último bloque:** se publicó hasta 3c5b2fa y después se retiró KPIs DM anterior:
vista, plantilla, bifurcación y kpi_chart.js de portal. No recrearlos. Contexto/
API/cálculos intactos; pruebas de cortes usan constructor/API y las dos Node
de gráfica usan el módulo vigente. 1693 servidor (incluyen 78 dirigidas), 505 Node, 40 Chrome;
revalidación KPI 10 (solapadas). Referencias idénticas en tres tamaños y CSP de
prueba verificada. Nuevos cambios sin push; continuar otras referencias y CSP.

**Actualización más reciente: integración Christian sobre 3410e89.** Leer
`docs/integracion-christian.md`. Los logos unificados/comando nuevo, Previas al
cierre y Capacidad diaria están preservados. Reorganizadas las 17 entradas
JS indicadas y fusionadas doce CSS exclusivos en seis destinos. 1691 servidor,
505 Node y 57 navegador finales pasan. Base visual: 3410e89, 54 referencias y
53 PNG (42 exactas; restantes hora/pintado, ver detalle). No sumar las corridas
solapadas ni afirmar una segunda corrida amplia íntegra. Continuar referencias
antiguas y CSP; no recrear hojas retiradas ni añadir fetch directo para lecturas.

**Actualización 26/10 posterior al rediseño:** lee también
`docs/preparacion-fase-11.md`. El usuario autorizó preparar la fase 11.
La fase 11 ya tiene un primer bloque completado: EVA-04 perdió su vista y
plantilla anteriores; el parámetro obsoleto abre la modular y conserva mes.
No recrearlas. Capturas vigentes idénticas antes/después a 1450/900/390 px;
1682 servidor (portal/core/accesos), 498 Node y 38 Chrome pasan. `enforced_csp` sirve para las pruebas
futuras; no hay bloqueo global. Faltan las otras referencias y CSP de captura
real/gráficos/ventanas. La evidencia de preparación que sigue es previa.
Segundo bloque posterior: diccionario sin vista/plantilla anterior, mantiene
búsqueda y enlaces obsoletos; capturas vigentes idénticas en tres tamaños.
La captura PNG real en la guía ya pasa con CSP gracias a dos huellas exactas
de estilos estáticos en core.frontend, sin unsafe-inline. 1686 servidor,
54 Chrome y 498 Node
pasan; se repitieron las 15 pruebas de captura. Falta extender la comprobación
a otras capturas, gráficas y ventanas y retirar las demás referencias. No
activar CSP global ni permisos todavía; no recrear las pantallas retiradas.
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
