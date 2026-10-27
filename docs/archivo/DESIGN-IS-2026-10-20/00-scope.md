# 00 · Alcance de la auditoría

**Fecha:** 2026-10-20
**Superficie auditada:** pantalla **EVA-04 Report** (`/operativa/eva-4/`), con el mes `2026-10`.

- Plantilla: `apps/portal/templates/portal/eva4.html` (35 líneas, CSS y script en línea).
- Base común: `apps/portal/templates/portal/base.html` y `apps/portal/static/portal/css/{portal,accessibility,navigation}.css`.
- Datos: `apps/portal/services/eva4.py`, `eva4_hours.py`.

**Cómo se midió:** se renderizó la página real con los datos de la base local
(78,038 bytes, 164 procesos). No se probó en un navegador real: no hay medición
de tiempo de carga ni capturas, y los tamaños de pantalla se infirieron de las
reglas `@media`. Lo inferido va marcado **INFERIDO**.

**Usuario principal:** Delivery Managers y dirección que revisan el consumo de
horas de los procesos de automatización (ROC y servicios afines).
**Tarea principal:** ver, por proceso, cuántas horas se invirtieron frente al
límite del servicio y cuáles clientes vencen o se pasan.

**Restricciones:** HTML/CSS propio en plantillas Django, sin framework de
componentes; encabezados de la tabla iguales a los del Excel (decisión del
usuario, 2026-10-20); el cálculo de horas (ROC ID + tag del BOT) no se debe tocar.

**Referencias:** el Excel «EVA-04 Report» del que se copian los encabezados.

**Alcance excluido:** otras pantallas del portal, el cálculo de datos y la
sincronización de la base.
