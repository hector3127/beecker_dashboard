import contextvars
import threading

import pytest

from core.utils import parallel
from core.utils.parallel import is_pool_worker, map_in_parallel


def test_results_keep_the_order_of_the_items():
    assert map_in_parallel(lambda n: n * 2, list(range(20)), 4) == [
        n * 2 for n in range(20)
    ]


def test_one_item_or_one_worker_runs_in_the_calling_thread():
    main = threading.get_ident()
    assert map_in_parallel(lambda n: threading.get_ident(), [1], 4) == [main]
    assert map_in_parallel(lambda n: threading.get_ident(), [1, 2], 1) == [
        main,
        main,
    ]


def test_every_task_runs_and_the_first_error_by_item_order_is_raised():
    ran = []

    def task(n):
        ran.append(n)
        if n in (3, 7):
            raise ValueError(f"fallo {n}")
        return n

    with pytest.raises(ValueError, match="fallo 3"):
        map_in_parallel(task, list(range(10)), 3)
    assert sorted(ran) == list(range(10))


def test_tasks_see_the_context_of_the_caller():
    variable = contextvars.ContextVar("variable", default="nada")
    variable.set("valor del llamador")

    assert (
        map_in_parallel(lambda n: variable.get(), [1, 2, 3, 4], 2)
        == ["valor del llamador"] * 4
    )


def test_worker_threads_close_their_database_connections_once(monkeypatch):
    closed = []
    monkeypatch.setattr(
        parallel.connections, "close_all", lambda: closed.append(1)
    )
    seen = []
    map_in_parallel(lambda n: seen.append(is_pool_worker()), list(range(12)), 3)

    assert all(seen)
    assert len(closed) == 3  # una por hilo, no una por tarea
    assert is_pool_worker() is False
