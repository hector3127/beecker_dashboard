# Ejecución programada de la base diaria

Cómo mantener al día la base (hojas de Sheets, Azure DevOps, horas de Clockify)
y las cachés del portal sin intervención. Medido el 19/10/2026 con los datos
reales.

## Qué se programa

| Tarea | Comando | Frecuencia | Duración medida |
| --- | --- | --- | --- |
| Hojas, Azure, lecturas y catálogos | `python manage.py sync_datastore --pasos hojas,azure,lecturas,catalogos` | cada hora | añade paneles completos; las mediciones anteriores de 57 s no incluyen este paso |
| Clockify y catálogos | `python manage.py sync_datastore --pasos clockify,catalogos` | cada día, 06:00 | 161 s (ventana abierta + verificación de 26 meses) |
| Precalentar pantallas | `python manage.py warm_cache` | cada 10 min | ~60 s con la caché vacía |
| Revisar frescura | `python manage.py check_datastore --lecturas` | cada hora | segundos |

- Los pasos son `hojas`, `azure`, `clockify`, `lecturas` y `catalogos`; sin `--pasos` corren
  todos. `--sin-verificar` omite la comparación de totales de Clockify.
- `lecturas` guarda el catálogo Clockify y los campos/relaciones completos del
  panel Azure. Ver [fuentes-persistentes.md](fuentes-persistentes.md): incluye
  migración, tareas opcionales, validación de encabezados y límites del fallback.
- El horario diario no tiene que ser el único: `--pasos clockify` puede correr
  más seguido (por ejemplo a mediodía) para ver las horas del día; solo
  descarga el mes abierto (7 solicitudes, ~15 s).
- `check_datastore` termina con error si las hojas o Azure tienen más de 3 h,
  o el mes actual de Clockify más de 30 h (`--hojas-horas`, `--azure-horas`,
  `--clockify-horas`). Su «último resultado» es la alerta.

## Antes de programar nada (una sola vez)

1. Migraciones: `python manage.py migrate`.
2. Carga inicial de Clockify (~40 min para agosto de 2024 en adelante):
   `python manage.py sync_datastore --desde 2024-08`. Esto también guarda hojas
   y Azure.
3. Variables en `.env` (sin ellas todo sigue leyendo de las fuentes como antes):
   `CLOCKIFY_STORE_ENABLED=1`, `SHEETS_STORE_ENABLED=1`,
   `AZURE_STORE_ENABLED=1`.
4. `python manage.py check_datastore` debe terminar sin error.

## Windows (Programador de tareas)

```powershell
.\scripts\schedule_windows.ps1 -DryRun            # ver qué crearía, sin crear nada
.\scripts\schedule_windows.ps1                    # crear o reemplazar las 4 tareas
.\scripts\schedule_windows.ps1 -Action Status     # última ejecución y resultado
.\scripts\schedule_windows.ps1 -Action Remove     # borrarlas
```

- Crea `Beecker-Sync-Horario`, `Beecker-Sync-Diario`, `Beecker-WarmCache` y
  `Beecker-Revisar`. Cada una escribe en `logs\` y no se lanza otra vez si la
  anterior sigue corriendo. Si la computadora estaba apagada a la hora de una
  tarea, corre al encender.
- Usa `.venv\Scripts\python.exe` del proyecto; con otra ruta, `-Python`. La
  hora diaria se cambia con `-DailyAt "07:30"`.
- Las tareas corren con tu usuario y solo mientras hay sesión iniciada. Para
  un servidor que debe correr sin sesión, crea las tareas con una cuenta de
  servicio (`schtasks /RU` y `/RP`) o con «Ejecutar tanto si el usuario ha
  iniciado sesión como si no» en la interfaz del Programador.

## Azure (la plataforma Genesis: App Service Linux con contenedor)

Lo importante es **dónde vive cada cosa**:

- Las tres sincronizaciones solo escriben en **PostgreSQL**. Pueden correr desde
  cualquier lugar que llegue a la base y a las APIs.
- `warm_cache` llena la **caché del equipo donde corre**. La caché de archivos
  (`.cache/`) es del contenedor y se pierde al reiniciarlo, así que
  `warm_cache` debe correr **en el mismo contenedor** que gunicorn.
- No se debe lanzar una sincronización desde una petición web: gunicorn corta a
  los 60 s y el diario tarda más.

| Qué | Opción recomendada | Alternativas |
| --- | --- | --- |
| Sincronizaciones (hojas, Azure, Clockify) | Pipeline programado de Azure DevOps: `scripts/azure-pipelines-sync.yml` (usa el Azure DevOps que ya tienen; el agente necesita acceso al firewall de PostgreSQL) | Azure Container Apps Job o Container Instances con la misma imagen y `scripts/run_job.sh horario|diario`; Kubernetes CronJob |
| `warm_cache` | Dentro del contenedor, desde el arranque (`startup.sh`): `bash scripts/warm_loop.sh &` antes de `gunicorn`. Nunca se solapa y espera `WARM_INTERVAL` (600 s) | `cron` dentro de la imagen. Con varias instancias, cada una necesita su propio ciclo, o pasar a una caché compartida (`DatabaseCache` en PostgreSQL o Redis) y entonces cualquier job puede precalentar |
| Revisión | Último paso del pipeline (ya incluido) o `scripts/run_job.sh revisar` | Application Insights: una prueba de disponibilidad sobre un endpoint propio |

Variables que necesita el contenedor / el pipeline: `DATABASE_URL`,
`DATABASE_SSL_REQUIRE=1`, `DJANGO_SECRET_KEY`, `GOOGLE_SPREADSHEET_ID` y el
archivo de la cuenta de servicio, `CLOCKIFY_API_KEY`, `CLOCKIFY_WORKSPACE_ID`,
`AZURE_DEVOPS_ORGANIZATION`, `AZURE_DEVOPS_PAT` y las tres banderas
`*_STORE_ENABLED`.

`scripts/azure-pipelines-sync.yml` y `scripts/warm_loop.sh` **no se han probado
en Azure**: se validó su sintaxis y los comandos que ejecutan. `startup.sh` es
del repositorio de Genesis y no está aquí.

## Qué pasa cuando algo falla

- **Candados.** Cada paso toma un candado en la base: si una ejecución sigue
  corriendo cuando llega la siguiente, esa se **omite** ese paso (los demás
  corren) y lo avisa. Un candado de un proceso que murió vence solo a los 15 min
  (hojas y catálogos), 30 min (Azure) o 3 h (Clockify).
- **Clockify intermitente.** La API de reportes tiene picos (se midió una
  respuesta de 30 s y una corrida con cortes de conexión). Las fallas de
  conexión se reintentan 3 veces (esperas de 5 y 20 s). Si fallan 3 meses
  seguidos al verificar, se omite el resto de la verificación hasta la
  siguiente corrida. Un código HTTP de error (403, 500) no se reintenta.
- **Un mes que no se pudo descargar** conserva el anterior (cada mes se
  reemplaza completo y de una vez). La corrida termina con error y el siguiente
  día lo vuelve a intentar; el mes actual siempre se descarga.
- **Un proyecto de Azure que falla** conserva su copia anterior; la corrida
  avisa cuál fue.
- **Si la base no se actualiza**, las pantallas siguen funcionando con el último
  corte, y `check_datastore` falla cuando pasa de su límite.
- **SQLite (desarrollo).** Las sincronizaciones escriben mientras el panel
  lee: se activa el modo WAL y una espera de 30 s para evitar «database is
  locked». En PostgreSQL no hace falta.

## Lo que no está resuelto

- Las tareas **no están instaladas** en ningún equipo: el script de Windows solo
  se probó en modo `-DryRun` y `Status`.
- Una escritura de la app en Sheets (por ejemplo un riesgo manual) borra la
  copia de esa hoja y la siguiente lectura va a Google; no espera a la
  siguiente sincronización.
- El panel IXS y su listado RAID usan la copia completa de la base cuando está
  disponible. Otras consultas Daily y metadatos de formularios siguen pudiendo
  leer Azure en vivo; no es un modo offline global.
