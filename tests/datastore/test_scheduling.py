from datetime import timedelta
from io import StringIO

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.utils import timezone

from apps.datastore.management.commands.sync_datastore import Command
from apps.datastore.models import (
    AzureProject,
    Client,
    ClockifyMonthSync,
    SheetSnapshot,
    SyncLock,
    SyncRun,
)
from apps.datastore.services.locks import sync_lock

pytestmark = pytest.mark.django_db


def test_a_second_run_is_refused_while_the_first_holds_the_lock():
    with sync_lock("hojas", 600) as first:
        with sync_lock("hojas", 600) as second:
            assert (first, second) == (True, False)
        # La ejecucion rechazada no suelta el candado de la primera.
        assert SyncLock.objects.filter(name="hojas").exists()
    assert not SyncLock.objects.filter(name="hojas").exists()


def test_different_steps_do_not_block_each_other():
    with sync_lock("hojas", 600) as hojas, sync_lock("azure", 600) as azure:
        assert hojas and azure


def test_the_lock_is_released_even_if_the_step_fails():
    with pytest.raises(RuntimeError):
        with sync_lock("clockify", 600):
            raise RuntimeError("fallo")
    with sync_lock("clockify", 600) as again:
        assert again is True


def test_an_abandoned_lock_is_taken_over_after_its_deadline():
    SyncLock.objects.create(
        name="azure",
        holder="proceso-muerto",
        locked_at=timezone.now() - timedelta(minutes=45),
    )
    with sync_lock("azure", 30 * 60) as taken:
        assert taken is True
        assert SyncLock.objects.get(name="azure").holder != "proceso-muerto"
    SyncLock.objects.create(
        name="hojas",
        holder="otro",
        locked_at=timezone.now() - timedelta(minutes=5),
    )
    with sync_lock("hojas", 15 * 60) as busy:
        assert busy is False


def options(**overrides):
    base = {
        "pasos": None,
        "solo_hojas": False,
        "solo_azure": False,
        "sin_hojas": False,
        "sin_azure": False,
        "sin_catalogos": False,
    }
    return {**base, **overrides}


@pytest.mark.parametrize(
    ("given", "expected"),
    [
        ({}, ["hojas", "azure", "clockify", "lecturas", "catalogos"]),
        ({"pasos": "hojas,azure,catalogos"}, ["hojas", "azure", "catalogos"]),
        ({"pasos": "clockify, catalogos"}, ["clockify", "catalogos"]),
        # El orden es siempre el de ejecucion, no el que se escribio.
        ({"pasos": "catalogos,hojas"}, ["hojas", "catalogos"]),
        ({"solo_hojas": True}, ["hojas", "catalogos"]),
        ({"solo_azure": True}, ["azure"]),
        ({"sin_azure": True}, ["hojas", "clockify", "lecturas", "catalogos"]),
        (
            {"sin_hojas": True, "sin_catalogos": True},
            ["azure", "clockify", "lecturas"],
        ),
        ({"pasos": "hojas,azure", "sin_azure": True}, ["hojas"]),
    ],
)
def test_the_flags_select_the_steps_of_each_schedule(given, expected):
    assert Command().selected_steps(options(**given)) == expected


def test_an_unknown_step_is_rejected_with_the_valid_ones():
    with pytest.raises(CommandError, match="Paso desconocido: horas"):
        Command().selected_steps(options(pasos="hojas,horas"))


def test_a_step_held_by_another_run_is_skipped_but_the_others_still_run():
    SyncLock.objects.create(
        name="hojas", holder="otro", locked_at=timezone.now()
    )
    out = StringIO()
    call_command("sync_datastore", "--pasos", "hojas,catalogos", stdout=out)
    text = out.getvalue()
    assert "hojas: otra sincronizacion sigue en curso; se omite." in text
    assert "Catalogos:" in text
    # El candado ajeno sigue en su lugar y el propio se solto.
    assert SyncLock.objects.get(name="hojas").holder == "otro"
    assert not SyncLock.objects.filter(name="catalogos").exists()


def test_locks_are_released_after_a_step_that_fails(settings):
    settings.CLOCKIFY_API_KEY = ""
    settings.CLOCKIFY_WORKSPACE_ID = ""
    with pytest.raises(CommandError, match="CLOCKIFY_API_KEY"):
        call_command("sync_datastore", "--pasos", "clockify", stdout=StringIO())
    assert not SyncLock.objects.exists()


def run_check(**limits):
    out = StringIO()
    args = [
        f"--{name.replace('_', '-')}={value}" for name, value in limits.items()
    ]
    try:
        call_command("check_datastore", *args, stdout=out)
    except CommandError as error:
        return out.getvalue(), str(error)
    return out.getvalue(), ""


def fresh_data(hours_ago=0.0):
    moment = timezone.now() - timedelta(hours=hours_ago)
    SheetSnapshot.objects.create(name="MPB", rows=[], synced_at=moment)
    AzureProject.objects.create(name="P", synced_at=moment)
    run = SyncRun.objects.create(kind="test")
    ClockifyMonthSync.objects.create(
        month=timezone.localdate().replace(day=1),
        entries_count=0,
        total_seconds=0,
        synced_at=moment,
        run=run,
    )


def test_the_check_reports_a_source_that_was_never_synced():
    out, error = run_check()
    assert "hojas: nunca sincronizado" in out
    assert "azure: nunca sincronizado" in error


def test_the_check_passes_when_everything_is_recent():
    fresh_data(hours_ago=0.5)
    out, error = run_check()
    assert error == ""
    assert "hojas: hace 0.5 h" in out and "VENCIDO" not in out


def test_the_check_fails_when_a_source_is_older_than_its_limit():
    fresh_data(hours_ago=5)
    out, error = run_check(hojas_horas=3, azure_horas=6, clockify_horas=30)
    assert error == "hojas vencido"
    assert "hojas: hace 5.0 h (limite 3 h) - VENCIDO" in out


def test_the_check_lists_runs_in_progress():
    fresh_data()
    SyncLock.objects.create(
        name="azure",
        holder="x",
        locked_at=timezone.now() - timedelta(minutes=7),
    )
    out, _ = run_check()
    assert "en curso: azure desde hace 7 min" in out


def test_catalogs_are_not_needed_for_the_check():
    # La revision no depende de que existan clientes u otros catalogos.
    fresh_data()
    assert Client.objects.count() == 0
    assert run_check()[1] == ""
