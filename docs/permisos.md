# Permisos y alcance de datos

Dos preguntas distintas, resueltas en un solo lugar (`apps/access`):

| Pregunta | Concepto | Ejemplo |
|---|---|---|
| ¿Qué puede **hacer**? | Capacidad | ver costos, consultar Operativa, editar acuerdos |
| ¿Sobre **qué** información? | Alcance | todo el portafolio, unas cuentas, unos proyectos |

Ocultar un elemento en el frontend no protege nada: la API y las vistas
revisan siempre. `/api/v1/me/` solo informa a la interfaz qué mostrar.

## Capacidades

Códigos estables (contrato con Genesis). Se agregan en
`apps/access/capabilities.py` junto con la pantalla o acción que protegen.

| Código | Qué permite |
|---|---|
| `view_executive` | Ver Business Overview |
| `view_operations` | Ver Operativa (incluye EVA-04, ya protegida en página y API) |
| `view_commercial` | Ver Comercial |
| `view_costs` | Ver costos, ingresos y márgenes |
| `view_agreements` | Consultar acuerdos y pendientes |
| `edit_agreements` | Crear y modificar acuerdos y pendientes |
| `edit_operations` | Modificar pendientes, hitos, riesgos y datos de proyectos (funciones de escritura del RPC) |
| `manage_integrations` | Configurar Azure DevOps y Clockify, claves y vínculos |

## RPC (`/api/rpc/`)

Cada función registrada declara su capacidad en `apps/access/rpc_policy.py`:
lectura `view_operations`, escritura `edit_operations`, configuración
`manage_integrations`; las de una cuenta aceptan también `view_agreements` y
validan el alcance (cuenta ajena: 404). Con alcance limitado solo se permiten las
funciones de cuenta; el resto trabaja con proyectos o con el equipo completo. Una
función sin política se rechaza y una prueba obliga a declarar las nuevas.

## Alcance

`AccessScope` tiene dos formas: **todo** o **limitado** a listas de cuentas
y proyectos. Reglas:

- Una cuenta se ve completa solo si está en la lista de cuentas. Tener un
  proyecto de la cuenta no abre sus totales.
- Un proyecto se ve si está en la lista o si su cuenta está permitida.
- Los "proyectos propios" de una persona (por ejemplo los de un Delivery
  Manager) llegan ya resueltos en la lista de proyectos.
- Un dato en blanco nunca concede nada.
- Los selectores reciben el alcance y filtran **antes** de calcular totales y
  rankings; las cachés se separan por alcance.
- Un detalle fuera de alcance responde **404**, no 403, para no confirmar que
  existe.

### Cifras del equipo completo

Con un alcance limitado, Operativa **no muestra** lo que no se puede recortar
por cuenta: las tarjetas EVA 1 y EVA 3, la capacidad instalada y la
facturabilidad global (la API de facturabilidad responde 403). El resto
(proyectos, salud, Delivery Managers, inversión, EVA-4 y las opciones de los
filtros) se calcula solo con lo permitido, y cada alcance tiene su propio corte
guardado.

### Acuerdos y pendientes

- **Consultar** pide `view_agreements` (o `edit_agreements`); **crear y cambiar**
  pide `edit_agreements`.
- Se ven solo los acuerdos de las cuentas del alcance. Los que no tienen cuenta
  son de quien tiene todo el portafolio. Los alias de una cuenta
  («Heineken» / «Heineken México») cuentan como la misma.
- Un acuerdo fuera del alcance responde **404**, igual que uno que no existe.
  Crear o mover un acuerdo a una cuenta fuera del alcance responde **403**.
- Cambiar `?account=` en la dirección no amplía lo que se ve: el servidor
  decide por el alcance, no por el parámetro.
- Cada registro de la API trae `actions` (`edit`, `change_status`) y la lista
  trae `can_edit`; la interfaz oculta lo que no se puede hacer, pero la
  autorización es siempre del servidor.

## Cómo se aplica

| Dónde | Cómo |
|---|---|
| Vista de página | `@require_capability("view_costs")` — sin sesión va al login, sin la capacidad 403 |
| Endpoint de la API | `permission_classes = [IsAuthenticated, capability_permission("view_costs")]` |
| Selector / servicio | recibe `scope_for(request)` y usa `filter_accounts` / `filter_projects` |

## La bandera `ACCESS_ENFORCED`

- **Apagada (por defecto):** todas las personas pueden todo y ven todo, como
  antes de existir esta app. El proveedor ni se consulta.
- **Encendida (`ACCESS_ENFORCED=1` en `.env`):** se aplican las capacidades y
  el alcance del proveedor.

Para encenderla sin dejar a nadie fuera:

```bash
python manage.py migrate
python manage.py access_setup --incluir-usuarios
```

Eso crea el grupo **Acceso completo** con todas las capacidades y suma a las
personas activas. Después se reparten capacidades por grupo en el
administrador (`/admin/`). Se puede repetir sin problema.

## Proveedores

`ACCESS_PROVIDER` apunta a la clase que responde `capabilities(user)` y
`scope(user)`. Hoy es `DjangoAccessProvider`: capacidades por permisos y
grupos de Django, y **alcance sin restricción** para quien tiene sesión,
porque Django no guarda a qué cuentas pertenece cada persona. El alcance
limitado llegará con el proveedor de Genesis.

## Pendiente de definir con Genesis

1. ¿Cómo llega la identidad a Django (sesión compartida, SSO, token, cabeceras)?
2. ¿Genesis maneja roles, permisos finos o ambos? ¿Los envía en cada petición,
   se consultan por API o se sincronizan?
3. ¿Puede expresar "estas cuentas", "estos proyectos" o "los míos"? ¿Con qué
   identificadores (ID de cliente, ROC ID, correo del DM)?
4. ¿Quién mantiene la relación persona ↔ Delivery Manager ↔ cuentas?
5. ¿Hay que registrar quién vio o cambió qué?
6. ¿Qué pantallas o campos considera sensibles?
