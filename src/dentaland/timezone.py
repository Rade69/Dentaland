"""Jedini izvor istine za timezone lokalne klinike.

Sve vrijeme u aplikaciji je timezone-aware (``zoneinfo``), nikad naivni
``datetime``. ``SARAJEVO`` je IANA zona (``Europe/Sarajevo``), ne fiksni UTC
offset — DST bi inače pomjerio rekurentne termine dva puta godišnje.
"""

from __future__ import annotations

from zoneinfo import ZoneInfo

SARAJEVO = ZoneInfo("Europe/Sarajevo")
