"""Dobles de prueba de Clockify."""

from datetime import date


class FakeResponse:
    def __init__(self, status_code, payload):
        self.status_code = status_code
        self._payload = payload

    def json(self):
        if isinstance(self._payload, Exception):
            raise self._payload
        return self._payload


class FakeSession:
    """Sesion HTTP que regresa respuestas en orden."""

    def __init__(self, responses):
        self.headers = {}
        self.responses = list(responses)
        self.calls = []

    def request(self, method, url, timeout, **kwargs):
        self.calls.append((method, url, kwargs))
        return self.responses.pop(0)


class DictCache:
    def __init__(self):
        self.values = {}

    def get(self, key):
        return self.values.get(key)

    def set(self, key, value, timeout):
        self.values[key] = value


class FakeClockifyClient:
    def __init__(self, projects, entries_by_project, failing=()):
        self.projects = projects
        self.entries_by_project = entries_by_project
        self.failing = set(failing)
        self.report_calls = []

    def list_projects(self, workspace_id):
        return self.projects

    def fetch_detailed_report(
        self,
        workspace_id,
        project_id,
        start_date: date,
        end_date: date,
        timezone_name,
    ):
        from apps.clockify.exceptions import ClockifyReportForbiddenError

        self.report_calls.append((project_id, start_date, end_date))
        if project_id in self.failing:
            raise ClockifyReportForbiddenError("HTTP 403")
        return self.entries_by_project.get(project_id, [])

    def fetch_detailed_report_counted(
        self,
        workspace_id,
        project_id,
        start_date: date,
        end_date: date,
        timezone_name,
    ):
        entries = self.fetch_detailed_report(
            workspace_id,
            project_id,
            start_date,
            end_date,
            timezone_name,
        )
        return entries, 1
