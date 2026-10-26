"""Persistent account logos with capability, scope and CSRF validation."""

import hashlib
import warnings

from django.http import HttpResponse, HttpResponseNotModified
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect
from PIL import Image, UnidentifiedImageError
from rest_framework.exceptions import NotFound, ParseError
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.access.checks import capability_by_method, resolve
from apps.access.scope import account_key
from apps.portal.models import AccountLogo
from apps.portal.services.account_logos import compact_logo, content_type

LogoPermission = capability_by_method(
    (
        "view_operations",
        "view_executive",
        "view_costs",
        "view_agreements",
        "edit_operations",
    ),
    ("edit_operations",),
)


def account(request):
    """Validate the requested account and its scope."""
    name = str(
        request.query_params.get("account") or request.data.get("account") or ""
    ).strip()
    if not name or len(name) > 150:
        raise ParseError("Indica una cuenta válida.")
    if not resolve(request).scope.allows_account(name):
        raise NotFound("No existe esa cuenta.")
    return name


def logo_row(row):
    """Only metadata goes into the catalogue response."""
    return {
        "account": row.account,
        "key": row.key,
        "url": (
            f"/api/v1/account-logos/{row.pk}/image/"
            f"?v={row.updated_at.timestamp()}"
        ),
    }


@method_decorator(csrf_protect, name="dispatch")
class AccountLogoListView(APIView):
    """Read visible logos, upload one or remove the current account logo."""

    permission_classes = [*APIView.permission_classes, LogoPermission]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get(self, request):
        """List visible metadata without loading image blobs."""
        access = resolve(request)
        rows = AccountLogo.objects.defer("image")
        return Response(
            {
                "data": {
                    "items": [
                        logo_row(row)
                        for row in rows
                        if access.scope.allows_account(row.account)
                    ],
                    "can_edit": access.can("edit_operations"),
                },
                "meta": {},
            }
        )

    def post(self, request):
        """Decode and store compact raster images."""
        name = account(request)
        upload = request.FILES.get("image")
        if not upload or upload.size > 2 * 1024 * 1024:
            raise ParseError("Elige una imagen PNG, JPG o WebP de hasta 2 MB.")
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("error", Image.DecompressionBombWarning)
                with Image.open(upload) as source:
                    if (
                        source.format not in {"PNG", "JPEG", "WEBP"}
                        or source.width * source.height > 16000000
                    ):
                        raise ValueError("Formato o dimensiones no válidos")
                    data = compact_logo(source)
        except (
            UnidentifiedImageError,
            OSError,
            ValueError,
            Image.DecompressionBombError,
            Image.DecompressionBombWarning,
        ):
            raise ParseError(
                "La imagen no es válida. Usa PNG, JPG o WebP."
            ) from None
        row, _ = AccountLogo.objects.update_or_create(
            key=account_key(name),
            defaults={"account": name, "image": data},
        )
        return Response({"data": logo_row(row), "meta": {}})

    def delete(self, request):
        """Remove only the selected account logo."""
        name = account(request)
        AccountLogo.objects.filter(key=account_key(name)).delete()
        return Response({"data": {"removed": True}, "meta": {}})


class AccountLogoImageView(APIView):
    """Serve validated raster content within account access."""

    permission_classes = AccountLogoListView.permission_classes

    def get(self, request, pk):
        """Revalidate private images to honour permission changes."""
        row = AccountLogo.objects.filter(pk=pk).first()
        if row is None or not resolve(request).scope.allows_account(
            row.account
        ):
            raise NotFound("No existe esa imagen.")
        data = bytes(row.image)
        etag = '"' + hashlib.sha256(data).hexdigest() + '"'
        if request.headers.get("If-None-Match") == etag:
            response = HttpResponseNotModified()
        else:
            response = HttpResponse(data, content_type=content_type(data))
        response["ETag"] = etag
        response["Cache-Control"] = "private, no-cache"
        response["X-Content-Type-Options"] = "nosniff"
        return response
