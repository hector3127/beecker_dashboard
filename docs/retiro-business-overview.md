# Fase 11: retiro de la presentación anterior de Business Overview

26/10/2026. Se retiran `portal/ejecutiva.html`, sus cinco parciales
(`_executive_*`, `_hero`, `_period_picker`), las hojas `executive_*.css`, los
scripts `executive_*.js` y el parámetro `?vista=anterior` de `/`. La ruta
sirve `pages/executive.html` y el corte llega por `screens/executive/`.

`views.ejecutiva` se conserva como entrada de precarga: `warm_cache` y
`executive_refresh` la llaman; ahora delega en `pages.executive`, con los
mismos permisos y periodo. No borrar ese punto de entrada. Sin cambios de
cifras, fuentes ni diseño.

Nueve pruebas Node ejecutaban los scripts anteriores (`executive_*`,
`financial`, `account_financials`); su lógica ya tiene pruebas equivalentes en
`format`, `ranking`, `monthly_chart`, `calendar` y `month_picker`, y las de
navegador de `test_ejecutiva*`, `test_acuerdos` y `test_flujos`. Las pruebas de
servidor que leían el HTML anterior ahora comprueban `pages/executive.html`; la
de alcance limitado comprueba además la API (`screens/executive/`), que es la
que entrega los datos y solo contiene la cuenta permitida.

Verificación: 1841 pruebas de portal, core, access, ejecutiva, acuerdos,
flujos, operativa, captura y comercial aprobadas; 472 Node aprobadas; ruff
aprobado.
