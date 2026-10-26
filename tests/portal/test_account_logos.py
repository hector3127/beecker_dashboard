"""Account logo persistence, validation, CSRF and access control."""

from io import BytesIO

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client
from PIL import Image

from apps.access.scope import AccessScope
from apps.portal.models import AccountLogo

pytestmark = pytest.mark.django_db
API = "/api/v1/account-logos/"


def picture():
    output = BytesIO()
    Image.new("RGB", (700, 400), "green").save(output, "JPEG")
    return SimpleUploadedFile("logo.jpg", output.getvalue(), "image/jpeg")


def upload(client, account="ACME"):
    return client.post(API, {"account": account, "image": picture()})


def test_upload_replace_serve_and_remove(client):
    response = upload(client)
    assert response.status_code == 200
    url = response.json()["data"]["url"]
    image = client.get(url)
    assert image["Content-Type"] in {"image/png", "image/webp"}
    with Image.open(BytesIO(image.content)) as decoded:
        assert decoded.size == (384, 219)
    assert upload(client, "Acme").status_code == 200
    assert AccountLogo.objects.count() == 1
    assert client.get(API).json()["data"]["items"][0]["account"] == "Acme"
    assert client.delete(API + "?account=ACME").status_code == 200
    assert not AccountLogo.objects.exists()


@pytest.mark.parametrize(
    "data",
    [
        b"not an image",
        b'<svg xmlns="http://www.w3.org/2000/svg"></svg>',
        b"x" * (2 * 1024 * 1024 + 1),
    ],
    ids=["invalid", "svg", "too-large"],
)
def test_invalid_files_do_not_replace_a_logo(client, data):
    upload(client)
    previous = bytes(AccountLogo.objects.get().image)
    bad = SimpleUploadedFile("logo.png", data, "image/png")
    assert (
        client.post(API, {"account": "ACME", "image": bad}).status_code == 400
    )
    assert bytes(AccountLogo.objects.get().image) == previous


def test_permissions_and_account_scope(client, enforced):
    enforced("initial-editor", caps=frozenset({"edit_operations"}))
    assert upload(client).status_code == 200
    row = AccountLogo.objects.get()
    enforced("reader", caps=frozenset({"view_operations"}))
    assert client.get(API).json()["data"]["can_edit"] is False
    assert upload(client).status_code == 403
    assert client.delete(API + "?account=ACME").status_code == 403
    enforced(
        "editor",
        caps=frozenset({"view_operations", "edit_operations"}),
        scope=AccessScope.limited(accounts=["Beta"]),
    )
    assert client.get(API).json()["data"]["items"] == []
    assert client.get(f"{API}{row.pk}/image/").status_code == 404
    assert upload(client).status_code == 404
    assert client.delete(API + "?account=ACME").status_code == 404
    assert upload(client, "Beta").status_code == 200


def test_csrf_required_even_in_local_mode():
    client = Client(enforce_csrf_checks=True)
    assert upload(client).status_code == 403
    assert client.delete(API + "?account=ACME").status_code == 403


def test_compression_alpha_size_and_private_revalidation(client):
    image = Image.new("RGBA", (1200, 700), (0, 0, 0, 0))
    from PIL import ImageDraw

    draw = ImageDraw.Draw(image)
    for x in range(0, 1200, 5):
        draw.line((x, 150, 1200 - x, 550), fill=(x % 255, 150, 200, 255))
    original = BytesIO()
    image.save(original, "PNG")
    response = client.post(
        API,
        {
            "account": "ACME",
            "image": SimpleUploadedFile(
                "transparent.png", original.getvalue(), "image/png"
            ),
        },
    )
    assert response.status_code == 200
    url = response.json()["data"]["url"]
    served = client.get(url)
    assert len(served.content) < len(original.getvalue())
    with Image.open(BytesIO(served.content)) as decoded:
        assert max(decoded.size) <= 384
        assert decoded.convert("RGBA").getpixel((0, 0))[3] == 0
    cached = client.get(url, HTTP_IF_NONE_MATCH=served["ETag"])
    assert cached.status_code == 304
    assert cached.content == b""
    assert cached["Cache-Control"] == "private, no-cache"


def test_legacy_png_still_loads(client):
    original = BytesIO()
    Image.new("RGB", (20, 20), "red").save(original, "PNG")
    row = AccountLogo.objects.create(
        key="old", account="Old", image=original.getvalue()
    )
    response = client.get(f"{API}{row.pk}/image/")
    assert response["Content-Type"] == "image/png"
    assert response.content == original.getvalue()
