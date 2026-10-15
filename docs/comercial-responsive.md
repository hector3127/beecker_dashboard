# Comercial y navegación de regreso

Se conserva la paleta y la lógica comercial: lectura del backlog, conversiones USD, filtros, totales, probabilidades y caché.

El resumen comercial agrupa los cuatro indicadores dentro de una tarjeta. Los importes tienen una fila completa para evitar cortes. Etapas y cuentas se presentan en tarjetas con botones Ver más consistentes. El pipeline se organiza en tablas de ancho completo, con desplazamiento horizontal dentro de cada tarjeta y la columna de cuenta fija; en móvil se indica cómo ver meses y totales. El selector de año sigue visible en móvil, en un control blanco con icono de calendario, etiqueta Año de referencia y año destacado. Los avisos de importes o tipos de cambio pendientes se muestran dentro del resumen; las probabilidades ficticias mantienen su advertencia.

Comercial ofrece Regresar a Business Overview únicamente cuando se abre desde Ver detalle de Comercial en Business Overview, mediante origen=business-overview. La navegación directa y desde el menú no muestran ese enlace. Cuando hay un rango de fechas válido seleccionado se conserva al regresar. El detalle de proyecto muestra Regresar a Operativa antes de cargar sus datos. Los enlaces de regreso existentes de EVA, Facturabilidad, DM, inversión, capacidad y listados indican explícitamente Regresar a Operativa. Cuentas y costos mantienen sus rutas de regreso correspondientes, incluyendo el retorno de costos a la cuenta y los periodos seleccionados. No se depende de history.back ni se abren pestañas nuevas.

Validación: 103 pruebas dirigidas de Django, 36 pruebas de JavaScript y Django check. En navegador se verificaron Ver más, apertura/cierre del detalle, regreso a Business Overview y anchos 320, 390, 820 y escritorio sin desbordamiento horizontal de la página. Las tablas de meses conservan desplazamiento interno.

La revisión /revision-comercial/ usa cifras y cuentas de referencia señaladas expresamente, sin conexión a las fuentes. La aplicación sigue usando los servicios existentes.
