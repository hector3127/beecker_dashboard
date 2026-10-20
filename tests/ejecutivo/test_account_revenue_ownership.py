from apps.ejecutivo.services.account_view import load_mpb_projects


class Reader:
    def __init__(self, sheets):
        self.sheets = sheets

    def sheet_exists(self, name):
        return name in self.sheets

    def read_values(self, name):
        return self.sheets[name]


def test_regional_mpb_account_uses_exact_revenue_project_id_for_2026():
    header = ["CLIENTE", "ID", "NOMBRE", "SERVICE", "ESTATUS"]
    rows = [
        header,
        ["Regional", "TYM.NSC.CAM.001", "Transport", "T&M", "Finalizado"],
        ["Regional", "TYM.NSC.CAM.002", "Other", "T&M", "Finalizado"],
        ["Regional", "TYM.NSC.CAM.003", "Old", "T&M", "Finalizado"],
    ]
    revenue = [
        ["Status", "Account", "", "", "ID", "", "Date"],
        ["Confirmed", "Panama", "", "", "TYM.NSC.CAM.001", "", "2026-07-01"],
        ["Confirmed", "Other", "", "", "TYM.NSC.CAM.002", "", "2026-07-01"],
        ["Confirmed", "Panama", "", "", "TYM.NSC.CAM.003", "", "2025-07-01"],
    ]
    result = load_mpb_projects(
        Reader({"MPB": rows, "DataRevenue": revenue}), "Panama"
    )
    assert [p["id"] for p in result] == ["TYM.NSC.CAM.001"]
    assert result[0]["servicio"] == "T&M"


def test_account_excludes_previous_year_mpb_project_before_totals(monkeypatch):
    from datetime import date
    from unittest.mock import Mock
    from apps.ejecutivo.services import account_view as view

    reader = Reader(
        {
            "MPB": [
                ["ID", "INICIO", "FIN"],
                ["OLD", "2025-01-01", "2025-12-31"],
                ["CURRENT", "2026-01-01", "2026-12-31"],
            ]
        }
    )
    reader.prefetch = lambda names: None
    monkeypatch.setattr(
        view,
        "read_history_projects",
        lambda *args: {"old": {"id": "OLD"}, "current": {"id": "CURRENT"}},
    )
    monkeypatch.setattr(view, "read_roc", lambda *args: [])
    monkeypatch.setattr(view, "read_project_statuses", lambda *args: {})
    monkeypatch.setattr(view, "load_mpb_projects", lambda *args: [])
    monkeypatch.setattr(
        view, "load_opportunities", lambda *args: {"items": [], "source": ""}
    )
    monkeypatch.setattr(
        view,
        "build_history_item",
        lambda pid, *args: {
            "id": pid["id"],
            "nps": 90 if pid["id"] == "OLD" else 80,
            "servicio": "AER",
            "estado": "Completado",
            "clockifyPending": True,
        },
    )
    result = view.build_account_view(reader, "Acme", Mock(), date(2026, 10, 14))
    assert [p["id"] for p in result["proyectos"]] == ["CURRENT"]
    assert result["nps"] == 80
    assert result["mpbPendientes"] == 1


def test_account_year_periods():
    from apps.ejecutivo.services.account_view import overlaps_account_year

    assert not overlaps_account_year("2025-01-01", "2025-12-31", 2026)
    assert not overlaps_account_year("2027-01-01", "2027-12-31", 2026)
    assert overlaps_account_year("2025-12-01", "2026-02-01", 2026)
    assert overlaps_account_year("2026-01-01", "", 2026)


def test_roc_closed_contracts_are_visible_without_duplicate_ids():
    from apps.ejecutivo.services.account_view import append_roc_projects

    projects = [{"id": "ROC.EXISTING"}]
    roc = [
        {"id": "ROC.EXISTING"},
        {
            "id": "ROC.CLOSED",
            "estado": "Closed",
            "proceso": "Bot",
            "botId": "OLD.BOT",
        },
    ]
    append_roc_projects(projects, roc, "Acme")
    assert len(projects) == 2
    assert projects[1]["servicio"] == "ROC"
    assert projects[1]["estado"] == "Completado"
    assert projects[1]["budget"] is None
    assert not projects[1]["clockifyPending"]


def test_heineken_mexico_uses_history_and_roc_account_name():
    from apps.ejecutivo.services.account_view import account_matches

    assert account_matches("Heineken", "Heineken Mexico")
    assert account_matches("Heineken Mexico", "Heineken")
    assert not account_matches("Nestle Mexico", "Heineken Mexico")


def test_mpb_excludes_ixb_projects_even_for_matching_account():
    header = ["CLIENTE", "ID", "NOMBRE", "SERVICE", "ESTATUS"]
    reader = Reader(
        {
            "MPB": [
                header,
                ["OXXO", "CCO.002", "Migracion", "IxB", "Deployment"],
                ["Other", "OTHER.001", "Other", "IxB", "Deployment"],
            ],
            "DataRevenue": [["Status", "Account", "", "", "ID", "", "Date"]],
        }
    )
    result = load_mpb_projects(reader, "Cadena Comercial Oxxo")
    assert result == []


def test_history_operational_block_provides_ixb_raas_saas_only():
    from apps.ejecutivo.services.account_view import read_history_projects

    rows = [
        [
            "DM",
            "Client",
            "Project ID",
            "Service",
            "Name",
            "",
            "Stage",
            "Start",
            "End",
            "Budget",
        ],
        [
            "Ana",
            "Cadena Comercial Oxxo.",
            "CCO.002_S1",
            "IxB",
            "Migracion",
            "",
            "Development",
            "2026-05-01",
            "2026-06-01",
            435,
        ],
        [
            "Ana",
            "OXXO",
            "CCO.001",
            "RaaS",
            "Bot",
            "",
            "Completed",
            "2025-02-01",
            "2025-02-27",
            250,
        ],
        [
            "Ana",
            "OXXO",
            "SAAS.1",
            "SaaS",
            "App",
            "",
            "Development",
            "2026-05-01",
            "2026-10-01",
        ],
        [
            "Ana",
            "OXXO",
            "AER.1",
            "AER",
            "Cell",
            "",
            "Development",
            "2026-05-01",
            "2026-10-01",
        ],
    ]
    result = read_history_projects(rows, "Cadena Comercial Oxxo")
    assert set(result) == {"cco.002_s1", "cco.001", "saas.1"}
    assert result["cco.002_s1"]["budget"] == 435
    assert result["cco.002_s1"]["etapas"][0]["fechaFinReal"] == "2026-06-01"
