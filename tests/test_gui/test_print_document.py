"""Testovi rendering-a dokumenta za štampu (DENT-016)."""

from __future__ import annotations

from dentaland.services.print_schedule import (
    PrintSchedule,
    PrintScheduleBlock,
    PrintScheduleEntry,
)
from desktop.print_document import build_day_document, build_week_document


def _entry(day_label: str = "Pon", **overrides) -> PrintScheduleEntry:
    fields = {
        "time_range": "09:00–09:30",
        "patient_name": "Ana Anić",
        "doctor_name": "Ljubo",
        "service": "Kontrola",
        "status_label": "Potvrđen",
        "day_label": day_label,
    }
    fields.update(overrides)
    return PrintScheduleEntry(**fields)


def _block(day_label: str = "Pon") -> PrintScheduleBlock:
    return PrintScheduleBlock(
        time_range="12:00–12:30",
        doctor_name="Ljubo",
        label="Pauza",
        day_label=day_label,
    )


def test_day_document_sadrzi_sve_entry_podatke(qtbot) -> None:
    schedule = PrintSchedule(
        title="Ponedjeljak, 17.08.2026.",
        entries=[_entry()],
        blocks=[],
    )
    text = build_day_document(schedule).toPlainText()

    for expected in (
        "Ponedjeljak, 17.08.2026.",
        "09:00–09:30",
        "Ana Anić",
        "Ljubo",
        "Kontrola",
        "Potvrđen",
    ):
        assert expected in text


def test_day_document_prikazuje_blocks(qtbot) -> None:
    schedule = PrintSchedule(
        title="Ponedjeljak, 17.08.2026.",
        entries=[],
        blocks=[_block()],
    )
    text = build_day_document(schedule).toPlainText()

    assert "Pauza" in text
    assert "12:00–12:30" in text
    assert "Ljubo" in text


def test_week_document_ima_kolone_po_danima(qtbot) -> None:
    schedule = PrintSchedule(
        title="17.08. – 22.08.2026.",
        entries=[
            _entry(day_label="Pon", patient_name="Ana Anić"),
            _entry(day_label="Uto", patient_name="Marko Marković", time_range="10:00–10:30"),
        ],
        blocks=[],
    )
    text = build_week_document(schedule).toPlainText()

    for day in ("Pon", "Uto", "Sri", "Čet", "Pet", "Sub"):
        assert day in text
    assert "Ana Anić" in text
    assert "Marko Marković" in text


def test_week_document_prikazuje_blocks_po_danu(qtbot) -> None:
    schedule = PrintSchedule(
        title="17.08. – 22.08.2026.",
        entries=[],
        blocks=[_block(day_label="Sri")],
    )
    text = build_week_document(schedule).toPlainText()

    assert "Pauza" in text
    assert "12:00–12:30" in text


def test_dokument_sadrzi_logo(qtbot) -> None:
    schedule = PrintSchedule(title="Ponedjeljak, 17.08.2026.", entries=[], blocks=[])
    html = build_day_document(schedule).toHtml()

    assert "data:image/png;base64" in html


def test_dokument_ne_sadrzi_kontakt_podatke(qtbot) -> None:
    schedule = PrintSchedule(
        title="Ponedjeljak, 17.08.2026.",
        entries=[_entry()],
        blocks=[_block()],
    )
    text = build_day_document(schedule).toPlainText().lower()

    for forbidden in ("telefon", "phone", "email", "napomena", "@"):
        assert forbidden not in text
