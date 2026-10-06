"""Dobles de prueba de Azure y Clockify para Capacidad instalada."""

from datetime import date, datetime

from apps.azure_devops.services.azure_client import flatten_iterations
from apps.azure_devops.services.project_resolver import resolve_azure_project
from apps.clockify.exceptions import ClockifyProjectError
from apps.clockify.services.clockify_client import ClockifyProject
from apps.clockify.services.time_entry_loader import ProjectReport
from core.time_entries.models import TimeEntry
from tests.capacidad import sample_data


class FakeAzureSource:
    """Azure con los arboles de sample_data."""

    def __init__(self):
        self.refresh_calls = []

    def resolve_project(self, project_id):
        return resolve_azure_project(project_id, sample_data.AZURE_PROJECTS)

    def list_iterations(self, azure_project, force_refresh):
        self.refresh_calls.append(force_refresh)
        iterations = []
        flatten_iterations(
            sample_data.AZURE_TREES[azure_project],
            "",
            iterations,
        )
        return iterations


def build_entry(index, record):
    return TimeEntry(
        entry_id=str(index),
        project_id="",
        resource_name=record["recurso"],
        entry_date=datetime.fromisoformat(record["fecha"]),
        duration_hours=record["duracion"],
        is_billable=True,
        costing_rate=0.0,
        task_name=record.get("task", ""),
    )


def build_report_loader(reader):
    def load_report(base_id, date_range: tuple[date, date], force_refresh):
        records = sample_data.CLOCKIFY.get(base_id)

        if records is None:
            raise ClockifyProjectError(f"Sin Clockify {base_id}")

        return ProjectReport(
            ClockifyProject(f"id-{base_id}", base_id),
            [
                build_entry(index, record)
                for index, record in enumerate(records)
            ],
            1,
        )

    return load_report
