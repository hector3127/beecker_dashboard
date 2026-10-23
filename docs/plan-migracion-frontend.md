# Plan de migración del frontend

Objetivo: HTML, CSS y JavaScript modular sobre Django, con el mismo
funcionamiento, listo para llevarse a Genesis y con permisos que Django valida
(`docs/permisos.md`). La integración con Genesis sigue pendiente de sus
respuestas; la migración del frontend sí avanza.

## Estado real (23/10/2026)

Tres cosas distintas, que no se confunden:

- **API**: existe `screens/…` con permiso y alcance validados en el servidor.
- **Frontend migrado**: la ruta activa (`apps/portal/urls.py`) sirve una
  plantilla de `frontend/templates/` con CSS y JS separados de `frontend/static/`.
- **Validación visual**: capturas lado a lado (anterior contra nueva) con los
  mismos datos. Los snapshots de texto de `tests/e2e` no la sustituyen.

Una pantalla solo cuenta como migrada si cumple las tres.

| Fase | Entrega | API | Frontend migrado | Estado |
|---|---|---|---|---|
| 0 | Línea base e2e | n/a | n/a | Hecha |
| 1 | `frontend/`: layouts, tokens, cliente de datos, importmap | n/a | Hecha | Hecha |
| 2 | App `access`: capacidades y alcance | Hecha | n/a | Hecha; apagada por defecto |
| 3 | EVA-04 | Hecha | Hecha | **Sin validación visual** |
| 4 | Operativa | Hecha | Hecha | **Sin validación visual** |
| 5 | Acuerdos | Hecha | No (la interfaz sigue en el JS anterior) | Parcial |
| 6 | Línea base de lo nuevo | n/a | n/a | Hecha |
| 7 | Comparativa, cuenta, Delivery Manager | Hecha | **No** | **Parcial: cambio de alcance** |
| 8 | Business Overview, diccionario, KPIs de DMs | Hecha | **No** | **Parcial: cambio de alcance** |
| 9 | Resto de pantallas | Parcial: EVA 1-3, Inversión, Capacidad y Facturabilidad; faltan Comercial, Costos, Todas las cuentas y Proyecto | **No** | **Parcial: permisos y APIs** |
| 10 | `proyecto_detalle` y fin de `/api/rpc/` | RPC con permisos | **No** | **Parcial** |
| 11 | Limpieza, CSP obligatoria, `ACCESS_ENFORCED=1` | n/a | **No** | **Pendiente** |

**Cambio de alcance (22/10/2026).** Las páginas nuevas de las fases 7 y 8 se
rehicieron con otro diseño y se devolvieron al anterior por pedido del usuario;
desde entonces esas rutas sirven las plantillas anteriores con el servidor ya
migrado (permisos, alcance, APIs). Pasarlas a `frontend/` exige primero igualar
el diseño (iconos, degradados, tarjetas) en `tokens.css` y `components.css`.

### Pantallas, una por una

Evidencia: ruta en `apps/portal/urls.py` → vista → plantilla servida.

| Pantalla | Ruta | Plantilla servida | API | Frontend migrado | Validación visual |
|---|---|---|---|---|---|
| Guía de interfaz | `guia-de-interfaz/` | `pages/guia.html` | `me`, `ping` | **Sí** | n/a (es nueva) |
| Operativa | `operativa/` | `pages/operativa.html` | `screens/operativa/…` | **Sí** | **Pendiente** |
| EVA-04 | `operativa/eva-4/` | `pages/eva4.html` (la anterior con `?vista=anterior` hasta el 3/11) | `screens/eva4/` | **Sí** | **Pendiente** |
| Horas por mes (cuenta) | `cuenta/<slug>/horas/` | `pages/account_hours.html` | `screens/cuenta/horas/` | **Sí** | n/a (funcionalidad nueva, del usuario) |
| Business Overview | `` (raíz) | `portal/ejecutiva.html` | `screens/executive/` | No | Igual (es la anterior) |
| Cuenta | `cuenta/<slug>/` | `portal/cuenta.html` | `screens/cuenta/…` | No | Igual (es la anterior) |
| Comparativa de márgenes | `ejecutiva/oportunidades/` | `portal/oportunidades_financieras.html` | `screens/margenes/…` | No | Igual |
| Delivery Manager | `operativa/delivery-manager/<slug>/` | `portal/delivery_manager.html` | `screens/delivery-managers/…` | No | Igual |
| KPIs de DMs | `operativa/kpis-delivery-managers/` | `portal/kpis_dm.html` | `screens/kpis-dm/` | No | Igual |
| Diccionario | `diccionario-datos/` | `portal/diccionario_datos.html` | `reference/glossary/` | No | Igual |
| Todas las cuentas | `ejecutiva/cuentas/` | `portal/todas_cuentas.html` | No | No | Igual |
| Costos | `ejecutiva/costos/detalle/` | `portal/costos_detalle.html` | JSON `ejecutiva/costos/` | No | Igual |
| Comercial | `comercial/` | `portal/comercial.html` | No | No | Igual |
| Inversión | `operativa/inversion/` | `portal/inversion.html` | `screens/inversion/` | No | Igual |
| Capacidad instalada y detalle | `operativa/capacidad-instalada/`, `capacidad-instalada/` | `portal/capacidad_instalada.html`, `portal/capacidad_detalle.html` | `screens/capacidad/` | No | Igual |
| Facturabilidad (general, especialidad, recurso) | `operativa/facturabilidad/…` | `portal/facturabilidad*.html` | `screens/facturabilidad/…` | No | Igual |
| Facturabilidad por área | `operativa/facturabilidad/area/` | `portal/facturabilidad_area.html` (con `gas_shim.js`) | RPC | No | Igual |
| EVA 1, 2 y 3 y sus cerrados | `operativa/eva-1/`, `eva-2/`, `eva-3/`, `…/cerrados/` | `portal/eva1|2|3.html` | `screens/eva-1|2|3/` | No | Igual |
| Proyecto | `proyecto/<id>/` | `portal/proyecto.html` | No | No | Igual |
| Detalle del proyecto | `proyectos/<id>/` | `portal/proyecto_detalle.html` (`proyecto_detalle.js` ≈ 1 MB, `/api/rpc/`) | RPC con permisos | **No** | Igual |

«Igual» significa que sigue la plantilla anterior, no que se haya migrado. En
`apps/portal/templates/portal/` quedan 33 plantillas, 17 scripts y 16 hojas de
estilo anteriores; en `frontend/` hay 5 plantillas (4 pantallas y la guía).

### Pendientes que no se dan por hechos

1. Frontend de las fases 7, 8 y 9 (ver tabla): ninguna pantalla de ellas usa
   `frontend/`.
2. Validación visual de Operativa y EVA-04 (y de todo lo que se migre).
3. `proyecto_detalle` por pestañas y retirar `/api/rpc/` y `gas_shim.js`.
4. Mover a servicios compartidos la preparación de datos que hoy viven en
   `views.py` y que usan las APIs: `operativa_context`,
   `operativa_block_context`, `operations_summary_data`, `kpi_context`,
   `dm_state`/`dm_rows`, `eva2_data`, `eva3_data`, `inversion_data`,
   `capacidad_data`, `facturabilidad_data`, `especialidad_data`, `recurso_data`
   (y `costos_revenue`). Sin duplicar ni cambiar cálculos.
5. Genesis: `ACCESS_ENFORCED` está apagado y el proveedor es
   `DjangoAccessProvider` (alcance completo a toda persona con sesión). Falta
   identidad, capacidades y alcance reales por cuenta y proyecto, y que el
   frontend adapte menús y acciones a `me/` (hoy el menú no se oculta).
6. CSP: por defecto **no hay política** (`CSP_REPORT_ONLY` solo se enciende con
   `1` y solo reporta). No hay bloqueo obligatorio y no puede haberlo mientras
   haya scripts y estilos en línea (23 plantillas anteriores).
7. Limpieza final de plantillas, estilos y scripts anteriores, que depende de
   los puntos 1 y 7.

> **Regla de diseño (22/10/2026).** Una pantalla migrada se ve idéntica a la
> anterior; solo cambian los datos, el alcance y los permisos. Se comprueba con
> capturas lado a lado (anterior contra nueva) antes de retirar la anterior. Las
> pantallas de la pestaña Business (Business Overview, cuenta, comparativa de
> márgenes, diccionario) y Delivery Manager y KPIs de DMs se rehicieron con otro
> diseño y se devolvieron al anterior: conservan su plantilla, estilos y scripts
> y mantienen lo nuevo del servidor (APIs `screens/…`, alcance, capacidades,
> diccionario único). Reproducirlas con `frontend/` exige igualar primero el
> diseño (iconos, degradados, tarjetas) en `tokens.css` y `components.css`.

Son **12 fases (0 a 11)**: los cambios del 22/10 agregan la 6 y reubican el
resto. Cada fase es un conjunto de commits en `main`, con la suite en verde.

## Reglas que se mantienen

Actualización para la fase 7: incorporar los nombres y campos solicitados por
Florencia en [cambios-florencia-2026-10-22.md](cambios-florencia-2026-10-22.md).
Bookings, revenue operado y cobrado quedan separados. La fecha de servicio G
es una suposición pendiente de validar con Finanzas (la decisión es suya, no
de la migración); el margen conserva su base.

- Django es el dueño de los datos, los cálculos y la autorización. El frontend
  solo muestra; ocultar un botón nunca sustituye la validación del servidor.
- Una sola fuente de HTML (`frontend/templates`), sin CSS ni JS en línea,
  colores solo en `tokens.css`, nada de `innerHTML` con datos.
- Cada pantalla: un resumen por pantalla en `/api/v1/screens/…`, endpoints
  aparte para desgloses y acciones, errores `{error: {code, message, fields}}`.
- Las cifras del equipo completo no se recortan por cuenta: con alcance
  limitado se ocultan (ver `docs/permisos.md`).
- Antes de migrar una pantalla se fija su comportamiento actual con un
  recorrido en navegador y, si aplica, un snapshot.

## Cambios del 22/10 (reunión del 21/10 y conciliación de KPIs)

Son cuatro piezas, hoy sin confirmar en `main`. Todas pasan la suite actual.

### A. Glosario y diccionario de datos

Qué es: `_executive_glossary.html` (guía desplegable en Business Overview),
textos nuevos en `data_dictionary.CONCEPTS` (comparación de cuentas, tarifa de
costo vendida, tarifa interna de banda, trabajo por entregar, previas al cierre)
y el enlace «Glosario de indicadores».

Riesgo: la misma definición vive en **tres sitios** (el glosario escrito a mano,
`CONCEPTS` y el cajón «Fuentes y cálculo» de `ejecutiva.html`). Se desalinean
con el primer cambio de regla.

Decisión: `CONCEPTS` es la única fuente. Un servicio entrega los conceptos
agrupados (Financiera, Operaciones, Comercial) en `GET /api/v1/reference/glossary/`;
el glosario de Business Overview y la página del diccionario lo dibujan con el
mismo componente `ui/glossary`. Una prueba verifica que cada concepto mostrado
exista en `CONCEPTS`. Contenido y estilo no dependen de Genesis.

### B. Comparación de cuentas en Business Overview

Qué es: `executive_rankings.js` + `_executive_ranking_card.html`. Busca por
cuenta, elige facturación, utilidad bruta o margen, parte las cuentas con dato
en mitad superior e inferior (hasta cinco por grupo, orden invertible), informa
cuántas no aplican y guarda búsqueda y orden en la URL.

Hallazgos:

1. **Alcance.** La página incrusta `financial_snapshot` completo
   (`json_script "financial-cache"`): cualquier persona con sesión recibe la
   facturación y el margen de **todas** las cuentas en el HTML. Con alcance
   limitado esto es una fuga. En la migración el listado sale de una API que lo
   filtra por alcance, y el snapshot deja de incrustarse.
2. **Cifras de empresa.** Los totales de Financiera, cobranza y comercial son
   del portafolio completo: con alcance limitado se ocultan (misma regla que
   Operativa); el listado de cuentas sí se entrega recortado.
3. **Dónde vive la regla.** La partición en mitades y el orden están en JS
   (`rankAccounts`, función pura con pruebas). Se conserva como `lib/ranking.js`
   con las mismas pruebas; si aparece otro consumidor (exportar, reporte) pasa
   a un selector de Python.
4. **Nombres.** El contrato usa `top_half` / `bottom_half`; «Cuentas sanas» y
   «no sanas» quedan como etiquetas de la interfaz. La nota de la pantalla ya
   aclara que son posiciones relativas, no una clasificación validada por
   Finanzas: conviene que las etiquetas no la contradigan.
5. **Dependencias.** Usa `executiveMoney` global (K/M/B) y `innerHTML` escapado
   a mano: pasan a `lib/format.js` (`formatMoney`, con las pruebas de
   `executive_numbers`) y a constructores de `lib/dom.js`.
6. **Navegación.** `ranking_buscar`, `ranking_criterio` y el orden de cada
   grupo se conservan al entrar a una cuenta y regresar: `data/navigation.js`
   (fase 7) debe preservarlos junto con el periodo y `volver`.

### C. Tarifa de costo vendida: pendiente

Qué es: columna «Tarifa de costo vendida» en la comparativa de márgenes
(ya confirmada, `5e7b167`). No se calcula, no se sustituye por la tarifa de
banda y no altera márgenes.

Decisión: el contrato la entrega como
`sold_cost_rate: {value: null, status: "pending_validation"}`. Una prueba
asegura que nunca se deduce de revenue ÷ horas ni de la tarifa de banda. Se
completa cuando Florencia confirme fuente, unidad y asignación.

### D. KPIs de Delivery Managers y conciliación

Qué es: `kpi_quarterly.py` (promedio trimestral de cortes mensuales, puro y con
pruebas), periodo anual por defecto, subcolumnas TP/T/C y notas de unidades
(T = días; C = consumo de horas sobre presupuesto).

Hallazgos:

- **No es un defecto de código.** El documento de conciliación muestra que el
  Excel y la aplicación miden otra cosa: septiembre da TP 9 contra 30, y T y C
  son ratios en el Excel y promedios en la aplicación. Faltan datos de
  negocio (lista de IDs, regla de T y C, si entra Miguel A. y los alias de
  nombres).
- **No se bloquea la migración.** Se migra el cálculo tal como está, con un
  snapshot previo (fase 6), sin tocar umbrales ni importar valores del Excel.
- El contrato manda números sin redondear (los trimestres conservan precisión)
  y las definiciones de TP, T y C como datos, para que no se repitan en HTML.
- Con alcance limitado, las filas se recortan por los proyectos de la persona.

El documento `conciliacion-kpis-dms-2026-10-22.md` queda como registro de lo
pendiente de negocio; no es parte del código.

## Fase 6: línea base de lo nuevo (hecha)

Los cambios del 22/10 quedaron confirmados en cuatro commits (glosario,
comparación de cuentas, documento de interfaz y KPIs de Delivery Managers) y
la línea base quedó fijada:

- `tests/e2e/test_ejecutiva_kpis.py`: glosario, comparación de cuentas
  (criterios, búsqueda sin acentos, orden, valores sin dato, estado en la URL,
  entrar a una cuenta y regresar) y KPIs de Delivery Managers (periodo anual,
  TP/T/C, trimestre como promedio de meses, notas de unidades).
- Snapshots: `ejecutiva_glosario`, `ejecutiva_comparacion` y `kpis_dm_historico`.
- `test_glossary_sources.py`: cada término del glosario declara el concepto del
  diccionario del que sale (se elimina cuando el glosario se genere de
  `CONCEPTS`, fase 8).

Hallazgo para la fase 8: `executive_report.js` todavía dibuja el ranking
anterior (grupos `healthy/unhealthy` y la nota de «indicadores monetarios
normalizados») y `executive_rankings.js` lo vuelve a dibujar encima. Hoy gana el
segundo por el orden de carga; el código viejo debe retirarse al migrar.

Lo que se planeaba para esta fase:

1. Confirmar los cambios del 22/10 en commits separados: glosario y
   diccionario; comparación de cuentas; KPIs DMs. (Hoy comparten `views.py` y
   `ejecutiva.html` con el resto.)
2. Recorridos en navegador sobre las pantallas actuales, antes de migrarlas:
   - Business Overview: abrir el glosario; buscar una cuenta, cambiar el
     criterio, invertir un grupo; entrar a una cuenta y regresar conservando
     búsqueda y orden.
   - KPIs DMs: periodo anual por defecto, histórico mensual y trimestral con
     TP/T/C, trimestre = promedio de meses.
3. Snapshot del texto visible de ambos recorridos.
4. Prueba que fija que el glosario sale de `CONCEPTS`.
5. Corregir la frase «La migración … sigue en pausa» del documento de interfaz.

## Fase 7a: comparativa de márgenes (API hecha; frontend no migrado)

> **Estado real:** los módulos de `frontend/` que esta sección menciona
> (páginas `pages/…`, `ui/detail-dialog`, `ui/agreements`, `data/navigation.js`,
> `lib/account-metrics`…) se retiraron el 22/10/2026 al volver al diseño
> anterior; sobreviven el servicio, la API y las pruebas de la API.

> Nota: la página usa la plantilla anterior; el contrato y el alcance de abajo
> siguen vigentes en la API.


- `GET /api/v1/screens/margenes/` (capacidad `view_costs`): oportunidades con
  `bookings`, `period_revenue`, `operated_revenue` + `operated_revenue_status`,
  `invoiced`, `collected`, `cost`, `sold_cost_rate` (siempre
  `{value: null, status: "pending_validation"}`), márgenes y desviación. Solo
  entrega las cuentas del alcance; una cuenta ajena es 404.
- `POST/GET .../margenes/actualizar/` prepara los costos; `GET /api/v1/costs/project/`
  entrega personas y tarifas de un Project ID (misma capacidad y alcance). El
  desglose anterior (`ejecutiva/costos/`) también valida capacidad y alcance.
- Página `frontend/templates/pages/margenes.html` + `pages/margenes/`; se
  retiraron la plantilla, el CSS y el JS anteriores. `lib/format.js` suma
  `formatMoney` y `formatPercent` (con pruebas).
- El destino de regreso lo sigue validando el servidor (`return_context`); por
  eso `data/navigation.js` se hará con la cuenta (7b), que es quien enlaza.
- Pruebas: `test_margins_api.py`, `tests/e2e/test_margenes.py` y el recorrido
  «Cuenta → comparativa → regresar» (el snapshot solo cambia el ícono ↗).

## Fase 7b: alcance de la cuenta (servidor hecho; frontend no migrado)

> **Estado real:** los módulos de `frontend/` que esta sección menciona
> (páginas `pages/…`, `ui/detail-dialog`, `ui/agreements`, `data/navigation.js`,
> `lib/account-metrics`…) se retiraron el 22/10/2026 al volver al diseño
> anterior; sobreviven el servicio, la API y las pruebas de la API.

- Hecho: `/cuenta/` (y su bloque de consumos) devuelve 404 para una cuenta fuera
  del alcance y 403 sin `view_operations` ni `view_agreements`;
  `cuenta/financiera/` exige `view_costs` y alcance. Ya no hay xfail de acceso.
- Hecho: `data/navigation.js` (`withReturn`) con pruebas; la comparativa lo usa.
- Hecho: la página de la cuenta es `pages/cuenta` con API propia
  (`screens/cuenta/`, `/consumos/`, `/finanzas/`): indicadores, gráficas,
  alertas, tabla, ventanas «Ver más» (`ui/detail-dialog`, `ui/filtered-table`),
  finanzas (solo con `view_costs`), horas de Clockify por lotes y acuerdos
  (`ui/agreements`, sobre `/api/v1/agreements/`). Los totales de pantalla se
  calculan en `lib/account-metrics.js` porque las horas llegan por lotes.
  Se retiraron la plantilla, la vista y el endpoint financiero anteriores.
- Diferencias menores respecto a la anterior: una alerta de consumo exige
  presupuesto mayor que cero; la distribución del consumo en la ventana de
  presupuesto es una lista (sin dona).
- Pendiente: `/api/rpc/obtenerVistaCuentaBeecker` sigue entregando cualquier
  cuenta a quien tenga sesión; desaparece con la fase 10.

## Fase 7c: Delivery Manager (API hecha; frontend no migrado)

> **Estado real:** los módulos de `frontend/` que esta sección menciona
> (páginas `pages/…`, `ui/detail-dialog`, `ui/agreements`, `data/navigation.js`,
> `lib/account-metrics`…) se retiraron el 22/10/2026 al volver al diseño
> anterior; sobreviven el servicio, la API y las pruebas de la API.

- `GET /api/v1/screens/delivery-managers/<slug>/?bloque=base|inv|horas`
  (`view_operations`): primero proyectos y estados; la inversión de Clockify y
  las horas por mes llegan en consultas aparte, y mientras faltan su estado es
  `pending` con cifras vacías (nunca cero).
- Alcance: el DM, sus totales, la inversión y las horas se calculan solo con
  los proyectos de las cuentas visibles; sin ninguno, el DM no existe (404).
  Cada alcance limitado guarda su propio corte en caché.
- Página `pages/delivery-manager` (resumen, tabla, gráfica de horas, detalle
  con CSV que neutraliza fórmulas: `lib/hours-report.js`, con pruebas). Se
  retiraron la plantilla y la vista anteriores; `warm_cache` usa `dm_state`.
- Diferencia: si las fuentes no responden y no hay a quién mostrar, la API da
  502 y la página lo dice; antes redirigía a Operativa.

## Fase 8: Business Overview, glosario y KPIs de DMs (API hecha; frontend no migrado)

> **Estado real:** los módulos de `frontend/` que esta sección menciona
> (páginas `pages/…`, `ui/detail-dialog`, `ui/agreements`, `data/navigation.js`,
> `lib/account-metrics`…) se retiraron el 22/10/2026 al volver al diseño
> anterior; sobreviven el servicio, la API y las pruebas de la API.

> Nota: Business Overview, diccionario y KPIs de DMs conservan su plantilla
> anterior. El Business Overview incrusta los cortes ya recortados al alcance
> (`scoped_snapshots`); el resto de lo descrito sigue vigente en la API.


- **8a.** `data_dictionary.GLOSSARY` declara el glosario corto junto a
  `CONCEPTS` (cada término cita su concepto); `reference/glossary` entrega
  ambos y el diccionario es `pages/diccionario`. «Fuentes y cálculo» de las
  tarjetas sale del mismo diccionario: se acabó la tercera copia. Una prueba
  avisa si un concepto citado desaparece.
- **8b.** `screens/executive/` (`view_executive`): cifras de empresa solo con
  alcance total; el listado de cuentas se recorta al alcance; un bloque que
  falta es `null`. Ya no se incrusta el snapshot completo en la página (cerró
  la fuga de facturación y oportunidades de todas las cuentas).
- **8c.** `pages/executive`: selector de periodo (`ui/period-picker`, con
  `lib/date-range`), tarjetas, rentabilidad mensual (`lib/monthly-model` +
  `ui/monthly-chart`), comparación de cuentas (`lib/ranking`, con el estado en
  la URL) y acuerdos de todas las cuentas (`ui/agreements`). Se retiraron la
  vista, 4 plantillas, 6 scripts y 5 hojas de estilo anteriores. El trabajo de
  preparación del corte ya no renderiza la página.
- **8d.** `screens/kpis-dm/` y `pages/kpis-dm`: T y C sin redondear, gráfica de
  C (`lib/kpi-chart`) y selector `ui/period-filter` (reutilizable por
  Facturabilidad). **Desviación del plan:** con alcance limitado la pantalla
  responde 403 en lugar de recortar filas; los cortes agregan a todo el equipo.
- Se conservan `ejecutiva/actualizacion/` y `executive_numbers.js` hasta migrar
  Costos, Todas las cuentas y Comercial (fase 9).

## Fase 9: permisos, alcance y APIs del resto de pantallas (frontend no migrado)

- `require_capability(code, whole_portfolio=True)`: con los accesos encendidos
  pide la capacidad y, si la pantalla muestra cifras de todo el portafolio o del
  equipo, rechaza (403) a quien tenga alcance limitado sin tocar las fuentes.
  Se aplicó a EVA 1-3 y sus cerrados, Inversión, Facturabilidad (4 pestañas),
  Capacidad (detalle, instalada y CSV), Comercial, Todas las cuentas y los
  endpoints JSON del Business Overview.
- `costos_detalle` pide `view_costs` (cuenta ajena 404; el listado completo,
  403 con alcance limitado); `proyecto` y `proyecto_detalle` piden
  `view_operations` y un proyecto de otra cuenta responde 404.
- `trust(request)` marca las peticiones internas del calentamiento de cache.
- No cambia ninguna pantalla: con `ACCESS_ENFORCED` apagado todo funciona igual.
- Se conserva «Horas por mes» de la cuenta (`pages/account_hours`, API
  `screens/cuenta/horas/`, `docs/reporte-horas-mensuales.md`) con su enlace en
  `cuenta.html` y su regreso; usa `views.authorized_account`.
- APIs de Operativa (`apps/portal/api/operations.py`, mismo permiso y alcance
  total): `screens/eva-1/`, `eva-2/`, `eva-3/`, `inversion/`, `capacidad/` y
  `facturabilidad/` (+ `especialidad/` y `recurso/`). Reutilizan las funciones de
  datos de las vistas (`eva2_data`, `facturabilidad_data`…), que ahora también
  arman las pantallas, y entregan los campos de `schemas.py` con `plain()`.
  Costos y Comercial ya tienen JSON (`ejecutiva/costos/`, `comercial_ejecutiva`,
  `screens/margenes/`), protegidos por capacidad y alcance.
- Pendiente de la 9: retirar `executive_numbers.js` y `ejecutiva/actualizacion/`
  cuando Costos, Todas las cuentas y Comercial dejen de usarlos.

## Fase 10: `/api/rpc/` con permisos (hecha); `proyecto_detalle` sin migrar

- `apps/access/rpc_policy.py` clasifica las 190 funciones del RPC: lectura
  (`view_operations`), escritura (`edit_operations`), configuración
  (`manage_integrations`) y las de cuenta con alcance. Se agregaron dos
  capacidades al catálogo (migración `access.0002`). Con alcance limitado solo
  funcionan las de cuenta; una función sin política se rechaza.
- `proyecto_detalle.js` (≈ 1 MB, 100+ llamadas RPC) **no se reescribe**: por la
  regla de diseño conserva su pantalla y sus llamadas; el RPC ya valida quién
  puede hacerlas. Retirar el RPC requiere una API por llamada y es trabajo
  aparte. Un proyecto de otra cuenta ya responde 404 en la página.

## Fase 11: limpieza (pendiente; solo se retiraron cuatro endpoints)

Estado a 22/10/2026, comprobado en el código:

- **CSP obligatoria: no es posible todavía** (y hoy ni siquiera hay política por defecto). 23 plantillas anteriores llevan
  scripts y estilos en línea (Business Overview 63 `style=`, Comercial 4 scripts,
  Capacidad 22 estilos…) más los bloques `{% block css %}`. Con la política en
  modo de bloqueo se rompen. Por defecto no hay política y el reporte solo se enciende con
  `CSP_REPORT_ONLY=1`; seguirá así hasta que esas pantallas pasen a
  `frontend/` con el diseño igualado (ver la regla de diseño).
- **`ACCESS_ENFORCED=1`: listo para encender, decisión de despliegue.** Todas las
  pantallas y el RPC ya validan capacidad y alcance. Antes: `python manage.py
  access_setup --incluir-usuarios` (migrar `access.0002` primero) y probar con
  una persona de alcance limitado. Ver `docs/permisos.md`.
- **Endpoints sin consumidor: retirados** (23/10/2026): `comercial_ejecutiva`,
  `operaciones_ejecutiva`, `rentabilidad_mensual` y `cuentas_rentabilidad`; nada
  del código los llamaba.
- **Se conservan** `ejecutiva/actualizacion/` y `executive_numbers.js` porque
  Costos, Todas las cuentas, Comercial y la barra de «corte anterior» los usan, y
  `eva4_anterior` hasta el 3/11/2026 (`ANTERIOR_HASTA`).

## Fases siguientes con lo nuevo integrado

- **7. Cuenta y Delivery Manager**: flujos «DM → proyecto → regresar» y
  «Cuenta → comparativa de márgenes → regresar». `data/navigation.js` reemplaza
  a `return_navigation.js` y conserva periodo, `volver` y los parámetros de la
  comparación. La comparativa expone `sold_cost_rate` pendiente. La cuenta y la
  comparativa validan el alcance (hoy una cuenta ajena se abre).
- **8. Business Overview**: API `screens/executive/` con cifras de empresa solo
  para alcance total y listado de cuentas recortado; sin snapshot incrustado;
  comparación de cuentas como `ui/account-ranking`; glosario y diccionario
  desde `reference/glossary`; KPIs DMs con `kpi_quarterly` en servicios.
- **9. Resto de pantallas**, de la más simple a la más compleja.
- **10. `proyecto_detalle`** por pestañas (minutas, Azure/RAID, daily,
  recursos, hitos, Gmail); desaparece `/api/rpc/`.
- **11. Limpieza** y encendido de los accesos.

## Pendiente de negocio (no bloquea el código)

1. Florencia: fuente, unidad y asignación de la tarifa de costo vendida.
2. Reunión de KPIs: IDs de los nueve proyectos de septiembre, regla de T y C,
   inclusión de Miguel A. y alias de nombres.
3. Finanzas: si «mitad superior / inferior» es aceptable como lectura de la
   comparación de cuentas o se necesita una clasificación validada.

## Pendiente de Genesis

Ver las preguntas en `docs/permisos.md`: identidad, roles, alcance por cuenta,
auditoría y despliegue.
