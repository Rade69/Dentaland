"""REF-00 — javni API contract servisnog sloja (za REF-03 i GUI kompatibilnost).

Zaključava SAMO javne simbole (bez vodećeg underscore-a) koje refaktor mora
očuvati: imena metoda ``AppointmentService``, polja DTO-ova, re-eksport iz
``dentaland.services`` i vrijednosti ``AppointmentStatus``. Privatne metode i
interne strukture NISU ovdje — to su implementacijski detalji, ne contract.
"""

from __future__ import annotations

from dataclasses import fields

from dentaland import services
from dentaland.models import AppointmentStatus
from dentaland.services import AppointmentService
from dentaland.services.booking import (
    AppointmentDTO,
    CalendarBlockDTO,
    DoctorDTO,
    ServiceOptionDTO,
    TimeOffDTO,
    WorkingHoursDTO,
)

PUBLIC_SERVICE_METHODS = {
    "from_sqlite",
    "set_doctor",
    "doctors",
    "services",
    "create",
    "update",
    "get",
    "all",
    "all_combined",
    "mark_arrived",
    "unmark_arrived",
    "mark_confirmed",
    "cancel",
    "delete",
    "mark_completed",
    "mark_no_show",
    "awaiting_confirmation",
    "cancelled_today",
    "pending_requests",
    "confirm_pending",
    "reject_pending",
    "service_choices",
    "service_options",
    "time_off_for_week",
    "breaks_for_week",
    "create_time_off",
    "list_time_off",
    "delete_time_off",
    "move",
    "list_doctors",
    "set_doctor_active",
    "add_service",
    "update_service",
    "list_working_hours",
    "set_working_hours",
}


def test_javne_metode_appointment_service() -> None:
    missing = [m for m in PUBLIC_SERVICE_METHODS if not hasattr(AppointmentService, m)]
    assert not missing, f"nedostaju javne metode AppointmentService: {missing}"


def test_appointment_dto_polja() -> None:
    assert {f.name for f in fields(AppointmentDTO)} == {
        "id",
        "patient_name",
        "phone",
        "email",
        "service",
        "note",
        "start",
        "end",
        "doctor_id",
        "doctor_name",
        "status",
        "confirmed_at",
        "arrived_at",
    }


def test_doctor_dto_polja() -> None:
    assert {f.name for f in fields(DoctorDTO)} == {"id", "ime", "aktivan"}


def test_service_option_dto_polja() -> None:
    assert {f.name for f in fields(ServiceOptionDTO)} == {
        "id",
        "naziv",
        "trajanje_min",
        "buffer_min",
    }


def test_calendar_block_dto_polja() -> None:
    assert {f.name for f in fields(CalendarBlockDTO)} == {
        "start",
        "end",
        "doctor_id",
        "label",
    }


def test_time_off_dto_polja() -> None:
    assert {f.name for f in fields(TimeOffDTO)} == {
        "id",
        "doctor_id",
        "doctor_name",
        "start",
        "end",
        "reason",
    }


def test_working_hours_dto_polja() -> None:
    assert {f.name for f in fields(WorkingHoursDTO)} == {
        "dan_u_sedmici",
        "od_local",
        "do_local",
    }


def test_services_reexport_sadrzi_stabilne_simbole() -> None:
    assert set(services.__all__) == {
        "AppointmentDTO",
        "AppointmentService",
        "DoctorDTO",
        "OverlapError",
        "ServiceOptionDTO",
        "WorkingHoursDTO",
        "ensure_seed_data",
    }


def test_appointment_status_vrijednosti() -> None:
    assert {s.value for s in AppointmentStatus} == {
        "SCHEDULED",
        "CANCELLED",
        "COMPLETED",
        "NO_SHOW",
        "PENDING",
        "REJECTED",
    }
