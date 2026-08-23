---
task_id: DENT-022
risk: HIGH
reviewer: pi
reviewer_role: Reviewer 2
role_note: >-
  Ispravljeno naknadno (23.8.2026) — Pi je ovaj review izvorno označio
  kao "Reviewer 1 (ponovni, runda 2)". Po CLAUDE.md/dentaland-agentski-razvoj.md,
  Codex je OBAVEZAN Reviewer 1 na HIGH taskovima kad je dostupan (jeste,
  od 19.8.2026), pa Pi ne može popuniti tu ulogu čak ni u drugoj rundi.
  Sadržaj review-a nije mijenjan pri ovoj ispravci — samo rola u
  frontmatteru i "SLJEDEĆE" blok niže. Codexov Reviewer 1 review runde 2
  je i dalje obavezan i nedostaje.
reviewed_commit: e4794467cc59ecdf9e51e397ca56c5d827b61716
previous_review: 2026-08-23-DENT-022-review-codex.md (REJECT, commit 770452d)
verdict: PASS
created_at: 2026-08-23
---

# DENT-022 — nezavisan HIGH-risk review (Pi, Reviewer 2)

```yaml
verdict: PASS
scope: PASS
acceptance: PASS
architecture: PASS
security: PASS
data_safety: PASS
migration_safety: PASS
blocking_findings: []
```

```text
CILJ: provjeriti da korektivni commit e479446 stvarno zatvara paralelni
      race (dva workera ne smiju oba poslati podsjetnik) i da ništa van
      DENT-022 scope-a nije dirano.
URAĐENO: PASS — atomski conditional claim (UPDATE ... WHERE
      reminder_sent_at IS NULL + rowcount) je ispravan i SQLite-kompatibilan;
      adversarno onesposobljavanje claim-a daje 2 slanja, vraćen kod daje
      tačno 1 slanje (20 pytest iteracija + 30 nezavisnih repro rundi).
NE DIRATI: model/migracija (nepromijenjeni od runde 1, već validirani),
      desktop/, web/, backend/main.py, backend/reminder_scheduler.py,
      booking/requests servisi.
SLJEDEĆE: Ovaj review važi kao Reviewer 2 (ne Reviewer 1 — vidi
      role_note u frontmatteru). Codex (obavezan Reviewer 1 na HIGH)
      mora još uraditi svoj Reviewer 1 review runde 2 nad commitom
      e479446 prije nego što se ide na Radovanov human approval i
      merge. Nema blokirajućih nalaza za implementera.
```

## 0. Metod

Nezavisan review od nule — nisam naslijedio implementerovo (Claude) ni
Codexovo rezonovanje. Rekonstruisao sam stvarno ponašanje iz koda, ponovio
realan file-backed SQLite paralelni scenario u sopstvenoj skripti, i
adversarno onesposobio atomski claim da dokažem da test stvarno hvata
duplo slanje. Produkcijski kod vraćen je tačno na `e479446` nakon
adversarne probe (nema diff-a u worktree-u, `git status --short` prazan).

## 1. Scope (diff `770452d..e479446`)

```text
git diff --name-only 770452d..e479446
→ src/dentaland/services/notifications.py
→ tests/test_backend.py
→ agent_reports/2026-08-23-DENT-022-reminder-dedup.md
→ agent_reports/2026-08-23-DENT-022-review-codex.md
```

Sva četiri fajla su u `allowed_paths` DENT-022. Grep za forbidden putanje:

```text
git diff --name-only 770452d..e479446 | grep -E "desktop/|web/|backend/main.py|backend/reminder_scheduler.py|services/booking.py|services/requests.py"
→ (prazno) — NEMA forbidden fajlova
```

Model i migracija su dodani u rundi 1 (`770452d`) i ovaj korektivni commit
ih NE mijenja:

```text
git diff 770452d..e479446 -- src/dentaland/models.py migrations/
→ (prazno)
```

`scope: PASS`.

## 2. Atomskost claim-a i rowcount (fokus 1)

Trenutni kod `send_due_appointment_reminders()` (commit `e479446`):

1. SELECT bira SCHEDULED termine u prozoru sa `reminder_sent_at IS NULL`
   (optimizacija, ne garancija).
2. Za svaki termin, u **zasebnoj** sesiji: `UPDATE appointments SET
   reminder_sent_at=:current WHERE id=:id AND reminder_sent_at IS NULL`,
   zatim `session.commit()`, pa `claimed = result.rowcount == 1`.
3. Samo `claimed == True` poziva `send_appointment_reminder`.

**Atomskost:** pojedinačni `UPDATE ... WHERE reminder_sent_at IS NULL` je
atomičan na nivou SQLite baze (single statement; SQLite serijalizuje
pisanje). Tačno jedan worker može prevesti red iz `NULL` u `current`; drugi
worker, čak i da je obavio SELECT dok je vrijednost bila `NULL`, dobije
`rowcount == 0` jer njegov WHERE više ne matchuje.

**Interpretacija `rowcount`:** za pysqlite DML, `CursorResult.rowcount` je
broj stvarno promijenjenih redova. WHERE garantuje `reminder_sent_at IS
NULL`, a SET postavlja `current` (datetime) — vrijednost se **uvijek**
mijenja (NULL → datetime), pa nema SQLite "no-op UPDATE rowcount==0" edge
case-a. WHERE je i po `id` (PK), pa maksimalno 1 red. `claimed == 1` je
ispravna i SQLite-kompatibilna interpretacija.

**Napomena (non-blocking, stil):** `result.rowcount` se čita NAKON
`session.commit()` — radi (CursorResult je materijalizovan pri execute),
ali čitljivije bi bilo pročitati ga prije commit-a. Nije bug.

**Napomena (non-blocking, tip):** `cast("CursorResult[Any]", ...)` sa
string literal je neobično, ali ispravno (runtime no-op) i `mypy` prolazi
čisto.

### Redoslijed claim/commit/SMTP i ponašanje pri grešci

Redoslijed je **claim → commit → SMTP slanje**.

- **Commit ne uspije** (npr. `database is locked` / disk greška): izuzetak
  propagira iz funkcije; sesija (context manager) rollback-uje UPDATE, red
  ostaje `NULL`, email nije poslat. `backend/reminder_scheduler.py`
  (`run_reminder_scheduler`) hvata `Exception`, loguje i nastavlja — naredni
  prolaz (15 min) prirodno retry-uje termin. **Nema duplog slanja, nema
  trajnog gubitka.**
- **SMTP ne uspije** (nakon uspješnog claim+commit): `send_appointment_reminder`
  interno hvata izuzetak i nikad ne baca (best-effort). Termin je već
  označen, pa se ne ponovo pokušava — **dokumentovan i planom prihvaćen
  kompromis** (plan, tačka 3: "označiti kao poslano BEZ OBZIRA na ishod
  SMTP slanja"), ne regresija.
- **Crash između commit-a i SMTP-a:** termin ostaje označen poslanim iako
  email nije otišao — inherentan trade-off "claim-before-send" pristupa.
  Cilj DENT-022 je "nikad duplo", ne "nikad propusti", pa je ovo ispravan
  izbor; trade-off je eksplicitno opisan u docstringu funkcije.

Ovo ujedno **zatvara Codex-ov nalaz runde 1** ("SMTP side-effect prethodi
commitu → commit padne poslije slanja → marker NULL → ponovno slanje"):
u novom redoslijedu commit se dešava PRIJE SMTP side-effecta, pa taj
scenario više ne postoji.

`architecture: PASS`.

## 3. Testovi (fokus 2 i 3)

### 3.1 Paralelni test — dvije zasebne sesije, file-backed SQLite

`test_scheduler_paralelno_pokretanje_ne_salje_dvaput` koristi pravu
file-backed bazu (`tmp_path`, `sqlite:///{db_path}`), dvije nezavisne
konekcije (`factory_a`, `factory_b`), `threading.Barrier(2)` i
`threading.Lock` za brojanje. Termin je na `now + 24h + 5min` — **unutar
presjeka oba prozora** (ne na granici), pa ne može ispasti prirodnim
pomakom prozora.

Pokrenut 20× uzastopno na vraćenom kodu `e479446`:

```text
20/20 passed (tačno 1 slanje svaki put)
```

### 3.2 Adversarna proba — onesposobljen atomski claim

Privremeno izmijenjeno `claimed = result.rowcount == 1` → `claimed = True`
(kopija fajla sačuvana u `/tmp`), pokrenut paralelni test 15×:

```text
15/15 FAILED
AssertionError: očekivano tačno jedno slanje, dobijeno:
['pacijent@example.com', 'pacijent@example.com']
assert 2 == 1
```

Pad je isključivo zbog **dva slanja** (ne lažni pad). Nakon toga
`git checkout -- src/dentaland/services/notifications.py` vratio je fajl
tačno na `e479446` (potvrđeno: `git diff --stat` prazan,
`git rev-parse HEAD` = `e4794467...`).

Zaključak: test **stvarno detektuje** nedostatak atomskog claim-a (2
slanja), a ne daje lažni PASS.

### 3.3 Nezavisna reprodukcija (odvojen repro, ne implementerov test)

Napisao sam sopstvenu skriptu (`/tmp/repro_dent022.py`) koja u 30 rundi,
svaka sa svežom file-backed bazom i dva threada na barijeri, broji poslane
emailove:

```text
REPRO_RESULT: 30/30 rundi tačno 1 slanje; rounda sa !=1 slanjem: 0
```

### 3.4 Sekvencijalni restart scenario

```text
pytest tests/test_backend.py::test_scheduler_ne_salje_dvaput_isti_termin \
       ::test_scheduler_bira_samo_scheduled_termine_u_uskom_prozoru \
       ::test_scheduler_odbija_naivno_trenutno_vrijeme -q
→ 3 passed
```

`test_scheduler_ne_salje_dvaput_isti_termin` sada koristi termin u presjeku
oba prozora (`now + 24h + 5min`), pa stvarno provjerava dedup filter
(`first == 1`, `second == 0`, `send.call_count == 1`,
`stored.reminder_sent_at is not None`) — Codex-ov nalaz runde 1 zatvoren.

`acceptance: PASS`.

## 4. Puna verifikacija

```text
pytest tests/ -q
→ 289 passed, 11 warnings   (287 baseline + 2 nova DENT-022 testa)

ruff check src/dentaland desktop backend tests
→ All checks passed!

mypy src/dentaland desktop backend
→ Success: no issues found in 36 source files
```

Warnings su postojeći dependency deprecation warning-i (httpx/slowapi/
alembic), ne vezani za ovaj task.

`security: PASS` i `data_safety: PASS` — izmjena ne dira sadržaj poruka
(minimizacija netaknuta), ne čita nove kredencijale, ne dodaje nove putanje
podataka; `reminder_sent_at` je interna dedup oznaka, bez PII.

## 5. Migracija

`e479446` NE mijenja `src/dentaland/models.py` ni `migrations/` (diff
prazan — dokaz u sekciji 1). Model kolona `reminder_sent_at` (nullable
`TZDateTime()`, `models.py:177`) i migracija `d4e5f6a7b8c9` (aditivna,
`revises c3d4e5f6a7b8`, `batch_alter_table` + `add_column`/`drop_column`)
nepromijenjeni su od runde 1, gdje je Codex nezavisno potvrdio stvaran
upgrade/downgrade/upgrade na SQLite bazi sa postojećim podacima
(`MIGRATION_ROUNDTRIP_PASS`). Migraciona provjera nije ponavljana jer
commit ne dira model/migraciju — `migration_safety: PASS`.

## Zaključak

`verdict: PASS`. Atomski conditional claim je strukturna (ne
probabilistička) garancija tačno jednog slanja po terminu, ispravno tumači
`rowcount`, ispravan je redoslijed claim → commit → SMTP (nema duplog slanja
ni pri commit/SMTP greškama), SQLite-kompatibilan, i nezavisno reprodukovan
(30/30 rundi + 20 pytest iteracija = 1 slanje; adversarno = 2 slanja).
Nema blokirajućih nalaza.

Non-blocking observations (ne zahtijevaju izmjenu, za zapis):
- `result.rowcount` čitan nakon `session.commit()` (stil).
- `cast("CursorResult[Any]", ...)` string literal (stil, mypy čist).
- claim-before-send trade-off (crash između commit-a i SMTP-a trajno
  propušta podsjetnik) — prihvaćen i dokumentovan kompromis u korist
  "nikad duplo".
