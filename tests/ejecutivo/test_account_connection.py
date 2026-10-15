from unittest.mock import Mock
from django.core.cache import cache
from httplib2 import ServerNotFoundError
from apps.ejecutivo import account_rpc


def test_account_network_error_uses_last_successful_result(monkeypatch):
    cache.clear()
    monkeypatch.setattr(account_rpc, "build_sheet_repository", lambda: object())
    build = Mock(return_value={"ok": True, "proyectos": [{"id": "A"}]})
    monkeypatch.setattr(account_rpc.account_view, "build_account_view", build)
    assert account_rpc.get_account_view("Acme")["ok"]
    build.side_effect = ServerNotFoundError("offline")
    saved = account_rpc.get_account_view("Acme")
    assert saved["stale"]
    assert saved["proyectos"] == [{"id": "A"}]
    missing = account_rpc.get_account_view("Other")
    assert not missing["ok"]
    assert "Google Sheets" in missing["error"]
    cache.clear()
