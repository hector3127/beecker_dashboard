"""Los conteos y riesgos no se mezclan entre nomenclaturas."""

from apps.ejecutivo.services.azure_stages import (
    count_work_items,
    filter_work_items_by_sprints,
    list_open_risk_titles,
)


def wi(path, state="Active", kind="Task", title="WI"):
    return {
        "fields": {
            "System.IterationPath": path,
            "System.State": state,
            "System.WorkItemType": kind,
            "System.Title": title,
        }
    }


def test_exact_s4_subiterations_and_unassigned_are_excluded():
    items = [
        wi(r"RAS.001\S4\Discovery", "Closed"),
        wi(r"RAS.001\Development_S4\Child"),
        wi(r"RAS.001\General_S4"),
        wi(r"RAS.001\Discovery_S40"),
        wi(r"RAS.001\Discovery_S3"),
        wi(r"RAS.001\Discovery"),
        wi(""),
        wi(r"RAS.001"),
    ]
    counts = count_work_items(items, ["S4"])
    assert counts["general"] == {"total": 3, "cerrados": 1, "pendientes": 2}
    assert counts["discovery"]["total"] == 1
    assert counts["development"]["total"] == 1
    assert counts["deployment"]["total"] == 0


def test_cr1_does_not_include_cr10_or_cr2():
    items = [
        wi(r"X\CR1\Deployment"),
        wi(r"X\Deployment_CR10"),
        wi(r"X\Deployment_CR2"),
        wi(r"X\Deployment"),
    ]
    assert count_work_items(items, ["CR1"])["general"]["total"] == 1


def test_only_risks_of_selected_nomenclature():
    items = [
        wi(r"X\S4", kind="Risk", title="S4 risk"),
        wi(r"X\S3", kind="Risk", title="S3 risk"),
        wi(r"X", kind="Risk", title="Unassigned risk"),
        wi(r"X\S4", "Closed", "Risk", "Closed risk"),
    ]
    selected = filter_work_items_by_sprints(items, ["S4"])
    assert list_open_risk_titles(selected) == ["S4 risk"]


def test_empty_nomenclature_and_missing_fields_do_not_match():
    assert filter_work_items_by_sprints([{}, wi(r"X\S4")], []) == []
    assert filter_work_items_by_sprints([{}, wi(r"X\S4")], [""]) == []


def test_case_insensitive_and_base_defaults_to_s1():
    from apps.ejecutivo.services.azure_stages import infer_sprint

    items = [wi(r"X\discovery_s1"), wi(r"X\Discovery_S10")]
    assert count_work_items(items, [infer_sprint("X")])["general"]["total"] == 1
