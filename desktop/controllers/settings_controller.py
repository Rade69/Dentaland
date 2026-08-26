"""Controller za postavke (REF-12).

Čista delegacija (facade) na ``store`` — bez ikakve logike, isti obrazac kao
``BlockoutController`` (REF-11). ``SettingsPanel`` konstruiše sopstvenu
privatnu instancu i delegira mutacijske pozive kroz nju.
"""

from __future__ import annotations

from datetime import time
from typing import Any


class SettingsController:
    """Facade nad store-om za postavke doktora/usluga/radnog vremena."""

    def __init__(self, store: Any) -> None:
        self._store = store

    def set_doctor_active(self, doctor_id: int, active: bool) -> Any:
        return self._store.set_doctor_active(doctor_id, active)

    def add_service(self, naziv: str, trajanje_min: int, buffer_min: int) -> Any:
        return self._store.add_service(naziv, trajanje_min, buffer_min)

    def update_service(
        self, service_id: int, naziv: str, trajanje_min: int, buffer_min: int
    ) -> Any:
        return self._store.update_service(service_id, naziv, trajanje_min, buffer_min)

    def set_working_hours(
        self, doctor_id: int, dan: int, intervals: list[tuple[time, time]]
    ) -> None:
        self._store.set_working_hours(doctor_id, dan, intervals)
