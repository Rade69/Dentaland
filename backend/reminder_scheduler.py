"""In-process scheduler za email podsjetnike na termine (DENT-020)."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable

from sqlalchemy.orm import Session

from dentaland.services.notifications import REMINDER_WINDOW, send_due_appointment_reminders

logger = logging.getLogger(__name__)

POLL_INTERVAL_SECONDS = REMINDER_WINDOW.total_seconds()

SessionFactory = Callable[[], Session]


async def run_reminder_scheduler(
    session_factory: SessionFactory,
    *,
    poll_interval_seconds: float = POLL_INTERVAL_SECONDS,
) -> None:
    """Periodično pokreni reminder job dok FastAPI aplikacija radi."""
    while True:
        try:
            sent = send_due_appointment_reminders(session_factory)
            logger.info("Reminder scheduler obradio %d termina.", sent)
        except asyncio.CancelledError:
            raise
        except Exception:
            # Scheduler je best-effort kao i notification servis: jedan DB/SMTP
            # problem ne smije ugasiti backend niti buduće prolaze joba.
            logger.exception("Reminder scheduler prolaz nije uspio.")
        await asyncio.sleep(poll_interval_seconds)
