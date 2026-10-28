# Manual de usuario de Dashboard Management

Borrador funcional para revisión de Wendy y Christian. Describe las funciones
disponibles; las opciones de cada persona dependen de los permisos configurados
en el despliegue. No sustituye la configuración de accesos de Genesis.

## Elegir la vista

La barra superior permite cambiar entre Business Overview, Operativa y
Comercial. Revisa el periodo y la fecha del último corte antes de comparar
cifras. Un dato pendiente no significa cero y un asterisco puede indicar
información parcial o un periodo aún abierto. Los importes se presentan en
dólares; K representa miles y M millones.

## Business Overview y cuentas

Business Overview reúne la información financiera, operativa y comercial.
Usa los filtros de periodo para trabajar con el mismo corte en todas las
comparaciones. El ranking permite acceder al listado completo de cuentas,
buscar una cuenta y cambiar su clasificación cuando se dispone de permiso.

Abre una cuenta para consultar sus proyectos, satisfacción, horas y alertas.
La comparación de márgenes y el reporte de horas son vistas de esa cuenta.
El botón Regresar conserva el origen de navegación; no es necesario volver
a buscar la cuenta desde el inicio.

En Horas por mes, selecciona año o rango de fechas, busca proyectos y elige
uno o varios antes de generar el reporte. El CSV corresponde a la selección.
Compara con Clockify usando exactamente el mismo periodo, proyectos y corte
de sincronización. Un mes en curso puede estar marcado como parcial.

## Operativa

Operativa permite revisar el portafolio, proyectos en ejecución o suspendidos,
inversión de horas y responsables de entrega. Servicio filtra la pantalla;
el selector Cuenta abre el detalle de la cuenta elegida.

Los Delivery Managers permiten profundizar en sus proyectos y horas. Los
tableros EVA presentan información de seguimiento. Antes de comparar con un
correo histórico, revisa fecha de corte, inclusión de suspendidos y el ID
completo del proyecto: un sufijo de sprint o CR puede distinguirlo del base.

En KPIs de Delivery Managers, TP es la cantidad de proyectos del corte.
T y C se presentan como porcentajes según las reglas documentadas en el
glosario de la pantalla. Las curvas muestran la evolución mensual; no
representan una predicción. Los meses futuros o sin datos no deben tratarse
como incumplimiento cero.

## Facturabilidad

Las vistas general, por especialidad, recurso y área muestran distintas
agrupaciones de los mismos datos. Revisa el glosario para distinguir horas
facturables, capacidad y porcentajes; no compares un promedio individual
con un porcentaje global como si fueran la misma medida.

En Facturabilidad por recurso, el selector **Plantilla en el mes de corte**
ofrece Todos — histórico, Activos confirmados, Bajas confirmadas y Sin estado
confirmado. Pulsa Aplicar plantilla. La tabla conserva los porcentajes
individuales; el promedio del equipo corresponde a la población seleccionada.
Los contadores indican la composición del conjunto histórico antes de filtrar.

El estado procede de Bandas/rol del mes de corte. Si eliges un mes anterior,
ves su situación en ese mes, no necesariamente la actual. La ausencia de una
banda o de horas no confirma una baja. Cuando RH no proporciona estado
suficiente, la persona se mantiene como Sin estado confirmado.

## Capacidad instalada y detalle diario

Elige el mes y espera a que termine la lectura de los proyectos. Puedes
buscar por recurso, proyecto o manager, y filtrar tecnología y concepto.
Los indicadores superiores corresponden al mes completo; los filtros actúan
sobre el listado. Cambiar la jornada modifica la referencia de capacidad,
no las horas que las personas registraron.

Pulsa el nombre de una persona desde Matriz de asignaciones o Capacidad por
recurso. Se abre su desglose con proyectos, conceptos y horas de cada día
laborable del mes. El detalle incluye todas sus asignaciones del corte,
aunque el buscador del listado estuviera limitado a un proyecto.

En pantallas pequeñas, desplaza horizontalmente la tabla dentro de su marco
para consultar las fechas. También puedes enfocar el marco con el teclado.
Las consultas sin terminar se muestran como Pendiente: sus horas no deben
interpretarse como cero. Regresar al listado recupera la vista y los filtros
que estabas utilizando. El CSV general sigue correspondiendo al listado
filtrado; abrir el detalle no cambia su selección.

## Comercial

Comercial presenta ventas cerradas, trabajo por entregar y oportunidades
previas al cierre. Utiliza el periodo y los filtros disponibles antes de
abrir el detalle de una oportunidad o cuenta. Booking, facturación y cobro
son conceptos distintos; consulta su definición en el glosario.

## Pestañas de proyecto

- **Ejecutivo:** estado general, indicadores, alertas y próximos hitos.
- **Planeación:** fechas, hitos, compromisos, vacaciones y avance del plan.
  Las horas estimadas aquí son planificación; no sustituyen el consumo real.
- **Esfuerzo:** consulta las horas reales registradas, su distribución y
  descripciones. Es la referencia para revisar horas trabajadas.
- **Recursos:** participantes y seguimiento del desempeño. Las evaluaciones
  se registran individualmente; la carga masiva espera la plantilla oficial.
- **Gestión RAID o Riesgos:** riesgos, problemas y oportunidades, con
  responsable, prioridad, seguimiento y acciones. Algunas operaciones guardan
  información en Azure; comprueba la confirmación antes de repetir una alta.
- **Acciones:** acuerdos y pendientes, fechas de compromiso y estados.
- **Cliente:** contactos, gobierno, ficha y documentación del proyecto.
- **Comunicación / Comunicados:** prepara los mensajes y revisa destinatarios
  y contenido antes de confirmar su envío.
- **Azure DevOps:** requerimientos, iteraciones, estados y seguimiento de
  los elementos vinculados. Un fallo de acceso no significa que no haya tareas.
- **IA:** genera apoyo al análisis a partir de la información disponible.
  Revisa el periodo, fuentes y contenido antes de utilizar un resultado.

Las pestañas disponibles cambian según el tipo de servicio del proyecto.

## Registrar y abrir un plan de trabajo

En Cliente, abre Documentación y agrega un vínculo. Selecciona el tipo
**Plan de trabajo** o **Roadmap**, introduce un nombre y una URL HTTP(S), y
guarda con los permisos correspondientes. No se sube ni se modifica el archivo
externo: se registra su enlace.

Al regresar a Planeación, el enlace aparece junto al roadmap o línea de
tiempo. Se abre en otra pestaña. El acceso al documento de SharePoint, Drive
u otro servicio requiere también sus permisos externos. Si no existe un
vínculo, la pantalla indica dónde registrarlo. Si falla la lectura, reabre
Planeación para reintentar. Eliminar el vínculo desde Cliente no elimina el
documento externo.

## Costos y datos incompletos

Un costo parcial puede deberse a bandas o tarifas faltantes. No debe
presentarse como costo definitivo ni ocultarse el aviso para que parezca
completo. RH debe proporcionar los datos correctos y el operador debe
sincronizar las fuentes. Completar una tarifa requiere respetar su vigencia;
no se debe aplicar una tarifa actual a todo el histórico sin validación.

## Actualización y problemas frecuentes

La plataforma usa copias sincronizadas para reducir las esperas. Recargar
el navegador no garantiza una sincronización nueva. Solicita al operador
verificar la fecha del corte si Clockify o Azure muestran cifras posteriores.

Si aparece Fuente no disponible, conserva el mensaje y el periodo para
reportarlo. No repitas una escritura cuando no sabes si ya se confirmó.
Un error en la hoja de origen puede impedir publicar un corte nuevo; la
aplicación conserva la última copia válida y advierte su antigüedad.

Al reportar un problema, incluye pantalla, cuenta o ID completo de proyecto,
periodo, acción realizada y resultado esperado. No compartas tokens, archivos
de credenciales ni contraseñas en capturas o mensajes.
