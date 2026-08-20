---
task_id: DENT-IMPROVE-002
risk: LOW
implementer: pi
reviewers: [claude]
status: IMPLEMENTATION_COMPLETE
created_at: 2026-08-20
---

# DENT-IMPROVE-002 — GitHub Actions CI

## Probni signal — `.agent/` navigacioni sloj (zabilježeno prije prve izmjene koda)

- **Fajlova pročitanih prije 1. izmjene koda: 11** read pozivom:
  `CLAUDE.md`, `.agent/PROJECT_MAP.md`, `.agent/TASK_ROUTING.md`,
  `agent_reports/DENT-IMPROVE-002-task-contract.md`, `pyproject.toml`,
  `README.md`, `docs/DENTALAND_IMPROVEMENT_BACKLOG.md`,
  `docs/dentaland-agentski-razvoj.md`, `tests/test_gui/conftest.py`,
  `agent_reports/README.md`, `agent_reports/2026-08-20-DENT-020-codex.md`
  (posljednji samo kao format-primjer implementer reporta). Dodatno,
  `AGENTS.md` je stigao kroz project context (system prompt), ne kao read.
- Koristio `.agent/PROJECT_MAP.md`: **DA** — Entry points / Agent workflow
  sekcije su odmah pokazale gdje je pyproject/README i gdje žive CI-vezane
  konvencije; "Run locally" je potvrdila tačne `pytest`/`ruff`/`mypy`
  komande koje workflow treba da reprodukuje.
- Koristio `.agent/TASK_ROUTING.md`: **DA** — zadatak je novi tip
  (CI/tooling), za koji routing nema namjenski paket, pa sam primijenio
  najbliži obrazac (tooling/config → pyproject + README + backlog), bez
  ulaska u `src/`/`desktop/`/`backend/`/`web/`/`migrations/`.
- Tražio dodatno pojašnjenje strukture: **DA, ciljano** — provjerio sam
  `git worktree list`, postojanje `setup.py`/`setup.cfg`/`[build-system]`
  (da odredim kako instalirati zavisnosti u CI bez diranja
  `pyproject.toml`), Qt/offscreen setup u `tests/test_gui/conftest.py`, i
  layout testova. Nije bilo repo-wide `ls`/`find` lutanja.
- Ostao u `allowed_paths`: **DA** — planirane izmjene su isključivo
  `.github/workflows/ci.yml` (novi fajl) i `README.md`; `pyproject.toml`
  nije dirnut (vidi "Tehničke odluke").

## Task Contract

Izvor: `agent_reports/DENT-IMPROVE-002-task-contract.md` (puni detalj u
`docs/DENTALAND_IMPROVEMENT_BACKLOG.md`, sekcija 3).

Cilj: automatski pokretati `pytest`, `ruff` i `mypy` na GitHubu za svaki
push/PR — trenutno te provjere postoje samo lokalno. LOW risk; jedan
nezavisan reviewer (Claude).

**Allowed paths:** `.github/workflows/`, `README.md` (i `pyproject.toml`
samo ako je nužno, uz eksplicitno obrazloženje).

**Forbidden paths:** `src/`, `desktop/`, `backend/`, `web/`, `migrations/`.

## Scope

- `.github/workflows/ci.yml` — novi workflow: checkout → setup-python →
  install dependencies → pytest → ruff → mypy.
- `README.md` — kratka napomena o CI.

Van scope-a i netaknuto: `pyproject.toml`, sav aplikativni kod
(`src/`/`desktop/`/`backend/`/`web/`/`migrations/`).

## Šta je urađeno

- Workflow se pokreće na `push` i `pull_request` (bez filtera grana).
- Jedan job na `ubuntu-latest`, jedan Python (bez matrixa, bez Dockera,
  bez coverage gate-a, bez složenog cachinga) — po constraint iz backloga.
- Koraci redom: `actions/checkout@v4`, `actions/setup-python@v5`
  (Python 3.12), sistemske Qt zavisnosti (za headless/offscreen PySide6),
  pip install zavisnosti, `pytest tests/ -q`,
  `ruff check src/dentaland desktop backend tests`,
  `mypy src/dentaland desktop backend` — iste komande kao u README-u.
- README dobija kratku sekciju "CI (GitHub Actions)".

## Tehničke odluke

### Python 3.12, ne 3.13+

`pyproject.toml` je izvor istine za tooling: `requires-python = ">=3.12"`,
`ruff target-version = "py312"`, `mypy python_version = "3.12"`. To je
projektni standard, pa CI koristi `python-version: "3.12"`. README kaže
"Python 3.13+", ali to je u neskladu sa `pyproject.toml` i tretirao sam
ga kao zastarjelu napomenu (3.12 je najniža deklarisana podržana verzija
i ujedno tooling target; ako CI prođe na 3.12, prođe i na novijim).

### Zavisnosti se instaliraju direktno, `pyproject.toml` se ne dira

Projekat nema `setup.py`/`setup.cfg` ni `[build-system]` u `pyproject.toml`,
pa `pip install -e ".[dev]"` trenutno ne može raditi bez izmjene
`pyproject.toml` (dodavanje `[build-system]` + `[tool.setuptools.packages.find]`).
Pošto backlog dozvoljava `pyproject.toml` "samo ako je nužno", a nužno nije
(CI može instalirati zavisnosti direktno), workflow navodi istu listu
zavisnosti kao `pyproject.toml` (`dependencies` + `dev`). Ovo je svjesni
trade-off: jedan spisak se duplira, ali se build konfiguracija projekta ne
mijenja u LOW-risk CI zadatku. Zabilježeno kao mogući kasniji follow-up
(centralizovati instalaciju kroz `[build-system]` kad se bude dirala
paketizacija, npr. DENT-IMPROVE-009).

### Sistemske Qt zavisnosti

`tests/test_gui/conftest.py` već postavlja `QT_QPA_PLATFORM=offscreen`, pa
nije potreban xvfb/display. PySide6 offscreen na `ubuntu-latest` ipak traži
par sistemskih biblioteka (`libegl1`, `libgl1`, `libxkbcommon0`,
`libxkbcommon-x11-0`, `libxcb-cursor0`, `libdbus-1-3`) — instaliraju se
apt-get korakom prije pip koraka. Ovo je dio "install dependencies", ne
scope expansion.

## Verifikacija (rezultati)

```text
git diff --check
→ PASS, exit 0

YAML parse (.github/workflows/ci.yml)
→ validan; 1 job (test), 7 koraka, env QT_QPA_PLATFORM=offscreen

ruff check src/dentaland desktop backend tests
→ All checks passed, exit 0

mypy src/dentaland desktop backend
→ Success: no issues found in 31 source files, exit 0

pytest tests/ -q
→ 222 passed, 11 warnings, exit 0
```

Warnings su postojeći dependency deprecation warning-i (FastAPI/alembic
sloj), ne vezani za ovaj task. Napomena: `pytest`/`ruff`/`mypy` su
pokrenuti nad nepromijenjenim aplikativnim kodom (diff dira samo
`.github/workflows/ci.yml`, `README.md` i ovaj report) — potvrđuju da
baseline i dalje prolazi i da nije dirnut nijedan `forbidden_path`.

Pravi GitHub Actions run nije moguće pokrenuti iz ovog okruženja (nema
push-a na remote) — potvrđuje se tek nakon merge-a. To je očekivano za
ovaj tip zadatka; lokalne komande koje workflow reprodukuje prolaze.

## Review

`PENDING` — implementer nije reviewer. Potreban je nezavisan Claude review
sa fokusom na scope (allowed/forbidden paths), acceptance kriterijume i
ispravnost workflow koraka.

## Integration status

`NOT_MERGED` — čeka nezavisan review.

## Handoff

CILJ: automatski pytest/ruff/mypy na GitHubu za svaki push/PR.

URAĐENO: workflow fajl + README napomena; nijedan aplikativni fajl nije
dirnut.

SLJEDEĆE: Claude radi nezavisan LOW-risk review; nakon PASS-a Radovanov
human approval, pa merge. Pravi CI run se vidi tek nakon push-a na GitHub.
