"""Rendering dokumenta za štampu rasporeda (DENT-016).

GUI/rendering sloj koji konzumira ``PrintSchedule``/``PrintScheduleEntry``/
``PrintScheduleBlock`` tipove iz ``src/dentaland/services/print_schedule.py``
(DENT-015). Nikad ne dodiruje ``AppointmentDTO`` — telefon/email/napomena
strukturno ne mogu ući u dokument jer ti tipovi nemaju takva polja.
"""

from __future__ import annotations

import base64
import html
from pathlib import Path

from PySide6.QtGui import QPageLayout, QPageSize, QTextDocument
from PySide6.QtPrintSupport import QPrinter, QPrintPreviewDialog
from PySide6.QtWidgets import QWidget

from dentaland.services.print_schedule import PrintSchedule

_LOGO_PATH = Path(__file__).resolve().parents[1] / "web" / "assets" / "logo.png"

# Mora pratiti WeekView.DAY_NAMES (desktop/views/week_view.py) — Pon–Sub.
WEEK_DAYS = ["Pon", "Uto", "Sri", "Čet", "Pet", "Sub"]


def _logo_data_uri() -> str:
    return "data:image/png;base64," + base64.b64encode(_LOGO_PATH.read_bytes()).decode("ascii")


def _escape(value: str) -> str:
    return html.escape(value, quote=True)


def _header_html(title: str) -> str:
    return (
        "<div style='text-align:center'>"
        f"<img src='{_logo_data_uri()}' width='48' height='48'/>"
        f"<h2 style='margin:4px 0'>{_escape(title)}</h2>"
        "</div>"
    )


def build_day_document(schedule: PrintSchedule) -> QTextDocument:
    """Dnevni raspored kao portrait dokument (hronološka tabela)."""
    document = QTextDocument()
    document.setHtml(_day_html(schedule))
    return document


def build_week_document(schedule: PrintSchedule) -> QTextDocument:
    """Sedmični raspored kao landscape dokument (kolone Pon–Sub)."""
    document = QTextDocument()
    document.setHtml(_week_html(schedule))
    return document


def _day_html(schedule: PrintSchedule) -> str:
    parts = [_header_html(schedule.title)]
    parts.append("<table border='1' cellspacing='0' cellpadding='4' width='100%'>")
    parts.append(
        "<tr>"
        "<th>Vrijeme</th><th>Pacijent</th><th>Doktor</th><th>Usluga</th><th>Status</th>"
        "</tr>"
    )
    for entry in schedule.entries:
        parts.append(
            "<tr>"
            f"<td>{_escape(entry.time_range)}</td>"
            f"<td>{_escape(entry.patient_name)}</td>"
            f"<td>{_escape(entry.doctor_name)}</td>"
            f"<td>{_escape(entry.service)}</td>"
            f"<td>{_escape(entry.status_label)}</td>"
            "</tr>"
        )
    for block in schedule.blocks:
        parts.append(
            "<tr>"
            f"<td>{_escape(block.time_range)}</td>"
            f"<td colspan='4' style='background:#eef1f4'>"
            f"{_escape(block.label)} — {_escape(block.doctor_name)}"
            "</td>"
            "</tr>"
        )
    parts.append("</table>")
    return "<html><body>" + "".join(parts) + "</body></html>"


def _week_html(schedule: PrintSchedule) -> str:
    columns: dict[str, list[str]] = {day: [] for day in WEEK_DAYS}
    for entry in schedule.entries:
        if entry.day_label in columns:
            columns[entry.day_label].append(
                "<div style='padding:3px 0'>"
                f"<b>{_escape(entry.time_range)}</b> — {_escape(entry.patient_name)}"
                "<br/>"
                f"<span style='font-size:10pt'>"
                f"{_escape(entry.service)} · {_escape(entry.doctor_name)} · "
                f"{_escape(entry.status_label)}"
                "</span>"
                "</div>"
            )
    for block in schedule.blocks:
        if block.day_label in columns:
            columns[block.day_label].append(
                "<div style='background:#eef1f4; padding:3px 0'>"
                f"{_escape(block.time_range)} — {_escape(block.label)} "
                f"({_escape(block.doctor_name)})"
                "</div>"
            )

    parts = [_header_html(schedule.title)]
    parts.append("<table border='1' cellspacing='0' cellpadding='4' width='100%'>")
    parts.append("<tr>" + "".join(f"<th>{day}</th>" for day in WEEK_DAYS) + "</tr>")
    parts.append(
        "<tr>"
        + "".join(
            f"<td valign='top'>{''.join(columns[day])}</td>" for day in WEEK_DAYS
        )
        + "</tr>"
    )
    parts.append("</table>")
    return "<html><body>" + "".join(parts) + "</body></html>"


def _printer(landscape: bool) -> QPrinter:
    printer = QPrinter(QPrinter.PrinterMode.HighResolution)
    printer.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
    printer.setPageOrientation(
        QPageLayout.Orientation.Landscape
        if landscape
        else QPageLayout.Orientation.Portrait
    )
    return printer


def preview_document(
    parent: QWidget | None,
    document: QTextDocument,
    landscape: bool,
    pdf_path: str | None = None,
) -> None:
    """Prikaži print preview (uvijek prije stvarne štampe/PDF-a).

    Ako je ``pdf_path`` postavljen, printer output je taj PDF fajl — "Print"
    iz preview-a zapisuje PDF umjesto slanja na fizički printer.
    """
    printer = _printer(landscape)
    if pdf_path is not None:
        printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
        printer.setOutputFileName(pdf_path)
    preview = QPrintPreviewDialog(printer, parent)
    preview.paintRequested.connect(document.print_)
    preview.exec()
