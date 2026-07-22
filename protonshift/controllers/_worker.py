"""Shared worker-thread guard for controllers.

Every controller runs disk/subprocess work on a daemon thread and reports back
via a queued Qt signal. Before this helper, any *unexpected* exception in a
worker body killed the thread before the result signal fired, permanently
wedging the controller's ``loading``/``busy`` flag (review M5).

``start_worker`` wraps the body: on any exception the ``on_error`` callback
receives a short ``"ExceptionType: message"`` string. ``on_error`` runs on the
worker thread, so it must be thread-safe — in practice, pass the ``emit`` of a
queued result/error signal and mutate GUI-read state only in the connected
handler on the GUI thread.

Deliberately PySide-free so it can be unit-tested without a Qt runtime.
"""

from __future__ import annotations

import threading
from collections.abc import Callable


def start_worker(
    target: Callable[..., None],
    *args: object,
    on_error: Callable[[str], None] | None = None,
) -> threading.Thread:
    """Run ``target(*args)`` on a daemon thread, routing exceptions to ``on_error``."""

    def _run() -> None:
        try:
            target(*args)
        except Exception as exc:  # noqa: BLE001 — the guard exists to stop thread death wedging the UI
            if on_error is not None:
                on_error(f"{type(exc).__name__}: {exc}")

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()
    return thread
