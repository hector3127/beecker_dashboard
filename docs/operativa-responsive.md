# Operativa y Business Overview

Se mantiene la paleta vigente. El nombre visible de Ejecutiva cambia a Business Overview; las rutas y claves de sus servicios se conservan.

Las tarjetas de Delivery Managers muestran Proyectos (en ejecución + suspendidos), Suspendidos, En tiempo, En ejecución, Inversión comercial e Inversión operativa. Se retira la fila Días restantes / Avance en horas y el riesgo alto de estas tarjetas; el detalle del DM conserva sus indicadores.

La inversión usa los mismos totales por proyecto que ya prepara el bloque de inversión: etiquetas INV_COMERCIAL e INV_OPERATIVA en Clockify para IXB/RaaS, AER y T&M activos dentro de sus fechas. Se cruza con los identificadores de los proyectos en ejecución del DM, respetando los filtros de Servicio y Cuenta. No se atribuye inversión de proyectos ajenos ni se añaden peticiones por DM. Las dos inversiones son horas, no importes monetarios. Si la consulta está incompleta o no hay proyectos cubiertos se muestra —; una consulta completada sin horas muestra 0 h.

Las respuestas progresivas de EVA y de inversión pueden terminar en cualquier orden: el navegador conserva los últimos totales y los reaplica a las tarjetas. El JSON enviado contiene solo los totales por proyecto y el estado, sin duplicar el historial mensual.

La caché del resumen de Operativa usa v9 para incorporar los identificadores por DM y el alcance AER/T&M; el agregado de inversión usa v3. Se mantienen las cachés de las fuentes, inversión y capacidad, sus tiempos de vigencia y el flujo de precarga.

Las tarjetas EVA se ordenan EVA 1, EVA 3 y EVA 4; se retiran las notas Cómo leer los EVA y Cómo se calculan los indicadores.

Las tarjetas se adaptan a tres, dos o una columna en el carrusel. Los filtros se apilan en móvil y las explicaciones de alcance se integran en secciones desplegables. La revisión estática en /revision-operativa/ usa cifras de referencia señaladas expresamente y no conecta a Sheets ni Clockify.

Validación: 88 pruebas dirigidas de Django y 36 pruebas de JavaScript; revisión de anchos de 320, 390, 820 y 1280 px sin desbordamiento horizontal de la página.
