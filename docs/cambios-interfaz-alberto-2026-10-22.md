# Revisión de interfaz solicitada por Alberto

Se aplican los puntos ratificados en la reunión del 21 de octubre. La integración con Genesis sigue pendiente de sus respuestas; la migración del frontend avanza por fases (ver `docs/plan-migracion-frontend.md`).

## Glosario

- Guía desplegable en Business Overview, agrupada por Financiera, Operaciones y Comercial.
- Acceso visible al diccionario completo y a sus fuentes y fórmulas.
- Definiciones de comparación de cuentas y distinción entre tarifa vendida e interna de banda.
- Documentación de trabajo por entregar y previas al cierre alineada con las reglas que ya utiliza el corte comercial.

## Comparación de cuentas en la pantalla principal

- Búsqueda por cuenta y criterio de facturación, utilidad bruta o margen porcentual.
- Se usa el listado completo del corte preparado; no se reordenan solamente los cinco registros del ranking anterior.
- La mitad superior e inferior forman grupos sin duplicados. Cada grupo muestra hasta cinco cuentas y permite invertir su orden mediante los encabezados.
- Los grupos son posiciones relativas; no reemplazan una clasificación de salud validada por Finanzas.
- Los valores no aplicables se excluyen del criterio correspondiente y se informa su cantidad. Los valores negativos y costos parciales se conservan.
- La búsqueda y el orden se conservan en la URL al entrar a una cuenta y regresar.
- Los cálculos originales y el modelo de clasificación del backend no se modifican.

## Tarifa de costo vendida: pendiente de datos

DataRevenue contiene Status, Cliente, Nombre de la oportunidad, Service Type, Project ID, Horas vendidas, Fecha Revenue Ajustado, USD Global Adj y Gross Margin Comercial. No contiene una tarifa de costo vendida validada.

La comparativa muestra una columna explícitamente pendiente con Florencia. No se calcula una tarifa a partir de revenue/horas, no se utiliza la tarifa de banda como sustituto y no se alteran márgenes. Falta confirmar fuente, unidad y asignación de la tarifa a la oportunidad o recurso para completar su integración.

El desglose de personas identifica su tarifa como interna de banda para evitar confusiones.

## Validación

Pruebas de plantillas, glosario, navegación, cálculo de oportunidades y reglas existentes del corte ejecutivo. Pruebas JavaScript de comparación sobre todas las cuentas, cambio de criterio, búsqueda, valores nulos/negativos, límites y ausencia de duplicados. Revisión visual de escritorio y móvil.
