"""Controller za blokadu/odsustvo vremena (REF-11).

Čista delegacija (facade) na ``store`` — bez ikakve logike, po uzoru na
``RequestController`` (REF-07). ``BlockoutPanel`` konstruiše sopstvenu
privatnu instancu i delegira mutacijske pozive kroz nju.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any


class BlockoutController:
    """Facade nad store-om za kreiranje i brisanje blokada vremena."""

    def __init__(self, store: Any) -> None:
        self._store = store

    def create_time_off(
        self, doctor_id: int, start: datetime, end: datetime, reason: str | None
    ) -> Any:
        return self._store.create_time_off(doctor_id, start, end, reason)

    def delete_time_off(self, block_id: int) -> None:
        self._store.delete_time_off(block_id)
