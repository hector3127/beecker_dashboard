"""Authenticated, whole-portfolio EVA extraction controls and timings."""

from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.access.checks import capability_permission
from apps.portal.services.eva_native_refresh import request_refresh
from apps.portal.services.eva_native_store import extraction_status


@method_decorator(csrf_protect, name="dispatch")
class EvaExtractionView(APIView):
    """GET is local/read-only; POST queues a source refresh."""

    permission_classes = [
        *APIView.permission_classes,
        capability_permission("view_operations", whole_portfolio=True),
    ]

    def get(self, request: Request) -> Response:
        """Read persisted timings and diagnostics without provider calls."""
        return Response(
            {"data": extraction_status(), "meta": {"source": "local"}},
            headers={"Cache-Control": "no-store"},
        )

    def post(self, request: Request) -> Response:
        """Start/coalesce an extraction; normal API CSRF policy is retained."""
        queued = request_refresh()
        return Response(
            {"data": {**extraction_status(), "queued": queued}, "meta": {}},
            status=202,
            headers={"Cache-Control": "no-store"},
        )
