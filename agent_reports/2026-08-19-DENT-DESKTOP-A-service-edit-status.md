# Implementer izveštaj — DENT-DESKTOP-A (Faza A)

Task: DENT-DESKTOP-A | Risk: MEDIUM | Implementer: pi | Status: REVIEWED (čeka human approval)

## Cilj faze

Servisni temelj za edit i statuse (prva od 6 faza redizajna desktop schedulera).
Bez diranja GUI (`desktop/`) ili šeme (`models.py`/`migrations/`).

## Izmijenjeni fajlovi

- `src/dentaland/services/booking.py` (mod)
- `src/dentaland/services/__init__.py` (mod — export `ServiceOptionDTO`)
- `tests/test_services.py` (mod — 16 novih testova)

## Šta je implementirano

- **`ServiceOptionDTO`** — stabilan read-model usluge (`id`, `naziv`, `trajanje_min`, `buffer_min`).
- **`AppointmentService.update(appt_id, *, patient_name, phone, email, doctor_id, service, note, start, end)`**:
  - mijenja sva polja i vraća `AppointmentDTO`;
  - overlap provjera za novog doktora kroz **postojeći** `_check_overlap(..., exclude_id=appt_id)`
    (termin pri editovanju ne kolidira sam sa sobom);
  - jedna transakcija — overlap provjera je PRIJE postavljanja polja, nema djelimičnog upisa;
  - dozvoljeno samo za `SCHEDULED`; terminalni (`CANCELLED`/`COMPLETED`/`NO_SHOW`) i
    nepostojeći termin bacaju jasan `ValueError`.
- **`mark_completed(appt_id)`** — `SCHEDULED → COMPLETED`, inače `ValueError`.
- **`mark_no_show(appt_id)`** — `SCHEDULED → NO_SHOW`, inače `ValueError`.
- **`service_options()`** — `list[ServiceOptionDTO]` sa trajanjem i bufferom iz baze
  (trajanje se ne hardkoduje).

## Šta namjerno NIJE implementirano

- Nema generičkog `set_status(...)` — samo uske, eksplicitne metode.
- Nema restore/reopen iz terminalnih stanja.
- Nema hard delete-a (Faza F, HIGH, zaseban task).
- `service_choices()` i `services()` ostaju netaknuti — `desktop/views/requests_panel.py`
  ih koristi, pa je trajanje izloženo kroz NOVU metodu `service_options()` (nula desktop izmjena).
- `confirm_request` u `requests.py` nije diran (nije u `allowed_paths`).

## Verifikacija

```
pytest tests/test_services.py -v   → 40 passed
pytest tests/ -q                   → 164 passed
ruff check src/dentaland tests     → All checks passed!
mypy src/dentaland                 → Success: no issues found in 8 source files
```

## Scope potvrda

`git status` pokazuje izmjene SAMO u `allowed_paths` (`booking.py`, `__init__.py`,
`test_services.py`). Nijedan `forbidden_path` nije diran (desktop/, models.py,
migrations/, backend/, web/, CLAUDE.md, docs/).

## Procesna napomena (transparentnost)

Task Contract (`agent_reports/DENT-DESKTOP-A-task-contract.md`) je već postojao u
`main`-u prije početka rada. Implementer ga je na početku slučajno prepisao
sopstvenom verzijom, zatim uočio grešku i **vratio original** (`git restore`) —
rad se od tada vodio isključivo po originalnom ugovoru, uključujući acceptance
stavku "update nad terminalnim terminom baca ValueError" koja je naknadno
dodata i pokrivena testom `test_update_odbija_terminalni_termin`.

## Review (Claude, Reviewer 1)

```yaml
verdict: PASS
scope: PASS
acceptance: PASS
architecture: PASS
security: PASS
blocking_findings: []
```

Nezavisno provjereno (ne samo preuzeto iz izvještaja):

- `pytest tests/ -q` → 164 passed (pokrenuto direktno u worktree-u).
- `ruff check src/dentaland tests` → All checks passed.
- `mypy src/dentaland` → Success, no issues.
- `git diff` pregledan red-po-red za sva tri fajla — izmjene su tačno ono što je opisano, ništa van `allowed_paths`.

Provjereno prema acceptance listi iz Task Contracta:

- `update()` mijenja sva navedena polja, koristi POSTOJEĆI `_check_overlap(..., exclude_id=appt_id)` (nije napravljen paralelni/novi helper — tačno kako je traženo), overlap provjera ide prije mutacije polja (jedna transakcija, nema djelimičnog upisa ako padne).
- `mark_completed`/`mark_no_show` slijede identičan obrazac kao postojeći `mark_arrived`/`cancel` — uska, eksplicitna metoda, nema generičkog `set_status`.
- Terminalna stanja (`CANCELLED`/`COMPLETED`/`NO_SHOW`) su read-only — `update`, `mark_completed`, `mark_no_show` svi bacaju `ValueError` na terminalnom terminu (test pokriva svaki slučaj, uključujući unakrsni: `mark_no_show` odbijen nad već-`COMPLETED` terminom).
- `service_options()` vraća `trajanje_min`/`buffer_min` iz baze, ne hardkodovano.
- Postojeći `service_choices()`/`services()` netaknuti (desktop GUI koji ih koristi ostaje kompatibilan) — dobra odluka da se ne mijenja postojeći potpis nego doda nova metoda.
- Nula izmjena u `desktop/`, `models.py`, `migrations/`.

Sitna, neblokirajuća napomena: `update()` zahtijeva `doctor_id` da postoji (`session.get(Doctor, doctor_id)` provjera) prije overlap provjere — nije bilo eksplicitno traženo u acceptance listi, ali je razumna odbrambena provjera koja sprečava FK grešku kasnije niz tok; ne smatram to scope creep-om jer je nužan preduslov da `_check_overlap`/mutacija uopšte imaju smisla.

Transparentnost implementera (Task Contract prepisan pa vraćen originalu, i naknadno dodata acceptance stavka za terminalni `update`) je tačno onako kako proces traži — nema razloga za REJECT, upravo suprotno, ovo je primjer dobrog samoprijavljivanja.

**Zaključak:** spremno za merge, uz human approval (Radovan) prema MEDIUM tok pravilu.
