"""Alcance de datos: cuentas y proyectos permitidos."""

from dataclasses import dataclass

import pytest

from apps.access.capabilities import CATALOG, CODES
from apps.access.scope import AccessScope


@dataclass
class Row:
    id: str
    account: str


ROWS = [
    Row("ROC.NSC.001", "Nestlé"),
    Row("SAAS.CAG.002", "Cagsa"),
    Row("DEV.ACM.003", "Acme"),
]


def test_catalog_codes_are_unique_labeled_and_snake_case():
    assert len(CODES) == len(CATALOG)
    for item in CATALOG:
        assert item.label.strip()
        assert item.code.replace("_", "").isalpha() and item.code.islower()


def test_everything_allows_any_account_and_project():
    scope = AccessScope.everything()

    assert scope.kind == "all"
    assert scope.allows_account("Cualquiera")
    assert scope.allows_project("X.1")
    assert scope.filter_accounts(["A", "B"]) == ["A", "B"]


def test_limited_without_anything_allows_nothing():
    scope = AccessScope.limited()

    assert scope.kind == "limited"
    assert not scope.allows_account("Nestlé")
    assert not scope.allows_project("ROC.NSC.001", account="Nestlé")
    assert scope.filter_projects(ROWS, lambda r: r.id) == []


@pytest.mark.parametrize("written", ["Nestlé", "nestle", "  NESTLÉ "])
def test_accounts_match_without_accents_case_or_spaces(written):
    assert AccessScope.limited(accounts=["Nestlé"]).allows_account(written)


def test_an_allowed_account_gives_access_to_its_projects():
    scope = AccessScope.limited(accounts=["Nestlé"])

    assert scope.allows_project("ROC.NSC.001", account="nestle")
    assert not scope.allows_project("SAAS.CAG.002", account="Cagsa")
    # Sin saber la cuenta del proyecto no se concede nada por la cuenta.
    assert not scope.allows_project("ROC.NSC.001")


def test_own_projects_do_not_open_their_whole_account():
    scope = AccessScope.limited(projects=["roc.nsc.001"])

    assert scope.allows_project("ROC.NSC.001", account="Nestlé")
    assert not scope.allows_project("ROC.NSC.999", account="Nestlé")
    # Una cuenta mezcla proyectos ajenos: sus totales no se ven completos.
    assert not scope.allows_account("Nestlé")


def test_filters_keep_order_and_combine_accounts_and_projects():
    scope = AccessScope.limited(accounts=["Cagsa"], projects=["DEV.ACM.003"])

    kept = scope.filter_projects(ROWS, lambda r: r.id, lambda r: r.account)

    assert [r.id for r in kept] == ["SAAS.CAG.002", "DEV.ACM.003"]
    assert scope.filter_accounts(["Nestlé", "Cagsa", "Acme"]) == ["Cagsa"]


def test_blank_values_never_match():
    scope = AccessScope.limited(accounts=[""], projects=[""])

    assert not scope.allows_account(None)
    assert not scope.allows_project(None)
