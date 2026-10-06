"""Compara el panel IXS y el RAID contra DailyPanelService.gs.

ixs_expected.json es la salida del original (harness de Node con
UrlFetchApp, CacheService y la hoja WorkItems_Avance simulados) para las
operaciones de ixs_data.json. El Azure simulado de este archivo replica
las mismas respuestas.
"""

import base64
import copy
import json
from pathlib import Path
from urllib.parse import unquote, urlparse

import pytest

from apps.daily.services import daily_sheets, ixs_raid
from apps.daily.services.daily_azure_client import DailyAzureClient
from apps.daily.services.daily_sheets import DailySheets
from apps.daily.services.ixs_panel import IxsAzure, load_panel
from tests.daily.fakes import FakeResponse, MemoryCache
from tests.daily.test_daily_parity import NOW
from tests.fakes import InMemorySheetRepository

HERE = Path(__file__).parent
DATA = json.loads((HERE / "ixs_data.json").read_text("utf-8"))
EXPECTED = json.loads((HERE / "ixs_expected.json").read_text("utf-8"))


class IxsAzureSession:
    """Organizacion simulada igual a la del harness del original."""

    def __init__(self, state):
        self.headers = {}
        self.state = state

    def request(
        self,
        method,
        url,
        timeout,
        params=None,
        json=None,
        data=None,
        headers=None,
    ):
        params = params or {}
        parts = [unquote(part) for part in urlparse(url).path.split("/")]
        token = base64.b64encode(f":{DATA['PAT']}".encode()).decode()

        if self.headers.get("Authorization") != f"Basic {token}":
            return FakeResponse(401, "no auth")

        if parts[1] != DATA["ORGANIZATION"]:
            return FakeResponse(404, "org")

        project = parts[2]
        mode = self.state["fail"].get(project, "")

        if parts[5] == "workitemtypes":
            return FakeResponse(
                200, {"value": DATA["FIELDS"].get(parts[6], [])}
            )

        if parts[5] == "classificationnodes":
            return FakeResponse(200, DATA["ITERATION_TREE"])

        if parts[5] == "wiql":
            if project == "ERR401":
                return FakeResponse(401, "unauthorized")

            if project == "ERR500" or mode == "wiql":
                return FakeResponse(503, "boom " * 100)

            ids = DATA["WIQL"].get(project, [])
            return FakeResponse(200, {"workItems": [{"id": i} for i in ids]})

        if method == "POST":
            return self.create(project, parts, data, headers or {})

        if len(parts) > 6 and parts[6]:
            return self.single(parts[6])

        if project == "BATCH403":
            return FakeResponse(403, "forbidden batch " * 20)

        if project == "BATCH500":
            return FakeResponse(500, "detail")

        return self.batch(params, mode)

    def create(self, project, parts, data, headers):
        body = jsonlib_loads(data)
        self.state["posts"].append(
            {
                "path": "/".join(parts[5:]),
                "contentType": headers.get("Content-Type"),
                "body": body,
            },
        )

        if project == "WRITE403":
            return FakeResponse(403, "forbidden")

        self.state["next_id"] += 1
        self.state["created"][self.state["next_id"]] = body
        return FakeResponse(200, {"id": self.state["next_id"]})

    def single(self, item_id):
        created = self.state["created"].get(int(item_id))

        if created is not None:
            relations = [
                op["value"] for op in created if op["path"] == "/relations/-"
            ]

            if any(r["url"].endswith("/107") for r in relations):
                return FakeResponse(500, "verify down")

            if any(r["url"].endswith("/106") for r in relations):
                relations = []

            return FakeResponse(
                200, {"id": int(item_id), "relations": relations}
            )

        item = DATA["WORK_ITEMS"].get(item_id)

        if item is None:
            return FakeResponse(
                404,
                f"TF401232: Work item {item_id} does not exist",
            )

        return FakeResponse(200, item)

    def batch(self, params, mode):
        expand = params.get("$expand")

        if expand == "relations" and mode == "relations":
            return FakeResponse(503, "relations down")

        if expand == "relations" and mode == "relations403":
            return FakeResponse(403, "relations forbidden")

        keep = params.get("fields")
        items = []

        for item_id in params["ids"].split(","):
            item = copy.deepcopy(DATA["WORK_ITEMS"][item_id])

            if expand != "relations":
                item.pop("relations", None)

            if keep:
                item["fields"] = {
                    key: value
                    for key, value in item["fields"].items()
                    if key in keep.split(",")
                }

            items.append(item)

        return FakeResponse(200, {"value": items})


def jsonlib_loads(data):
    return json.loads(data)


@pytest.fixture(scope="module")
def results():
    state = {"fail": {}, "posts": [], "created": {}, "next_id": 5000}
    repository = InMemorySheetRepository(copy.deepcopy(DATA["SHEETS"]))
    azure = IxsAzure(
        organization=DATA["ORGANIZATION"],
        personal_access_token=DATA["PAT"],
        active_project=DATA["ACTIVE"],
        resolve_project=lambda project_id: DATA["RESOLVE"].get(project_id, ""),
        build_client=lambda: DailyAzureClient(
            DATA["ORGANIZATION"],
            DATA["PAT"],
            session=IxsAzureSession(state),
            sleep=lambda seconds: None,
        ),
        cache=MemoryCache(),
        load_progress=lambda: daily_sheets.load_progress_map(
            DailySheets(repository, repository, NOW, DATA["NOW"]),
        ),
    )
    functions = {
        "obtenerPanelAzureProyectoIXS": lambda project, force=False: load_panel(
            azure,
            project,
            force,
            DATA["NOW"],
        ),
        "ixsRaidListarProyecto": lambda project, force=False: (
            ixs_raid.list_raid(
                azure,
                project,
                force,
                DATA["NOW"],
            )
        ),
        "ixsRaidCamposTipo": lambda *args: ixs_raid.raid_field_types(
            azure, *args
        ),
        "ixsRaidAltaOpciones": lambda *args: ixs_raid.raid_creation_options(
            azure,
            *args,
        ),
        "ixsRaidCrearRegistro": lambda *args: ixs_raid.create_raid_record(
            azure,
            *args,
        ),
    }
    outputs = []

    for name, args in DATA["OPERATIONS"]:
        if name == "__fail":
            state["fail"][args[0]] = args[1]
            outputs.append(None)
            continue

        outputs.append(json.loads(json.dumps(functions[name](*args))))

    return outputs, state["posts"]


@pytest.mark.parametrize("index", range(len(DATA["OPERATIONS"])))
def test_operation_matches_original(results, index):
    expected = EXPECTED["results"][index]
    actual = results[0][index]

    if expected is None:
        assert actual is None
        return

    assert actual == expected["result"], DATA["OPERATIONS"][index]


def test_created_payloads_match_original(results):
    assert results[1] == EXPECTED["posts"]
