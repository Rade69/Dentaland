---
task_id: DENT-IMPROVE-005
risk: MEDIUM
implementer: crush
reviewers: [claude]
verdict: PASS_WITH_NOTES
created_at: 2026-08-21
---

# DENT-IMPROVE-005 — nezavisan review (Claude)

## Metod

Nezavisna provjera od nule (`independent-review` skill) — Crush-ov
izvještaj (`agent_reports/2026-08-21-DENT-IMPROVE-005-settings.md`)
tretiran kao tvrdnja, ne dokaz. Sve niže je nezavisno rekonstruisano,
ponovo pokrenuto i adversarno testirano u worktree-u
`Dentaland-worktrees/DENT-IMPROVE-005-settings`
(`task/DENT-IMPROVE-005-settings`, granat od `main` `e3376ea`).

## Scope

```text
git diff --stat
 desktop/views/main_window.py       |  6 +-
 src/dentaland/services/__init__.py |  2 +
 src/dentaland/services/booking.py  | 138 +++++
 tests/test_services.py             | 89 +++
+ desktop/views/settings_panel.py (novo)
+ tests/test_gui/test_settings_panel.py (novo)
```

Sve unutar `allowed_paths`. `models.py`/`migrations/` nedirani —
potvrđeno kroz `git diff --stat`.

## Verdikt: PASS_WITH_NOTES

### Acceptance

| Kriterij | Status | Dokaz |
|---|---|---|
| aktivacija/deaktivacija doktora bez brisanja istorije | PASS | `set_doctor_active` samo mijenja `aktivan` flag; test `test_set_doctor_active_ne_brise_termine` potvrđuje termin ostaje |
| promjena trajanja usluge utiče na nove termine | PASS | `update_service` mijenja `Service` red; postojeći termini referenciraju `service_id`, ne kopiraju trajanje (potvrdio čitanjem `Appointment`/`Service` relacije) |
| radno vrijeme podržava split shift | PASS, adversarno potvrđeno | vidi niže |
| validacija sprečava nelogične intervale | PASS | dan 1..7, `od<do`, no-overlap — sve testirano i adversarno provjereno |
| postojeći scheduler nastavlja raditi | PASS | pun regression set (251) i dalje prolazi |

### Reprodukcija (nezavisna, ne prepisana)

```text
pytest tests/ -q → 251 passed, 11 warnings (identično Crush-ovoj tvrdnji)
ruff check src/dentaland desktop backend tests → All checks passed
mypy src/dentaland desktop backend → Success, 34 source files
```

### Pokušaj obaranja (Korak 4) — adversarni testovi, uklonjeni nakon review-a

Napisao sam i pokrenuo tri testa koje Crush-ov set nije pokrio, isti
fixture setup kao `tests/test_services.py`:

1. **Touching boundary split shift** — `08:00–12:00` i `12:00–16:00` u
   istom danu (dodiruju se, ne preklapaju) — realan jutro/popodne
   scenario. **PASS** — oba intervala prihvaćena, `right[0] < left[1]`
   provjera ispravno tretira dodir kao ne-overlap.
2. **Prazna lista intervala** — `set_working_hours(doctor_id, dan, [])`
   (scenario: GUI "Ukloni interval" pa "Sačuvaj" dok je lista prazna).
   **PASS** — briše sve postojeće intervale tog dana bez greške,
   `list_working_hours` vraća prazno.
3. **Izolacija po danu** — postavljanje radnog vremena za ponedjeljak ne
   smije dirati već postavljeno radno vrijeme za utorak. **PASS** —
   `set_working_hours` briše/upisuje samo redove sa istim
   `(doctor_id, dan_u_sedmici)`, drugi dan netaknut.

Nisam uspio oboriti implementaciju — jača potvrda nego da nisam ni
tražio. Testovi obrisani nakon provjere, nisu dio isporuke.

### `blocking_findings`

Nijedan.

### Napomene (ne blokiraju)

1. **GUI test coverage gap na "Radno vrijeme" tabu.** Servisni sloj
   (`set_working_hours`) je dobro testiran (uklj. moje adversarne
   dodatke), ali `SettingsPanel` GUI testovi (`test_settings_panel.py`)
   pokrivaju samo Doktori/Usluge tabove (3 taba postoje, checkbox
   toggle, usluge tabela) — nijedan test ne klika "Dodaj interval"/
   "Ukloni interval"/"Sačuvaj" niti otvara `IntervalDialog`/
   `ServiceDialog` kroz `qtbot`. Kod izgleda ispravan vizuelnom
   inspekcijom (isti obrazac kao `BlockoutPanel`), ali najsloženiji dio
   UI-ja (tri dijaloga, split-shift interakcija) nije GUI-testiran.
2. **Asimetrija između "Doktori" i "Radno vrijeme" tabova, nije bug.**
   `_refresh_doctors` (Doktori tab) koristi `store.list_doctors()` (SVI,
   uklj. neaktivne), dok `_refresh_doctors_combo` (Radno vrijeme tab)
   koristi postojeći `store.doctors()` (samo `aktivan=True`, provjereno
   u `booking.py:165-170`, nepromijenjeno ovim taskom). Posljedica: čim
   se doktor deaktivira, nestaje iz combo-a na Radno vrijeme tabu — ali
   njegovi `WorkingHours` redovi ostaju u bazi (nisu obrisani), samo
   privremeno nedostupni za uređivanje dok se doktor ne reaktivira.
   Razumno ponašanje, ne defekt, ali vrijedno da Radovan zna za ovu
   posljedicu.

## Probni signal — `.agent/` sloj (potvrđeno protiv Crush-ovog izvještaja)

Konzistentno sa stvarnim scope-om. Crush je nastavio obrazac iz
`DENT-IMPROVE-004` (Pi) — kombinovao Feature/Desktop GUI/Booking routing
pakete, koristio `blockout_panel.py` kao referentni obrazac za novi
`settings_panel.py` (isti duck-typed `store`, isti `changed` signal
princip) — konzistentnost stila kroz dva različita implementera je sama
po sebi dobar signal da `.agent/` sloj i postojeći kod uspostavljaju
zajedničku konvenciju koju agenti prate bez eksplicitnog uputstva.

## Integration status

`REVIEWED → PASS_WITH_NOTES` — čeka Radovanov human approval (MEDIUM
risk), zatim merge i post-merge integration gate na `main`.

## Handoff

CILJ: minimalne postavke — doktori (aktivan/neaktivan), usluge
(dodaj/uredi), radno vrijeme (split shift po doktoru/danu).

URAĐENO: PASS_WITH_NOTES — implementacija ispravna, u scope-u, adversarno
provjerena na tri granična slučaja (touching boundary, prazna lista,
izolacija po danu). Nema blocking findings.

NE DIRATI: `models.py`/`migrations/`, korisnički nalozi/RBAC/SMTP UI —
nisu dirani, van scope-a (eksplicitno isključeno u Task Contractu).

SLJEDEĆE: Radovanov human approval → merge → post-merge integration gate
na `main`. Zatim `DENT-IMPROVE-006` (Novi zahtjevi ekran) po
koordinacionoj napomeni iz Task Contracta.
