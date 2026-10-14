# Integración del RAR del compañero

Fecha: 13 de octubre de 2026.

Origen: `C:/Users/hecto/Downloads/beecker_dashboard-main (1).rar`.
Destino: `C:/beecker_dashboard`.

Se incorporaron 24 archivos de la copia, incluyendo pantallas renovadas,
funciones nuevas y pruebas. Se combinaron las diferencias compartidas para
conservar las correcciones locales; no se reemplazó el proyecto completo.

## Funcionalidad incorporada

- Comercial: Backlog_Proyectos, filtros, paginación, pipeline y USD.
- Operativa: apertura desde caché y actualización por bloques mediante
  `/operativa/datos/`, con inversión por etiquetas y capacidad diaria.
- EVA 3: proyectos AER/T&M y enriquecimiento de consumos pendientes.
- EVA 1 y EVA 2: resumen IXB/RaaS según las pantallas del RAR.
- Delivery Manager: equipo, riesgos, inversión e historial mensual.
- Cuenta: consumo, presupuestos, alertas y consultas de consumos por bloques.
- Panel anterior: mejoras de navegación y acceso a capacidad.
- Fechas Clockify: layout completo MPB y equivalencias únicas AER/TYM.

## Ajustes locales preservados

- Facturabilidad: DEV, QA, ROC, ARQ, BA y SM, con capacidad calculada solo
  para personas vigentes con horas positivas en el mes. La cifra de 58
  corresponde a los datos de septiembre revisados; no es un número fijo.
- Fuente de personas: Bandas/rol propio; festivos y avisos de meses sin
  plantilla histórica.
- Lectura MPB con encabezados alternos, fecha fin en columna I y avisos
  controlados cuando MPB no se puede interpretar.
- Delivery Managers de AER/T&M desde MPB e historial de proyectos.
- Exclusión de proyectos sin Delivery Manager del ranking mejor/peor.
- Configuración que permite desactivar caché de Sheets con cero.

Las copias facturability_imported y facturability_roster del RAR contienen
las mismas funciones locales. Se reutilizaron los módulos canónicos sin
duplicarlos ni regresar al cálculo anterior basado en Recursos.

## Correcciones de integración

- Tipos, formato e importaciones del código nuevo.
- Validación de respuestas incompletas de EVA.
- No se consultan riesgos AER cuando no hay proyectos que consultar.
- Errores de origen se conservan en el detalle del manager y de cuenta.
- Se conservan enlaces de cuenta a proyecto y de manager a cuenta.
- Ruta compatible `/operativa/operations-resumen/` junto a la nueva
  `/operations/resumen/`.
- Pruebas actualizadas para las nuevas pantallas y la carga asíncrona.
- pytest recopila solo `tests/`; las copias temporales no se recopilan.

No se copiaron credenciales, `.env`, entornos virtuales, SQLite ni cachés
del RAR. El código previo de los archivos compartidos está respaldado en
`tmp/backup-antes-integracion-rar.zip`. Los archivos nuevos pueden
identificarse con `git status`.

## Validación

- 1,053 pruebas aprobadas; cobertura de 90.50%.
- Ruff y mypy sin errores.
- Django system check sin errores.

La validación automatizada usa dobles para las nuevas fuentes externas.
No se efectuó una revisión visual en navegador ni una consulta integral
en vivo de todas las pantallas nuevas.
