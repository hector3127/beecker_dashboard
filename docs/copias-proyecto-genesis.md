# Copias manuales de proyectos para Genesis

Fuente: `apps/datastore/services/project_sheets.py`,
`apps/datastore/management/commands/sync_project_sheets.py` y
`tests/datastore/test_project_sheets.py`.

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
