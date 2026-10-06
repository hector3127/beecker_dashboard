import base64

import pytest

from apps.azure_devops.exceptions import AzureDevOpsRequestError
from apps.azure_devops.services.azure_client import (
    AzureDevOpsClient,
    build_basic_auth,
)
from apps.azure_devops.services.portfolio_risks import (
    build_portfolio_risks,
    group_projects_by_azure,
)
from apps.azure_devops.services.project_resolver import resolve_azure_project
from apps.azure_devops.services.risk_severity import label_risk_severity
from tests.clockify.fakes import FakeResponse, FakeSession

AZURE_PROJECTS = ["AMK.008", "GPO.007 MultiProfile", "Análisis"]


@pytest.mark.parametrize(
    ("internal_id", "expected"),
    [
        ("AMK.008", "AMK.008"),
        ("amk.008_S2", "AMK.008"),
        ("analisis", "Análisis"),
        ("NO.EXISTE", ""),
    ],
)
def test_resolve_azure_project(internal_id, expected):
    assert resolve_azure_project(internal_id, AZURE_PROJECTS) == expected


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("1 - Critical", "Alto"),
        ("2 - High", "Alto"),
        ("3 - Medium", "Medio"),
        ("4 - Low", "Bajo"),
        ("Baja", "Bajo"),
        ("", "Medio"),
        (None, "Medio"),
    ],
)
def test_label_risk_severity(raw, expected):
    assert label_risk_severity(raw) == expected


def build_work_item(item_id, state, severity, changed, item_type="Risk"):
    return {
        "id": item_id,
        "fields": {
            "System.WorkItemType": item_type,
            "System.State": state,
            "System.Title": f"Riesgo {item_id}",
            "System.ChangedDate": changed,
            "Microsoft.VSTS.Common.Severity": severity,
            "System.AssignedTo": {"displayName": "Ana Ruiz"},
        },
    }


PROJECT_ROWS = [
    {"ID_Proyecto": "AMK.008", "Nombre": "Cobranza", "Cliente": "ACME"},
    {"ID_Proyecto": "AMK.008_S2", "Nombre": "Cobranza 2", "Cliente": "ACME"},
    {"ID_Proyecto": "SIN.AZURE", "Nombre": "Otro", "Cliente": "Globex"},
    {"ID_Proyecto": "Análisis", "Nombre": "", "Account": "Initech"},
]

WORK_ITEMS = {
    "AMK.008": [
        build_work_item(1, "Active", "3 - Medium", "2026-09-01T10:00:00Z"),
        build_work_item(2, "Proposed", "2 - High", "2026-08-01T10:00:00Z"),
        build_work_item(3, "Closed", "1 - Critical", "2026-09-30T10:00:00Z"),
        build_work_item(4, "Active", "1", "2026-09-15T10:00:00Z", "Bug"),
        build_work_item(5, "Active", "2 - High", "2026-09-20T10:00:00.5Z"),
    ],
}


def load_work_items(project_name):
    if project_name == "Análisis":
        raise AzureDevOpsRequestError("Azure DevOps respondio 403.")
    return WORK_ITEMS.get(project_name, [])


def test_groups_internal_projects_by_azure_project():
    groups = group_projects_by_azure(PROJECT_ROWS, AZURE_PROJECTS)

    assert list(groups) == ["AMK.008", "Análisis"]
    assert groups["AMK.008"].internal_ids == ["AMK.008", "AMK.008_S2"]
    assert groups["AMK.008"].clients == ["ACME"]
    assert groups["Análisis"].clients == ["Initech"]


def test_portfolio_risks_filter_sort_and_shape():
    groups = group_projects_by_azure(PROJECT_ROWS, AZURE_PROJECTS)

    result = build_portfolio_risks(groups, load_work_items, "beecker org")

    assert result["ok"] is True
    assert [risk["id"] for risk in result["riesgos"]] == [5, 2, 1]
    assert result["total"] == 3
    assert result["riesgosAltos"] == 2
    first_risk = result["riesgos"][0]
    assert first_risk["proyecto"] == "AMK.008, AMK.008_S2"
    assert first_risk["clientes"] == ["ACME"]
    assert first_risk["responsable"] == "Ana Ruiz"
    assert first_risk["fechaCambio"] == "2026-09-20T10:00:00.500Z"
    assert first_risk["url"] == (
        "https://dev.azure.com/beecker%20org/AMK.008/_workitems/edit/5"
    )


def test_severity_from_alternative_field():
    groups = group_projects_by_azure(PROJECT_ROWS[:1], AZURE_PROJECTS)
    work_item = build_work_item(9, "Active", "", "2026-09-01T10:00:00Z")
    work_item["fields"]["Custom.RiskSeverity"] = "4 - Low"

    result = build_portfolio_risks(groups, lambda _: [work_item], "org")

    assert result["riesgos"][0]["impacto"] == "Bajo"
    assert result["riesgos"][0]["severity"] == "4 - Low"


def test_client_uses_basic_auth_and_batches_ids():
    ids = [{"id": number} for number in range(1, 201)]
    session = FakeSession(
        [
            FakeResponse(200, {"workItems": ids}),
            FakeResponse(200, {"value": [{"id": 1}]}),
            FakeResponse(500, {}),
        ],
    )
    client = AzureDevOpsClient("org", "pat", session=session)

    items = client.list_work_items("AMK.008")

    expected_token = base64.b64encode(b":pat").decode()
    assert session.headers["Authorization"] == f"Basic {expected_token}"
    assert build_basic_auth("pat") == f"Basic {expected_token}"
    assert items == [{"id": 1}]
    first_batch = session.calls[1][2]["params"]["ids"].split(",")
    assert len(first_batch) == 180
    wiql = session.calls[0][2]["json"]["query"]
    assert "[System.TeamProject] = 'AMK.008'" in wiql


def test_client_raises_on_wiql_error():
    session = FakeSession([FakeResponse(401, {})])
    client = AzureDevOpsClient("org", "pat", session=session)

    with pytest.raises(AzureDevOpsRequestError):
        client.list_work_items("AMK.008")
