"""REF-02 — range-based scheduling reads + eager loading."""

from __future__ import annotations

from datetime import UTC, date, datetime, time, timedelta

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from dentaland.models import (
    Appointment,
    AppointmentStatus,
    Base,
    Doctor,
    Service,
    TimeOff,
    WorkingHours,
)
from dentaland.services import AppointmentService


@pytest.fixture()
def engine() -> Engine:
    eng = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(eng, "connect")
    def _enable_foreign_keys(dbapi_connection, connection_record) -> None:  # noqa: ANN001
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(eng)
    yield eng
    eng.dispose()


@pytest.fixture()
def session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, expire_on_commit=False)


def _seed(sf: sessionmaker[Session]) -> tuple[int, int, int]:
    with sf() as session:
        d1 = Doctor(ime="Ljubo")
        d2 = Doctor(ime="Zorka")
        svc = Service(naziv="Kontrola", trajanje_min=30, buffer_min=0)
        session.add_all([d1, d2, svc])
        session.commit()
        return d1.id, d2.id, svc.id


def _add_appt(
    sf: sessionmaker[Session],
    doctor_id: int,
    service_id: int,
    start: datetime,
    end: datetime,
    status: AppointmentStatus = AppointmentStatus.SCHEDULED,
) -> None:
    with sf() as session:
        session.add(
            Appointment(
                doctor_id=doctor_id,
                service_id=service_id,
                ime="Pacijent",
                start_time=start,
                end_time=end,
                status=status,
            )
        )
        session.commit()


def _at(day: int, hour: int, minute: int = 0) -> datetime:
    return datetime(2026, 8, day, hour, minute, tzinfo=UTC)


def test_range_vraca_samo_termine_u_periodu(session_factory: sessionmaker[Session]) -> None:
    sf = session_factory
    d1, _d2, svc = _seed(sf)
    _add_appt(sf, d1, svc, _at(17, 8), _at(17, 8, 30))   # ponedjeljak
    _add_appt(sf, d1, svc, _at(18, 9), _at(18, 9, 30))   # utorak
    _add_appt(sf, d1, svc, _at(19, 10), _at(19, 10, 30))  # srijeda

    svc_obj = AppointmentService(sf)
    day = svc_obj.appointments_for_range(_at(17, 0), _at(18, 0))

    assert [a.start for a in day] == [_at(17, 8)]


def test_range_termin_preko_ponoci_se_vraca_u_oba_dana(
    session_factory: sessionmaker[Session],
) -> None:
    sf = session_factory
    d1, _d2, svc = _seed(sf)
    # 17.8. 23:00 -> 18.8. 01:00 (preko ponoći).
    _add_appt(sf, d1, svc, _at(17, 23), _at(18, 1))

    svc_obj = AppointmentService(sf)
    day17 = svc_obj.appointments_for_range(_at(17, 0), _at(18, 0))
    day18 = svc_obj.appointments_for_range(_at(18, 0), _at(19, 0))

    assert len(day17) == 1  # end 01:00 > 17.8. 00:00, start 23:00 < 18.8. 00:00
    assert len(day18) == 1  # start 23:00 < 19.8. 00:00, end 01:00 > 18.8. 00:00


def test_range_termin_preko_kraja_sedmice(session_factory: sessionmaker[Session]) -> None:
    sf = session_factory
    d1, _d2, svc = _seed(sf)
    week_start = _at(17, 0)  # ponedjeljak 17.8.
    week_end = _at(23, 0)    # nedjelja 23.8. (DAY_COUNT=6: Pon–Sub)

    # Subota 22.8. 23:00 -> nedjelja 23.8. 01:00 — premošćuje kraj prikaza.
    _add_appt(sf, d1, svc, _at(22, 23), _at(23, 1))
    # Nedjelja 23.8. 01:30 — počinje poslije kraja sedmice, ne pripada.
    _add_appt(sf, d1, svc, _at(23, 1, 30), _at(23, 2))

    svc_obj = AppointmentService(sf)
    week = svc_obj.appointments_for_range(week_start, week_end)

    assert len(week) == 1
    assert week[0].start == _at(22, 23)


def test_range_doctor_filter(session_factory: sessionmaker[Session]) -> None:
    sf = session_factory
    d1, d2, svc = _seed(sf)
    _add_appt(sf, d1, svc, _at(17, 8), _at(17, 8, 30))
    _add_appt(sf, d2, svc, _at(17, 9), _at(17, 9, 30))

    svc_obj = AppointmentService(sf)
    only_d1 = svc_obj.appointments_for_range(_at(17, 0), _at(18, 0), doctor_id=d1)
    all_docs = svc_obj.appointments_for_range(_at(17, 0), _at(18, 0))

    assert [a.doctor_id for a in only_d1] == [d1]
    assert {a.doctor_id for a in all_docs} == {d1, d2}


def test_range_iskljucuje_pending_i_rejected(session_factory: sessionmaker[Session]) -> None:
    sf = session_factory
    d1, _d2, svc = _seed(sf)
    _add_appt(sf, d1, svc, _at(17, 8), _at(17, 8, 30))
    _add_appt(sf, d1, svc, _at(17, 9), _at(17, 9, 30), status=AppointmentStatus.REJECTED)

    svc_obj = AppointmentService(sf)
    result = svc_obj.appointments_for_range(_at(17, 0), _at(18, 0))

    assert [a.start for a in result] == [_at(17, 8)]


def test_range_eager_load_konstantan_broj_upita(
    session_factory: sessionmaker[Session], engine: Engine
) -> None:
    sf = session_factory
    with sf() as session:
        docs = [Doctor(ime=f"D{i}") for i in range(4)]
        svcs = [Service(naziv=f"S{i}", trajanje_min=30, buffer_min=0) for i in range(6)]
        session.add_all(docs + svcs)
        session.commit()
        doc_ids = [d.id for d in docs]
        svc_ids = [s.id for s in svcs]
        base = _at(17, 8)
        for i in range(12):
            start = base + timedelta(minutes=30 * i)
            session.add(
                Appointment(
                    doctor_id=doc_ids[i % len(doc_ids)],
                    service_id=svc_ids[i % len(svc_ids)],
                    ime="Pacijent",
                    start_time=start,
                    end_time=start + timedelta(minutes=30),
                    status=AppointmentStatus.SCHEDULED,
                )
            )
        session.commit()

    query_count = 0

    def _count(dbapi_connection, cursor, statement, parameters, context, executemany) -> None:  # noqa: ANN001
        nonlocal query_count
        query_count += 1

    event.listen(engine, "before_cursor_execute", _count)
    try:
        svc_obj = AppointmentService(sf)
        result = svc_obj.appointments_for_range(base, base + timedelta(days=1))
    finally:
        event.remove(engine, "before_cursor_execute", _count)

    assert len(result) == 12
    # Lazy (bez selectinload) = 1 + 4 doktora + 6 servisa = 11 upita;
    # eager load = 1 glavni + 2 selectinload = 3. Prag <=5 razlikuje ta dva.
    assert query_count <= 5, f"očekivano <=5 upita, dobijeno {query_count}"


def test_awaiting_confirmation_nema_n1_upit(
    engine: Engine, session_factory: sessionmaker[Session]
) -> None:
    """DENT-IMPROVE-021 nalaz (31.8.2026, otkriveno testiranjem preko
    stvarne mreže — VPS preko SSH tunela): ``awaiting_confirmation`` nije
    imao ``selectinload`` (za razliku od ``appointments_for_range``),
    pa je ``_to_dto``/``_service_name`` lazy-loadovao doctor/service
    PO TERMINU — nezamjetno lokalno (SQLite), stvarno sporo preko mreže."""
    sf = session_factory
    with sf() as session:
        docs = [Doctor(ime=f"D{i}") for i in range(4)]
        svcs = [Service(naziv=f"S{i}", trajanje_min=30, buffer_min=0) for i in range(6)]
        session.add_all(docs + svcs)
        session.commit()
        doc_ids = [d.id for d in docs]
        svc_ids = [s.id for s in svcs]
        base = _at(17, 8)
        for i in range(12):
            start = base + timedelta(minutes=30 * i)
            session.add(
                Appointment(
                    doctor_id=doc_ids[i % len(doc_ids)],
                    service_id=svc_ids[i % len(svc_ids)],
                    ime="Pacijent",
                    start_time=start,
                    end_time=start + timedelta(minutes=30),
                    status=AppointmentStatus.SCHEDULED,
                    confirmed_at=None,
                )
            )
        session.commit()

    query_count = 0

    def _count(dbapi_connection, cursor, statement, parameters, context, executemany) -> None:  # noqa: ANN001
        nonlocal query_count
        query_count += 1

    event.listen(engine, "before_cursor_execute", _count)
    try:
        svc_obj = AppointmentService(sf)
        result = svc_obj.awaiting_confirmation()
    finally:
        event.remove(engine, "before_cursor_execute", _count)

    assert len(result) == 12
    assert query_count <= 5, f"očekivano <=5 upita, dobijeno {query_count}"


def test_cancelled_today_nema_n1_upit(
    engine: Engine, session_factory: sessionmaker[Session]
) -> None:
    """Isti nalaz kao ``test_awaiting_confirmation_nema_n1_upit`` —
    ``cancelled_today`` je imao identičan propust."""
    sf = session_factory
    today = datetime.now(UTC).date()
    with sf() as session:
        docs = [Doctor(ime=f"D{i}") for i in range(4)]
        svcs = [Service(naziv=f"S{i}", trajanje_min=30, buffer_min=0) for i in range(6)]
        session.add_all(docs + svcs)
        session.commit()
        doc_ids = [d.id for d in docs]
        svc_ids = [s.id for s in svcs]
        base = datetime(today.year, today.month, today.day, 8, tzinfo=UTC)
        for i in range(12):
            start = base + timedelta(minutes=30 * i)
            session.add(
                Appointment(
                    doctor_id=doc_ids[i % len(doc_ids)],
                    service_id=svc_ids[i % len(svc_ids)],
                    ime="Pacijent",
                    start_time=start,
                    end_time=start + timedelta(minutes=30),
                    status=AppointmentStatus.CANCELLED,
                )
            )
        session.commit()

    query_count = 0

    def _count(dbapi_connection, cursor, statement, parameters, context, executemany) -> None:  # noqa: ANN001
        nonlocal query_count
        query_count += 1

    event.listen(engine, "before_cursor_execute", _count)
    try:
        svc_obj = AppointmentService(sf)
        result = svc_obj.cancelled_today(today)
    finally:
        event.remove(engine, "before_cursor_execute", _count)

    assert len(result) == 12
    assert query_count <= 5, f"očekivano <=5 upita, dobijeno {query_count}"


def test_breaks_for_week_nema_n1_upit(
    engine: Engine, session_factory: sessionmaker[Session]
) -> None:
    """N+1 nalaz (31.8.2026, otkriveno testiranjem preko stvarne mreže —
    VPS preko SSH tunela): ``breaks_for_week`` je pravio POSEBAN
    ``WorkingHours`` upit PO aktivnom doktoru unutar petlje — 4 doktora =
    5 upita (1 doctors + 4 working_hours). Ova funkcija se zove na SVAKI
    refresh rasporeda (doktor tab, dan/sedmica toggle, auto-refresh
    tajmer), pa je bila direktan uzrok primjetnog kašnjenja preko mreže."""
    sf = session_factory
    week_start = date(2026, 8, 17)
    with sf() as session:
        docs = [Doctor(ime=f"D{i}") for i in range(4)]
        session.add_all(docs)
        session.commit()
        for doctor in docs:
            # Split-shift (dva perioda istog dana) pravi "PAUZU" bloka
            # između njih — ono što `breaks_for_week` stvarno računa.
            session.add_all(
                [
                    WorkingHours(
                        doctor_id=doctor.id,
                        dan_u_sedmici=1,
                        od_local=time(8, 0),
                        do_local=time(12, 0),
                        timezone="Europe/Sarajevo",
                    ),
                    WorkingHours(
                        doctor_id=doctor.id,
                        dan_u_sedmici=1,
                        od_local=time(13, 0),
                        do_local=time(17, 0),
                        timezone="Europe/Sarajevo",
                    ),
                ]
            )
        session.commit()

    query_count = 0

    def _count(dbapi_connection, cursor, statement, parameters, context, executemany) -> None:  # noqa: ANN001
        nonlocal query_count
        query_count += 1

    event.listen(engine, "before_cursor_execute", _count)
    try:
        svc_obj = AppointmentService(sf)
        result = svc_obj.breaks_for_week(week_start)
    finally:
        event.remove(engine, "before_cursor_execute", _count)

    assert len(result) == 4  # jedna PAUZA po doktoru (12:00-13:00)
    # Lazy (bez IN batch) = 1 doctors + 4 working_hours = 5 upita;
    # batch = 1 doctors + 1 working_hours = 2. Prag <=3 razlikuje ta dva.
    assert query_count <= 3, f"očekivano <=3 upita, dobijeno {query_count}"


def test_range_start_na_granici_kraja_se_ne_ukljucuje(
    session_factory: sessionmaker[Session],
) -> None:
    sf = session_factory
    d1, _d2, svc = _seed(sf)
    # start_time == range_end — dodiruje kraj half-open intervala, ne uključuje se.
    _add_appt(sf, d1, svc, _at(18, 0), _at(18, 0, 30))

    svc_obj = AppointmentService(sf)
    result = svc_obj.appointments_for_range(_at(17, 0), _at(18, 0))

    assert result == []


def test_range_end_na_granici_pocetka_se_ne_ukljucuje(
    session_factory: sessionmaker[Session],
) -> None:
    sf = session_factory
    d1, _d2, svc = _seed(sf)
    # end_time == range_start — dodiruje početak half-open intervala, ne uključuje se.
    _add_appt(sf, d1, svc, _at(16, 16, 30), _at(17, 0))

    svc_obj = AppointmentService(sf)
    result = svc_obj.appointments_for_range(_at(17, 0), _at(18, 0))

    assert result == []


def test_schedule_snapshot_koristi_jednu_transakciju(
    engine: Engine, session_factory: sessionmaker[Session]
) -> None:
    """DENT-IMPROVE-022: tri odvojena store poziva su ranije otvarala 3
    BEGIN/ROLLBACK para; ``schedule_snapshot`` otvara tačno jedan."""
    sf = session_factory
    d1, _d2, svc = _seed(sf)
    _add_appt(sf, d1, svc, _at(17, 8), _at(17, 8, 30))

    begins = 0
    rollbacks = 0

    def _begin(conn) -> None:  # noqa: ANN001
        nonlocal begins
        begins += 1

    def _rollback(conn) -> None:  # noqa: ANN001
        nonlocal rollbacks
        rollbacks += 1

    event.listen(engine, "begin", _begin)
    event.listen(engine, "rollback", _rollback)
    try:
        svc_obj = AppointmentService(sf)
        svc_obj.schedule_snapshot(_at(17, 0), _at(18, 0), date(2026, 8, 17))
    finally:
        event.remove(engine, "begin", _begin)
        event.remove(engine, "rollback", _rollback)

    assert begins == 1, f"očekivano 1 BEGIN, dobijeno {begins}"
    assert rollbacks == 1, f"očekivano 1 ROLLBACK, dobijeno {rollbacks}"


def test_schedule_snapshot_rezultat_identican_odvojenim_pozivima(
    session_factory: sessionmaker[Session],
) -> None:
    sf = session_factory
    d1, d2, svc = _seed(sf)
    _add_appt(sf, d1, svc, _at(17, 8), _at(17, 8, 30))
    _add_appt(sf, d2, svc, _at(17, 9), _at(17, 9, 30))
    with sf() as session:
        session.add(
            TimeOff(
                doctor_id=d2,
                od_datetime=_at(17, 12),
                do_datetime=_at(17, 13),
                razlog="Odsustvo",
            )
        )
        session.commit()

    svc_obj = AppointmentService(sf)
    week_start = date(2026, 8, 17)
    range_start = _at(17, 0)
    range_end = _at(18, 0)

    appts, blocks = svc_obj.schedule_snapshot(range_start, range_end, week_start)

    expected_appts = svc_obj.appointments_for_range(range_start, range_end)
    expected_blocks = svc_obj.time_off_for_week(week_start) + svc_obj.breaks_for_week(
        week_start
    )

    assert appts == expected_appts
    assert blocks == expected_blocks


def test_schedule_snapshot_doctor_filter_samo_appointments(
    session_factory: sessionmaker[Session],
) -> None:
    """``doctor_id`` filtrira SAMO termine, ne kalendarske blokove."""
    sf = session_factory
    d1, d2, svc = _seed(sf)
    _add_appt(sf, d1, svc, _at(17, 8), _at(17, 8, 30))
    with sf() as session:
        session.add(
            TimeOff(
                doctor_id=d2,
                od_datetime=_at(17, 12),
                do_datetime=_at(17, 13),
                razlog="Odsustvo",
            )
        )
        session.commit()

    svc_obj = AppointmentService(sf)
    appts, blocks = svc_obj.schedule_snapshot(
        _at(17, 0), _at(18, 0), date(2026, 8, 17), doctor_id=d1
    )

    assert [a.doctor_id for a in appts] == [d1]
    assert {b.doctor_id for b in blocks} == {d2}
