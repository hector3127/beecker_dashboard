# Revisión solicitada por Dirección · 17 de noviembre de 2026

Alcance: Dashboard Management local, rama `codex/hector`. Genesis y los
cierres históricos no se modifican en esta revisión. No se ha publicado ni
subido este trabajo a Git.

## Cambios aplicados

- Resumen ejecutivo y navegación en español; tarjeta Finanzas e importes en
  USD, con las escalas K/M/B explicadas.
- Glosario de indicadores con 24 conceptos, tres categorías (Financieros,
  Comerciales y Operativos) y columnas Indicador, Qué mide y Cálculo.
  Se quitan las columnas de fuentes/notas, los grupos Otros y los glosarios
  repetidos del resumen. La API conserva los metadatos de fuente.
- En el panel de Finanzas: importe cobrado, ingresos contratados, utilidad
  bruta y cobertura diferenciada entre proyectos completos, parciales y sin
  costo disponible. Los proyectos de meses futuros se identifican aparte.
- El aviso identifica proyectos con costos por revisar; conserva el motivo
  disponible, las personas sin tarifa y el carácter parcial del margen.
- Detalle financiero y comparativa de oportunidades llaman ingresos
  contratados a los importes que incluyen Confirmed. Booking se reserva para
  oportunidades ganadas. No se alteran las bases monetarias de los cálculos.
- Comercial: Ventas ganadas (booking), Ingresos confirmados futuros e Importe
  de oportunidades abiertas. La tarifa de costo de venta sigue pendiente de
  validación; no se sustituye por una tarifa interna.
- Operaciones: Saldo de capacidad (h), Consumo de capacidad (%) y, cuando el
  saldo es negativo, Exceso sobre capacidad con su magnitud positiva. El
  saldo numérico original permanece firmado en los datos. Se corrige el
  panel que todavía describía presupuesto como denominador.
- Se retiran los controles de actualización manual y captura del resumen;
  se mantiene la consulta del estado de preparación cuando faltan bloques,
  sin pedir una actualización manual al usuario ni activar tareas nuevas.
- El selector Desde–Hasta existente se conserva y se prueba su aplicación.

## Reglas contrastadas

Facturación: facturados y cobrados, incluido factoraje. Cobranza: cobrado
entre facturación del mismo periodo. Ingresos contratados: también incluye
confirmados. Utilidad: facturación menos costos; margen: utilidad entre
facturación. La comparativa por oportunidad incluye confirmados y mantiene
la desviación en puntos porcentuales. Los futuros confirmados deben estar
después del corte y dentro del rango. No se cambian cierres ni fórmulas EVA.

## Hallazgos pendientes en la fuente guardada

Auditoría de solo lectura de SQLite: DataRevenue sincronizada el 09/11/2026.
Se filtraron estados confirmados, facturados o cobrados, fechas de 2026 e
importes finitos distintos de cero. Se excluyeron filas de años distintos y
filas vacías sin importes. Los números siguientes son filas de la copia
importada y deben verificarse contra la hoja actual antes de corregirla.

| Identificador | Filas | Importe USD | Cuentas |
| --- | --- | ---: | --- |
| TBD | 1171, 1674, 1883, 3585 | 22,380.00 | Aramark |
| Vacío | 53, 85, 190, 370, 678, 685, 689, 714, 772, 4150, 4298 | 68,249.21 | Aiwyn, Atlas NextWave, Grupo Posadas, Heineken Mexico, MAS Seguros |

Estos 15 registros suman 90,629.21 USD de ingresos con un identificador por
validar. No son 15 proyectos distintos ni 90,629.21 USD de costos faltantes.
El análisis no acredita que todos deban tener horas: licencias u otros
conceptos pueden requerir un tratamiento propio. No se les asignan costos
de otro proyecto por coincidencia de cuenta o por semejanza de nombre.
Para cerrar estos casos hace falta confirmar su proyecto o su tratamiento
contable con la persona responsable de la hoja. El margen parcial existente
no se convierte en un margen definitivo por modificar textos.

## Pendientes de las siguientes revisiones

- Conciliar la cobertura financiera con la hoja vigente y validar el corte
  contable con Florencia/Luis Daniel.
- Revisar con Gera el alcance de capacidad/consumo/facturabilidad y las reglas
  diferentes de EVA1/EVA3 en Operativa. No se redefine su negocio con esta
  limpieza financiera.
- Acordar la periodicidad de actualización antes de activar un automatismo.
  La sugerencia de PDF del final de pantalla no se ha implementado.

## Verificación

95 pruebas backend de glosario, páginas, finanzas, bandas y oportunidades;
475 pruebas Node del frontend; 71 pruebas de navegador del resumen,
el glosario y los detalles de costos y márgenes, incluidos calendario, errores de preparación, CSP, teclado,
filtrado/orden y tamaños de escritorio/móvil. Ruff de los archivos Python
editados y revisión visual del glosario. La revisión visual final incluye el panel financiero y el glosario
en escritorio y móvil. No equivale a la suite completa del
repositorio ni a una conciliación de los importes reales de la base.


## Ajustes visuales posteriores del 17/11

- Botón de regreso del glosario más compacto y sin botones de información
  en las tres tarjetas.
- Importes en USD en los encabezados de Finanzas y Comercial. La nota K/M/B
  queda debajo del conjunto. Los iconos son decorativos; no inventan tendencias.
- El usuario solicita recuperar y corregir la captura: Descargar captura
  vive al final del resumen. La copia PNG elimina menús y ayudas flotantes;
  no abre el calendario ni altera el periodo. Los SVG de las ilustraciones
  y barras se preparan en la copia para conservar sus colores y dimensiones.
- Última validación: 47 pruebas de navegador del resumen/exportador y 475
  Node. Se revisan PNG reales de escritorio y móvil, CSP y píxeles de iconos.
