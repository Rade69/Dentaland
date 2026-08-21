"""Testovi glavnog prozora."""

from __future__ import annotations

from datetime import date, datetime, timedelta

import pytest
from PySide6.QtGui import QPalette
from PySide6.QtWidgets import QApplication, QDialog, QLabel

from desktop.fake_data import SARAJEVO, FakeStore
from desktop.views import main_window as main_window_mod
from desktop.views.main_window import MainWindow


@pytest.fixture()
def window(qtbot, store: FakeStore, week_start: date) -> MainWindow:
    win = MainWindow(store, week_start)
    qtbot.addWidget(win)
    return win


def test_stampaj_dugme_postoji(window: MainWindow) -> None:
    assert window.print_action.text() == "Štampaj raspored"


def test_dashboard_prisiljava_svijetlu_paletu(window: MainWindow) -> None:
    app = QApplication.instance()
    assert app is not None
    palette = app.palette()
    assert palette.color(QPalette.ColorRole.Window).name() == "#ffffff"
    assert palette.color(QPalette.ColorRole.Text).name() == "#10213d"


def test_sidebar_prikazuje_stvarni_dentaland_logo(window: MainWindow) -> None:
    logo = window.sidebar.findChild(QLabel, "sidebarLogo")
    assert logo is not None
    assert logo.pixmap() is not None and not logo.pixmap().isNull()


def test_navigacija_mijenja_sedmicu_i_sidebar_rutu(window: MainWindow) -> None:
    original = window.week_start
    window._move_week(1)
    assert window.week_start == original + timedelta(days=7)
    assert window.week_view.week_start == window.week_start

    window.sidebar.route_selected.emit("pacijenti")
    assert window.page_stack.currentWidget() is window._route_pages["pacijenti"]


def test_novi_zahtjevi_ruta_vodi_na_dedicated_stranicu(window: MainWindow) -> None:
    window.sidebar.route_selected.emit("zahtjevi")

    assert window.page_stack.currentWidget() is window.requests_page
    assert window._route_pages["zahtjevi"] is window.requests_page


def test_datumski_raspon_zavrsava_subotom(window: MainWindow) -> None:
    assert "17 – 22. avgust 2026" in window.range_label.text()


def test_footer_ostaje_vidljiv_na_laptop_visini(
    window: MainWindow,
    qtbot,
) -> None:
    window.resize(1536, 760)
    window.show()
    qtbot.wait(20)

    assert window.status_legend.isVisible()
    assert window.status_legend.height() >= 48
    assert "Otkazan / Nije došao" in window.status_legend.text()
    assert "No-show" not in window.status_legend.text()
    assert window.status_legend.geometry().bottom() <= window.schedule_page.rect().bottom()
    assert window.sidebar.staff.isVisible()
    assert window.sidebar.staff.geometry().bottom() <= window.sidebar.rect().bottom()


def test_auto_refresh_tajmer_je_pokrenut_i_zove_refresh_dashboard(
    window: MainWindow, store: FakeStore
) -> None:
    assert window._auto_refresh_timer.isActive()

    store.create(
        "Novi Pacijent", "", "", "Kontrola", "",
        datetime(2026, 8, 17, 9, 0, tzinfo=SARAJEVO),
        datetime(2026, 8, 17, 9, 30, tzinfo=SARAJEVO),
    )
    window._auto_refresh_timer.timeout.emit()

    assert "Čeka potvrdu (1)" in window.status_legend.text()


def test_footer_prikazuje_brojno_stanje_termina_prikazane_sedmice(
    window: MainWindow, store: FakeStore
) -> None:
    assert "Čeka potvrdu (0)" in window.status_legend.text()

    store.create(
        "Ana", "", "", "Kontrola", "",
        datetime(2026, 8, 17, 9, 0, tzinfo=SARAJEVO),
        datetime(2026, 8, 17, 9, 30, tzinfo=SARAJEVO),
    )
    window._refresh_dashboard()

    assert "Čeka potvrdu (1)" in window.status_legend.text()


def test_nema_po_doktoru_paralelno(window: MainWindow) -> None:
    buttons = [b.text() for b in window.schedule_page.findChildren(main_window_mod.QPushButton)]
    assert "Po doktoru" not in buttons
    assert "Paralelno" not in buttons


def test_dan_dugme_prebacuje_na_day_view(
    qtbot, appointment_service, week_start
) -> None:
    win = MainWindow(appointment_service, week_start)
    qtbot.addWidget(win)

    assert win.day_button.isEnabled()
    win.day_button.click()

    assert win.view_stack.currentWidget() is win.day_view
    assert win.day_button.isChecked()
    assert not win.week_button.isChecked()

    win.week_button.click()
    assert win.view_stack.currentWidget() is win.week_view


def test_dan_pa_danas_prikazuje_danasnji_dan_i_strelica_po_1_dan(
    qtbot, appointment_service, week_start
) -> None:
    win = MainWindow(appointment_service, week_start)
    qtbot.addWidget(win)

    win.day_button.click()
    assert win.view_stack.currentWidget() is win.day_view

    win._go_today()
    assert win.day_view.day == date.today()

    before = win.day_view.day
    win._move_week(1)
    assert win.day_view.day == before + timedelta(days=1)


def test_legenda_doktora_je_poravnata_sa_desnim_panelima(
    qtbot,
    appointment_service,
    week_start,
) -> None:
    window = MainWindow(appointment_service, week_start)
    qtbot.addWidget(window)
    window.resize(1536, 760)
    window.show()
    qtbot.wait(20)

    assert window.doctor_legend.isVisible()
    assert window.doctor_legend.geometry().left() == window.dashboard_panels.geometry().left()
    assert "top: -3px" in window.styleSheet()
    assert "background-color: #ffffff" in window.styleSheet()


def test_tabovi_za_doktore_postoje(qtbot, appointment_service, week_start) -> None:
    win = MainWindow(appointment_service, week_start)
    qtbot.addWidget(win)
    assert win.doctor_tabs is not None
    labels = [win.doctor_tabs.tabText(i) for i in range(win.doctor_tabs.count())]
    assert labels == ["Svi doktori", "Ljubo", "Zorka", "Ana"]


def test_unos_u_svi_doktori_bira_doktora_u_modalu(
    qtbot, appointment_service, week_start, monkeypatch
) -> None:
    class FakeEditor:
        def __init__(
            self,
            doctors,
            service_options,
            start,
            *,
            appointment=None,
            selected_doctor_id=None,
            parent=None,
        ):
            self.doctors = doctors

        def exec(self):
            return QDialog.DialogCode.Accepted

        def get_data(self):
            zorka_id = next(d[0] for d in self.doctors if d[1] == "Zorka")
            return {
                "patient_name": "Ana Anić",
                "phone": "",
                "email": "",
                "doctor_id": zorka_id,
                "service": "Kontrola",
                "note": "",
                "start": datetime(2026, 8, 17, 8, 0, tzinfo=SARAJEVO),
                "duration_min": 30,
            }

        def show_error(self, message):
            pass

    monkeypatch.setattr(main_window_mod, "AppointmentEditorDialog", FakeEditor)

    win = MainWindow(appointment_service, week_start)
    qtbot.addWidget(win)
    assert win._current_doctor_id is None  # podrazumijevano "Svi doktori"

    start = datetime(2026, 8, 17, 8, 0, tzinfo=SARAJEVO)
    win.week_view.slot_selected.emit(start)

    created = appointment_service.all_combined()
    assert len(created) == 1
    assert created[0].doctor_name == "Zorka"


def test_klik_na_slot_otvara_editor_i_dodaje_termin(qtbot, store, week_start, monkeypatch) -> None:
    class FakeEditor:
        def __init__(
            self,
            doctors,
            service_options,
            start,
            *,
            appointment=None,
            selected_doctor_id=None,
            parent=None,
        ):
            self.start = start

        def exec(self):
            return QDialog.DialogCode.Accepted

        def get_data(self):
            return {
                "patient_name": "Ana Anić",
                "phone": "061/123-456",
                "email": "ana@example.com",
                "doctor_id": None,
                "service": "Kontrola",
                "note": "bez napomene",
                "start": self.start,
                "duration_min": 30,
            }

        def show_error(self, message):
            pass

    monkeypatch.setattr(main_window_mod, "AppointmentEditorDialog", FakeEditor)
    win = MainWindow(store, week_start)
    qtbot.addWidget(win)

    start = datetime(2026, 8, 17, 8, 0, tzinfo=SARAJEVO)
    win.week_view.slot_selected.emit(start)

    appts = store.all()
    assert len(appts) == 1
    assert appts[0].patient_name == "Ana Anić"
    assert appts[0].start == start
    assert appts[0].end == start + timedelta(minutes=30)  # trajanje iz editora, ne 60 hardkodovanih
    assert win.week_view.rowSpan(0, 0) == 1
    assert win.week_view.rowCount() == 12


def test_nema_qinputdialog_toka(qtbot, appointment_service, week_start) -> None:
    win = MainWindow(appointment_service, week_start)
    qtbot.addWidget(win)
    assert not hasattr(main_window_mod, "QInputDialog")
    assert not hasattr(win, "_doctor_for_new_appointment")


def test_overlap_greska_se_prikazuje_u_dijalogu_i_ne_zatvara_ga(
    qtbot, appointment_service, week_start, monkeypatch
) -> None:
    appointment_service.create(
        "Postojeći", "", "", "Kontrola", "",
        datetime(2026, 8, 17, 9, 0, tzinfo=SARAJEVO),
        datetime(2026, 8, 17, 9, 30, tzinfo=SARAJEVO),
    )

    class FakeEditor:
        instances = []

        def __init__(
            self,
            doctors,
            service_options,
            start,
            *,
            appointment=None,
            selected_doctor_id=None,
            parent=None,
        ):
            self.errors = []
            self.exec_count = 0
            FakeEditor.instances.append(self)

        def exec(self):
            self.exec_count += 1
            # prvi pokušaj: Accepted (create baca OverlapError), drugi: odustanak
            return (
                QDialog.DialogCode.Accepted
                if self.exec_count == 1
                else QDialog.DialogCode.Rejected
            )

        def get_data(self):
            return {
                "patient_name": "Ana",
                "phone": "",
                "email": "",
                "doctor_id": 1,
                "service": "Kontrola",
                "note": "",
                "start": datetime(2026, 8, 17, 9, 0, tzinfo=SARAJEVO),
                "duration_min": 30,
            }

        def show_error(self, message):
            self.errors.append(message)

    monkeypatch.setattr(main_window_mod, "AppointmentEditorDialog", FakeEditor)
    win = MainWindow(appointment_service, week_start)
    qtbot.addWidget(win)

    win.week_view.slot_selected.emit(datetime(2026, 8, 17, 9, 0, tzinfo=SARAJEVO))

    assert FakeEditor.instances
    editor = FakeEditor.instances[0]
    assert len(editor.errors) == 1  # overlap greška prikazana inline
    assert editor.exec_count == 2  # dijalog je ponovo otvoren, pa korisnik odustao


def test_klik_na_termin_otvara_detalje(
    qtbot, appointment_service, week_start, monkeypatch
) -> None:
    dto = appointment_service.create(
        "Ana", "", "", "Kontrola", "",
        datetime(2026, 8, 17, 9, 0, tzinfo=SARAJEVO),
        datetime(2026, 8, 17, 9, 30, tzinfo=SARAJEVO),
    )

    class FakeDetails:
        instances = []

        def __init__(self, appointment, parent=None):
            self.appointment = appointment
            FakeDetails.instances.append(self)

        def exec(self):
            return QDialog.DialogCode.Rejected

        def selected_action(self):
            return None

    monkeypatch.setattr(main_window_mod, "AppointmentDetailsDialog", FakeDetails)
    win = MainWindow(appointment_service, week_start)
    qtbot.addWidget(win)

    win.week_view.appointment_clicked.emit(dto.id)

    assert len(FakeDetails.instances) == 1
    assert FakeDetails.instances[0].appointment.id == dto.id


def test_context_action_confirm_poziva_mark_confirmed(
    qtbot, appointment_service, week_start
) -> None:
    dto = appointment_service.create(
        "Ana", "", "", "Kontrola", "",
        datetime(2026, 8, 17, 9, 0, tzinfo=SARAJEVO),
        datetime(2026, 8, 17, 9, 30, tzinfo=SARAJEVO),
    )
    win = MainWindow(appointment_service, week_start)
    qtbot.addWidget(win)

    win._handle_appointment_action(dto.id, "confirm")

    assert appointment_service.get(dto.id).confirmed_at is not None


def test_context_action_completed_osvjezava_status_summary(
    qtbot, appointment_service, week_start
) -> None:
    dto = appointment_service.create(
        "Ana", "", "", "Kontrola", "",
        datetime(2026, 8, 17, 9, 0, tzinfo=SARAJEVO),
        datetime(2026, 8, 17, 9, 30, tzinfo=SARAJEVO),
    )
    win = MainWindow(appointment_service, week_start)
    qtbot.addWidget(win)

    win._handle_appointment_action(dto.id, "completed")

    assert "Završen (1)" in win.status_legend.text()


def test_delete_akcija_trajno_uklanja_termin_kroz_pravi_servis(
    qtbot, appointment_service, week_start, monkeypatch
) -> None:
    """Faza F (HIGH) — end-to-end kroz pravi AppointmentService, ne fake."""
    dto = appointment_service.create(
        "Ana", "", "", "Kontrola", "",
        datetime(2026, 8, 17, 9, 0, tzinfo=SARAJEVO),
        datetime(2026, 8, 17, 9, 30, tzinfo=SARAJEVO),
    )
    win = MainWindow(appointment_service, week_start)
    qtbot.addWidget(win)

    class FakeDeleteDialog:
        def __init__(self, appt, parent=None):
            pass

        def exec(self):
            return QDialog.DialogCode.Accepted

    monkeypatch.setattr(main_window_mod, "DeleteAppointmentDialog", FakeDeleteDialog)

    win._handle_appointment_action(dto.id, "delete")

    assert appointment_service.get(dto.id) is None


def test_delete_odustani_ne_brise_termin(
    qtbot, appointment_service, week_start, monkeypatch
) -> None:
    dto = appointment_service.create(
        "Ana", "", "", "Kontrola", "",
        datetime(2026, 8, 17, 9, 0, tzinfo=SARAJEVO),
        datetime(2026, 8, 17, 9, 30, tzinfo=SARAJEVO),
    )
    win = MainWindow(appointment_service, week_start)
    qtbot.addWidget(win)

    class FakeDeleteDialog:
        def __init__(self, appt, parent=None):
            pass

        def exec(self):
            return QDialog.DialogCode.Rejected

    monkeypatch.setattr(main_window_mod, "DeleteAppointmentDialog", FakeDeleteDialog)

    win._handle_appointment_action(dto.id, "delete")

    assert appointment_service.get(dto.id) is not None


def test_doctor_badge_prikazuje_broj_termina_po_doktoru(
    qtbot, appointment_service, week_start
) -> None:
    win = MainWindow(appointment_service, week_start)
    qtbot.addWidget(win)
    doctor_ids = {d.ime: d.id for d in appointment_service.doctors()}
    ljubo_id = doctor_ids["Ljubo"]

    assert win._doctor_badge_labels[ljubo_id].text() == "0"

    appointment_service.set_doctor(ljubo_id)
    appointment_service.create(
        "Ana", "", "", "Kontrola", "",
        datetime(2026, 8, 17, 9, 0, tzinfo=SARAJEVO),
        datetime(2026, 8, 17, 9, 30, tzinfo=SARAJEVO),
    )
    win._refresh_dashboard()

    assert win._doctor_badge_labels[ljubo_id].text() == "1"


def test_doctor_badge_se_azurira_pri_navigaciji(
    qtbot, appointment_service, week_start
) -> None:
    win = MainWindow(appointment_service, week_start)
    qtbot.addWidget(win)
    doctor_ids = {d.ime: d.id for d in appointment_service.doctors()}
    ljubo_id = doctor_ids["Ljubo"]

    appointment_service.set_doctor(ljubo_id)
    appointment_service.create(
        "Ana", "", "", "Kontrola", "",
        datetime(2026, 8, 24, 9, 0, tzinfo=SARAJEVO),
        datetime(2026, 8, 24, 9, 30, tzinfo=SARAJEVO),
    )
    win._refresh_dashboard()
    assert win._doctor_badge_labels[ljubo_id].text() == "0"  # izvan sedmice

    win._move_week(1)
    assert win._doctor_badge_labels[ljubo_id].text() == "1"  # sada u sedmici


def test_doctor_avatar_velicina_je_povecana(
    qtbot, appointment_service, week_start
) -> None:
    win = MainWindow(appointment_service, week_start)
    qtbot.addWidget(win)

    assert main_window_mod.DOCTOR_AVATAR_SIZE >= 48
    avatar = win.doctor_legend.findChild(QLabel, "doctorAvatarLjubo")
    assert avatar is not None
    assert avatar.width() >= 48


def test_doctor_panel_je_sakriven_kad_store_nema_doktore(
    qtbot, store, week_start
) -> None:
    win = MainWindow(store, week_start)  # FakeStore nema doctors
    qtbot.addWidget(win)
    assert win.doctor_legend.isHidden()
