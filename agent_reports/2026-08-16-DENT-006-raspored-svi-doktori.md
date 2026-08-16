---
task_id: DENT-006
risk: MEDIUM
implementer: crush
reviewers: [claude]
verdict: PASS_WITH_NOTES
commits: []
created_at: 2026-08-16
---

# DENT-006 — Raspored prikazuje sva tri doktora istovremeno, u boji

## Task Contract

Vidi `agent_reports/DENT-006-task-contract.md`. Plan implementera u
`agent_reports/DENT-006-plan.md`.

## Šta je urađeno

- `src/dentaland/services/booking.py` — `AppointmentDTO` dobija `doctor_id`/
  `doctor_name`; nova `all_combined()` (svi termini, svi doktori); `move()`
  sad koristi doktora IZ SAMOG TERMINA (`appt.doctor_id`) umjesto
  `self.doctor_id` — ispravno, jer drag&drop mora raditi za bilo kojeg
  doktora u kombinovanom prikazu, ne samo za trenutno "aktivnog"; `doctors()`
  sortira po `id` (redoslijed tabova), ne alfabetski.
- `desktop/views/week_view.py` — `_fetch_appointments()` (koristi
  `all_combined` ako postoji, inače `all()` — FakeStore kompatibilnost),
  `_appointments_by_cell()` sad vraća LISTU po ćeliji (više doktora može
  dijeliti isti slot — ranije nemoguće, ispravno prepoznato), boja-kodiranje
  po doktoru, `set_filter(doctor_id|None)`. GUI-side pre-check koji je
  blokirao drop na "zauzet" slot je namjerno uklonjen — sad servisni sloj
  (doktor-specifičan `OverlapError`) je jedini autoritet, što je tačno ono
  što treba kad isti slot legitimno može imati termine više doktora.
- `desktop/views/main_window.py` — `QTabBar` (Svi doktori/Dr Ljubo/Dr Zorka/
  Dr Ana) zamjenjuje `QComboBox`; klik na prazan slot dok je "Svi doktori"
  aktivan traži doktora kroz `QInputDialog` prije otvaranja dijaloga za unos
  — otkazivanje tog izbora ispravno prekida cijeli tok (nema termina bez
  vlasnika).
- Testovi: 2 nova u `test_services.py` (kombinovan dohvat, move preko
  doktora), 4 nova u `test_gui/` (tabovi, traženje doktora, kombinovani
  prikaz, boje, filter).

## Verifikacija (nezavisno ponovo pokrenuto)

| Komanda | Rezultat |
|---|---|
| `pytest tests/ -q` | 51 passed |
| `ruff check src/dentaland desktop tests` | All checks passed |
| `grep -ri sqlalchemy desktop/views/*.py` | prazno (OK) |
| `git diff --stat` na svih 9 `forbidden_paths` | prazno — potvrđeno netaknuto |
| `mypy src/dentaland desktop` | 8 grešaka, isto kao baseline na `main` (vidi napomenu) |

## Review (Claude, 16.8.2026)

```yaml
verdict: PASS_WITH_NOTES
scope: PASS
acceptance: PASS
architecture: PASS
security: PASS
blocking_findings: []
```

Pročitan cio diff (`booking.py`, `week_view.py`, `main_window.py`) i svi
novi/izmijenjeni testovi. Svih sedam acceptance stavki potvrđeno:

- Raspored prikazuje sva tri doktora istovremeno kad je "Svi doktori"
  aktivan, boja po doktoru (testirano da su boje različite i da nisu bijela
  default boja).
- Filter tabovi rade — filtriranje na jednog doktora testirano, uključujući
  da sufiks `[Ime]` ispravno nestaje kad je filter aktivan (samo se
  pojavljuje u kombinovanom prikazu gdje je razlikovanje potrebno).
- Klik na prazan slot dok je "Svi doktori" aktivan traži doktora prije
  kreiranja — testirano, uključujući da otkazivanje ne kreira termin.
- Drag&drop nastavlja da radi, sad ispravno i za termine BILO KOJEG doktora
  (testirano `test_move_radi_za_termin_drugog_doktora` — servis čiji je
  `self.doctor_id` Ljubo uspješno pomjera Zorkin termin, jer overlap-check
  ide preko `appt.doctor_id`, ne preko trenutno "aktivnog" doktora).
- `all_combined()` postoji i testirana je.
- Nula SQLAlchemy importa u `desktop/views/`.
- Postojeći testovi i dalje prolaze (FakeStore kompatibilnost očuvana kroz
  `getattr` provjere na `doctors`/`all_combined`/`doctor_id`/`doctor_name`).

**Posebno dobra odluka, vrijedna isticanja:** uklanjanje GUI-side
pre-provjere "je li ćelija zauzeta" prije drop-a. Stara logika bi
pogrešno blokirala validan drop drugog doktora u slot koji dijeli sa
prvim doktorom — sad servisni sloj (doktor-specifičan `OverlapError`) je
jedini autoritet, što je tačno ispravno za kombinovani prikaz. Ovo nije
bilo eksplicitno traženo u Task Contractu kao "ukloni provjeru", implementer
je sam prepoznao da je stara provjera pogrešna za novi kontekst — dobar
znak nezavisnog razumijevanja problema, ne mehaničko slijeđenje uputstva.

**Mypy napomena (LOW, ne blokira):** baseline na `main` ima 8 grešaka prije
ovog zadatka; DENT-006 ukloni jednu (`QComboBox`-vezanu, pošto je taj
widget zamijenjen tabovima) i uvede jednu novu, sličnog karaktera
(`week_view.py:155` — `getattr` defensive pattern vraća `Any | None` gdje
`dict.get` očekuje `int`, isti stil kao postojeći FakeStore-kompatibilni
kod). Neto bez pogoršanja broja, kvalitativno ista vrsta poznatog duga.

Verdikt: **PASS_WITH_NOTES**. Spremno za human approval.

## Integration status

MERGED → INTEGRATION_VERIFIED → DONE. Mergovano u `main` (commit `9f15a07`, merge commit poslije). Post-merge integration gate: pun test suite (51/51), `ruff check` na cijelom repou — oba prošla. Napomena:
DENT-007 (Claude, paralelno) mijenja `src/dentaland/models.py` da učini
`doctor_id`/`service_id`/`start_time`/`end_time` nullable — kad se OBA
mergiraju, `booking.py` (uključujući izmjene iz ovog zadatka) će trebati
malu popravku tipova (5 mypy grešaka, već najavljeno u DENT-007 evidence
fajlu) jer mypy ne može statički znati da su ta polja uvijek popunjena za
SCHEDULED termine. Nije blokirajuće za merge ovog zadatka, ali treba
riješiti kao brz follow-up poslije oba merge-a.
