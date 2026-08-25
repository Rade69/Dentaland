"""Status prezentaciona pravila — jedan izvor istine za simbol/boju/naziv.

Dijele ih: status legenda (``main_window.py``), kartica termina
(``WeekView``/``DayView``), detalji termina (``appointment_details.py``) i
tekstualna lista više termina u istoj ćeliji, da simboli nikad ne izgube
sinhronizaciju.

Namjerno OBIČNI Unicode dingbat/geometrijski simboli (ne slikovni emoji
poput 🕐/👤/💜) — slikovni emoji zahtijevaju posebni font boje (Segoe UI
Emoji) koji se u malom QLabel HTML tekstu ne mora učitati, pa su znali
ispasti prazni/nečitljivi. Ovi simboli su i oblikom različiti (ne samo
bojom) — čitljivo i bez oslanjanja na boju.
"""

from __future__ import annotations

from dentaland.services import AppointmentDTO

STATUS_META: dict[str, tuple[str, str, str]] = {
    "confirmed": ("✓", "#149447", "Potvrđen"),
    "waiting": ("◷", "#ff8a00", "Čeka potvrdu"),
    "arrived": ("▲", "#1473e6", "Stigao"),
    "completed": ("★", "#7c3aed", "Završen"),
    "no_show": ("!", "#c2410c", "Nije došao"),
    "cancelled": ("✗", "#ef334f", "Otkazan"),
}
STATUS_ORDER = ["confirmed", "waiting", "arrived", "completed", "no_show", "cancelled"]


def status_key(appt: AppointmentDTO) -> str:
    """Mapira termin na ključ statusa iz ``STATUS_META``."""
    status = getattr(getattr(appt, "status", None), "value", None)
    if status == "NO_SHOW":
        return "no_show"
    if status == "CANCELLED":
        return "cancelled"
    if status == "COMPLETED":
        return "completed"
    if getattr(appt, "arrived_at", None) is not None:
        return "arrived"
    if getattr(appt, "confirmed_at", None) is not None:
        return "confirmed"
    return "waiting"


def status_icon(appt: AppointmentDTO) -> str:
    """Čisto prezentaciono mapiranje statusnih podataka na ikonicu."""
    return STATUS_META[status_key(appt)][0]
