# Ejecutiva: orden y adaptación de la interfaz

Se conservan los colores existentes: banner violeta/rosa, tarjetas claras,
acentos verdes de Operations y magenta de Comercial. No se aplica ninguna
de las paletas exploradas en las maquetas.

Orden: resumen financiero/operativo/comercial, rentabilidad mensual, cuentas,
proyectos que requieren decisión y acuerdos.

Se reemplazan las reglas acumuladas que fijaban las tarjetas a 328 px y
reducían textos a 8–9 px. `executive_layout.css`, limitado a `.executive-page`,
controla alturas naturales, columnas adaptables, márgenes y campos.
En móvil, prioridades, cuentas y acuerdos se muestran en fichas, conservando
el contenido y las acciones existentes. El calendario conserva su formulario
y sus atajos, con espacio para móvil.

Los mensajes sobre filtros de Operativa y la antigua leyenda de datos de
ejemplo se retiran. Los importes se identifican como USD en sus componentes.
Las explicaciones de fuentes y clasificación se integran en desplegables.
Los avisos de errores, cifras parciales y datos pendientes se conservan.

La gráfica usa el ancho real de su contenedor y se redibuja al cambiarlo,
sin consultar de nuevo la API. Hasta seis meses caben en móvil; los rangos
largos conservan desplazamiento dentro de la gráfica para poder leerlos.
Se mantienen los valores del servidor y los colores de sus tres series.
Los meses sin margen interrumpen la línea y los costos pendientes no se
representan como costos cero.

No se cambian cálculos, fuentes, cachés, periodos ni endpoints de negocio.
Las pruebas frontend verifican datos preparados, periodos, valores negativos,
meses pendientes y rangos largos. También se validan las vistas de Django.

La carpeta `design/executiva-propuesta/revision-actual` contiene una captura
HTML generada con los templates y assets reales para la comprobación visual.
Usa cifras de referencia y no ejecuta consultas de negocio. No es otra
propuesta de colores ni la página conectada a datos reales.
