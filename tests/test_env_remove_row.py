"""Regression test for issue #52: the env editor's ✕ button was a no-op.

QML calls ``model.removeRow(i)``. QAbstractItemModel already exposes that
name as an invokable C++ convenience, so a same-named Python slot is never
reached from QML — the call lands on the built-in, which delegates to the
virtual ``removeRows()``. The fix overrides ``removeRows``; this test drives
the call through a real QML engine (not Python) so the dispatch path that
broke is the one being tested. Runs headless via QT_QPA_PLATFORM=offscreen
(set in CI; forced here for local runs).
"""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QUrl  # noqa: E402
from PySide6.QtGui import QGuiApplication  # noqa: E402
from PySide6.QtQml import QQmlApplicationEngine  # noqa: E402

from protonshift.controllers.env_controller import EnvVarsModel  # noqa: E402

_QML = b"""
import QtQml
QtObject {
    required property var model
    function removeAt(i) { return model.removeRow(i) }
}
"""


def _qml_root(model: EnvVarsModel) -> tuple[QQmlApplicationEngine, object]:
    # engine returned so it outlives the root object in the caller's scope
    engine = QQmlApplicationEngine()
    engine.setInitialProperties({"model": model})
    engine.loadData(_QML, QUrl("test_env_remove_row.qml"))
    roots = engine.rootObjects()
    assert roots, "inline QML failed to load"
    return engine, roots[0]


def test_qml_remove_row_removes_from_model() -> None:
    QGuiApplication.instance() or QGuiApplication([])
    model = EnvVarsModel()
    model.reset_rows([("FOO", "1"), ("BAR", "2")])
    modified: list[bool] = []
    model.modified.connect(lambda: modified.append(True))

    engine, root = _qml_root(model)
    assert root.removeAt(0) is True
    assert model.to_dict() == {"BAR": "2"}
    assert modified, "removal must emit modified so the editor turns dirty"


def test_qml_remove_row_out_of_range_is_rejected() -> None:
    QGuiApplication.instance() or QGuiApplication([])
    model = EnvVarsModel()
    model.reset_rows([("FOO", "1")])

    engine, root = _qml_root(model)
    assert root.removeAt(5) is False
    assert root.removeAt(-1) is False
    assert model.to_dict() == {"FOO": "1"}
