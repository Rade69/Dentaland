---
task_id: DENT-022
risk: HIGH
reviewer: codex
reviewer_role: Reviewer 1
reviewed_commit: 770452db78f425fadc0a4e83bc33bdb3f57cc9cd
verdict: REJECT
created_at: 2026-08-23
---

# DENT-022 — nezavisan HIGH-risk review (Codex, Reviewer 1)

```yaml
verdict: REJECT
scope: PASS
acceptance: REJECT
architecture: REJECT
security: PASS
data_safety: PASS
migration_safety: PASS
blocking_findings:
  - location: src/dentaland/services/notifications.py:108
    rule: DENT-022 objective i acceptance — slučajno dvostruko/paralelno pokretanje ne smije poslati isti podsjetnik dva puta
    finding: SELECT reminder_sent_at IS NULL i SMTP slanje nisu atomski claim; dva procesa mogu oba pročitati NULL i poslati prije prvog UPDATE/COMMIT-a
  - location: tests/test_backend.py:264
    rule: DENT-022 acceptance — test mora simulirati dva preklapajuća poziva i dokazati samo jedno slanje
    finding: termin je tačno na početku prvog prozora, pa ga drugi prozor pomjeren za 1 min prirodno isključuje; test ne provjerava preklapajući termin niti paralelni race
```

CILJ: Nezavisno provjeriti da DENT-022 bez gubitka podataka sprečava duplo
slanje podsjetnika nakon restarta i slučajnog paralelnog scheduler procesa.

URAĐENO: **REJECT** — migracija, scope i sekvencijalni restart slučaj su
ispravni, ali stvarni paralelni scenario i dalje šalje isti email dva puta.

NE DIRATI: Uspješnu aditivnu migraciju i nepovezane desktop/web/backend
fajlove. Problem je ograničen na atomsko zauzimanje posla u notification
servisu i regresioni test koji mora stvarno pokriti preklapanje/paralelizam.

SLJEDEĆE: Implementer treba uvesti atomski conditional claim nad redom prije
SMTP poziva (ili drugi SQLite-kompatibilan mehanizam koji garantuje da samo
jedan worker dobije pravo slanja), dodati stvarno preklapajući/paralelni test,
pa vratiti izmjenu na novi Reviewer 1 review. Poslije toga i dalje je obavezan
Reviewer 2 i human approval prije merge-a.

## 1. Scope i kod

Diff commita `770452d` sadrži šest fajlova i svi su u `allowed_paths`:

- `src/dentaland/models.py`
- `migrations/versions/d4e5f6a7b8c9_reminder_sent_at.py`
- `src/dentaland/services/notifications.py`
- `tests/test_backend.py`
- dva DENT-022 fajla u `agent_reports/`

Nema izmjena u `desktop/`, `web/`, `backend/main.py`,
`backend/reminder_scheduler.py`, booking ili requests servisu.

Model i migracija koriste nullable DateTime obrazac dosljedan postojećim
`confirmed_at`/`arrived_at` kolonama. Pozivaoci
`send_due_appointment_reminders()` pregledani su kroz repo; produkcijski
poziv ostaje `backend/reminder_scheduler.py` i taj fajl nije mijenjan.

## 2. Migracija na stvarnoj SQLite bazi

Nezavisno je napravljena stvarna SQLite baza na reviziji `c3d4e5f6a7b8`, sa
doktorom, uslugom i terminom čija su sva postojeća polja namjerno popunjena,
uključujući `confirmed_at`, `arrived_at`, kontakt, napomenu, status i
timestamps. Zatim je izvršeno:

```text
alembic upgrade head
alembic downgrade -1
alembic upgrade head
```

Rezultat: `MIGRATION_ROUNDTRIP_PASS 16 17 Postojeci Pacijent`.

- upgrade dodaje samo `reminder_sent_at = NULL` (16 → 17 kolona);
- svi stari podaci su byte/value-ekvivalentni poslije upgrade-a;
- downgrade vraća identičnu listu 16 kolona i identičan cijeli red;
- `confirmed_at` i `arrived_at` ostaju prisutni i netaknuti;
- ponovni upgrade opet dodaje samo novu NULL kolonu.

`migration_safety: PASS` i `data_safety: PASS`.

## 3. Transakcija i dokazani race

Funkcija drži dohvat, slanje, postavljanje `reminder_sent_at` i commit u istoj
SQLAlchemy sesiji. To zatvara sekvencijalni restart slučaj nakon uspješnog
commita, ali **ne uklanja race**: email se šalje prije nego što je marker
postavljen/commitovan, a obični SELECT ne zaključava niti atomski zauzima red.

Adversarni scenario je koristio pravu file-backed SQLite bazu, dvije zasebne
sesije i dva threada. Mock SMTP poziv je barijerom zadržao oba workera dok oba
ne pročitaju termin. Rezultat sa implementiranim fixom:

```text
CONCURRENT_SEND_COUNT 2
CONCURRENT_ERRORS []
```

Oba workera su poslala isti email. Činjenica da su operacije u istoj sesiji
nije dovoljna; potreban je atomski conditional UPDATE/claim čiji rezultat samo
jednom workeru daje pravo slanja (ili ekvivalentna SQLite-kompatibilna
serializacija). Ovo je blocking finding jer Task Contract eksplicitno navodi
slučajno dvostruko pokretanje scheduler-a kao dio cilja.

Dodatno, SMTP side-effect prethodi commitu: ako commit zakaže nakon slanja,
marker ostaje NULL i naredni poziv ponovo šalje. To je isti osnovni nedostatak
neatomskog side-effect/DB toka i treba ga uzeti u obzir pri korekciji.

## 4. Adversarna provjera novog testa

Privremeno su uklonjena oba produkcijska reda:

- `Appointment.reminder_sent_at.is_(None)` filter;
- `appointment.reminder_sent_at = current` update.

Pokrenut je tačno
`test_scheduler_ne_salje_dvaput_isti_termin`; test je stvarno pao, a fix je
zatim vraćen i isti test je ponovo prošao. Međutim, pad nije dokazao duplo
slanje:

```text
first == 1       PASS
second == 0      PASS
send.call_count == 1  PASS
stored.reminder_sent_at is not None  FAIL (bio je NULL)
```

Razlog: `start = now + 24h` je tačno donja granica prvog prozora. Drugi poziv
koristi `now + 1min`, pa njegov prozor počinje minut poslije termina i više ga
ne bira. Komentar da su prozori „i dalje preklapajući“ jeste tačan za prozore,
ali **termin nije u njihovom presjeku**. Implementerova tvrdnja da je bez fixa
dobijen `send.call_count == 2` nije reprodukovana i proturječi stvarnom
rezultatu.

Test treba staviti termin unutar presjeka (npr. `now + 24h + 5min`) i dodati
konkurentni scenario sa dvije zasebne sesije; tek tada štiti oba obećana
slučaja.

## 5. Standardna verifikacija

Na vraćenom, tačnom commitu `770452d`:

```text
pytest tests -q  -> 288 passed, 11 warnings
ruff check src/dentaland desktop backend tests -> All checks passed
mypy src/dentaland desktop backend -> Success: no issues found in 36 source files
```

Automatski paket je čist, ali nema test koji modeluje dokazani paralelni race,
pa ne može nadjačati živu reprodukciju duplog slanja.
