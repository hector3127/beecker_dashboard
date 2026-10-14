# Revisión de la copia del compañero

Fecha: 13 de octubre de 2026.

Origen: `C:/Users/hecto/Downloads/beecker_dashboard-main (1)/beecker_dashboard-main`.
Destino: `C:/beecker_dashboard`.

La carpeta de origen no incluye un repositorio Git, por lo que no permite
identificar ni traer una rama remota por nombre. Se compararon sus archivos
con los del proyecto local, ignorando las diferencias entre finales de línea.

## Resultado

- 361 archivos compartidos eran idénticos al iniciar la revisión.
- Los seis archivos modificados localmente también coincidían con la copia:
  `azure_stages.py`, `ixb_history.py`, `ixb_summary.py` y sus tres archivos de
  pruebas de consumo, historial y nomenclaturas.
- Los nueve archivos restantes de código, configuración y pruebas que
  diferían en la copia coinciden exactamente con el commit `c9d7b5a`,
  anterior a la incorporación del portal. Las otras diferencias son README
  y el archivo de ejemplo de configuración.
- No hay archivos nuevos en la copia del compañero respecto al proyecto.
- La copia no contiene `apps/portal` ni las pruebas del portal. No se
  sustituyeron las rutas actuales por sus rutas anteriores.

Por tanto, no había cambios funcionales nuevos de esa copia por importar.
Se conservan el portal, Facturabilidad y las mejoras locales de Capacidad
y Clockify. Se corrigieron formato, importaciones, documentación y una
comprobación de tipos de fecha en los archivos compartidos, manteniendo
su comportamiento.

No se copiaron credenciales, configuración privada, entornos virtuales,
base de datos ni cachés de la carpeta de origen.

## Respaldo y validación

El estado inicial de los seis archivos modificados está respaldado en
`tmp/backup-integracion-companero.zip`.

Las comprobaciones de estilo de Ruff y tipos de mypy pasan. Django no
detecta problemas de configuración. La suite completa de pruebas verifica
la combinación conservada.
