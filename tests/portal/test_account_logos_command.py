"""El comando account_logos mueve los logos entre bases sin perder bytes."""

import pytest
from django.core.management import CommandError, call_command

from apps.portal.models import AccountLogo

pytestmark = pytest.mark.django_db


def test_export_then_import_restores_the_same_images(tmp_path):
    AccountLogo.objects.create(key="acme", account="ACME", image=b"\x89PNGdata")
    file = tmp_path / "logos.json"

    call_command("account_logos", "export", str(file))
    AccountLogo.objects.all().delete()
    call_command("account_logos", "import", str(file))

    row = AccountLogo.objects.get(key="acme")
    assert (row.account, bytes(row.image)) == ("ACME", b"\x89PNGdata")


def test_import_updates_without_deleting_other_logos(tmp_path):
    AccountLogo.objects.create(key="old", account="Old", image=b"1")
    file = tmp_path / "logos.json"
    file.write_text(
        '[{"key": "acme", "account": "ACME", "image": "Mg=="}]',
        encoding="utf-8",
    )

    call_command("account_logos", "import", str(file))

    assert AccountLogo.objects.count() == 2


def test_a_broken_file_is_reported(tmp_path):
    file = tmp_path / "logos.json"
    file.write_text("no es json", encoding="utf-8")

    with pytest.raises(CommandError):
        call_command("account_logos", "import", str(file))
