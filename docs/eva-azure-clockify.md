# Migración de EVA 1 a Azure y Clockify

## Primer bloque: lector de Summary (28/10/2026)

Base bda55fe. El usuario autoriza iniciar la sustitución de Sheets y del
Histórico por Azure/Clockify y consultar, sin modificar, la referencia
`C:/qa_automation_platform/apps/msp_qa/`. Se revisaron block_splitter,
description_parser y azure_iterations. No se copian credenciales ni se
añaden dependencias entre repositorios.

La tabla de IXB/RaaS/SaaS referida como EVA 1 corresponde internamente a
eva2/ixb_summary y eva_cut. El módulo interno eva1 corresponde a AER/T&M.
No cambiar el módulo equivocado por la nomenclatura de las pantallas.

### Implementado

- Lectura GET del Summary/description con el cliente Azure existente.
  Contrato oficial: [Projects Get](https://learn.microsoft.com/en-us/rest/api/azure/devops/core/projects/get?view=azure-devops-rest-7.1).
- Diccionario explícito de etiquetas en español, inglés y portugués para
  DM, ID, servicio, nombre, cliente, inicio, fin, presupuesto y estado.
  Normaliza acentos y separadores. Reconoce metadatos de roles/duración
  por separado y reporta etiquetas desconocidas sin adivinar equivalencias.
- Texto y HTML, incluidos pares de celdas de tablas; sin ejecutar HTML.
- Bloques S#, CR, CR#, y compuestos CR#_S#. Reconoce el caso real
  `CHANGE REQUEST 2 / SPRNT 1`. CR y CR1 permanecen distintos.
- Horas con sufijos de bloque quedan en el bloque correspondiente.
  No se heredan presupuesto, fechas, ID ni estado a bloques hijos.
  Solo nombre, cliente, servicio y DM explícitos del preámbulo son comunes.
- Encabezados duplicados, campos contradictorios, fechas inválidas y
  presupuestos ambiguos quedan como incidencias. No gana el último valor.
- Función financiera aislada con las reglas recién autorizadas por el
  usuario: ETC = Budget - Burn; desviación = min(ETC, 0); avance =
  Burn/Budget × 100. Budget cero deja avance pendiente; Burn ausente no
  equivale a cero. No modifica todavía los cálculos de la pantalla activa.
- Comando audit_eva_azure: solo lee proyectos seleccionados, escribe un
  informe local y no publica cortes. Puede reproducir muestras sin red.

```powershell
.venv/Scripts/python.exe manage.py audit_eva_azure --project AMK.012 --project MCC.023 --output tmp/eva-azure-audit.json
# Reproducción de una muestra local {"PROYECTO": "descripción"}:
.venv/Scripts/python.exe manage.py audit_eva_azure --project AMK.012 --input tmp/azure-summary-samples.json --output tmp/eva-azure-audit.json
```

Los informes pueden contener nombres de personas; son artefactos locales,
no se comitean. `ready` significa interpretación estructural completa del
Summary, no aprobación de la relación Clockify ni integridad histórica.

### Evidencia real y pruebas

Se consultaron AMK.012, MCC.023 y NSC.B.003 por GET con la conexión actual:
8 bloques, 7 estructuralmente completos, ningún proyecto fallido.
AMK.012 tiene CR2/S1, CR1/S1 y S1: se mantienen separados. CR1/S1 trae
`29/10/025`; se reporta invalid_start, no se convierte a 2025 por suposición.
Los valores `90 hrs.` y `412 a utilizar` se reconocen como horas.
No se deduce que AMK.012_CR del portal corresponde a CR1/S1 o CR2/S1.
Muestras e informe locales en tmp/azure-summary-samples.json y
tmp/eva-azure-audit.json, obtenidos el 28/10/2026.

`pytest tests/azure_devops tests/datastore/test_azure_store.py -q --no-cov
--tb=short`: 75 aprobadas, incluidas 26 nuevas de bloques, conflictos,
HTML, fechas, presupuestos, fórmulas y comando offline sin conexión Azure.
Ruff/check y format de los cinco archivos Python del bloque aprobados;
manage.py check sin incidencias. No se requieren pruebas visuales: no hay
cambios de frontend ni de rutas activas. No se afirma regresión completa.

### Continuación necesaria antes de retirar Sheets

1. Ampliar la auditoría al inventario autorizado completo. El comando pide
   proyectos explícitos; no implica que el catálogo actual sea exhaustivo.
2. Persistir versiones del Summary y el origen/fecha de cada campo en la
   base actual; no llevar peticiones por proyecto al render de EVA.
3. Relación explícita de cada bloque con proyecto/tarea/tags de Clockify.
   Verificar CR vs CR1 y los compuestos con evidencia, sin unir por parecido.
4. Burn facturable en Start–Finish, limitado al corte, con cobertura de
   sincronización comprobada y asignación exclusiva por nomenclatura.
   No sumar dos veces registros de proyectos/bloques que comparten catálogo.
5. Estado y conteos por iteración/bloque, incluyendo suspendidos y
   excluyendo cerrados/completados. Riesgos activos al corte: guardar o
   consultar revisiones; el estado actual no reconstruye el estado pasado.
6. Cortes históricos locales y KPI mensual (último lunes–jueves del mes),
   permisos, filtros y contratos de API existentes; comparar con evidencia
   antes de activar la nueva fuente. No inventar históricos anteriores.

La fuente activa de EVA sigue igual al cierre de este primer bloque.
No se ha aplicado migración de base, modificado Sheets/Azure/Clockify ni
silenciado la incidencia #REF! de origen. PostgreSQL espera Genesis y las
evaluaciones esperan la plantilla oficial. Sin push.
