---
task_id: REF-03
risk: MEDIUM
reviewer: claude
implementer: crush (podjela) + codex (F1 test fix nakon 3 neuspjele Crush runde)
reviewer_role: Reviewer 2 (arhitektura)
previous_review: 2026-08-24-REF-03-review-pi.md (fresh Reviewer 1, PASS)
verdict: PASS
commits: [d966200]
created_at: 2026-08-24
---

# REF-03 — Claude review (arhitektura, Reviewer 2)

```yaml
verdict: PASS
scope: PASS
acceptance: PASS
architecture: PASS
blocking_findings: []
```

```text
CILJ: Nezavisno provjeriti arhitekturu podjele booking.py (appointments/
      availability/settings/facade) i donijeti arhitektonsku odluku o P6
      nalazu koji je Pi eksplicitno proslijedio meni.
URAĐENO: PASS — arhitektura pregledana ranije (prije Codex prvog review-a)
      i ovdje potvrđena; P6 procijenjen kao namjerna, ispravna strogoća,
      ne defekt.
NE DIRATI: desktop/**, requests.py, print_schedule.py, models.py,
      migrations/** — nedirano kroz cijeli REF-03 (4 runde F1 popravki).
SLJEDEĆE: Radovanov human approval, pa merge — prije REF-04.
```

## 1. P6 — arhitektonska odluka (eksplicitno proslijeđeno od Pi-ja)

Pregledao sam `test_booking_facade_javne_metode_imaju_samo_dozvoljeni_oblik`
liniju po liniju. Linija 153: `assert not name.startswith("_")` — svaka
privatna metoda na `AppointmentService` (osim eksplicitno izuzetog
`_require_doctor`) pada test, bez obzira na sadržaj.

**Odluka: PASS, namjerno i ispravno — ne mijenjati.**

Razlozi:

1. Cilj REF-03 (Task Contract, plan sekcija 10) eksplicitno kaže facade
   "više NIJE mjesto za nove funkcije" — ovo se ne odnosi samo na
   poslovnu logiku (SQL, overlap), nego na BILO KAKVU novu funkciju,
   uključujući bezazlene privatne helpere. Ako neko misli da facade
   treba pomoćnu funkciju, to je znak da ta funkcija pripada u jedan od
   četiri modula, ne u facade — facade treba biti dovoljno tanak da mu
   sopstveni helperi nisu potrebni.
2. Ako se ikad pojavi legitimna potreba za privatnim helperom u
   facade-u, test će EKSPLICITNO pući i primorati svjesnu odluku
   (dodavanje u `_FACADE_EXEMPT_METHODS` uz obrazloženje) — isti obrazac
   kao REF-00/REF-01 testovi koji su namjerno pukli kad se stanje
   svjesno promijenilo. Eksplicitan FAIL koji traži svjesnu odluku je
   bolji ishod od tihog dopuštanja.
3. Asimetrija rizika: cijena "previše strogo" je nizak (test pukne, neko
   svjesno doda izuzetak) naspram cijene "previše labavo" (tiha
   regresija — poslovna logika se vraća u facade neopaženo, tačno ono
   što su četiri runde F1 popravki pokušavale spriječiti).

Pi je ispravno prepoznao ovo kao nešto što HVATA VIŠE nego što je striktno
traženo (ne manje) — takav profil greške (lažni negativ na budući
legitiman kod) je neuporedivo jeftiniji od lažnog pozitiva (propušten
regresija), pa ne mijenjam test.

## 2. Nezavisna verifikacija (ponovljena, ne prepisana)

```text
pytest tests/ -q                              → 336 passed, 11 warnings
ruff check src/dentaland desktop backend tests → All checks passed!
mypy src/dentaland desktop backend             → Success: no issues found in 40 source files
```

## 3. Arhitektura podjele — potvrđeno (pregledano prije Codexovog prvog review-a)

Pregledao sam `appointments.py`, `availability.py`, `settings.py` i
`booking.py` (facade) u cjelini kad sam pisao prvobitni Task Contract
prompt za Crush-a. Ovdje potvrđujem da se nije promijenilo kroz sve
F1 runde (F1 popravke su dirale ISKLJUČIVO `tests/test_ref03_booking_split.py`
— potvrđeno svakim review-om usput, i ovdje ponovo `git diff --stat`):

- Zavisnosti strogo jednosmjerne: `availability → models`,
  `appointments → availability + models`, `settings → appointments + models`.
  Nema kružnog uvoza.
- Ciklični import izbjegnut ispravnom odlukom: `DoctorDTO` u `settings.py`,
  `ServiceOptionDTO` u `appointments.py`, `settings.py` zavisi od
  `appointments.py` (ne obrnuto) — jednosmjerno.
- Tri nejasna slučaja (`doctors()`/`list_doctors()`, `list_working_hours`,
  `service_choices`/`service_options`) su istražena preko stvarne GUI
  upotrebe (`grep` po `desktop/`), ne nagađana — Pi i Codex su nezavisno
  potvrdili bar dio tih nalaza (npr. `list_working_hours` samo u
  `settings_panel.py`).
- Facade je stvarno tanak — potvrđeno i ranijim čitanjem `booking.py` i
  sada formalno kroz AST allowlist test.

## 4. Scope kroz cijeli ciklus (4 runde F1)

Svaka runda (`e8d1ab7` → `6e5680c` → `5a1acd0` → `d966200`) je dirala
ISKLJUČIVO `tests/test_ref03_booking_split.py` (plus `agent_reports/**`).
Produkcijski kod (`booking.py`, `appointments.py`, `availability.py`,
`settings.py`) je identičan onome što je nezavisno pregledano prije
Codexovog prvog review-a — nijedna od četiri runde nije "usput" promijenila
produkcijsku logiku dok se test kvalitet popravljao.

## Zaključak

PASS. Arhitektura podjele je čista (jednosmjerne zavisnosti, tanak facade,
istražene nejasne odluke). Konačan AST allowlist test je strukturno
robustan — dokazano kroz četiri runde adversarne eskalacije (Codex 3x,
Pi 1x nezavisno) bez preostalog lažnog PASS-a. P6 je namjerna, ispravna
strogoća, ne defekt. Nema blokirajućih nalaza. Čeka Radovanov human
approval prije merge-a.
