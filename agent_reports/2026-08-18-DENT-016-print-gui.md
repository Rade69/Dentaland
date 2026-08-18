---
task_id: DENT-016
risk: MEDIUM
implementer: crush
reviewers: [claude]
verdict: PENDING
commits: []
created_at: 2026-08-18
---

# DENT-016 — Štampa rasporeda (GUI/rendering)

## Šta je urađeno

- `desktop/print_document.py` (novo) — rendering sloj nad `PrintSchedule`
  tipovima (DENT-015): `build_day_document()` (portrait, hronološka tabela),
  `build_week_document()` (landscape, kolone Pon–Sub grupisane po
  `day_label`), logo kao base64 data-URI, HTML-escape svih polja, i
  `preview_document()` (uvijek `QPrintPreviewDialog`; opcioni `pdf_path`).
  Nikad ne dodiruje `AppointmentDTO` — telefon/email/napomena strukturno ne
  mogu ući u dokument.
- `desktop/views/main_window.py::_on_print` — meni sa tri opcije
  ("Štampaj prikazanu sedmicu", "Štampaj jedan dan…", "Sačuvaj kao PDF"),
  date-picker (`QCalendarWidget`) za dan, uvijek preview prije štampe/PDF-a.
- `tests/test_gui/test_print_document.py` (novo) — 6 testova.

## Nalaz razriješen (prije koda)

`PrintScheduleEntry` nije imao polje za dan, pa sedmične kolone Pon–Sub nisu
bile moguće. Radovan je odlučio da DENT-015 doda `day_label` — Pi je to
implementirao i DENT-015 je merge-ovan, pa je ovaj sloj pisan protiv konačnog
interfejsa (normalan import, ne TYPE_CHECKING).

## Verifikacija (stvarni rezultati)

| Komanda | Rezultat |
|---|---|
| `pytest tests/ -q` | 123 passed |
| `ruff check desktop tests` | All checks passed |
| `mypy desktop` | 7 grešaka — sve baseline (appointment_dialog/week_view/main_window), nula novih iz DENT-016 |
| grep kontakt-polja u generisanom dokumentu | prazno (test `test_dokument_ne_sadrzi_kontakt_podatke`) |

## Odbačene opcije

- `QPainter` direktno za rendering — odbačeno: `QTextDocument` + HTML tabela
  je jednostavnije za dvije orijentacije/layoute.
- Direktan `save_pdf` bez preview-a — odbačeno: contract traži "uvijek preview
  prije štampe/PDF-a"; PDF ide kroz `preview_document(pdf_path=...)`.
- `TYPE_CHECKING` import tipova — odbačeno: DENT-015 je merge-ovan, pa se
  tipovi importuju normalno.

## Review

```yaml
verdict: PASS
scope: PASS
acceptance: PASS
architecture: PASS
security: PASS
blocking_findings: []
```

Nezavisno provjereno (ne samo pročitano):

- `pytest tests/ -q` → **126 passed** (123 + 3 nova testa za pola-sata
  klik iz nezavisnog fix-a na `week_view.py`, nepovezano sa DENT-016 —
  nula pada u DENT-016 testovima).
- `ruff check src/dentaland desktop backend tests` → PASS.
- `mypy src/dentaland desktop backend` → **7 grešaka**, isti baseline,
  nula novih iz `print_document.py`/`main_window.py`.
- `grep -n "phone\|email\|note\|telefon\|napomena" desktop/print_document.py`
  → samo u dokumentacionom komentaru koji OBJAŠNJAVA garanciju, ne u
  stvarnom kodu koji bi ta polja mogao pročitati.
- Pregledan kod: `_escape()` (HTML-escape) se dosljedno primjenjuje na
  SVA polja prije umetanja u HTML — sprečava i slučajno curenje kroz
  neplanirano HTML/markup u imenu pacijenta i sl. `preview_document()`
  ispravno prisiljava `QPrintPreviewDialog` za oba puta (štampa i PDF —
  PDF ide kroz isti preview sa printer output-om preusmjerenim na fajl,
  ne zaobilazi pregled). `_week_html()` grupiše po `day_label` iz
  DENT-015 (strukturno polje, ne parsiranje stringa — tačno kako je
  dogovoreno kad je nalaz o nedostajućem polju riješen).
- Scope: `print_schedule.py` (DENT-015) nije diran, samo importovan —
  potvrđeno `git diff --stat` prije merge-a pokazuje samo fajlove iz
  DENT-016 `allowed_paths`.

Manja, ne-blokirajuća napomena: "Sačuvaj kao PDF" uvijek izvozi
PRIKAZANU sedmicu (ne nudi izbor dana za PDF) — razumno tumačenje
kontrakta (tri opcije, PDF nije eksplicitno vezan za dan), ali vrijedi
znati ako se kasnije pokaže potreba za dnevnim PDF izvozom.

## Integration status

MERGED → INTEGRATION_VERIFIED → DONE. Mergovano u `main` (--no-ff),
poslije merge-a pun test suite: 126 passed, ruff čist, mypy baseline
nepromijenjen (7/7).
