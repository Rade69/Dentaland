# Implementer izveštaj — DENT-015

Task: DENT-015 | Risk: MEDIUM | Implementer: pi | Status: IMPLEMENTED (čeka review)

## Šta je urađeno

`src/dentaland/services/print_schedule.py` (novi fajl, čist servisni sloj, BEZ Qt):

- Tri dataclass-a:
  - `PrintScheduleEntry(time_range, patient_name, doctor_name, service, status_label, day_label)`
  - `PrintScheduleBlock(time_range, doctor_name, label, day_label)`
  - `PrintSchedule(title, entries, blocks)`
  - **Nijedan nema `phone`/`email`/`note` (ni `telefon`/`napomena`) polja u tipu**
    — strukturna minimizacija podataka, isti obrazac kao `backend/notifications.py`
    (DENT-011): curenje na papir/PDF nije ni moguće kroz ovaj kod.
- `build_day_schedule(service, day)` i `build_week_schedule(service, week_start)`:
  - pozivaju postojeće `AppointmentService.all_combined()`, `time_off_for_week()`,
    `breaks_for_week()` — NIŠTA u `booking.py`/`requests.py` nije mijenjano;
  - isključuju `CANCELLED`/`NO_SHOW` (operativni raspored, ne istorijski log);
  - `build_week_schedule` pokriva tačno `WEEK_DAY_COUNT = 6` dana (Pon–Sub),
    konstanta dokumentovana da prati `WeekView.DAY_COUNT` (ne 5 ni 7);
  - blokovi (odsustvo/pauza) se clip-uju na traženi raspon, pa se pojavljuju i u
    dnevnom i u sedmičnom prikazu;
  - `status_label` koristi IDENTIČNE srpske tekstove kao statusna legenda iz
    DENT-009 (`desktop/views/main_window.py`): "Potvrđen" / "Čeka potvrdu" /
    "Stigao" / "Završen" — nema novoizmišljenih formulacija;
  - block label normalizuje "VAN ORDINACIJE"→"Van ordinacije" i
    "PAUZA"→"Pauza" (custom `razlog` ostaje netaknut);
  - entries i blocks sortirani hronološki;
  - vremena se formatiraju u `Europe/Sarajevo` (timezone-aware, `ZoneInfo`),
    ne u UTC.

## Verifikacija

```
pytest tests/test_print_schedule.py -v    → 8 passed
pytest tests/ -q                          → 116 passed
ruff check src/dentaland tests            → All checks passed!
mypy src/dentaland                        → Success: no issues found in 7 source files
```

## Napomene za reviewera (security/scope fokus)

- Minimizacija je na nivou TIPA, ne discipline prikaza — reviewer može provjeriti
  `test_dataclassi_nemaju_privatna_polja_u_tipu` (provjerava odsustvo
  `phone`/`email`/`note`/`telefon`/`napomena` kroz `dataclasses.fields`).
- Usluga i doktor se prikazuju (potvrđena poslovna odluka), kontakt-podaci i
  napomene nikad.
- `test_nema_qt_importa` provjerava da fajl nema PySide6/PyQt importa (GUI sloj
  je DENT-016, Codex — potpuno odvojeni fajlovi, potvrđeno u koordinaciji).
- Nije diran nijedan `forbidden_path` — `git status` pokazuje samo tri nova
  fajla u `allowed_paths` (`print_schedule.py`, `test_print_schedule.py`,
  `agent_reports/...`).

## Dirnuti fajlovi (svi u allowed_paths)

- `src/dentaland/services/print_schedule.py` (nov)
- `tests/test_print_schedule.py` (nov)

## Follow-up (Claude, 18.8.2026) — dodato `day_label` polje

Crush (implementer DENT-016, GUI/rendering sloj) je tokom rada ispravno
primijetio prazninu u dogovorenom interfejsu: sedmični layout za štampu
treba kolone po danu (Pon–Sub), a `PrintScheduleEntry`/`Block` nisu
nosili dan kao strukturirani podatak — samo `time_range` string. Crush
je ispravno NIJE sam dirao `print_schedule.py` (van `allowed_paths`
DENT-016 kontrakta), nego je pitao za odluku.

Dodano `day_label: str` (npr. "Pon", isti skraćeni oblik kao
`WeekView.DAY_NAMES`) na oba tipa — strukturno polje, ne parsiranje iz
`time_range`. Odbačena alternativa: parsirati dan iz `time_range`
stringa (krhko, GUI sloj ne bi trebalo da zna format tog stringa) ili
promijeniti sedmični prikaz u hronološku listu bez kolona (mijenja
prihvaćen dizajn iz DENT-016 kontrakta bez razloga).

Provjereno: `pytest tests/test_print_schedule.py -v` → **9 passed**
(dodat `test_day_label_je_isti_dan_za_sve_entries_u_build_day_schedule`,
proširena dva postojeća testa sa `day_label` asercijama), puni suite →
**117 passed**, ruff i mypy čisti. `day_label` je popunjen i za dnevni
raspored (svi entries/blocks imaju isti dan po definiciji, GUI sloj ga
jednostavno ne koristi za grupisanje u tom slučaju) — dosljedan
interfejs bez posebnih slučajeva po pozivaocu.

## Review

```yaml
verdict: PASS
scope: PASS
acceptance: PASS
architecture: PASS
security: PASS
blocking_findings: []
```

Implementacija (Pi) je solidna — strukturna minimizacija stvarno
osigurana na nivou tipa (ne samo discipline), status tekstovi dosljedni
sa DENT-009 legendom, timezone-aware kroz cijeli fajl, WEEK_DAY_COUNT
eksplicitno dokumentovan da prati `WeekView.DAY_COUNT` umjesto
hardkodovane pretpostavke. `day_label` dopuna (Claude, poslije upita
od Crush-a) zatvara jedini stvaran nedostatak u interfejsu — nezavisno
verifikovano testovima, ne samo tvrdnjom.

## Integration status

READY_FOR_REVIEW → REVIEWED (Claude PASS) — spremno za human approval
i merge. DENT-016 (Crush) sada može nastaviti protiv potpunog
interfejsa.
