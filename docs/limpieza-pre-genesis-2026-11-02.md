# Limpieza de la referencia antes de Genesis

Autorización del usuario, 02/11/2026: preparar una versión estable del dashboard,
retirar archivos de datos/integraciones innecesarios y publicar los cambios.

## Retiro de archivos generados del código versionado

Se retiran de Git, conservándolos físicamente en el equipo:

- `styles.json`: salida vacía de una inspección manual de estilos; el único
  consumidor encontrado es un test_zz local que la escribe, no la aplicación.
- `tmp/boss-september-people.json`
- `tmp/boss-workbook-data.json`
- `tmp/facturability-tests.txt`
- `tmp/own-september-gse.json`
- `tmp/people-comparison-output.txt`
- `tmp/people_comparison.json`
- `tmp/reconciliation-output.txt`
- `tmp/september-reconciliation.json`

Los ocho archivos tmp son salidas de auditoría/reconciliación, sin referencias
en aplicación, pruebas permanentes o scripts versionados. No son fixtures ni
fuentes del producto. `.gitignore` ya excluía tmp; se agregan exclusiones exactas
para otros artefactos locales y auxiliares test_zz. La limpieza no purga el
historial Git ni sustituye un procedimiento de revocación de credenciales.

## Se conserva

- `.env`, `key.json`, SQLite, copias WAL, respaldos, CSV y exportaciones locales:
  no se eliminan ni se publican. No se ejecuta migrate ni sync en la base real.
- Integraciones Azure/Clockify/Sheets/Drive/Gmail/IA activas, con sus contratos.
- `core/rpc/registry.py` y servicios registrados: consumidores en API/precarga.
- Transporte RPC montado exclusivamente por pruebas y sus pruebas funcionales.
- Fixtures, JSON de cálculos y snapshots con consumidores. No se retiran pruebas
  solo por ser antiguas; los retiros de diseño se rigen por cierre-fase-11.md.
- Scripts de operación/despliegue y herramientas de migración aún documentados;
  conservar no equivale a usarlos dentro de Genesis.
- Cambios locales ajenos ya presentes en tests/tools y archivos staged retirados:
  no se revierten ni se incorporan al commit de esta limpieza.

Genesis no se modifica. El plan/inventario de la integración se incorpora al
dashboard como documentación; ninguna integración nueva queda activa por esto.


## Evidencia de publicación

Limpieza confirmada en 412b6b3: nueve archivos eliminados únicamente del
índice, 3,648 líneas menos. Su existencia local se verificó después del
commit. El diff staged ajeno se comparó byte a byte y quedó intacto.
6b10ea0 corrige el doble de prueba de capacidad para no requerir key.json y
explicita tipos/cobertura no nula del guardado derivado de Azure; no cambia
sus resultados válidos ni las reglas del producto.

La documentación y .gitignore se publican en un bloque posterior con la
validación final. G00 registra los límites del CI legado, que no se ocultan
ni se solucionan excluyendo pruebas funcionales. No se borra historial Git.
