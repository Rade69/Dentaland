---
task_id: DENT-IMPROVE-014
risk: HIGH
reviewer: pi
role: Reviewer 2 (arhitektura/scope + nezavisna reprodukcija)
verdict: PASS_WITH_NOTES
date: 2026-08-27
---

# DENT-IMPROVE-014 — Pi nezavisan review (append-only audit jezgro)

Nezavisan pregled, izveden od nule — nisam čitao Codex rezonovanje prije
sopstvene provjere. Svi ključni nalazi **reprodukovani uživo**, ne preuzeti
iz izvještaja.

## Obim / scope — PROLAZI

- **Nema scope creep-a.** Izmjene ograničene na `allowed_paths`:
  `models.py` (samo dodati AuditEvent/AuditAction), `services/audit.py`,
  nova migracija, `tests/test_audit.py`.
- **Nula instrumentacije stvarnih poziva** — grep potvrda: `grep -rn
  "write_audit_event|AuditEvent|AuditAction"` u `appointments.py`, `auth.py`,
  `backend/main.py` → **0 pogodaka** (potvrđeno, ne preuzeto).
- **`desktop/**` i `web/**` netaknuti** — nisu u `git status`, potvrđeno.

## Forbidden paths — PROLAZI

`git diff HEAD` za sve zaštitne putanje → **prazan**:

- `src/dentaland/services/appointments.py`, `auth.py` — netaknuti
- `backend/main.py` — netaknut
- `desktop/**`, `web/**` — netaknuti
- `migrations/env.py`, `alembic.ini` — netaknuti
- Postojeće migracije — samo nova `f6a7b8c9d0e1` dodana, postojeće netaknute

## Arhitektonska ocjena `src/dentaland/services/audit.py` — PROLAZI

- **Poslovna logika ostaje u servisnom sloju** — `write_audit_event` je u
  `services/audit.py`, nema logike u routeru/backend-u. Ispravno.
- **API dizajn (obavezan `session_factory` + opcioni `session=`) čist i
  konzistentan sa `_revoke_active_sessions` iz DENT-IMPROVE-013** — isti
  obrazac "radi na postojećoj sesiji, ne commit-uje kada je sesija
  proslijeđena". Prilagođen da bude javni (ne `_`-prefiks) jer je 014C
  cross-modul pozivalac — ispravno obrazloženo u planu (Opcija A/B/C/D
  razmotrene, izbor obrazložen).

## Atomski `session=` API — NEZAVISNO REPRODUKOVAN (ključno)

Nisam prihvatio na riječ ni Codexa ni implementera — napisao sam **svoju**
proboverifikaciju atomičnosti nad in-memory SQLite:

```
SCENARIO 1 (rollback): session= + prateća izmjena, onda session.rollback()
  → Nakon rollback, audit redova: 0  (dokaz da rollback povlači audit red)

SCENARIO 2 (commit): session= + prateća izmjena, onda session.commit()
  → Nakon commit, audit redova: 1    (dokaz da commit upisuje oboje)

SCENARIO 3 (ne commit-uje): session= bez commit-a, druga sesija provjera
  → Prije commit-a druga sesija vidi: 1 (samo prethodni; audit red NE
    curi prije commit-a — dokaz da funkcija ne commit-uje)
```

**Zaključak:** `write_audit_event(..., session=)` zaista omogućava 014C
atomsku upotrebu — audit upis i izmjena termina idu u istu transakciju,
rollback poništava oboje. Dizajn je spreman za 014C bez dodatnog kruga.

## Migracija — PROLAZI (ručno potvrđeno)

- `down_revision = e5f6a7b8c9d0`, `alembic heads` → `f6a7b8c9d0e1 (head)`.
- `alembic upgrade head` na čistoj SQLite bazi → lanac svih 6 revizija
  čisto, `audit_events` sa **tačno 9 kolona**
  (`id, actor_user_id, action, resource_type, resource_id, occurred_at,
  request_id, source_ip, metadata_minimal`).
- `downgrade -1` → uklanja **samo** `audit_events`, svih ostalih 8 tabela
  ostaje netaknuto (7 domain + users/sessions).
- **Ne dira postojećih 7 tabela** — potvrđeno.

## Standardni gateovi (reprodukovano)

- `pytest tests/ -q` → **410 passed, 2 skipped** (potvrđeno, ne preuzeto)
- `ruff check src/dentaland desktop backend tests scripts/agent_sensors.py` → **All checks passed**
- `mypy src/dentaland desktop backend` → **54 fajla, 0 grešaka**
- `python scripts/agent_sensors.py --all` → **0 blocking findings**

## Provjera za 014B (ja kao budući implementer) — PROLAZI

Kako ću implementirati 014B (LOGIN_SUCCESS/LOGIN_FAILURE), provjerio sam da
mi jezgro daje sve što treba:

- `write_audit_event(session_factory, action, *, actor_user_id=None,
  resource_type=None, resource_id=None, request_id=None, source_ip=None,
  metadata=None, session=None)` — sve što mi treba za login.
- `authenticate_user` vraća `AuthenticatedUser(id, username, role)` → imam
  `user.id` za `LOGIN_SUCCESS` i `user.role` za response.
- **`auth.py` NEMA pristup `Request`/`source_ip`** (potvrđeno grepom) —
  `source_ip` **mora** doći iz `backend/main.py` route handlera
  (`request.client.host`). Zato 014B audit poziv ide u route handler (ne u
  `authenticate_user`), ili moram proširiti `authenticate_user` signature sa
  opcionim `source_ip: str | None = None`. Ovo je u skladu sa 014B
  kontraktom (tačka 2) — jezgro mi ništa ne nedostaje.
- **Slazem se da 014B NEMA potrebu za `session=`** — login audit desiće se u
  route handleru posle `authenticate_user` vrati, bez okolne transakcije.
  Samostalni mod (`session_factory` bez `session=`) je tačno ono što mi
  treba.

**Zaključak 014B:** jezgro mi daje kompletan API. Nisam blokiran ni na jednoj
tački; mogu početi čim se 014 merge-uje.

## Nalazi

- **N1 (non-blocking, kozmetički):** `metadata_minimal` se namjerno ne
  validira/sanitizuje (dokumentovano, i ja se slažem jer bi generički
  denylist dao lažan osjećaj sigurnosti). **Ali** — drugačenije od Codexa,
  koji je primijetio isto — smatram da bi **konkretan follow-up** bio:
  eksplicitno upozorenje (koje već postoji u docstringu) + oslonac na to da
  014B/014C imaju vlastite testove za tajnu/PII zabranu. Ovo je već
  ispunjeno u kontraktima 014B/014C. Nije potrebna izmjena sada.
- **N2 (informativno):** `audit_events` `actor_user_id` nullable je ispravno
  — `LOGIN_FAILURE` (NULL) i desktop appointment pozivi (NULL). Radovanova
  odluka, ispoštovana bez izmišljanja lažnog actor-a. Potvrđeno da je to
  jedini ispravan pristup za sada.

## Verdict: PASS_WITH_NOTES

Kod je arhitektonski čist i minimalan, obim strogo ispoštovan (nula
instrumentacije), svi forbidden paths netaknuti, migracija tačna (9 kolona,
izolovana downgrade), `session=` atomski API **nezavisno dokazan sopstvenom
probom**, i — što je za mene najvažnije — **014B je kompletno spreman**: imam
`write_audit_event` signature, `user.id`, i jasno mi je da `source_ip` mora
doći iz route handlera. Nema blokirajućih nalaza.

Napomena: **DENT-IMPROVE-012 kritični nalaz (372/4 fail) — VAŽNO —
ispravljen.** Moj raniji nalaz je bio validan; noviji `migrations/env.py`
sada ima uslov `== "sqlite:///dentaland.db"` koji poštuje eksplicitne URL-ove
postojećih SQLite testova (komentar eksplicitno citira "Pi review,
DENT-IMPROVE-012"). Tačno stanje sada: **DENT-012 ça suite sa `DATABASE_URL`
→ 376 passed, 0 failed** (potvrđeno ponovo). Nalaz nije gušen — bio je
zabilježen i strukturno ispravljen.
