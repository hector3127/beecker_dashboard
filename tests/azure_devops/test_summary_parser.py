"""Summary variants and scope isolation for the EVA source transition."""

import json
from decimal import Decimal
from io import StringIO
from unittest.mock import Mock, patch

import pytest
from django.core.management import call_command

from apps.azure_devops.services.azure_client import AzureDevOpsClient
from apps.azure_devops.services.summary_parser import parse_summary
from apps.portal.services.eva_azure_source import (
    candidate_rows,
    financials,
    summary_date,
    summary_hours,
)


@pytest.mark.parametrize(
    "header,code",
    [
        ("SPRINT #01", "S1"),
        ("S10", "S10"),
        ("Iteración 2", "S2"),
        ("Change Request", "CR"),
        ("CR1", "CR1"),
        ("CR2", "CR2"),
        ("Solicitud de cambio #2", "CR2"),
        ("CHANGE REQUEST 2 / SPRNT 1", "CR2_S1"),
        ("CR1 / Sprint #2", "CR1_S2"),
    ],
)
def test_headers(header, code):
    blocks = parse_summary(header + "\nHoras: 90")
    assert len(blocks) == 1
    assert blocks[0].code == code
    assert blocks[0].fields["budget"] == "90"


def test_shared_metadata_never_spreads_budget_dates_or_status():
    blocks = parse_summary(
        "DM: Ana\nServicio: IXB\nBudget: 999\nStart: 2026-01-01\n"
        "Status: Closed\nSprint 1\nHoras: 90\nSprint 2\nHoras: 45\n"
        "CR\nHoras: 10\nCR1\nHoras: 20"
    )
    assert [b.code for b in blocks] == ["", "S1", "S2", "CR", "CR1"]
    assert [b.fields["budget"] for b in blocks] == [
        "999",
        "90",
        "45",
        "10",
        "20",
    ]
    assert all(b.fields["delivery_manager"] == "Ana" for b in blocks)
    assert all(
        "start" not in b.fields and "status" not in b.fields for b in blocks[1:]
    )


def test_composite_scoped_hours_stay_in_their_cr():
    blocks = parse_summary(
        "CHANGE REQUEST 2 / SPRNT 1\nHoras_CR: 90 hrs.\n"
        "CHANGE REQUEST 1 / SPRNT 1\nHoras_CR: 91 hrs.\n"
        "SPRINT #1\nHoras: 155"
    )
    assert [(b.code, b.fields["budget"]) for b in blocks] == [
        ("CR2_S1", "90 hrs."),
        ("CR1_S1", "91 hrs."),
        ("S1", "155"),
    ]


def test_html_tables_metadata_and_unknown_labels():
    block = parse_summary(
        "<h2>Sprint 1</h2><table><tr><td>Budget</td><td>90</td></tr>"
        "<tr><td>QA</td><td>Bea</td></tr></table>"
        "<p>Etiqueta nueva: 22</p><script>Horas: 999</script>"
    )[0]
    assert block.fields == {"budget": "90"}
    assert block.metadata == {"qa": "Bea"}
    assert block.unknown_labels == ["Etiqueta nueva"]


def test_conflicts_and_duplicate_headers_are_not_silently_overwritten():
    block = parse_summary(
        "Sprint 1\nBudget: 90\nHoras: 100\nSprint 1\nHoras: 90"
    )[0]
    assert "budget" not in block.fields
    assert "conflicting_field:budget" in block.issues
    assert "duplicate_block" in block.issues


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("90 hrs.", "90"),
        ("412 a utilizar", "412"),
        ("12,5 horas", "12.5"),
        ("1000", "1000"),
        ("1.000", None),
        ("-90", None),
        ("90 USD", None),
        ("NaN", None),
        ("90 + 10", None),
    ],
)
def test_hours_do_not_guess_ambiguous_values(raw, expected):
    assert summary_hours(raw) == (Decimal(expected) if expected else None)


def test_candidate_dates_and_missing_data_are_explicit():
    assert summary_date("29/10/025") is None
    row = candidate_rows("AMK.012", "Sprint 2\nBudget: 90")[0]
    assert row["project_id"] == "AMK.012_S2"
    assert row["budget"] == "90"
    assert not row["ready"]
    assert "missing:start" in row["issues"]


def test_financials_user_rules_and_pending():
    result = financials(Decimal(90), Decimal(179))
    assert result["etc"] == result["hours_deviation"] == Decimal(-89)
    assert result["advance"] == Decimal(179) / 90 * 100
    assert financials(Decimal(0), Decimal(0))["advance"] is None
    assert financials(Decimal(90), None)["etc"] is None


def test_summary_client_encodes_project_and_only_reads():
    client = AzureDevOpsClient("org", "test-token")
    client._send = Mock(return_value={"description": "Budget: 10"})
    assert (
        client.get_project_summary("AMK.012 CR")["description"] == "Budget: 10"
    )
    args, kwargs = client._send.call_args
    assert args[0] == "GET"
    assert args[1].endswith("/_apis/projects/AMK.012%20CR")
    assert "json" not in kwargs


def test_offline_command_never_opens_azure(tmp_path):
    sample, output = tmp_path / "samples.json", tmp_path / "report.json"
    sample.write_text(
        json.dumps({"AMK.012": "Sprint 1\nBudget: 90"}), encoding="utf-8"
    )
    with patch(
        "apps.portal.management.commands.audit_eva_azure.AzureDevOpsGateway"
    ) as gateway:
        call_command(
            "audit_eva_azure",
            project=["AMK.012"],
            input=str(sample),
            output=str(output),
            stdout=StringIO(),
        )
    gateway.assert_not_called()
    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["historical"] is False
    assert report["rows"][0]["project_id"] == "AMK.012_S1"


def test_full_project_catalog_paginates_and_keeps_summary(monkeypatch):
    monkeypatch.setattr(
        "apps.azure_devops.services.azure_client.PROJECTS_PAGE_SIZE", 2
    )
    client = AzureDevOpsClient("org", "fake")
    client._send = Mock(
        side_effect=[
            {"value": [{"id": "a", "description": "A"}, {"id": "b"}]},
            {"value": [{"id": "c", "description": "C"}]},
        ]
    )
    assert [p["id"] for p in client.list_summary_projects()] == ["a", "b", "c"]
    assert client._send.call_args.kwargs["params"]["$skip"] == 2


def test_eva_work_items_do_not_use_the_1000_item_dashboard_cap():
    client = AzureDevOpsClient("org", "fake")
    client._send = Mock(
        return_value={"workItems": [{"id": i} for i in range(1001)]}
    )
    client._read_work_item_batch = Mock(
        side_effect=lambda url, ids: [{"id": i} for i in ids]
    )
    assert len(client.list_eva_work_items("AMK.012")) == 1001


def test_incomplete_eva_batch_is_an_error():
    from apps.azure_devops.exceptions import AzureDevOpsRequestError

    client = AzureDevOpsClient("org", "fake")
    client._send = Mock(return_value={"workItems": [{"id": 1}]})
    client._read_work_item_batch = Mock(return_value=[])
    with pytest.raises(AzureDevOpsRequestError):
        client.list_eva_work_items("AMK.012")
