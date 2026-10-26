# Fase 11: retiro de la presentación anterior de Cuenta

26/10/2026. Se retiran `portal/cuenta.html`, la vista `views.cuenta` y el
parámetro `?vista=anterior` de `/cuenta/<slug>/`, que siempre sirve
`pages/account.html` con datos por API (`screens/cuenta/`). Se conservan
`authorized_account`, `cuenta_financiera` y las rutas de horas/consumos. Sin
cambios de cifras, permisos ni diseño. Horas por mes no se toca.

Dos pruebas de `tests/portal/test_views.py` leían el HTML anterior (lista de
proyectos y alertas); ahora comprueban que la ruta sirve la plantilla
modular con la cuenta correcta. El contenido (proyectos, NPS, ROC,
oportunidades) ya está cubierto por `tests/portal/test_account_api.py` y
`tests/e2e/test_cuenta.py`.

Verificación: 1821 pruebas de portal, core, access, cuenta, flujos, todas
las cuentas, operativa y ejecutiva aprobadas tras ajustar esas dos; ruff y
mypy de pages.py aprobados.
