# Manual de usuario: la base de datos del dashboard

Guía para entender, **sin conocimientos técnicos**, de dónde salen los datos
del dashboard, cada cuánto se actualizan y qué hacer cuando algo no cuadra.

> El detalle técnico completo está en
> [llenado-de-la-base.md](llenado-de-la-base.md). Este manual lo resume en
> lenguaje sencillo.

---

## 1. La idea en una frase

El dashboard **ya no pregunta a Clockify, Google Sheets y Azure DevOps cada vez
que abres una pantalla**. Una vez por hora (y una vez al día para las horas)
un proceso automático **copia** esa información a una base de datos propia, y
las pantallas leen de ahí.

**Analogía:** antes, cada vez que alguien pedía un dato, un mensajero iba a
tres oficinas distintas a buscarlo (lento). Ahora, un mensajero hace el recorrido
cada hora, deja todo en un archivero y todos consultan el archivero (rápido).

**Qué cambia para ti:**

| Antes | Ahora |
|---|---|
| Algunas pantallas tardaban de decenas de segundos a minutos | La mayoría de las pantallas abre en menos de un segundo (en las mediciones, 36 de 40) |
| Siempre se veía el dato "en vivo" | Se ve el dato **de la última copia** (hasta 1 hora de diferencia en hojas y Azure; 1 día en horas de Clockify) |

---

## 2. Qué información se copia

Son tres fuentes, y cada una se copia a sus propias tablas.

### 2.1 Google Sheets (cada hora)

Se copian **12 hojas** del Spreadsheet. Cada una se guarda completa:

| Hoja | Qué contiene (en palabras simples) |
|---|---|
| Proyectos | La lista de proyectos: cliente, responsable, servicio, estado, fechas y presupuesto |
| Historico_Proyectos | Las etapas por las que ha pasado cada proyecto y sus fechas |
| MPB | Contratos y presupuesto de horas por proyecto |
| ROC | Procesos de automatización y renovaciones |
| DataRevenue | La facturación: cuánto, a quién, en qué fecha |
| Recursos | Qué persona está asignada a qué proyecto |
| Riesgos | Riesgos capturados por proyecto |
| Bandas/rol | La banda y el rol de cada persona, y su identificador en Clockify |
| Master rates | La tarifa por hora de cada banda |
| Banda salarial | Los salarios por banda |
| Backlog_Proyectos | Las oportunidades comerciales (ganadas y abiertas) |
| CatalagoProyectos | El catálogo de proyectos con su cliente y servicio |

### 2.2 Azure DevOps (cada hora)

Por cada proyecto de Azure se copia:
- Sus **tareas y elementos de trabajo** (hasta los 1,000 más recientes).
- Sus **riesgos y oportunidades** abiertos (el "RAID").
- Sus **iteraciones** (sprints) con fechas.

### 2.3 Clockify (cada día)

Se copian **todas las horas registradas por todo el equipo**, un mes completo a
la vez. Por cada registro se guarda: la persona, el proyecto, la tarea, el día,
cuántas horas, las etiquetas y si es facturable.

Los meses ya cerrados no cambian, así que no se vuelven a descargar. Cada día se
vuelve a copiar el mes actual (y el anterior si estamos a principios de mes), y
se revisa que los meses antiguos **sigan coincidiendo** con Clockify. Si alguien
modificó horas de un mes antiguo, ese mes se vuelve a copiar solo.

### 2.4 Catálogos (después de cada copia)

Con lo que ya se copió, el sistema arma tres listas ordenadas: **clientes,
personas y proyectos**. Su utilidad es reunir en uno solo los nombres que se
escriben distinto en cada hoja ("Acme", "ACME", "Acme  Corp."). **Todavía no se
ven en ninguna pantalla**: se consultan y corrigen desde el administrador.

---

## 3. Qué pantalla usa qué información

| Pantalla | De dónde sale lo que muestra |
|---|---|
| **Business Overview** (portada) | Facturación y cobranza (DataRevenue), costos (horas de Clockify × tarifas de Bandas/rol y Master rates), ventas y oportunidades (Backlog_Proyectos), presupuesto y avance de horas (MPB, Historico_Proyectos y Clockify) |
| **Todas las cuentas / Detalle de costos** | Facturación (DataRevenue) y costos (horas de Clockify × tarifa) |
| **Operativo** | Proyectos (MPB, ROC), horas (Clockify) y, en IXB/RaaS, avance (Azure DevOps) |
| **EVA 1 y EVA 2** (IXB y RaaS) | Hojas de proyectos, horas de Clockify y avance de Azure DevOps |
| **EVA 3** (AER y T&M) | MPB y las horas de Clockify |
| **EVA 4** | ROC y el consumo de horas por tarea y mes de Clockify |
| **Delivery Manager** | Sus proyectos (hojas), horas (Clockify) y avance (Azure) |
| **Cuenta** | Los proyectos del cliente (MPB, Historico_Proyectos, ROC, DataRevenue) y sus horas |
| **Proyecto** | Datos del proyecto (hojas), horas (Clockify), etapas, riesgos y sprints (Azure) |
| **Comercial** | Backlog_Proyectos |
| **Capacidad instalada** | Recursos, Bandas/rol, MPB, ROC y horas de Clockify |
| **Facturabilidad e Inversión** | Horas de Clockify frente a la capacidad del equipo (Bandas/rol y Recursos) |

> Esta tabla se hizo leyendo el código; si una pantalla muestra algo que no
> coincide, avísalo para corregir el manual.

---

## 4. ¿Qué tan al día están los datos?

Los datos son **tan nuevos como la última copia**:

| Información | Se actualiza | Diferencia máxima normal |
|---|---|---|
| Hojas de Google Sheets | cada hora | hasta 1 hora |
| Azure DevOps | cada hora | hasta 1 hora |
| Horas de Clockify | cada día | hasta 1 día |

**Ejemplo:** si alguien corrige una cifra en `DataRevenue` a las 10:05 y la copia
horaria corrió a las 10:00, el dashboard mostrará la cifra nueva hasta las
11:00. No es un error: es el funcionamiento normal.

**Hojas que no se copian.** Algunas hojas se siguen leyendo directo de Google
(por ejemplo `Clockify_Vinculos`, `Sprints` y `Minutas`). Un cambio en ellas se
ve casi de inmediato, sin esperar la copia horaria.

---

## 5. Cómo saber si todo está funcionando

### 5.1 Revisar que la base esté al día

Abre una terminal en la carpeta del proyecto y ejecuta:

```bash
python manage.py check_datastore
```

Verás algo así:

```
hojas: hace 0.4 h (limite 3 h)
azure: hace 0.4 h (limite 3 h)
clockify (mes actual): hace 2.8 h (limite 30 h)
```

| Resultado | Significa |
|---|---|
| Cada línea muestra "hace X h" dentro del límite | Todo bien |
| Una línea dice **VENCIDO** | Esa fuente lleva más tiempo del permitido sin copiarse. Ver 5.2 |
| Dice **nunca sincronizado** | Esa fuente jamás se ha copiado. Hay que hacer la carga inicial (ver 6.3) |

Límites: hojas y Azure, **3 horas**; horas de Clockify, **30 horas**.

### 5.2 Si algo aparece como VENCIDO

La causa casi siempre es que **la tarea automática no se está ejecutando**
(por ejemplo, no está programada en este equipo o el equipo estaba apagado).
Actualiza a mano:

```bash
python manage.py sync_datastore --pasos hojas,azure
```

Tarda cerca de un minuto. Después vuelve a correr `check_datastore`.

---

## 6. Tareas habituales

### 6.1 Actualizar a mano hojas y Azure (≈ 1 minuto)

```bash
python manage.py sync_datastore --pasos hojas,azure,catalogos
```

Úsalo cuando acabas de cambiar algo en una hoja y quieres verlo ya.

### 6.2 Actualizar las horas de Clockify (≈ 3 minutos)

```bash
python manage.py sync_datastore --pasos clockify,catalogos
```

### 6.3 Volver a copiar un mes concreto de Clockify

Úsalo si alguien editó horas de un mes y quieres verlas ya:

```bash
python manage.py sync_datastore --mes 2026-10
```

### 6.4 Carga inicial (solo la primera vez o si la base está vacía)

```bash
python manage.py sync_datastore --desde 2024-08
```

Puede tardar **cerca de una hora**. No la interrumpas.

### 6.5 Programar que se actualice solo

Está explicado en [ejecucion-programada.md](ejecucion-programada.md). Lo
recomendado:

| Qué | Cada cuánto |
|---|---|
| Hojas y Azure | cada hora |
| Horas de Clockify | cada día |

### 6.6 Activar o desactivar la lectura desde la base

En el archivo `.env` hay tres interruptores, uno por fuente:

```
CLOCKIFY_STORE_ENABLED=1
SHEETS_STORE_ENABLED=1
AZURE_STORE_ENABLED=1
```

- **Solo vale `1`** para activarlos. Con `true`, `yes` o vacío quedan
  **apagados sin avisar**.
- Si un interruptor está apagado, esa fuente se consulta en vivo, como antes.
- Después de cambiar el `.env`, **reinicia el servidor**.

---

## 7. Preguntas frecuentes

**Cambié una hoja y el dashboard sigue mostrando el dato anterior.**
Es normal si la hoja es una de las 12 copiadas: se verá en la siguiente copia
(máximo 1 hora). Para verlo ya, usa 6.1.

**Registré horas en Clockify y no aparecen.**
Las horas se copian una vez al día. Para verlas ya, usa 6.2.

**Un proyecto muestra "No se encontró una coincidencia única en Clockify".**
No es un problema de la base. Falta ligar el ID del proyecto con su proyecto de
Clockify en la hoja `Clockify_Vinculos`. Esa hoja se lee en vivo, así que basta
con agregar la fila y recargar.

**¿La base "pisa" lo que escribo en Sheets?**
No. La base solo **lee** de Sheets, Clockify y Azure; nunca escribe en ellos. Lo
que escribes sigue siendo la fuente verdadera.

**¿Qué pasa si la copia falla a medias?**
Nada se mezcla. Cada fuente se guarda "de una sola vez": las pantallas siguen
viendo la copia anterior hasta que la nueva termina bien. Si un proyecto de
Azure o un mes de Clockify falla, se conserva su copia anterior.

**¿Qué pasa si dos copias se lanzan al mismo tiempo?**
El sistema usa un "candado": la segunda se omite con un aviso. No se duplica
nada.

**¿Se puede perder información?**
La base es una **copia** de las fuentes, no la fuente. Si se borrara, se
reconstruye con la carga inicial (6.4).

**Una cifra de una pantalla no coincide con la hoja.**
1. Revisa la antigüedad con `check_datastore` (5.1).
2. Actualiza a mano (6.1 o 6.2) y vuelve a mirar.
3. Si sigue sin coincidir, anota la pantalla, el dato y la hoja o proyecto, y
   repórtalo al equipo técnico.

---

## 8. Glosario

| Término | Significa |
|---|---|
| **Base de datos** | El archivero donde se guarda la copia de la información |
| **Sincronizar / copiar** | Traer la información de Sheets, Clockify o Azure a la base |
| **Fuente** | El lugar de donde viene el dato original (Sheets, Clockify o Azure) |
| **Vencido** | Una fuente lleva más tiempo del permitido sin copiarse |
| **En vivo** | Consultar directamente la fuente en ese momento, sin pasar por la base |
| **Carga inicial** | La primera copia completa; tarda cerca de una hora |
| **Candado** | Marca que evita que dos copias corran a la vez |
| **Alias** | Otra forma de escribir el mismo nombre ("ACME" y "Acme") |
| **RAID** | Riesgos, supuestos, incidencias y dependencias de un proyecto |
| **Burn / consumo** | Horas ya trabajadas frente al presupuesto |
| **ETC** | Horas que faltan: presupuesto menos consumo |

---

## 9. A quién acudir

- Si `check_datastore` falla y 5.2 no lo resuelve, o la carga inicial se
  interrumpe: equipo técnico.
- Si una hoja cambió de estructura (se movieron columnas): avisar antes de
  moverlas, porque los catálogos se leen por posición y por encabezado.
