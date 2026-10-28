"""Summary counts reconcile to visible rows, including pending dimensions."""

from apps.portal.services.summary_dm_totals import dm_totals


def test_dm_counts_services_stages_and_totals():
    rows = [
        {
            "fields": {"delivery_manager": "Ana", "service": "IxB"},
            "calendar_stage": "Deployment",
        },
        {
            "fields": {"delivery_manager": "Ana", "service": "RaaS"},
            "calendar_stage": "Discovery",
        },
        {
            "fields": {"delivery_manager": "Luis", "service": "SaaS"},
            "calendar_stage": "Development",
        },
        {"fields": {}, "calendar_stage": "Solapamiento de etapas"},
    ]
    result = dm_totals(rows)
    assert result["total"] == 4
    assert sum(result["service_totals"]) == sum(result["status_totals"]) == 4
    assert result["rows"][0]["manager"] == "Ana"
    assert result["rows"][0]["total"] == 2
    assert result["service_totals"] == [1, 0, 1, 0, 1, 1]
    assert result["status_totals"] == [0, 1, 1, 1, 1]
    for dm in result["rows"]:
        assert sum(dm["services"]) == sum(dm["statuses"]) == dm["total"]
    assert dm_totals(rows[:1])["total"] == 1


def test_empty_summary():
    result = dm_totals([])
    assert result["total"] == 0
    assert result["rows"] == []
    assert sum(result["service_totals"]) == sum(result["status_totals"]) == 0
