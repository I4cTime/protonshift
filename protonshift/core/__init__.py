"""ProtonShift domain core — pure Python, no UI, no web layer.

These modules are the crown jewels lifted straight out of the original
ProtonShift backend. They know nothing about Qt or FastAPI; the UI binds to
them through thin QObject controllers in ``protonshift.controllers``.
"""
