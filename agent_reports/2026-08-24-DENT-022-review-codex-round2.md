---
task_id: DENT-022
risk: HIGH
reviewer: codex
reviewer_role: Reviewer 1
review_round: 2
reviewed_commits:
  - e4794467cc59ecdf9e51e397ca56c5d827b61716
  - 778ade8fab6aec18621972e037df1b9805061af8
previous_review: 2026-08-23-DENT-022-review-codex.md (REJECT)
verdict: PASS_WITH_NOTES
created_at: 2026-08-24
---

# DENT-022 — nezavisan HIGH-risk review, runda 2 (Codex, Reviewer 1)

```yaml
verdict: PASS_WITH_NOTES
scope: PASS
acceptance: PASS_WITH_NOTES
architecture: PASS
security: PASS
data_safety: PASS
migration_safety: PASS
blocking_findings: []
```

CILJ: Nezavisno provjeriti da korektivni commit `e479446` zatvara oba
blocking findinga iz Codex Reviewer 1 runde 1: stvarni paralelni race i lažno
modelovan sekvencijalni test.

URAĐENO: **PASS_WITH_NOTES** — oba prethodna blocking findinga su zatvorena
statički i živim adversarnim dokazom. Nema blokera za human approval/merge.
Neblokirajuća napomena je da je nužna korekcija promijenila redoslijed iz
originalnog Task Contracta sa „pošalji pa označi“ u „atomski zauzmi/commituj
pa pošalji“; time je garancija namjerno at-most-once, uz poznat crash prozor.

NE DIRATI: Model i migraciju, koji nisu mijenjani u rundi 2 i već su prošli
stvarni SQLite migration round-trip u Reviewer 1 rundi 1; forbidden putanje
ostaju netaknute.

SLJEDEĆE: Reviewer 2 je evidentiran kao Pi (`778ade8`). Radovan treba u human
approval koraku eksplicitno prihvatiti dokumentovani at-most-once kompromis
(moguć propušten podsjetnik pri crashu između commita i SMTP poziva), zatim se
može merge-ovati i pokrenuti post-merge integration gate.

## 1. Scope i impact

Korektivni diff `770452d..e479446` dira samo:

- `src/dentaland/services/notifications.py`
- `tests/test_backend.py`
- implementer izvještaj i prethodni Codex review u `agent_reports/`

Metadata commit `778ade8` dodaje/ispravlja samo Pi Reviewer 2 izvještaj.
Nema izmjena u `desktop/`, `web/`, `backend/main.py`,
`backend/reminder_scheduler.py`, booking/requests servisu, modelu ili
migracijama. Produkcijski pozivalac ostaje postojeći reminder scheduler.

`scope: PASS`.

## 2. Blocking finding #1 — paralelni race

Nova implementacija prvo radi optimistički SELECT kandidata, ali odluka ko
smije poslati više ne zavisi od tog SELECT-a. Za svaki kandidat izvršava se
jedan conditional DML:

```text
UPDATE appointments
SET reminder_sent_at = :current
WHERE id = :id AND reminder_sent_at IS NULL
```

UPDATE se commituje prije SMTP side-effecta. Samo pozivalac sa
`rowcount == 1` šalje; drugi paralelni worker dobija `rowcount == 0` i
preskače termin. SQLite serijalizuje konkurentne writere, a NULL→datetime
promjena i PK uslov čine rowcount nedvosmislenim (0 ili 1).

Nezavisni live repro koristio je 30 svježih file-backed SQLite baza, po dvije
zasebne engine/session fabrike i dva threada sinhronizovana barijerom. Termin
je bio u reminder prozoru. Rezultat:

```text
ROUND2_CONCURRENCY_PASS 30 rounds; exactly 1 send each
```

U svakoj rundi rezultati workera bili su `[0, 1]`, bez izuzetaka i sa tačno
jednim SMTP pozivom. Prethodni dokaz `CONCURRENT_SEND_COUNT 2` više se ne
reprodukuje.

`architecture: PASS`; blocking finding #1 je zatvoren.

## 3. Blocking finding #2 — regresioni test

Sekvencijalni test sada stavlja termin na
`now + REMINDER_LEAD_TIME + 5min`, unutar presjeka oba prozora. Drugi poziv
pomjeren za jedan minut zato bi bez dedupa ponovo izabrao isti termin.

Dodan je zaseban `test_scheduler_paralelno_pokretanje_ne_salje_dvaput` sa
pravom file-backed SQLite bazom, dvije nezavisne konekcije/sesije, dva threada
i eksplicitnim provjerama:

- tačno jedan SMTP poziv;
- zbir povratnih vrijednosti oba workera je 1;
- marker je trajno upisan;
- threadovi završavaju bez hang-a.

Adversarno sam privremeno promijenio samo odluku
`claimed = result.rowcount == 1` u `claimed = True`. Paralelni test je pao
isključivo na duplom slanju:

```text
AssertionError: očekivano tačno jedno slanje, dobijeno:
['pacijent@example.com', 'pacijent@example.com']
assert 2 == 1
```

Fajl je zatim vraćen tačno na `HEAD` (`778ade8`), worktree je bio čist, a
isti test ponovo je prošao. Dakle test nije lažni PASS i hvata baš uklanjanje
atomskog claim mehanizma.

Ciljani scheduler paket:

```text
4 passed, 2 warnings
```

`acceptance: PASS_WITH_NOTES`; blocking finding #2 je zatvoren.

## 4. Poznati at-most-once kompromis

Redoslijed je sada claim → commit → SMTP. To je potrebno da se zatvori
paralelni duplicate race, ali znači:

- pad commita: email nije poslan i marker nije trajno upisan;
- SMTP neuspjeh: marker ostaje postavljen (postojeći best-effort/no-retry
  poslovni izbor);
- crash procesa poslije commita, a prije SMTP poziva: marker ostaje postavljen
  i email može biti trajno propušten.

Posljednja tačka nije duplicate regresija i eksplicitno je dokumentovana u
rundi 2, ali literalna acceptance rečenica iz prvobitnog Task Contracta kaže
da se marker postavlja „nakon best-effort slanja u istoj sesiji/transakciji“.
Korekcija nužno radi suprotno kako bi garantovala at-most-once bez outboxa ili
provider idempotency ključa. Zato je verdict `PASS_WITH_NOTES`, a human
approval treba eksplicitno prihvatiti ovaj precizirani kompromis; ne smije se
tvrditi exactly-once/delivery garancija koju sistem nema.

## 5. Migracija i data safety

`e479446` i `778ade8` ne mijenjaju model ni migraciju. Reviewer 1 runda 1 je
već nezavisno izvršila stvarni SQLite ciklus sa postojećim popunjenim redom:

```text
upgrade head -> downgrade -1 -> upgrade head
MIGRATION_ROUNDTRIP_PASS 16 17 Postojeci Pacijent
```

Tada je potvrđeno da downgrade uklanja samo `reminder_sent_at`, dok svih 16
starih kolona, cijeli red, `confirmed_at` i `arrived_at` ostaju netaknuti.
Pošto runda 2 nema schema diff, rezultat ostaje primjenjiv.

`data_safety: PASS`; `migration_safety: PASS`; `security: PASS` (sadržaj
emaila, minimizacija i SMTP konfiguracija nisu dirani).

## 6. Puna verifikacija

Na čistom `778ade8` nakon vraćanja adversarne izmjene:

```text
pytest tests -q
-> 289 passed, 11 warnings

ruff check src/dentaland desktop backend tests
-> All checks passed!

mypy src/dentaland desktop backend
-> Success: no issues found in 36 source files
```

Upozorenja su postojeća dependency/deprecation upozorenja iz
httpx/slowapi/alembic, bez novog DENT-022 upozorenja.
