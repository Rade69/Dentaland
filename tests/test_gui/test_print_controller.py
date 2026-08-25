"""Testovi PrintController-a (REF-07)."""

from __future__ import annotations

from datetime import date

from desktop.controllers import print_controller as pc_mod
from desktop.controllers.print_controller import PrintController

WEEK_START = date(2026, 8, 17)


def _controller() -> PrintController:
    return PrintController(object(), None, lambda: WEEK_START)


def test_print_week_poziva_build_i_preview(monkeypatch) -> None:
    calls: list = []

    def fake_build_week_schedule(store, week_start):
        calls.append(("schedule", week_start))
        return "sched"

    def fake_build_week_document(schedule):
        calls.append(("document", schedule))
        return "doc"

    def fake_preview_document(parent, doc, **kwargs):
        calls.append(("preview", doc, kwargs))

    monkeypatch.setattr(pc_mod, "build_week_schedule", fake_build_week_schedule)
    monkeypatch.setattr(pc_mod, "build_week_document", fake_build_week_document)
    monkeypatch.setattr(pc_mod, "preview_document", fake_preview_document)

    _controller().print_week()

    assert calls == [
        ("schedule", WEEK_START),
        ("document", "sched"),
        ("preview", "doc", {"landscape": True}),
    ]


def test_save_pdf_koristi_getSaveFileName_i_pdf_path(monkeypatch) -> None:
    def fake_get_save_file_name(parent, title, default, filter):
        return ("/tmp/raspored.pdf", "PDF")

    preview_kwargs: list = []

    monkeypatch.setattr(pc_mod.QFileDialog, "getSaveFileName", fake_get_save_file_name)
    monkeypatch.setattr(pc_mod, "build_week_schedule", lambda store, ws: "sched")
    monkeypatch.setattr(pc_mod, "build_week_document", lambda schedule: "doc")
    monkeypatch.setattr(
        pc_mod,
        "preview_document",
        lambda parent, doc, **kwargs: preview_kwargs.append(kwargs),
    )

    _controller().save_pdf()

    assert preview_kwargs == [{"landscape": True, "pdf_path": "/tmp/raspored.pdf"}]


def test_save_pdf_ne_preview_kad_otkazano(monkeypatch) -> None:
    monkeypatch.setattr(
        pc_mod.QFileDialog, "getSaveFileName", lambda *args: ("", "")
    )
    monkeypatch.setattr(pc_mod, "build_week_schedule", lambda store, ws: "sched")

    called: list = []
    monkeypatch.setattr(pc_mod, "preview_document", lambda *a, **k: called.append(1))

    _controller().save_pdf()

    assert called == []
