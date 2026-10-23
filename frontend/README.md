# Frontend del portal

HTML, CSS y JavaScript modular, sin compilación. Django solo entrega las
plantillas y los archivos estáticos; los datos llegan por `/api/v1/`.

```
templates/   única fuente del HTML (layouts, partials, pages)
static/      se publica en /static/app/
  styles/    tokens → base → layout → components → a11y, y un CSS por pantalla
  scripts/
    data/    lo único que conoce URLs y el servidor (config, api-client, url-state)
    lib/     utilidades sin DOM global (dom.js)
    ui/      componentes que dibujan lo que reciben; no piden datos
    pages/   un main.js por pantalla: pide datos y monta los componentes
  assets/    imágenes
```

## Reglas

- **Sin CSS ni JS en línea.** El CSP en modo reporte (`CSP_REPORT_ONLY=1`)
  avisa en el log (`csp`) de lo que una política estricta rechazaría.
- **Colores solo en `styles/tokens.css`.** Los demás archivos usan `var(--…)`.
  Una prueba compara los tokens con los de `portal.css` mientras convivan.
- **Nada de `innerHTML` con datos.** Se construye con `lib/dom.js`.
- **`ui/` no importa de `data/`.** Recibe datos y emite eventos; así se puede
  llevar a otra plataforma sin tocar nada de Django.
- **Cada módulo compartido se declara en el importmap de `layouts/base.html`**
  con un nombre estable (`#app/…`). Una prueba verifica que no falte ninguno.
  Los `main.js` de `pages/` se cargan con `<script type="module">` y se
  importan con sus secciones por rutas relativas (`./sections/x.js`); en
  producción `core.storage` les pone huella igual que al CSS.
- **Las rutas y la raíz de la API salen de `#app-config`**, no del código. Si
  el portal se monta en otro lugar solo cambia `FRONTEND_API_BASE`.

## Probar

```bash
node --test tests/frontend/*.test.mjs
```

Los recorridos en navegador están en `tests/e2e/` (`pytest tests/e2e`).
La página `/guia-de-interfaz/` muestra los componentes y los estados.

## Pantallas migradas

| Pantalla | Página | API |
|---|---|---|
| EVA-04 | `templates/pages/eva4.html`, `scripts/pages/eva4/` | `GET /api/v1/screens/eva4/?mes=AAAA-MM` |
| Operativa | `templates/pages/operativa.html`, `scripts/pages/operativa/` | `GET /api/v1/screens/operativa/` (corte guardado), `.../datos/?bloque=` (base y bloques), `.../facturabilidad/` |
| Capacidad diaria | `templates/pages/capacity_daily.html`, `scripts/pages/capacity_daily/` | `GET /api/v1/screens/capacidad/diaria/?mes=AAAA-MM` y `.../proyecto/?mes=...&proyecto=...&iteration=...` |

El inventario completo y actualizado de rutas se mantiene en
`docs/plan-migracion-frontend.md`. En Capacidad diaria, `model.js` conserva las
reglas previas, `view.js` construye nodos sin HTML con datos y `main.js` carga
la API (máximo dos proyectos simultáneos) y coordina filtros y exportación.
