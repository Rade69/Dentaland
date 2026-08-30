---
task_id: DENT-IMPROVE-019
risk: HIGH
implementer: claude
reviewers: [codex]
status: "NOT STARTED"
created_at: 2026-08-30
depends_on: none
---

# DENT-IMPROVE-019 — TZDateTime na Postgresu čuva pogrešno vrijeme (timestamptz fix)

## Kontekst

Otkriveno slučajno tokom DENT-IMPROVE-018 end-to-end testiranja na test
VPS-u (30.8.2026): potvrđen termin za `11:00 UTC` je u bazi završio kao
`13:00 UTC` — dva sata pogrešno, tačno razlika vremenske zone Postgres
servera (`Europe/Berlin`, ljeti UTC+2).

**Reprodukovano i lokalno**, ne samo na VPS-u: isti test protiv lokalnog
dev Postgres-a (`Europe/Budapest`, isti UTC+2 ljeti) daje identičan
kvar. Ovo NIJE VPS-specifičan problem — pogađa svaki Postgres server
čija je `TimeZone` GUC vrijednost različita od UTC.

## Root cause

`TZDateTime` (`src/dentaland/models.py:55-79`) je definisan sa
`impl = DateTime` — BEZ `timezone=True`. Na Postgresu to znači kolona
tipa `timestamp without time zone`, ne `timestamptz`.

Kad se tz-aware Python `datetime` (npr. `11:00 UTC`) upiše u
`timestamp without time zone` kolonu, Postgres ga implicitno pretvori
u sesijsku `TimeZone` (server default, npr. `Europe/Berlin`) PRIJE nego
što odbaci oznaku zone — upisuje "goli" broj `13:00` bez ikakve
naznake da je pomjeren. `process_result_value` zatim taj naivan broj
tretira KAO DA jeste UTC (`value.replace(tzinfo=UTC)`) — druga greška
koja se dodaje na prvu, ali čak i bez nje, upisana vrijednost je već
pogrešna.

**Zašto 473 postojeća testa (uključujući DENT-IMPROVE-018 Postgres run)
ovo nisu uhvatila**: testovi koji provjeravaju `appt.start_time`
vrijednosti (npr. `test_confirm_request_postavlja_doktora_uslugu_vrijeme`)
koriste `sqlite:///:memory:` fixture, NE `DATABASE_URL_TEST` — čak i
kad je ta env varijabla postavljena. SQLite nema sesijsku
vremensku-zonu konverziju, pa problem nikad nije mogao da se pojavi u
tim testovima. Postojećih ~20 testova koji STVARNO rade protiv
Postgres-a (kroz `DATABASE_URL_TEST`) provjeravaju strukturu migracija,
ne tačnu vrijednost timestamp round-trip-a — rupa u pokrivenosti, ne
namjeran propust.

## Zašto HIGH risk

Utiče na SVAKU `TZDateTime` kolonu (`start_time`, `end_time`,
`confirmed_at`, `arrived_at`, `reminder_sent_at`, `created_at`,
`updated_at`, `telegram_link_token_expires_at`,
`telegram_subscribed_at`, `Session.expires_at/created_at/revoked_at`,
`AuditLog.occurred_at`, `WorkingHours.od_datetime/do_datetime`) na
SVAKOM Postgres serveru čija sesijska `TimeZone` nije UTC — što je
sasvim realan scenario za bilo koji hosting koji se na kraju izabere.
Direktno krši CLAUDE.md pravilo "Sve vrijeme je timezone-aware
(zoneinfo/timestamptz), nikad naivni datetime" — namjera pravila je
tačno ono što ovaj bug krši, samo na nivou tipa kolone koji sam naziv
`TZDateTime` implicira da je već ispravno riješeno.

**Srećna okolnost**: hosting/produkcijska odluka je i dalje eksplicitno
odgođena (CLAUDE.md "Otvorena pitanja") — nijedan Postgres server sa
STVARNIM pacijentskim podacima još ne postoji. Migracija ispod NE mora
rješavati oporavak istorijskih (potencijalno već pomjerenih) podataka.

## Cilj

`TZDateTime` postaje stvarno tz-aware na nivou Postgres kolone
(`timestamptz`/`timestamp with time zone`), ispravno round-trip-uje
BEZ OBZIRA na sesijsku `TimeZone` servera. Dodati regresioni test koji
ovo stvarno provjerava protiv pravog Postgres-a (ne samo SQLite), sa
sesijom eksplicitno postavljenom na NE-UTC zonu — da rupa u pokrivenosti
koja je sakrila ovaj bug ne može sakriti regresiju.

## Required scope

1. **`src/dentaland/models.py`** — `TZDateTime.impl` promijeniti sa
   `DateTime` na `DateTime(timezone=True)`. `process_result_value`
   dodatno normalizovati na `.astimezone(UTC)` i za već tz-aware
   vrijednosti (ne samo `tzinfo is None` granu) — docstring već
   obećava "vraća se kao timezone-aware UTC", trenutni kod to ne
   garantuje kad Postgres vrati offset koji nije `+00:00`.

2. **Migracija** (`migrations/versions/*.py`) — `ALTER COLUMN ... TYPE
   timestamptz USING <col> AT TIME ZONE 'UTC'` za SVE `TZDateTime`
   kolone nabrojane gore. `USING ... AT TIME ZONE 'UTC'` tretira
   postojeću naivnu vrijednost KAO DA već jeste UTC (ispravna
   pretpostavka za bilo koju vrijednost upisanu dok je sesija
   slučajno bila UTC — što je najbolja moguća pretpostavka bez
   stvarnih podataka za oporavak, vidi napomenu o hosting odluci
   iznad). Eksplicitno NE pokušavati "popraviti" već pomjerene
   vrijednosti — nema pouzdanog načina da se zna koja je sesija bila
   aktivna kad je svaki red upisan, a nema ni stvarnih podataka za
   koje bi to bilo bitno.
   `downgrade()` radi obrnuto (`TYPE timestamp USING <col> AT TIME
   ZONE 'UTC'`).

3. **Testovi** (`tests/test_models.py` ili novi
   `tests/test_tzdatetime_postgres.py`) — SAMO protiv pravog Postgresa
   (skip bez `DATABASE_URL_TEST`, isti obrazac kao postojeći
   `test_postgres_migration.py`):
   - Eksplicitno postaviti sesijsku `TimeZone` na NE-UTC vrijednost
     (npr. `SET TIME ZONE 'America/New_York'` na konekciji prije
     testa) — dokazuje da fix ne zavisi od servera koji je slučajno
     već UTC.
   - Upisati tz-aware `datetime` (bilo koje UTC offset-e, ne samo
     `+00:00` — npr. proslijediti `datetime(..., tzinfo=ZoneInfo("Asia/Tokyo"))`)
     preko ORM-a, pročitati nazad, provjeriti `==` originalnoj
     vrijednosti (Python datetime `==` ispravno poredi apsolutni
     trenutak bez obzira na tzinfo offset).
   - Regresioni test KONKRETNO za scenario koji je otkriven: upiši
     `11:00 UTC`, pročitaj, mora biti `11:00 UTC` (ne `13:00`) — mora
     PASTI sa starim kodom (`impl = DateTime` bez `timezone=True`),
     PROĆI sa fixom (ista adversarna metodologija kao
     DENT-IMPROVE-013 F1 fix, vidi
     `agent_reports/2026-08-27-DENT-IMPROVE-013-auth-rbac.md`).
   - Migracija: `alembic upgrade head` na praznoj test bazi (ne samo
     `create_all()`), provjeri da kolona STVARNO ima `timestamptz` tip
     (`information_schema.columns.data_type`), ne samo da migracija
     ne baci grešku.

4. **Postojeći testovi ne smiju pući** — puna `pytest tests/ -q`
   verifikacija i bez i sa `DATABASE_URL`/`DATABASE_URL_TEST`.

## Šta NE dirati

- Ne mijenjati `AppointmentService.from_sqlite` / Faza 0 desktop→SQLite
  putanju — SQLite nema ovaj problem (nema sesijsku vremensku zonu),
  fix je isključivo Postgres-stranski (kolona tip + migracija).
- Ne pokušavati "popraviti" postojeće podatke u koloni pretpostavkom o
  tome kad je koji red upisan — nema pouzdanog načina, i nema stvarnih
  podataka za koje bi to bilo bitno (vidi Cilj/Kontekst).
- Ne dirati DENT-IMPROVE-018 kod (`telegram.py`, webhook) — taj kod je
  ispravno formatirao ŠTA GOD je dobio kao `start_time`; korupcija se
  dešava PRIJE njega, u samom upisu. DENT-IMPROVE-018 evidence ostaje
  validan za ono što dokazuje (Telegram mehanika), uz napomenu o ovom
  odvojenom nalazu.

## Acceptance criteria

- [ ] `TZDateTime` koristi `DateTime(timezone=True)`, `process_result_value`
      normalizuje na UTC i za tz-aware ulaz
- [ ] Migracija mijenja SVE `TZDateTime` kolone na `timestamptz`,
      testirana `alembic upgrade head` na praznoj Postgres bazi
      (i lokalno, i po mogućnosti provjereno na test VPS-u)
- [ ] Regresioni test dokazano PADA sa starim kodom, PROLAZI sa fixom
      (isto kao DENT-IMPROVE-013 metodologija)
- [ ] Test eksplicitno mijenja sesijsku TimeZone na ne-UTC prije
      provjere round-trip-a
- [ ] `pytest tests/ -q` (i bez i sa `DATABASE_URL_TEST`), `ruff`,
      `mypy`, `agent_sensors.py --all` čisti
- [ ] Evidence eksplicitno navodi da li je test VPS Postgres baza
      (test podaci) stvarno migrirana i provjerena, ili samo lokalno

## Review

Codex (jedini reviewer). Human approval prije merge-a. Codex posebno
provjerava: (a) da li `USING ... AT TIME ZONE 'UTC'` pretpostavka ima
smisla s obzirom da nema stvarnih produkcijskih podataka, (b) da li
regresioni test STVARNO dokazuje razliku (pao bi sa starim kodom), (c)
da li fix pokriva SVE `TZDateTime` kolone, ne samo `start_time`/`end_time`.

## Koordinacija

```bash
python scripts/coordination.py claim --task DENT-IMPROVE-019 --agent claude --paths src/dentaland/models.py,migrations/versions/**,tests/test_models.py,tests/test_postgres_migration.py
```

Nema poznatih zavisnosti sa DENT-IMPROVE-018 (odvojen, paralelan
worktree/grana) — ali oba diraju `migrations/versions/`, pa treba
paziti na redoslijed `down_revision` lanca prilikom merge-a oba u
`main` (koji god se prvi mergira, drugi treba rebase svoje migracije
da nastavi lanac).
