# Integracion local del ZIP (3) (2) - 15 de octubre de 2026

Se integraron las mejoras del ZIP sobre el proyecto activo, preservando .env,
credenciales, cache y base de datos local. Se guardaron respaldos del codigo
modificado y una copia consistente de SQLite en tmp/backup-version-3-2-*.
No se importaron archivos temporales de conciliacion ni previews de design.

## Preferencias existentes conservadas

- Top cuentas no sanas muestra cinco; el listado completo conserva todas.
- Se conserva el enlace Panel anterior en la navegacion comun.
- DataRevenue es la primera referencia de cuenta por ID. Para proyectos sin
  revenue, se usa el ID exacto del historico. A:I tiene prioridad; el bloque
  derecho permite resolver una cuenta regional cuando A:I no la identifica.
  Un nombre generico de Arca no asigna automaticamente todos los paises a Mexico.
- Las variantes S# solo se separan financieramente si figuran de forma
  independiente en DataRevenue; en otro caso sus horas pertenecen al ID base.
- Los proyectos sin revenue mantienen su costo y perdida en USD y afectan
  al margen de la cuenta. Las cantidades incompletas siguen provisionales.

Django no requiere migraciones nuevas para esta integracion.
