from datetime import datetime

from apps.ejecutivo.services.project_dashboard import current_history_status


def test_deployment_resumption_overrides_old_suspension():
    history = {
        "historialCompleto": [
            {"fase": "Deployment", "fechaInicio": "2026-10-15"}
        ],
        "suspensiones": [
            {"fechaInicio": "2026-09-25", "fechaFin": "2026-10-15"}
        ],
    }
    assert (
        current_history_status("Suspendido", history, datetime(2026, 10, 16))
        == "Deployment"
    )
    history["suspensiones"].append({"fechaInicio": "2026-10-17"})
    assert (
        current_history_status("Suspendido", history, datetime(2026, 10, 16))
        == "Deployment"
    )
    assert (
        current_history_status("Deployment", history, datetime(2026, 10, 18))
        == "Suspendido"
    )
