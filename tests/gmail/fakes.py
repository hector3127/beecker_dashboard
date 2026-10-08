"""Datos y dobles de Gmail para las pruebas (sin red ni correos reales)."""

from typing import Any

ME = "hector@beecker.ai"


def make_message(
    subject: str,
    sender: str,
    to: str = "",
    cc: str = "",
    reply_to: str = "",
    message_id: str = "<m1@mail>",
    references: str = "",
    date: int = 1000,
    snippet: str = "",
) -> dict[str, Any]:
    """Mensaje de Gmail leido con format=metadata."""
    headers = [
        {"name": "Subject", "value": subject},
        {"name": "From", "value": sender},
        {"name": "To", "value": to},
        {"name": "Cc", "value": cc},
        {"name": "Message-ID", "value": message_id},
    ]

    if reply_to:
        headers.append({"name": "Reply-To", "value": reply_to})

    if references:
        headers.append({"name": "References", "value": references})

    return {
        "id": f"msg{date}",
        "internalDate": str(date),
        "snippet": snippet,
        "payload": {"headers": headers},
    }


def make_thread(thread_id: str, *messages: dict[str, Any]) -> dict[str, Any]:
    """Hilo de Gmail con sus mensajes."""
    return {"id": thread_id, "messages": list(messages)}


class FakeGmail:
    """Gmail en memoria: registra lo que se intento crear o enviar."""

    def __init__(self, threads: dict[str, dict[str, Any]]) -> None:
        self.threads = threads
        self.queries: list[tuple[str, int]] = []
        self.drafts: list[tuple[str, str]] = []
        self.sent: list[tuple[str, str]] = []

    def search_thread_ids(self, query: str, limit: int) -> list[str]:
        """Devuelve los hilos cuyo asunto contiene el texto buscado."""
        self.queries.append((query, limit))
        wanted = [
            part.strip('"').lower()
            for part in query.replace("subject:", " ").split('"')
            if part.strip()
        ]

        def matches(thread: dict[str, Any]) -> bool:
            subject = thread["messages"][0]["payload"]["headers"][0]["value"]

            return all(word in subject.lower() for word in wanted)

        return [tid for tid, thread in self.threads.items() if matches(thread)][
            :limit
        ]

    def get_thread(self, thread_id: str) -> dict[str, Any]:
        """Lee un hilo."""
        return self.threads[thread_id]

    def create_draft(self, raw: str, thread_id: str) -> dict[str, Any]:
        """Guarda el borrador en memoria."""
        self.drafts.append((raw, thread_id))

        return {
            "id": "d1",
            "message": {"id": "msgdraft", "threadId": thread_id},
        }

    def send_message(self, raw: str, thread_id: str) -> dict[str, Any]:
        """Guarda el envio en memoria."""
        self.sent.append((raw, thread_id))

        return {"id": "msgsent", "threadId": thread_id}


class FakeResponse:
    """Respuesta HTTP minima."""

    def __init__(self, status_code: int, payload: Any = None) -> None:
        self.status_code = status_code
        self._payload = payload

    def json(self) -> Any:
        """Cuerpo JSON."""
        if self._payload is None:
            raise ValueError("sin cuerpo")

        return self._payload


class FakeHttp:
    """Cliente HTTP que responde lo programado y anota las llamadas."""

    def __init__(self, *responses: FakeResponse) -> None:
        self.responses = list(responses)
        self.calls: list[tuple[str, str, dict[str, Any]]] = []

    def _next(self) -> FakeResponse:
        return self.responses.pop(0)

    def request(self, method: str, url: str, **kwargs: Any) -> FakeResponse:
        """Simula requests.request."""
        self.calls.append((method, url, kwargs))

        return self._next()

    def post(self, url: str, **kwargs: Any) -> FakeResponse:
        """Simula requests.post."""
        self.calls.append(("POST", url, kwargs))

        return self._next()

    def get(self, url: str, **kwargs: Any) -> FakeResponse:
        """Simula requests.get."""
        self.calls.append(("GET", url, kwargs))

        return self._next()
