"""Regresiones de nomenclaturas simultaneas y vigencia por historico."""

from datetime import date, datetime

from apps.ejecutivo.services.ixb_history import resolve_history_period
from apps.ejecutivo.services.ixb_summary import IxbSources, build_ixb_summary

TODAY = date(2026, 10, 12)


def event(pid, status, start, finish=""):
    return {
        "Project ID": pid,
        "Status": status,
        "Start": start,
        "Finish": finish,
    }


def test_two_active_versions_ignore_project_state_and_keep_own_budget():
    projects = [
        {
            "ID_Proyecto": "RAS.001_S4",
            "Servicio": "RaaS",
            "Estado": "Cerrado",
            "Budget_Hrs": 40,
        },
        {
            "ID_Proyecto": "RAS.001_S4",
            "Servicio": "RaaS",
            "Estado": "Cerrado",
            "Budget_Hrs": 10,
        },
        {
            "ID_Proyecto": "RAS.001_CR1",
            "Servicio": "RaaS",
            "Estado": "Completed",
            "Budget_Hrs": 20,
        },
    ]
    history = [
        event("RAS.001_S4", "Discovery OP", TODAY, TODAY),
        event("RAS.001_CR1", "Development", "2026-10-01", "2026-10-20"),
    ]
    result = build_ixb_summary(
        IxbSources(projects, history, lambda _: [], None),
        datetime(2026, 10, 12, 12),
    )
    rows = {row["idProyecto"]: row for row in result["filas"]}
    assert set(rows) == {"RAS.001_S4", "RAS.001_CR1"}
    assert rows["RAS.001_S4"]["budget"] == 50
    assert rows["RAS.001_CR1"]["budget"] == 20
    assert rows["RAS.001_S4"]["status"] == "Discovery"
    assert rows["RAS.001_CR1"]["status"] == "Development"
    assert result["pivoteServicio"][0]["total"] == 2


def test_completed_version_does_not_hide_other_suffix():
    history = [
        event("RAS.001_CR1", "Completed", "2026-10-10"),
        event("RAS.001_S4", "Discovery", TODAY),
    ]
    assert not resolve_history_period(history, "RAS.001_CR1", TODAY).active
    assert resolve_history_period(history, "RAS.001_S4", TODAY).active


def test_start_today_is_included_but_future_is_excluded():
    history = [event("X_S4", "Discovery", TODAY)]
    assert resolve_history_period(history, "X_S4", TODAY).active
    assert not resolve_history_period(
        history, "X_S4", date(2026, 10, 11)
    ).active


def test_completed_final_day_stays_visible_until_next_day():
    history = [
        event("X_S4", "Deployment", "2026-10-01", TODAY),
        event("X_S4", "Completed", TODAY, TODAY),
    ]
    result = resolve_history_period(history, "X_S4", TODAY)
    assert result.active and not result.closed_stages["deployment"]
    assert not resolve_history_period(
        history, "X_S4", date(2026, 10, 13)
    ).active


def test_future_phases_and_completed_do_not_advance_current_stage():
    history = [
        event("X_S4", "Discovery", TODAY, "2026-10-13"),
        event("X_S4", "Development", "2026-10-14", "2026-10-20"),
        event("X_S4", "Deployment EST", "2026-10-21", "2026-10-28"),
        event("X_S4", "Completed", "2026-10-28"),
    ]
    result = resolve_history_period(history, "X_S4", TODAY)
    assert result.active and result.status == "Discovery"
    assert result.finish.date() == date(2026, 10, 28)


def test_suspended_without_phase_and_resumed_phase():
    history = [event("X", "Suspendido", "2026-10-01")]
    assert resolve_history_period(history, "X", TODAY).status == "Suspendido"
    history.append(event("X", "Development", TODAY))
    assert resolve_history_period(history, "X", TODAY).status == "Development"


def test_case_and_spaces_and_no_cross_suffix_fallback():
    history = [
        event(" ras.001_s4 ", "Discovery OP", TODAY),
        event("RAS.001", "Completed", "2026-01-01"),
    ]
    assert resolve_history_period(history, "RAS.001_S4", TODAY).active
    assert not resolve_history_period(history, "RAS.001_CR2", TODAY).active


def test_overdue_remains_active_until_completed_and_plan_is_fallback():
    history = [event("X", "Deployment EST", "2026-10-01", "2026-10-10")]
    assert resolve_history_period(history, "X", TODAY).active
    history.append(event("X", "Deployment", "2026-10-14"))
    assert not resolve_history_period(history, "X", TODAY).active


def test_closed_summary_lists_only_completed_projects():
    projects = [
        {"ID_Proyecto": "GPO.007", "Servicio": "IXB", "Budget_Hrs": 100},
        {"ID_Proyecto": "AMK.009_S3", "Servicio": "IXB", "Budget_Hrs": 50},
    ]
    history = [
        event("GPO.007", "Discovery", "2026-01-05", "2026-02-01"),
        event("GPO.007", "Deployment", "2026-02-02", "2026-03-01"),
        event("GPO.007", "Completed", "2026-03-02"),
        event("AMK.009_S3", "Development", "2026-09-01", "2026-12-01"),
    ]
    now = datetime(2026, 10, 12, 12)
    sources = IxbSources(projects, history, lambda _: [], None)

    closed = build_ixb_summary(sources, now, closed=True)
    active = build_ixb_summary(sources, now)

    assert [row["idProyecto"] for row in closed["filas"]] == ["GPO.007"]
    row = closed["filas"][0]
    assert row["status"] == "Cerrado"
    assert row["fechaInicio"].startswith("2026-01-05")
    assert row["fechaFin"].startswith("2026-03-02")
    assert row["budget"] == 100
    assert [row["idProyecto"] for row in active["filas"]] == ["AMK.009_S3"]


def test_cancelled_project_is_never_an_active_phase():
    from datetime import date

    from apps.ejecutivo.services.ixb_history import resolve_history_period

    rows = [
        {
            "Project ID": "MIT.001",
            "Status": "Development",
            "Start": "2026-01-05",
            "Finish": "2026-02-01",
        },
        {
            "Project ID": "MIT.001",
            "Status": "Cancelled",
            "Start": "2026-02-24",
            "Finish": "2026-02-24",
        },
    ]
    assert not resolve_history_period(
        rows, "MIT.001", date(2026, 10, 13)
    ).active
    assert not resolve_history_period(
        [{"Project ID": "X", "Status": "Unknown", "Start": "2026-01-01"}],
        "X",
        date(2026, 10, 13),
    ).active
