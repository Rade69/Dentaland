---
task_id: DENT-IMPROVE-022
risk: MEDIUM
implementer: crush
reviewers: [claude]
status: "NOT STARTED"
created_at: 2026-08-31
depends_on: none
---

# DENT-IMPROVE-022 — Raspored refresh u JEDNOJ transakciji (ne tri)

## Kontekst

Radovan je uživo testirao desktop aplikaciju povezanu na test VPS preko
SSH tunela (DENT-IMPROVE-020/021 kontekst, `.agent/CURRENT_STATE.md`) i
primijetio primjetnu pauzu (~kašnjenje) na klik doktor-taba i dan/sedmica
dugmadi u toolbaru, u odnosu na klik na paneле u lijevom sidebaru.

**Dijagnostika (već urađena, ne ponavljati)**: privremeno uključeno
`log_min_duration_statement=0` na Postgres serveru (test VPS), Radovan
klikao po aplikaciji, log pročitan preko SSH-a. Otkriveno:

1. **Već popravljeno u ovoj sesiji** (DENT-IMPROVE prethodni commit-i,
   `c6afde4`, `c8225f0`): dva N+1 upit bug-a (`awaiting_confirmation`/
   `cancelled_today` u `appointments.py`, `breaks_for_week` u
   `availability.py`) — SVA TRI su NEZAVISNA, ne dirati ih ponovo.
2. **Ostaje otvoreno (OVAJ task)**: `ScheduleController.refresh()`
   (`desktop/controllers/schedule_controller.py`) poziva TRI ODVOJENE
   store metode — `appointments_for_range`, `time_off_for_week`,
   `breaks_for_week` — svaka OTVARA SVOJU `with session_factory() as
   session:` (svoj BEGIN/ROLLBACK par). Rezultat: 3 odvojene mrežne
   transakcije za JEDAN konceptualni "snapshot rasporeda", umjesto
   jedne.

**Izmjereno** (test VPS preko SSH tunela, Contabo): ~35ms mrežnog
kašnjenja PO POJEDINAČNOM upitu/round-trip-u (server obrađuje upit za
<1ms — kašnjenje je čisto mrežno, ne SQL). Sa ~11 ukupnih round-trip-ova
po refresh-u (3 BEGIN + 3 ROLLBACK + 5 SELECT-a), to je ~385ms SAMO na
mrežno kašnjenje po jednom kliku doktor-taba/dan-sedmica dugmeta.
Spajanje u JEDNU transakciju (1 BEGIN + 1 ROLLBACK + isti broj SELECT-a)
uklanja ~4 round-trip-a (2 suvišna BEGIN/ROLLBACK para) — ne rješava
mrežno kašnjenje po SELECT-u (to je inherentno SSH tunel testiranju,
van obima), ali smanjuje UKUPAN broj round-trip-ova.

**Napomena o razmjeru dobitka**: ovo NIJE dramatično rješenje (network
latency po pojedinačnom upitu ostaje ista) — cilj je smanjiti BROJ
transakcija sa 3 na 1, ne broj SELECT upita (ti su već optimalni nakon
N+1 popravki). Radovan je EKSPLICITNO odlučio da ovo ipak vrijedi
uraditi (nije obavezno prihvatiti "dovoljno dobro" stanje).

## Cilj

`ScheduleController.refresh()` dobija PODATKE (appointments + blocks)
kroz JEDAN pOZIV servisnog sloja koji interno otvara TAČNO JEDNU
`with session_factory() as session:` sesiju za sve tri vrste upita
(appointments_for_range logika + time_off_for_week logika +
breaks_for_week logika), umjesto tri odvojena poziva/sesije.

## Required scope

1. **Novа kombinovana servisna funkcija** — predložena lokacija:
   `src/dentaland/services/appointments.py` (već uvozi
   `selectinload`/`select`, prirodno mjesto za "snapshot" fasadu koja
   uvozi iz `availability.py`), ime po slobodnom izboru implementera
   (npr. `schedule_snapshot`), potpis približno:

   ```python
   def schedule_snapshot(
       session_factory: Callable[[], Session],
       range_start: datetime,
       range_end: datetime,
       week_start: date,
       doctor_id: int | None = None,
   ) -> tuple[list[AppointmentDTO], list[CalendarBlockDTO]]:
       """Termini + kalendarski blokovi (odsustva + pauze) u JEDNOJ
       sesiji/transakciji — vidi DENT-IMPROVE-022 Task Contract za
       kontekst (mrežno kašnjenje po transakciji na SSH-tunelovanoj
       konekciji)."""
   ```

   Unutar JEDNOG `with session_factory() as session:` bloka:
   - Ista upit logika kao trenutni `appointments_for_range` (ISTI
     `select(Appointment).options(selectinload(...), selectinload(...))
     .where(...)` — kopirati TAČNO, ne mijenjati filtere/semantiku).
   - Ista upit logika kao trenutni `time_off_for_week` (kopirati TAČNO).
   - Ista upit logika kao trenutni `breaks_for_week` (kopirati TAČNO —
     UKLJUČUJUĆI već popravljeni `IN (...)` batch iz `c8225f0`, NE
     vraćati stari N+1 obrazac).

   **VAŽNO — ne duplirati logiku ručnim kopiranjem ako se može
   izbjeći**: ako je jednostavnije, umjesto copy-paste-a, PREFERIRANO
   je da se `appointments_for_range`/`time_off_for_week`/
   `breaks_for_week` prošire OPCIONIM `session: Session | None = None`
   parametrom (ako je proslijeđen, koristi se direktno bez otvaranja
   nove `with session_factory()`; ako nije, ponašanje identično
   ranijem — POTPUNO BACKWARD-COMPATIBLE, svi postojeći pozivi bez tog
   parametra rade nepromijenjeno). Onda `schedule_snapshot` otvori
   JEDNU sesiju i pozove sve tri postojeće funkcije s tom sesijom —
   nema duplirane logike, manji rizik od buduće divergencije. Implementer
   bira pristup (copy-paste vs. session parametar) — obrazložiti izbor
   u evidence izvještaju.

2. **`AppointmentService` facade** (`src/dentaland/services/booking.py`)
   — nova metoda koja delegira na `schedule_snapshot` (isti facade
   obrazac kao ostale metode u toj klasi — JEDNA linija delegacije,
   vidi npr. `breaks_for_week`/`time_off_for_week` metode tamo za
   stil). **PAŽNJA**: postoji arhitektonski test
   (`tests/test_ref03_booking_split.py`) koji provjerava da facade
   metode imaju SAMO dozvoljen oblik (jednolinijska delegacija) — nova
   metoda mora zadovoljiti taj ugovor ILI biti eksplicitno dodana u
   `_FACADE_EXEMPT_METHODS` listu u tom test fajlu SAMO ako stvarno
   sadrži više od delegacije (provjeriti prije nego se doda izuzetak —
   ne dodavati izuzetak bez pravog razloga).

3. **`desktop/controllers/schedule_controller.py`** —
   `ScheduleController.refresh()` (i `_fetch_appointments`/
   `_fetch_blocks` po potrebi) mijenja se da:
   - AKO `store` ima `schedule_snapshot` metodu (`getattr` provjera,
     isti duck-typing obrazac kao ostatak fajla — vidi
     `_fetch_appointments`/`_fetch_blocks` za stil), pozvati JE i
     dobiti `(appointments, blocks)` odjednom.
   - AKO NEMA (backward-compat za bilo koji test/fake store koji ne
     implementira novu metodu), PASTI NAZAD na postojeće ponašanje
     (`_fetch_appointments()` + `_fetch_blocks()` odvojeno) — ne smije
     se srušiti ako store nema novu metodu.
   - `set_doctor_filter`/`_active_range` logika (koja trenutno
     prosljeđuje `doctor_id` SAMO u `_fetch_appointments`, ne u
     `_fetch_blocks`) mora ostati identična semantika — `breaks_for_week`/
     `time_off_for_week` NIKAD nisu filtrirani po doktoru (svi
     aktivni doktori), samo `appointments_for_range` jeste kad je
     tab specifičnog doktora aktivan. Nova kombinovana putanja mora
     poštovati ISTU semantiku (doctor_id ide SAMO u appointments dio
     upita, ne u blocks dio).

4. **Testovi**:
   - Novi test (npr. u `tests/test_ref02_range_reads.py`, isti fajl
     gdje žive N+1 regresioni testovi iz ove sesije) koji brojanjem
     upita (isti `event.listen(engine, "before_cursor_execute", ...)`
     obrazac kao postojeći N+1 testovi u tom fajlu) dokazuje da
     `schedule_snapshot` koristi TAČNO JEDAN `BEGIN`/transakcijski
     kontekst — npr. provjeriti da SELECT upiti (ne brojati
     BEGIN/COMMIT/ROLLBACK posebno ako se teško broje kroz
     `before_cursor_execute` — pogledati kako `session_factory` fixture
     u tom fajlu radi transakcije, prilagoditi provjeru realnosti;
     ALTERNATIVA ako brojanje transakcija nije praktično: provjeriti da
     je REZULTAT (appointments + blocks) identičan onome što bi dala
     STARA odvojena tri poziva, za isti scenario kao postojeći N+1
     testovi).
   - Test da `ScheduleController` I DALJE radi ispravno sa store-om
     koji NEMA `schedule_snapshot` (fallback putanja) — postojeći
     `tests/test_gui/test_schedule_controller.py` testovi ne smiju
     pući; ako fake/mock store tamo nema novu metodu, to je upravo
     dokaz da fallback radi.
   - Test da `doctor_id` filter i dalje radi ispravno (appointments
     filtrirani po doktoru, blocks NE) kroz novu putanju — postojeći
     `test_gui` testovi za doctor filter ne smiju pući, dodati novi
     ako pokrivenost nedostaje.

## Šta NE dirati

- Ne mijenjati SQL/filter logiku unutar tri postojeće funkcije — SAMO
  kako se sesija otvara/dijeli. Isti razlog kao ranije N+1 popravke:
  izlazni podaci moraju ostati bit-za-bit identični, mijenja se SAMO
  broj round-trip-ova.
- Ne dirati `awaiting_confirmation`/`cancelled_today`
  (`appointments.py`) niti `breaks_for_week`-ov `IN (...)` batch
  (`availability.py`) — već popravljeno u ovoj sesiji (`c6afde4`,
  `c8225f0`), taj kod je gotov i testiran.
- Ne dirati `_refresh_dashboard()` (`desktop/views/main_window.py`) —
  poznat, SEPARATAN nalaz (`pending_requests()` se poziva 3x zaredom
  u toj funkciji) koji NIJE dio ovog task-a, prijaviti kao
  `OUT_OF_SCOPE_FINDING` ako se dotakne, ne popravljati usput.
- Ne mijenjati `AppointmentDTO`/`CalendarBlockDTO` strukture.

## Acceptance criteria

- [ ] `ScheduleController.refresh()` (kad store podržava
      `schedule_snapshot`) pravi TAČNO JEDNU sesiju/transakciju za
      appointments+time_off+breaks, ne tri
      **DOKAZANO**, ne samo tvrđeno — mjerenje/test mora pokazati
      stvarnu razliku (broj upita/transakcija prije i poslije)
- [ ] Store BEZ `schedule_snapshot` metode i dalje radi (fallback na
      staru putanju) — postojeći testovi ne smiju pući
- [ ] Rezultat (appointments + blocks, uključujući doctor_id filter
      semantiku) IDENTIČAN prije/poslije za isti scenario
- [ ] `pytest tests/ -q` (i bez i sa `DATABASE_URL_TEST`), `ruff`,
      `mypy`, `agent_sensors.py --all` čisti
- [ ] Evidence izvještaj eksplicitno navodi koji pristup je izabran
      (copy-paste logike vs. opcioni `session` parametar) i zašto

## Review

Claude (jedini reviewer — Crush je implementer, pravilo od 29.8.2026:
implementer nikad nije isti agent kao reviewer). Human approval
(Radovan) prije merge-a.

## Koordinacija

```bash
python scripts/coordination.py claim --task DENT-IMPROVE-022 --agent crush --paths src/dentaland/services/appointments.py,src/dentaland/services/booking.py,src/dentaland/services/availability.py,desktop/controllers/schedule_controller.py,tests/test_ref02_range_reads.py,tests/test_ref03_booking_split.py
```

Nema poznatih zavisnosti sa paralelnim taskovima. Grana/worktree već
pripremljena: `task/DENT-IMPROVE-022-schedule-single-transaction`
(`C:\Users\38765\Desktop\Dentaland-worktrees\DENT-IMPROVE-022-schedule-single-transaction`).
