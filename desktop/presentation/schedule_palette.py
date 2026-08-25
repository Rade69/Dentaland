"""Paleta boja kartica termina po doktoru — jedan izvor istine.

Koriste je ``WeekView`` i ``DayView`` za background/border/text boju
kartice termina, indeksirano po rednom broju doktora (modulo dužina
palete).
"""

from __future__ import annotations

DOCTOR_CARD_PALETTE: list[tuple[str, str, str]] = [
    ("#ebf8ed", "#9bd5a4", "#174d26"),
    ("#fff0f2", "#ff9aaa", "#6b1e2c"),
    ("#edf4ff", "#8ab7ff", "#153b73"),
    ("#fff8df", "#e8cb67", "#634c00"),
    ("#f5efff", "#b9a0ef", "#49307d"),
    ("#e9fbff", "#88d9e8", "#15505d"),
]
