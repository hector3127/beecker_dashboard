"""Azure DevOps simulado para las pruebas del Daily."""

import base64
import copy
import json
import json as jsonlib
from urllib.parse import unquote, urlparse

from tests.daily import sample_data as sample


class FakeResponse:
    def __init__(self, status_code, body):
        self.status_code = status_code
        self.text = body if isinstance(body, str) else json.dumps(body)

    def json(self):
        return json.loads(self.text)


class FakeAzureSession:
    """Responde como la organizacion simulada del harness del original."""

    posts: list[dict[str, object]] = []

    def __init__(self):
        self.headers = {}
        self.calls = []

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
        self.calls.append((method, url, params))
        parts = [unquote(part) for part in urlparse(url).path.split("/")]
        expected = (
            "Basic "
            + base64.b64encode(
                f":{sample.PAT}".encode(),
            ).decode()
        )

        if self.headers.get("Authorization") != expected:
            return FakeResponse(401, "no auth")

        if parts[1] != sample.ORGANIZATION:
            return FakeResponse(404, "org")

        if parts[2] == "_apis" and parts[3] == "projects":
            if len(parts) == 4:
                return FakeResponse(200, {"value": sample.AZURE_PROJECTS})

            project = next(
                (p for p in sample.AZURE_PROJECTS if p["name"] == parts[4]),
                None,
            )
            return (
                FakeResponse(200, project)
                if project
                else FakeResponse(404, "project")
            )

        project_name = parts[2]

        if parts[5] == "workitemtypes":
            return FakeResponse(200, {"value": sample.RISK_FIELDS})

        if parts[5] == "classificationnodes":
            return FakeResponse(200, sample.ITERATION_TREE)

        if method == "POST" and parts[5] != "wiql":
            body = json if json is not None else jsonlib.loads(data)
            FakeAzureSession.posts.append(
                {"path": "/".join(parts[5:]), "body": body},
            )

            if project_name == "WRITE403":
                return FakeResponse(403, "forbidden")

            return FakeResponse(200, {"id": 999})

        if parts[5] == "wiql":
            if project_name == "ERR401":
                return FakeResponse(401, "unauthorized")

            if project_name == "ERR500":
                return FakeResponse(500, "boom " * 100)

            query = json["query"]
            route = next(
                (ids for text, ids in sample.WIQL_ROUTES if text in query),
                [],
            )
            return FakeResponse(200, {"workItems": [{"id": i} for i in route]})

        if project_name == "DETAIL500":
            return FakeResponse(500, "detail")

        if len(parts) > 6:
            return FakeResponse(200, sample.WORK_ITEMS[parts[6]])

        fields = params.get("fields")
        items = []

        for item_id in params["ids"].split(","):
            item = copy.deepcopy(sample.WORK_ITEMS[item_id])

            if fields:
                keep = fields.split(",")
                item["fields"] = {
                    key: value
                    for key, value in item["fields"].items()
                    if key in keep
                }

            items.append(item)

        return FakeResponse(200, {"value": items})


class MemoryCache:
    def __init__(self):
        self.values = {}

    def get(self, key):
        return self.values.get(key)

    def set(self, key, value, timeout):
        self.values[key] = copy.deepcopy(value)

    def delete(self, key):
        return self.values.pop(key, None)
