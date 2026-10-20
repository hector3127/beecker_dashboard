"""Request-local explicit bypass of source caches in background refreshes."""

from contextvars import ContextVar

force_sources = ContextVar("force_sources", default=False)
