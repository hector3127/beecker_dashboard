# Copias manuales de proyectos para Genesis

Fuente: `apps/datastore/services/project_sheets.py`,
`apps/datastore/management/commands/sync_project_sheets.py` y
`tests/datastore/test_project_sheets.py`.

## Transferencia validada a PostgreSQL local el 05/11/2026

El paquete complementario `tmp/genesis-hojas-manuales-20261105` contiene
30 snapshots verificados. Se exportó desde la base local en modo de solo
lectura, con la red bloqueada. Las 16 copias manuales suman 127 registros
y sus matrices coinciden con la SQLite de trabajo de Genesis.

La fusión selectiva se ejecutó en PostgreSQL 16.15 local. Se crearon las
16 copias y se conservaron íntegros los 14 snapshots anteriores. Se
verificaron matrices, conteos, fechas originales e IDs locales. Una
segunda aplicación conservó las copias y sus IDs. Los conteos de las
otras 25 tablas del módulo permanecieron iguales.

El cotejo cubrió Acciones, Cliente, Comunicación y Planeación en 176
proyectos, y RAID AER en 15. Las 719 respuestas de API devolvieron HTTP
200 y coincidieron con SQLite. El cotejo fijó el 04/11/2026 para reproducir
los resultados originales guardados; para Cliente se mantuvo el contexto de
DM y cliente vacío del cotejo original.

Para un destino nuevo, importar primero el paquete principal y después
fusionar las copias manuales. Con la conexión local configurada, ejecutar
desde `C:/Genesis/genesis/Genesis`:

```powershell
$dmPaquete = 'C:/beecker_dashboard/tmp/genesis-hojas-manuales-20261105'
$dmHojas = @(
    'AER_Acciones', 'AER_ClienteDocs', 'AER_ClienteGobierno', 'AER_ClienteInfo',
    'AER_Contactos', 'AER_Planeacion', 'AER_Riesgos', 'AER_Vacaciones',
    'Comunicados', 'IXS_Acciones', 'IXS_Cliente_Contactos',
    'IXS_Cliente_Documentos', 'IXS_Cliente_Gobierno', 'IXS_Cliente_Info',
    'IXS_Planeacion', 'Pendientes_Minutas'
)
$dmArgumentos = @()
foreach ($dmHoja in $dmHojas) {
    $dmArgumentos += '--hoja'
    $dmArgumentos += $dmHoja
}
uv run python manage.py importar_hojas_proyecto_dm $dmPaquete @dmArgumentos --settings=Genesis.settings_test_postgres
uv run python manage.py importar_hojas_proyecto_dm $dmPaquete @dmArgumentos --aplicar --settings=Genesis.settings_test_postgres
```

La primera llamada inspecciona y la segunda aplica el plan validado. El
paquete complementario y el respaldo previo están bajo `tmp/` ignorado.
La evidencia corresponde a PostgreSQL local. P2 y P3 continúan pendientes
para UAT y cuentas de servicio.

## Flujo de descarga y exportación

Las hojas de Acciones, Cliente, Comunicados y pendientes están declaradas en
el catálogo de Google, pero no forman parte de `STORED_SHEETS`. Por eso la
sincronización habitual no guarda sus contenidos en la base. Este comando
ofrece una carga explícita sin modificar esa sincronización ni sus tareas.

## Inspeccionar sin descargar

Desde `C:/beecker_dashboard`, en PowerShell:

```powershell
.venv/Scripts/python manage.py sync_project_sheets
```

Muestra si existe cada copia local, su fecha original y si el catálogo
guardado declara la hoja. No utiliza credenciales, consulta Google, toma
candados ni modifica la base. El catálogo puede estar desactualizado: la
inspección no comprueba el estado actual del origen.

Para limitar el alcance, repetir `--hoja`:

```powershell
.venv/Scripts/python manage.py sync_project_sheets --hoja Comunicados --hoja Pendientes_Minutas
```

## Carga explícita preparada

El siguiente comando **sí consulta Google y escribe en la base local**.
No se ejecutó durante la preparación del flujo:

```powershell
.venv/Scripts/python manage.py sync_project_sheets --hoja Comunicados --hoja Pendientes_Minutas --aplicar
```

Sin `--hoja`, `--aplicar` selecciona las doce fuentes admitidas:

- `AER_Acciones`, `IXS_Acciones`, `Comunicados` y `Pendientes_Minutas`.
- `AER_Contactos`, `AER_ClienteInfo`, `AER_ClienteGobierno`, `AER_ClienteDocs`.
- `IXS_Cliente_Contactos`, `IXS_Cliente_Info`, `IXS_Cliente_Gobierno`,
  `IXS_Cliente_Documentos`.

Usa la configuración de Sheets ya existente y solicita un repositorio sin
caché ni respaldo local. Reutiliza el candado `hojas` de `sync_datastore`.
Solo lee Google: no crea pestañas, completa encabezados ni escribe celdas.

Todas las hojas seleccionadas deben existir y tener los encabezados que
usan los lectores de las pantallas. Un error de descarga, una hoja ausente
o encabezados corruptos impiden publicar el conjunto. La escritura local
es atómica; un fallo revierte todas las copias del intento. No elimina
copias anteriores ni modifica las hojas no seleccionadas. Una hoja con
encabezados válidos y sin registros se conserva como copia vacía válida.

Guarda las matrices originales sin transformar texto, JSON, fechas, horas
ni estados. Publica también el catálogo de nombres del origen. La revisión
de fuentes invalida resultados anteriores mediante `save_snapshot`, igual
que el flujo existente. No recalcula los KPIs ni modifica meses cerrados.

## Exportación y transferencia

Las nuevas copias se incluyen en el exportador existente del grupo `hojas`:

```powershell
.venv/Scripts/python manage.py export_for_genesis --group hojas --out tmp/export-hojas-proyecto
.venv/Scripts/python manage.py export_for_genesis --verify tmp/export-hojas-proyecto
```

El destino debe ser nuevo y estar vacío. El paquete incluye todas las
copias de hojas guardadas, no solo las elegidas en esta carga. Contiene
datos reales: conservarlo fuera de Git.

En Genesis, desde `C:/Genesis/genesis/Genesis`, ya se puede validar sin
importar:

```powershell
uv run python manage.py importar_datos_dm C:/beecker_dashboard/tmp/export-hojas-proyecto --solo-verificar
```

La fusión acotada ya está preparada en Genesis. Primero inspeccionar, desde
`C:/Genesis/genesis/Genesis`:

```powershell
uv run python manage.py importar_hojas_proyecto_dm C:/beecker_dashboard/tmp/export-hojas-proyecto --hoja Comunicados --hoja Pendientes_Minutas
```

La escritura requiere repetir el comando con `--aplicar`. Sin `--hoja`
selecciona las doce fuentes manuales y exige que todas estén en el paquete.
Este comando solo admite el grupo `hojas`, con manifiesto y SHA válidos.
Conserva las matrices y sus fechas originales, actualiza por nombre y
preserva los IDs locales. No importa IDs del origen, no elimina hojas ni
sustituye `__sheet_ids__`; ignora las fuentes no seleccionadas del paquete.

Una copia distinta con fecha igual o anterior a la local rechaza todo el
conjunto. Si la matriz y el conteo son idénticos, una copia igual o más
antigua se conserva sin escritura. Una observación más reciente actualiza
la hoja. Los cambios son atómicos y una actualización concurrente impide
sobrescribir la copia que cambió. El plan se vuelve a calcular al aplicar.

El importador general con `--reemplazar` sustituye tablas completas; no
usarlo como fusión parcial. Ninguno de estos preparativos autoriza cargar
UAT/producción ni activa G8. No se descargaron ni importaron copias reales.

## Evidencia

36 pruebas nuevas cubren inspección sin red ni escrituras, selección
acotada, candado, un lote de lectura, integridad de matrices, fallos de
descarga/validación y reversión, además de la exportación verificable.
La inspección real se ejecutó con SQLite abierto en modo `ro` y la red
bloqueada; confirmó las doce hojas declaradas y sin copia. No se ejecutó
`--aplicar`, ni una exportación o importación de datos reales.

La fusión de Genesis agrega 48 pruebas propias de validación, selección,
fechas, PK locales, rollback y concurrencia. Suite completa del módulo:
1,156 pruebas pasan, cobertura 92.29 %. Ruff, formato propio y mypy pasan.
No se ejecutó una importación real. Los gates globales siguen pendientes:
make no está instalado y la guardia ajena de registro de jobs espera
redactar_entregables, ausente también al ejecutar esa prueba aislada.

## Carga local ejecutada el 04/11/2026

Se ejecutó el flujo de doce hojas: 18 registros descargados en 13.78 s.
El paquete verificado tiene 26 snapshots. Tras confirmar el destino SQLite
local y respaldar las copias anteriores, Genesis creó las doce hojas con
el importador selectivo. Sus catorce copias anteriores siguen intactas.
Una nueva inspección del mismo paquete propone conservar las doce.

Cotejo sin red y en solo lectura: matrices, conteos y fechas coinciden;
176 proyectos comparados en Acciones, Cliente y Comunicación sin diferencias.
Cliente usa contexto DM/cliente vacío en ambos lados para aislar las hojas.
La ficha de proyecto no se vuelve a cotejar aquí. Hay acciones en dos
proyectos, contactos/documentos en dos y comunicados en uno; los demás
no tienen capturas de esas listas en el origen. AER_ClienteGobierno está
vacía con encabezados válidos y conserva las sugerencias originales.

142 pruebas focalizadas pasan. Datos y respaldo solo bajo tmp ignorado.
No se cargó UAT/producción, no se activaron sincronizaciones programadas
ni se modificaron meses KPI cerrados. El cotejo completo de Ejecutivo IXS
con Pendientes_Minutas disponible sigue siendo el siguiente paso.

## Fuentes opcionales de Planeación y RAID

Las doce hojas predeterminadas se conservan. Para cargar estas cuatro fuentes
adicionales, seleccionarlas explícitamente en el dashboard:

```powershell
.venv/Scripts/python manage.py sync_project_sheets --hoja AER_Planeacion --hoja AER_Riesgos --hoja AER_Vacaciones --hoja IXS_Planeacion --aplicar
```

Después de exportar/verificar el grupo `hojas`, inspeccionar en Genesis:

```powershell
uv run python manage.py importar_hojas_proyecto_dm C:/beecker_dashboard/tmp/hojas-g10e5f-20261104 --hoja AER_Planeacion --hoja AER_Riesgos --hoja AER_Vacaciones --hoja IXS_Planeacion
```

Solo `--aplicar` escribe. Estas fuentes no se añaden a `STORED_SHEETS` ni a
la selección por defecto. Se exige UID/ID_Proyecto y, según la hoja,
Actividad, Riesgo, Recurso/Inicio/Fin o Tipo/DatosJSON. Se conservan las
mismas garantías de integridad, fechas, transacción e identidad local.

Carga local ejecutada el 04/11: 109 registros en 13.29 s, exportación de
30 snapshots verificada e importación de solo las cuatro hojas. Las 26
copias anteriores de Genesis permanecen intactas. Cotejo con el original:
176 Planeación y 15 RAID AER sin diferencias. Doce de 15 ejecutivos AER
ya están completos; los otros tres requieren ficha/reporte Clockify.
El cotejo integral de Ejecutivo AER sigue pendiente.

Diez pruebas nuevas por repositorio. Dashboard: 224 datastore/repositorio y
contratos en una corrida; Genesis: 1,166 del módulo completo, cobertura
92.31 %. Ruff, formato propio y mypy pasan. No se actualiza la evidencia
anterior de la suite completa del dashboard ni del frontend.
