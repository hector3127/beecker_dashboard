import os

import pytest

pytestmark = pytest.mark.django_db(transaction=True)


def test_dom(datos, portal):
    portal.set_viewport_size({"width": 1450, "height": 1000})
    portal.goto(portal.base + os.environ["DOM_PATH"])
    portal.wait_for_timeout(3000)
    out = portal.evaluate(
        "(sel) => document.querySelector(sel).outerHTML", os.environ["DOM_SEL"]
    )
    open(os.environ["DOM_OUT"], "w", encoding="utf-8").write(out)
