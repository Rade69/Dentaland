---
task_id: DENT-IMPROVE-002
risk: LOW
implementer: pi
reviewers: [claude]
verdict: PASS_WITH_NOTES
created_at: 2026-08-20
---

# DENT-IMPROVE-002 — nezavisan review (Claude)

## Metod

Nezavisna provjera od nule (`independent-review` skill) — Pi-jev izvještaj
(`agent_reports/2026-08-20-DENT-IMPROVE-002-pi.md`) tretiran kao tvrdnja,
ne dokaz. Sve niže je nezavisno rekonstruisano i ponovo pokrenuto u
worktree-u `Dentaland-worktrees/DENT-IMPROVE-002-ci`
(`task/DENT-IMPROVE-002-ci`, granat od `main` `ae7bf53`), ne prepisano iz
implementer reporta.

## Scope

```text
git status --short --branch
 M README.md
?? .github/
?? agent_reports/2026-08-20-DENT-IMPROVE-002-pi.md
```

`.github/workflows/ci.yml` (novi fajl) + `README.md` (dopuna sekcijom "CI
(GitHub Actions)"). `pyproject.toml` nedirnut. Nijedan `forbidden_path`
(`src/`, `desktop/`, `backend/`, `web/`, `migrations/`) nije dirnut —
potvrđeno kroz `git status`, ne samo kroz izjavu u izvještaju.

## Verdikt: PASS_WITH_NOTES

### Acceptance

| Kriterij | Status | Dokaz |
|---|---|---|
| workflow na `push` i `pull_request` | PASS | nezavisno parsiran YAML (`yaml.safe_load`): `on: {push: None, pull_request: None}`, bez ograničenja grana |
| sve tri provjere prolaze | PASS (lokalno) | nezavisno pokrenuto u ovom worktree-u: `pytest` 222 passed, `ruff` all checks passed, `mypy` 0 grešaka u 31 fajlu — identično Pi-jevoj tvrdnji, ne prepisano od njega |
| Python verzija usklađena sa projektom | PASS, uz napomenu | `pyproject.toml` je izvor istine za tooling (`requires-python>=3.12`, `ruff target-version="py312"`, `mypy python_version="3.12"`); CI koristi `3.12` — ispravna odluka. README.md ima pre-existing kontradiktoran tekst "Python 3.13+" (linija 9) — vidi OUT_OF_SCOPE_FINDING niže |
| README navodi CI | PASS | dodana sekcija, link na workflow fajl je tačan |
| bez matrixa/Dockera/coverage | PASS | jedan job, jedan Python, bez cache/coverage koraka |

### Architecture

Workflow koraci (checkout → setup-python → sistemske Qt zavisnosti → pip
install → pytest → ruff → mypy) su 1:1 iste komande kao lokalni `README.md`
"Provjere prije commita" blok — nema skrivenog drugačijeg ponašanja CI
naspram lokalnog. Zavisnosti u `Install Python dependencies` koraku ručno
upoređene red-po-red sa `pyproject.toml` `[project.dependencies]` +
`[project.optional-dependencies].dev` — identičan skup, namjerno dupliran
umjesto `pip install -e .` jer `pyproject.toml` nema `[build-system]`.
Razumna LOW-risk odluka za CI-only task; ne dira paketizaciju.

### Security

`QT_QPA_PLATFORM=offscreen` je postavljen i na job-level env i već postoji
kao `os.environ.setdefault(...)` u `tests/test_gui/conftest.py` (provjereno
direktno u fajlu) — redundantno, ne štetno. SMTP-zavisni testovi
(`test_backend.py`, `test_notifications.py`, `test_requests.py`) ne
zahtijevaju kredencijale u CI — `notifications.py` čita
`DENTALAND_SMTP_HOST` sa `os.environ.get(..., "")` i graceful no-op ako
prazno (potvrđeno čitanjem koda), a lokalni pytest run u ovom worktreeu
(bez ijedne `DENTALAND_SMTP_*` varijable postavljene) prolazi čisto — isto
okruženje kao CI će imati.

### Pokušaj obaranja (Korak 4)

Tražio sam: YAML "Norway problem" (`on:` kao boolean) — GitHub Actions ima
custom parser koji ovo ispravno tretira, nije stvaran bug, samo kvirka
generičkih YAML parsera; verzije alata nisu pinovane (`ruff>=0.6`,
`mypy>=1.14`) ni lokalno ni u CI — konzistentno ponašanje, nije novi rizik;
apt paket lista za PySide6 headless nije nezavisno potvrđena na pravom
`ubuntu-latest` runneru (ne mogu izvršiti GitHub Actions iz ovog
okruženja) — jedini preostali rezidualni rizik, isto ograničenje koje je
i Pi eksplicitno priznao, ne skriveno.

### `blocking_findings`

Nijedan.

### Napomene (ne blokiraju PASS)

1. **Verifikacija ostaje djelimična dok se ne izvrši pravi GitHub Actions
   run** — lokalne komande i YAML struktura su nezavisno potvrđene, ali
   "CI je zeleno" formalno važi tek nakon prvog push-a na GitHub. Ovo je
   inherentno ovom tipu LOW zadatka (isto što je Pi već zapisao), ne
   nalaz protiv implementacije.
2. **`OUT_OF_SCOPE_FINDING` — RIJEŠENO na eksplicitan Radovanov zahtjev
   nakon review-a.** `README.md` linija 9 je izmijenjena sa "Python 3.13+"
   na "Python 3.12+", uz referencu na `pyproject.toml` kao izvor istine.
   Ovo je jednolinijski doc-fix, ne funkcionalna izmjena — nije mijenjao
   verdikt niti zahtijevao novi review krug.
3. Dupliranje zavisnosti (workflow vs `pyproject.toml`) — implementerova
   odluka je razumna i dobro obrazložena; slažem se da rješavanje kroz
   `[build-system]` ide u `DENT-IMPROVE-009` (paketizacija), ne ovdje.

## Probni signal — `.agent/` sloj (potvrđeno protiv Pi-jevog izvještaja)

Pi-jeva tvrdnja (11 fajlova, koristio `PROJECT_MAP.md`/`TASK_ROUTING.md`,
ciljano pojašnjenje strukture, ostao u scope-u) je konzistentna sa
stvarnim scope-om diffa koji sam nezavisno provjerio — implementacija
zaista ostaje strogo u `allowed_paths`. Ovo je prvi test na potpuno novom
tipu zadatka (CI/tooling) van dosadašnjih Bug/Feature/Review kategorija —
`.agent/TASK_ROUTING.md` nema namjenski paket za CI, pa je Pi primijenio
najbliži obrazac (tooling/config) umjesto lutanja — konzistentno sa
ranijim nalazima da sloj pomaže i kad tačan routing paket ne postoji, dok
je `PROJECT_MAP.md` "Run locally" sekcija dovoljna da odredi tačne
komande.

## Integration status

`REVIEWED → PASS_WITH_NOTES` — čeka Radovanov human approval, zatim merge
i post-merge integration gate na `main`. Pravi GitHub Actions status se
potvrđuje tek nakon push-a.

## Handoff

CILJ: Automatski pytest/ruff/mypy na GitHubu za svaki push/PR.

URAĐENO: PASS_WITH_NOTES — implementacija ispravna, u scope-u, lokalno
nezavisno reprodukovana. Nema blocking findings.

NE DIRATI: `pyproject.toml`, aplikativni kod — nisu dirani, van scope-a.

SLJEDEĆE: Radovanov human approval → merge → post-merge integration gate
na `main` → provjeriti prvi stvarni GitHub Actions run nakon push-a
(rezidualni rizik: apt paket lista za PySide6 headless). Odvojeno,
opciono: trivijalan doc-fix za README "Python 3.13+" kontradikciju
(OUT_OF_SCOPE_FINDING, nije dio ovog taska).
