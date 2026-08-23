---
task_id: DENT-023
risk: LOW
implementer: pi
reviewers: [claude]
status: IMPLEMENTATION_COMPLETE
commits: [795aa125d3b1826ccbc12e711d8a2dca7f252fc2]
created_at: 2026-08-23
---

# DENT-023 — SMTP env var dokumentacija (.env.example + README)

## Task Contract

Izvor: `agent_reports/DENT-023-task-contract.md` (pun tekst). Cilj:
`src/dentaland/services/notifications.py` čita SMTP postavke iz env
varijabli (`DENTALAND_SMTP_HOST/PORT/USER/PASSWORD/FROM`), ali nigdje u
repou ne postoji dokumentacija tih varijabli. LOW risk — čista
dokumentacija, bez izmjene logike.

## Šta je urađeno

1. **`.env.example`** (novi fajl u korijenu) — dokumentuje svih 5
   `DENTALAND_SMTP_*` varijabli sa objašnjenjem i PRIMJER (ne stvarnim)
   vrijednostima. Sadrži:
   - napomenu da su varijable OPCIONE (bez `DENTALAND_SMTP_HOST` slanje
     se tiho preskače, aplikacija ne puca),
   - napomenu da aplikacija NE čita `.env` fajl automatski — fajl je
     samo referenca za ručno kucanje,
   - Gmail "App Password" specifičnost (16 znakova, generisan na
     `myaccount.google.com/apppasswords` uz 2-Step Verification, NE
     obična lozinka — greška `534 5.7.9 Application-specific password
     required`).
   - `DENTALAND_SMTP_PASSWORD=` je namjerno prazan (bez ijedne stvarne
     tajne).

2. **`README.md`** — novi odjeljak `## Email obavještenja (SMTP)`,
   umetnut između "Lokalno testiranje" i "Testovi i provjera koda".
   Objašnjava:
   - da su varijable opcione (aplikacija radi bez njih, samo ne šalje
     email),
   - upućuje na `.env.example`,
   - da varijable moraju biti postavljene u ISTOM terminalu/procesu
     koji pokreće `dev_local.py` (`_build_env()` kopira `os.environ` u
     trenutku poziva, ne čita `.env` fajl automatski),
   - tačne PowerShell komande prije `python scripts/dev_local.py`,
   - Gmail App Password specifičnost.

Nije implementirano automatsko učitavanje `.env` fajla (python-dotenv) —
van obima ovog LOW taska.

## Changed files

- `.env.example` — novi fajl (dokumentacija SMTP env varijabli).
- `README.md` — novi odjeljak "Email obavještenja (SMTP)", +32 linije.

## Verifikacija (rezultati)

Prije izmjena, baseline na worktree-u (isti kao kontrakt, 287):
```text
pytest tests/ -q → 287 passed, 11 warnings
```

Poslije izmjena:
```text
ruff check src/dentaland desktop backend tests
→ All checks passed!, exit 0

pytest tests/ -q
→ 287 passed, 11 warnings, exit 0  (baseline, nepromijenjen)
```

Warnings su postojeći dependency deprecation warning-i
(httpx/slowapi/alembic), ne vezani za ovaj task. Dokumentacija ne dira
kod, pa je baseline broj testova očuvan.

Dodatna provjera: `.env.example` ne sadrži stvarne kredencijale —
`DENTALAND_SMTP_PASSWORD=` je prazan, ostale vrijednosti su očigledni
primjeri (`smtp.gmail.com`, `tvoja.adresa@gmail.com`).

## Review

`PENDING` — implementer nije reviewer. Claude radi nezavisan LOW-risk
review; human approval nije obavezan, Radovan odlučuje.

## Integration status

`NOT_MERGED` — čeka nezavisan review.

## Handoff

CILJ: SMTP env varijable dokumentovane na jednom mjestu, bez izmjene koda.

URAĐENO: `.env.example` (svih 5 varijabli + Gmail App Password uputstvo)
i README odjeljak sa tačnim PowerShell koracima.

NE DIRATI: `src/dentaland/services/notifications.py`, `backend/`,
`desktop/`, `scripts/dev_local.py` — nijedan nije mijenjan.

SLJEDEĆE: Claude nezavisan review (LOW risk, human approval nije obavezan).
