from datetime import date

import pytest

from apps.clockify.exceptions import (
    ClockifyReportForbiddenError,
    ClockifyRequestError,
)
from apps.clockify.services.clockify_client import ClockifyClient
from tests.clockify.fakes import FakeResponse, FakeSession


def build_entry(entry_id, project_id="cp-1"):
    return {"_id": entry_id, "projectId": project_id}


def build_client(responses):
    session = FakeSession(responses)
    sleeps = []
    client = ClockifyClient("clave", session=session, sleep=sleeps.append)
    return client, session, sleeps


def test_api_key_goes_in_header():
    _, session, _ = build_client([])

    assert session.headers == {"X-Api-Key": "clave"}


def test_report_is_split_in_blocks_of_31_days():
    client, session, _ = build_client(
        [
            FakeResponse(200, {"timeentries": [build_entry("a")]}),
            FakeResponse(200, {"timeentries": [build_entry("b")]}),
        ],
    )

    entries = client.fetch_detailed_report(
        "ws",
        "cp-1",
        date(2026, 1, 1),
        date(2026, 2, 15),
        "America/Mexico_City",
    )

    assert [entry["_id"] for entry in entries] == ["a", "b"]
    first_body = session.calls[0][2]["json"]
    second_body = session.calls[1][2]["json"]
    assert first_body["dateRangeStart"] == "2026-01-01T00:00:00.000"
    assert first_body["dateRangeEnd"] == "2026-01-31T23:59:59.999"
    assert second_body["dateRangeStart"] == "2026-02-01T00:00:00.000"


def test_report_pages_until_short_page():
    full_page = [build_entry(str(index)) for index in range(200)]
    client, _, _ = build_client(
        [
            FakeResponse(200, {"timeentries": full_page}),
            FakeResponse(200, {"timeentries": [build_entry("final")]}),
        ],
    )

    entries = client.fetch_detailed_report(
        "ws",
        "cp-1",
        date(2026, 1, 1),
        date(2026, 1, 2),
        "America/Mexico_City",
    )

    assert len(entries) == 201


def test_retries_when_rate_limited():
    client, session, sleeps = build_client(
        [
            FakeResponse(429, {}),
            FakeResponse(200, {"timeentries": []}),
        ],
    )

    client.fetch_detailed_report(
        "ws",
        "cp-1",
        date(2026, 1, 1),
        date(2026, 1, 1),
        "America/Mexico_City",
    )

    assert len(session.calls) == 2
    assert sleeps == [2.5]


def test_forbidden_report_raises_specific_error():
    client, _, _ = build_client([FakeResponse(403, {})])

    with pytest.raises(ClockifyReportForbiddenError):
        client.fetch_detailed_report(
            "ws",
            "cp-1",
            date(2026, 1, 1),
            date(2026, 1, 1),
            "America/Mexico_City",
        )


def test_entry_from_other_project_is_rejected():
    client, _, _ = build_client(
        [FakeResponse(200, {"timeentries": [build_entry("a", "otro")]})],
    )

    with pytest.raises(ClockifyRequestError):
        client.fetch_detailed_report(
            "ws",
            "cp-1",
            date(2026, 1, 1),
            date(2026, 1, 1),
            "America/Mexico_City",
        )


def test_missing_timeentries_is_not_zero_hours():
    client, _, _ = build_client([FakeResponse(200, {"otro": []})])

    with pytest.raises(ClockifyRequestError):
        client.fetch_detailed_report(
            "ws",
            "cp-1",
            date(2026, 1, 1),
            date(2026, 1, 1),
            "America/Mexico_City",
        )


def test_list_projects_paginates():
    first_page = [
        {"id": str(index), "name": f"P{index}"} for index in range(200)
    ]
    client, session, _ = build_client(
        [
            FakeResponse(200, first_page),
            FakeResponse(200, [{"id": "x", "name": "Ultimo"}]),
        ],
    )

    projects = client.list_projects("ws")

    assert len(projects) == 201
    assert session.calls[1][2]["params"]["page"] == 2


def test_list_workspaces_maps_names():
    client, _, _ = build_client(
        [FakeResponse(200, [{"id": "w1", "name": "Beecker"}])],
    )

    assert client.list_workspaces() == [{"id": "w1", "nombre": "Beecker"}]
