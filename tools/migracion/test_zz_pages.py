"""Capturas temporales (no se confirman)."""

import os

import pytest

from tests.portal.test_views import stub_history

pytestmark = pytest.mark.django_db(transaction=True)

OUT = os.environ.get("SHOTS_DIR", ".")
TAG = os.environ.get("SHOTS_TAG", "x")
PAGES = dict(
    item.split("=", 1)
    for item in os.environ.get("SHOTS_PAGES", "").split(";")
    if item
)
WIDTH = int(os.environ.get("SHOTS_WIDTH", "1450"))


@pytest.mark.parametrize("name", list(PAGES))
def test_shot(monkeypatch, datos, portal, name):
    stub_history(monkeypatch)
    portal.set_viewport_size({"width": WIDTH, "height": 1000})
    portal.goto(portal.base + PAGES[name])
    portal.wait_for_timeout(3500)
    clip = os.environ.get("SHOTS_CLIP")
    if clip:
        x, y, w, h = (int(v) for v in clip.split(","))
        portal.screenshot(
            path=f"{OUT}/{TAG}_{name}.png",
            clip={"x": x, "y": y, "width": w, "height": h},
            full_page=True,
        )
    else:
        portal.screenshot(path=f"{OUT}/{TAG}_{name}.png", full_page=True)
