from datetime import date

from apps.portal.services.revenue_costs import resolve_cost_scope


def test_roc_monthly_id_and_base_january():
    today = date(2026, 10, 14)
    ids = ["ROC.AEC.002", "ROC.AEC.002.07"]
    assert resolve_cost_scope(ids[1], ids, today) == (
        "ROC.AEC.002",
        date(2026, 7, 1),
        date(2026, 7, 31),
        7,
    )
    assert resolve_cost_scope(ids[0], ids, today) == (
        "ROC.AEC.002",
        date(2026, 1, 1),
        date(2026, 1, 31),
        1,
    )


def test_roc_without_variants_keeps_full_year():
    today = date(2026, 10, 14)
    assert resolve_cost_scope("ROC.AIN.002", ["ROC.AIN.002"], today) == (
        "ROC.AIN.002",
        date(2026, 1, 1),
        today,
        None,
    )
    assert resolve_cost_scope("AER.AEC.002.07", [], today)[0] == "AER.AEC.002"


def test_month_scope_current_and_future_months():
    today = date(2026, 10, 14)
    assert resolve_cost_scope("ROC.AEC.002.10", [], today)[2] == today
    assert resolve_cost_scope("ROC.AEC.002.12", [], today)[1:3] == (
        date(2026, 12, 1),
        date(2026, 12, 31),
    )
