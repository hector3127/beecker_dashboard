from django.core.cache import cache

from apps.portal.services import account_options


def test_navigation_includes_every_financial_account_and_reuses_cache(
    monkeypatch,
):
    cache.clear()
    calls = []

    def load():
        calls.append(True)
        return {
            "accounts": [
                {"name": "Arca Continental México"},
                {"name": "Heineken Mexico"},
                {"name": "Cuenta sin proyectos activos"},
            ]
        }

    monkeypatch.setattr(account_options, "load_account_profitability", load)
    names = account_options.account_names(["Cuenta antigua"])
    assert set(names) == {
        "Arca Continental México",
        "Heineken Mexico",
        "Cuenta sin proyectos activos",
    }
    assert account_options.account_names() == names
    assert len(calls) == 1
    cache.clear()


def test_source_failure_preserves_previous_choices(monkeypatch):
    cache.clear()

    def fail():
        raise ValueError("Fuente no disponible")

    monkeypatch.setattr(account_options, "load_account_profitability", fail)
    assert account_options.account_names(["Cuenta disponible"]) == [
        "Cuenta disponible"
    ]


def test_operativa_header_has_no_reference_period():
    from pathlib import Path

    template = Path("frontend/templates/pages/operativa.html").read_text(
        encoding="utf-8"
    )
    assert "Trimestre de referencia" not in template
    assert 'aria-label="Abrir detalle de cuenta"' in template
