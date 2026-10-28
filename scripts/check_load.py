"""Prueba acotada de GET concurrentes en el servidor local, sin escrituras."""

import argparse
import json
import statistics
import time
from concurrent.futures import ThreadPoolExecutor
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import (
    HTTPRedirectHandler,
    ProxyHandler,
    Request,
    build_opener,
)


class NoRedirect(HTTPRedirectHandler):
    """Una redirección no convierte la prueba local en una consulta externa."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        """Las respuestas 3xx se registran como error, sin seguir su destino."""
        return None


def run_load(url: str, requests: int = 40, workers: int = 4) -> dict:
    """Mide respuestas JSON locales sin compartir cookies entre peticiones."""
    parsed = urlsplit(url)
    if parsed.scheme not in {"http", "https"} or parsed.hostname not in {
        "localhost",
        "127.0.0.1",
        "::1",
    }:
        raise ValueError("Solo se permiten servidores locales HTTP(S).")
    if (
        parsed.username
        or parsed.password
        or not 1 <= requests <= 1000
        or not 1 <= workers <= 32
    ):
        raise ValueError(
            "Usa 1–1000 solicitudes y 1–32 conexiones, "
            "sin credenciales en la URL."
        )

    def get(_: int) -> tuple[float, str]:
        start = time.perf_counter()
        try:
            opener = build_opener(ProxyHandler({}), NoRedirect())
            with opener.open(
                Request(url, headers={"Accept": "application/json"}), timeout=30
            ) as response:
                data = json.load(response)
                body = (
                    data.get("data", data) if isinstance(data, dict) else None
                )
                error = (
                    ""
                    if response.status == 200
                    and isinstance(body, dict)
                    and body.get("ok", True)
                    and not body.get("error")
                    and not data.get("error")
                    else "Respuesta no válida"
                )
        except (HTTPError, URLError, OSError, ValueError) as exception:
            error = type(exception).__name__
        return time.perf_counter() - start, error

    started = time.perf_counter()
    with ThreadPoolExecutor(max_workers=workers) as pool:
        outcomes = list(pool.map(get, range(requests)))
    timings = sorted(duration for duration, _ in outcomes)
    return {
        "requests": requests,
        "workers": workers,
        "success": sum(not error for _, error in outcomes),
        "errors": [error for _, error in outcomes if error],
        "elapsed_seconds": round(time.perf_counter() - started, 3),
        "median_seconds": round(statistics.median(timings), 3),
        "p95_seconds": round(
            timings[max(0, (95 * len(timings) + 99) // 100 - 1)], 3
        ),
    }


def main() -> None:
    """No consulta Azure/Clockify directamente ni envía datos de formularios."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("url", help="Endpoint JSON local de lectura.")
    parser.add_argument("--requests", type=int, default=40)
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()
    result = run_load(args.url, args.requests, args.workers)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(bool(result["errors"]))


if __name__ == "__main__":
    main()
