"""Testovi tri semantički različita desna dashboard panela."""

from datetime import date, datetime
from types import SimpleNamespace

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QLabel, QPushButton
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from dentaland.models import Appointment, AppointmentStatus, Base
from dentaland.services import AppointmentService, ensure_seed_data
from desktop.fake_data import SARAJEVO
from desktop.views import requests_panel as rp
from desktop.views.requests_panel import DashboardPanels


class DashboardStore:
    def __init__(self) -> None:
        self.confirmed_ids: list[int] = []
        self.cancelled_ids: list[int] = []
        self._awaiting = [
            SimpleNamespace(
                id=7,
                patient_name="Marko Bošnjak",
                service="Kontrola",
                start=datetime(2026, 8, 18, 11, 30, tzinfo=SARAJEVO),
            )
        ]

    def pending_requests(self):
        return [SimpleNamespace(id=1, ime="Jelena Kovač", requested_date=date(2026, 8, 18))]

    def awaiting_confirmation(self):
        return list(self._awaiting)

    def cancelled_today(self):
        return [
            SimpleNamespace(
                patient_name="Ivana M.",
                service="Pregled",
                start=datetime(2026, 8, 17, 14, 0, tzinfo=SARAJEVO),
            )
        ]

    def mark_confirmed(self, appt_id: int) -> None:
        self.confirmed_ids.append(appt_id)
        self._awaiting = [a for a in self._awaiting if a.id != appt_id]

    def cancel(self, appt_id: int) -> None:
        self.cancelled_ids.append(appt_id)
        self._awaiting = [a for a in self._awaiting if a.id != appt_id]


def _button(box, text: str) -> QPushButton:
    for button in box.findChildren(QPushButton):
        if button.text() == text:
            return button
    raise AssertionError(f"dugme '{text}' nije pronađeno")


def _labels(box) -> str:
    return "\n".join(label.text() for label in box.findChildren(QLabel))


def test_paneli_ne_mijesaju_zahtjeve_i_termine(qtbot) -> None:
    panels = DashboardPanels(DashboardStore())
    qtbot.addWidget(panels)

    assert panels.pending_box.title() == "Novi zahtjevi (1)"
    assert "Jelena Kovač" in _labels(panels.pending_box)
    assert "Kontrola" not in _labels(panels.pending_box)

    assert panels.awaiting_box.title() == "Čekaju potvrdu (1)"
    assert "Marko Bošnjak" in _labels(panels.awaiting_box)
    assert "Kontrola" in _labels(panels.awaiting_box)

    assert panels.cancelled_box.title() == "Otkazani danas (1)"
    assert "Ivana M." in _labels(panels.cancelled_box)
    assert "Pregled" in _labels(panels.cancelled_box)


def test_cekaju_potvrdu_ima_potvrdi_i_odbaci_a_otkazani_nemaju(qtbot) -> None:
    panels = DashboardPanels(DashboardStore())
    qtbot.addWidget(panels)

    assert _button(panels.awaiting_box, "Potvrdi") is not None
    assert _button(panels.awaiting_box, "Odbaci") is not None
    assert not panels.cancelled_box.findChildren(QPushButton)


def test_klik_na_potvrdi_zove_mark_confirmed_i_uklanja_stavku(qtbot) -> None:
    store = DashboardStore()
    panels = DashboardPanels(store)
    qtbot.addWidget(panels)

    qtbot.mouseClick(_button(panels.awaiting_box, "Potvrdi"), Qt.MouseButton.LeftButton)
    qtbot.wait(10)  # dovrši deleteLater() od stare stavke (deferred delete event)

    assert store.confirmed_ids == [7]
    assert panels.awaiting_box.title() == "Čekaju potvrdu (0)"
    assert "Marko Bošnjak" not in _labels(panels.awaiting_box)


def test_klik_na_odbaci_zove_cancel_i_uklanja_stavku(qtbot) -> None:
    store = DashboardStore()
    panels = DashboardPanels(store)
    qtbot.addWidget(panels)

    qtbot.mouseClick(_button(panels.awaiting_box, "Odbaci"), Qt.MouseButton.LeftButton)
    qtbot.wait(10)

    assert store.cancelled_ids == [7]
    assert panels.awaiting_box.title() == "Čekaju potvrdu (0)"
    assert "Marko Bošnjak" not in _labels(panels.awaiting_box)


def test_pending_ima_obradi_ne_potvrdi_odbij(qtbot) -> None:
    panels = DashboardPanels(DashboardStore())
    qtbot.addWidget(panels)

    assert _button(panels.pending_box, "Obradi") is not None
    pending_buttons = [b.text() for b in panels.pending_box.findChildren(QPushButton)]
    assert "Potvrdi" not in pending_buttons
    assert "Odbij" not in pending_buttons


def test_nema_sljedeci_slobodan_termin(qtbot) -> None:
    panels = DashboardPanels(DashboardStore())
    qtbot.addWidget(panels)
    assert not hasattr(panels, "next_free_box")


def test_confirmation_dialog_uklonjen() -> None:
    assert not hasattr(rp, "ConfirmationDialog")


def test_overlap_pri_potvrdi_prikazuje_inline_gresku_i_ne_rusi_zahtjev(
    qtbot, monkeypatch, tmp_path
) -> None:
    engine = create_engine(f"sqlite:///{tmp_path / 'd.db'}")
    Base.metadata.create_all(engine)
    sf = sessionmaker(bind=engine, expire_on_commit=False)
    ensure_seed_data(sf)
    service = AppointmentService(sf, doctor_id=1)  # Ljubo

    # postojeći SCHEDULED termin u 09:00 kod Ljube
    service.create(
        "Postojeći", "", "", "Kontrola", "",
        datetime(2026, 8, 18, 9, 0, tzinfo=SARAJEVO),
        datetime(2026, 8, 18, 9, 30, tzinfo=SARAJEVO),
    )

    # PENDING zahtjev za isti datum
    with sf() as session:
        pending = Appointment(
            ime="Jelena Kovač",
            telefon="061",
            email="j@x.com",
            requested_date=date(2026, 8, 18),
            status=AppointmentStatus.PENDING,
        )
        session.add(pending)
        session.commit()
        pending_id = pending.id

    class FakeDialog:
        instances = []

        def __init__(self, request, doctors, services, parent=None):
            self.errors = []
            self.exec_count = 0
            self.action_count = 0
            FakeDialog.instances.append(self)

        def exec(self):
            self.exec_count += 1
            return QDialog.DialogCode.Accepted

        def selected_action(self):
            self.action_count += 1
            return "confirm" if self.action_count == 1 else "reject"

        def values(self):
            # isto vrijeme/doktor kao postojeći termin -> overlap
            return (1, 1, datetime(2026, 8, 18, 9, 0, tzinfo=SARAJEVO))

        def show_error(self, message):
            self.errors.append(message)

    monkeypatch.setattr(rp, "ProcessRequestDialog", FakeDialog)

    panels = DashboardPanels(service)
    qtbot.addWidget(panels)
    request = SimpleNamespace(
        id=pending_id,
        ime="Jelena Kovač",
        telefon="061",
        email="j@x.com",
        requested_date=date(2026, 8, 18),
    )

    panels._confirm(request)

    assert FakeDialog.instances
    dialog = FakeDialog.instances[0]
    assert dialog.exec_count == 2  # dijalog je ponovo otvoren poslije overlap greške
    assert len(dialog.errors) == 1  # inline greška prikazana

    # drugi pokušaj je "reject" -> zahtjev je odbijen (ne ostaje PENDING bez znaka)
    with sf() as session:
        row = session.get(Appointment, pending_id)
        assert row.status == AppointmentStatus.REJECTED
