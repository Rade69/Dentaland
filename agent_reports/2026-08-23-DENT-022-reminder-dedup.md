# Implementer izvještaj — DENT-022 (zaštita od dupliranog slanja podsjetnika, HIGH)

Task: DENT-022 | Risk: HIGH | Implementer: Claude (direktno) | Status: IMPLEMENTED (runda 2) — čeka novi Reviewer 1 (Codex)

## Cilj

Zatvoriti eksplicitno prihvaćen rizik iz DENT-020: bez oznake "podsjetnik
poslan", restart backend-a ili slučajno dvostruko pokretanje scheduler-a
može poslati isti podsjetnik dva puta. Vidi puni plan (napisan PRIJE
koda, po HIGH-risk proceduri) u `agent_reports/2026-08-23-DENT-022-plan.md`.

## Fact found — stvaran mehanizam duplikata (prije koda)

Prozor `[now+24h, now+24h+15min)` se svaki put računa iznova iz
`datetime.now(UTC)` u trenutku poziva. Uzastopni pozivi iz STABILNOG
scheduler loop-a prirodno ne preklapaju prozore (pomjeraju se za tačno
15 min svaki put). Rizik je specifičan za: (1) restart procesa unutar
~15 min od zadnjeg poziva — novi `now` se može preklopiti sa već
obrađenim prozorom; (2) dva istovremena scheduler procesa. Ovo je
provjereno čitanjem koda prije pisanja bilo kakvog fixa.

## Runda 1 — REJECT (Codex, Reviewer 1)

Prva verzija (commit `770452d`) je odbijena — vidi
`agent_reports/2026-08-23-DENT-022-review-codex.md` za pun nezavisan
nalaz. Dva blokirajuća nalaza:

1. **Prava race-condition, ne samo teorijski rizik.** SELECT
   `reminder_sent_at IS NULL` i SMTP slanje nisu bili atomski — dva
   procesa mogu oba pročitati NULL i oba poslati prije nego što ijedan
   commituje. Codex je ovo dokazao pravom file-backed SQLite bazom, dvije
   sesije, dva threada, sa barijerom: `CONCURRENT_SEND_COUNT 2`.
2. **Moja vlastita adversarna provjera u ovom izvještaju (runda 1) je
   bila FAKTIČKI NETAČNA.** Napisao sam da je test bez fixa pao sa
   `send.call_count == 2`. Codex je reprodukovao isti korak i dobio
   drugačiji, stvaran rezultat: `send.call_count == 1`, a pravi failure
   je bio `stored.reminder_sent_at is not None` → `AssertionError: assert
   None is not None`. Razlog: termin je bio postavljen tačno na
   `now + REMINDER_LEAD_TIME`, na samoj donjoj granici prvog prozora —
   drugi poziv (`now + 1min`) ima prozor pomjeren za minut, pa termin
   prirodno ispadne iz njega bez obzira na dedup filter. Test dakle NIJE
   testirao ono što je tvrđeno da testira. Ovo je greška u mojoj
   provjeri, ne u Codexovoj — ispravno uhvaćena nezavisnim review-om,
   što je tačno svrha obaveznog Reviewer 1/2 procesa.

## Runda 2 — šta je promijenjeno

### `src/dentaland/services/notifications.py`

`send_due_appointment_reminders()` promijenjena iz "SELECT → pošalji →
upiši marker → commit" u **"zauzmi pa pošalji"**: prije SMTP poziva radi
se atomski `UPDATE appointments SET reminder_sent_at = :current WHERE id
= :id AND reminder_sent_at IS NULL`, pa se provjerava `rowcount`. Samo
worker čiji UPDATE stvarno pogodi red (rowcount == 1) šalje email; ako je
neki drugi worker već zauzeo taj red (rowcount == 0), termin se
preskače bez slanja. Atomičnost pojedinačnog UPDATE-a na nivou baze
(SQLite serijalizuje pisanje na fajl) garantuje da tačno jedan pozivalac
"pobijedi" bez obzira na thread/proces interleaving — ovo NIJE
probabilistička popravka, nego strukturna (ista klasa garancije kao
`EXCLUDE` constraint filozofija iz `CLAUDE.md`, primijenjena na
aplikacionom nivou jer SQLite nema `EXCLUDE`).

Dodat `from sqlalchemy import update`, `from sqlalchemy.engine import
CursorResult`, `from typing import Any, cast` — `cast` je potreban jer
mypy statički tipizira `Session.execute()` kao `Result[Any]`, koji nema
`.rowcount`; `CursorResult[Any]` je tačan runtime tip za DML `UPDATE`
izraze.

### `tests/test_backend.py`

- **Ispravljen `test_scheduler_ne_salje_dvaput_isti_termin`**: termin
  sad na `now + REMINDER_LEAD_TIME + 5min` (unutar presjeka oba prozora),
  ne na granici — test sad stvarno provjerava dedup filter, ne samo
  pomak prozora.
- **Nov `test_scheduler_paralelno_pokretanje_ne_salje_dvaput`**: prava
  file-backed SQLite baza (`tmp_path`, ne `StaticPool`/dijeljena
  konekcija), dvije nezavisne konekcije/sesije (`factory_a`,
  `factory_b`) kao dva odvojena scheduler procesa, `threading.Barrier(2)`
  koja pušta oba threada u isto vrijeme, thread-safe brojanje poziva
  (`threading.Lock`). Replicira Codexovu metodu iz runde 1.

## Izmijenjeni/novi fajlovi (svi u allowed_paths)

- `src/dentaland/models.py` — `Appointment.reminder_sent_at:
  Mapped[datetime | None]` (`TZDateTime()`, nullable, bez default-a) —
  isti obrazac kao `confirmed_at`/`arrived_at` (DENT-012). Nepromijenjeno
  od runde 1, Codex je nezavisno potvrdio `data_safety: PASS`.
- `migrations/versions/d4e5f6a7b8c9_reminder_sent_at.py` — aditivna
  Alembic revizija, revises `c3d4e5f6a7b8`. Nepromijenjeno od runde 1,
  Codex je nezavisno potvrdio `migration_safety: PASS`
  (`MIGRATION_ROUNDTRIP_PASS`, upgrade/downgrade/upgrade na pravoj bazi
  sa postojećim podacima).
- `src/dentaland/services/notifications.py` — vidi "Runda 2" iznad.
- `tests/test_backend.py` — vidi "Runda 2" iznad.

## Šta NIJE mijenjano (potvrđeno)

- `send_appointment_reminder()`, `send_booking_confirmation()`,
  `send_appointment_confirmed()` — netaknuto.
- `REMINDER_LEAD_TIME`/`REMINDER_WINDOW` konstante, sam mehanizam
  prozora — netaknuto.
- `backend/reminder_scheduler.py`, `backend/main.py` — netaknuto.
- `desktop/`, `web/` — netaknuto.

## Verifikacija (runda 2)

```text
pytest tests/ -q                              → 289 passed (288 runda-1 baseline + 1 novi paralelni test)
ruff check src/dentaland desktop backend tests → All checks passed!
mypy src/dentaland desktop backend             → Success: no issues found in 36 source files
```

Migracija nije ponovo ručno testirana u rundi 2 — fajl je nepromijenjen
od runde 1, gdje je Codex nezavisno potvrdio `migration_safety: PASS`
pravim upgrade/downgrade/upgrade ciklusom na SQLite bazi sa postojećim
podacima (vidi review fajl).

## Adversarna samo-provjera — runda 2 (stvaran tool output, ne parafraza)

Privremeno vraćen commitovan (odbijen) `notifications.py` iz `HEAD`
(`git show HEAD:... > notifications.py`), zadržan NOVI test. Pokrenut
`pytest tests/test_backend.py -q -k paralelno`:

```text
FAILED tests/test_backend.py::test_scheduler_paralelno_pokretanje_ne_salje_dvaput
AssertionError: očekivano tačno jedno slanje, dobijeno:
['pacijent@example.com', 'pacijent@example.com']
assert 2 == 1
```

Zatim vraćen fix, ponovo pokrenuto:

```text
tests/test_backend.py .                                                  [100%]
1 passed, 14 deselected, 2 warnings in 1.13s
```

Ovo je stvaran, karakter-po-karakter tačan zapis tool outputa (ne
tvrdnja bez provjere kao u rundi 1).

## Odbačene opcije

Vidi plan fajl (poseban `reminder_log` tabela, distribuirana brava,
retry logika za neuspjele SMTP pokušaje) — sve odbačeno prije koda,
obrazloženo tamo.

## Sljedeći korak

Čeka nov, nezavisan review od **Codex** (obavezan Reviewer 1 na HIGH) —
implementer se ne vraća da sam sebe pregleda. Nakon PASS-a od Codexa,
slijedi Reviewer 2 (Crush ili Pi), pa Radovanov human approval prije
merge-a — ništa od toga još nije urađeno za ovu rundu.
