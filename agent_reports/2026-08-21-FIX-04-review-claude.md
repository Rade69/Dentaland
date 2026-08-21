---
task_id: FIX-04
reviewer: claude
risk: MEDIUM
verdict: PASS
date: 2026-08-21
---

# Review — FIX-04 (ne gutati ValueError bez feedbacka, MEDIUM)

```yaml
verdict: PASS
scope: PASS
acceptance: PASS
architecture: PASS
blocking_findings: []
```

## Scope — PASS

`git diff --stat`: samo `desktop/views/main_window.py` (+14/-5) i
`tests/test_gui/test_main_window.py` (+88). Unutar `allowed_paths`.
`booking.py` netaknut — servisne poruke se koriste direktno (`str(exc)`),
ne prepisuju.

## Implementacija — PASS, tačno prati kontrakt

Sva tri mjesta (`_handle_appointment_action` method_map dispatch,
`_cancel_appointment`, `_delete_appointment`) zamijenjena identično
predloženom obrascu: `try/except ValueError as exc:
QMessageBox.warning(self, "<naslov>", str(exc))`, sa
`self._refresh_dashboard()` i dalje VAN try/except (izvršava se bez
obzira na ishod — nepromijenjeno ponašanje, provjereno u diff-u na sva
tri mjesta). `suppress`/`contextlib` import uklonjen (bio bi
neiskorišten). `QMessageBox` dodat u postojeći `PySide6.QtWidgets`
import blok.

## Adversarna provjera (nezavisna reprodukcija — posebno pažljivo, s obzirom na FIX-03 presedan lažnih testova)

Pošto je ova sesija već jednom otkrila test koji daje lažan PASS na
buggy kodu (FIX-03, geometrijsko poređenje), posebno sam provjerio da
mockovani `QMessageBox.warning` testovi ovdje stvarno rade:

1. Privremeno vratio `with suppress(ValueError)` na PRVO mjesto
   (method_map dispatch), zadržavajući fix na druga dva (kopija fajla,
   ne `git checkout --`).
2. Pokrenuo `test_status_akcija_na_terminalnom_terminu_prikazuje_poruku`
   → **PADA** (`assert 0 == 1`, `warnings` lista prazna) — test stvarno
   hvata regresiju, nije lažan PASS.
3. Vratio fix iz backup kopije — `git hash-object` potvrđuje bit-za-bit
   identičan sadržaj kao prije (`1a5c02f`).
4. Ponovni pun test suite: **272 passed** (269 baseline + 3 nova).
5. Ciljano pokrenuo i sva 4 postojeća regresiona testa uspješnog puta
   (`test_context_action_confirm_poziva_mark_confirmed`,
   `test_context_action_completed_osvjezava_status_summary`,
   `test_delete_akcija_trajno_uklanja_termin_kroz_pravi_servis`,
   `test_delete_odustani_ne_brise_termin`) zajedno sa tri nova — svih 7
   PASS. Uspješan put nije regresiran.

Nisam ponavljao identičnu provjeru za preostala dva mjesta
(`_cancel_appointment`, `_delete_appointment`) jer su strukturno
identična (isti `try/except`+mock obrazac) i test mehanizam
(monkeypatch na `QMessageBox.warning`, direktna provjera liste poziva)
ne zavisi od Qt layout timinga koji je bio uzrok FIX-03 problema — ovaj
mock pristup je fundamentalno drugačiji i pouzdaniji (direktno presreće
poziv, ne mjeri geometriju).

## Zaključak

Sve iz kontrakta ispunjeno: nijedna od tri akcije više ne guta
`ValueError` u tišini, poruka je čista servisna poruka bez traceback-a,
`_refresh_dashboard()` se i dalje izvršava nakon greške, uspješan put
nepromijenjen. **PASS.** MEDIUM risk — human approval (Radovan)
obavezan prije merge-a.

## Verifikacija (ponovljena nezavisno, na finalnom stanju)

```text
pytest tests/ -q                              → 272 passed, 11 warnings
ruff check src/dentaland desktop backend tests → All checks passed!
mypy src/dentaland desktop backend             → Success: no issues found in 35 source files
```

## Handoff

```text
CILJ: Nijedna appointment akcija u main_window.py ne guta ValueError u
      tišini — korisnik dobija jasnu servisnu poruku, UI ostaje
      stabilan, uspješan put nepromijenjen.
URAĐENO: PASS — sva tri mjesta popravljena identično kontraktu,
      adversarno potvrđeno (test genuinski pada bez fixa na bar jednom
      mjestu, strukturno identičan mehanizam na preostala dva).
NE DIRATI: booking.py, ostali desktop/dialog fajlovi — ništa od toga
      nije dirano.
SLJEDEĆE: commit (2 fajla + 2 agent_report-a) i merge u main, čim
      Radovan da human approval (MEDIUM — obavezan). Zatim FIX-05
      (DayView drag & drop, MEDIUM) ili FIX-06 (vizuelno usklađivanje
      Settings/Blockout, LOW) — posljednja dva u korektivnom paketu.
```
