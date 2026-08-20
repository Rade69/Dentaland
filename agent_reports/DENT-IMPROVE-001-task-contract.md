---
task_id: DENT-IMPROVE-001
risk: LOW
implementer: claude
reviewers: []
created_at: 2026-08-20
---

# DENT-IMPROVE-001 — Context Debt cleanup u `.agent/`

## Odstupanje od Uloge tabele

Po `docs/dentaland-agentski-razvoj.md` LOW-risk zadatke implementira
Crush/Pi, Claude je Reviewer. Ovdje Claude namjerno implementira sam:
zadatak čisti `.agent/CURRENT_STATE.md` i `.agent/TASK_ROUTING.md`, iste
fajlove koje je Claude izgradio i čiju je validacionu istoriju (probni
krugovi DENT-016–020) sam vodio kroz cijelu sesiju — najbolji dostupan
kontekst o tome šta je aktivno pravilo naspram jednokratnog nalaza.
Radovan je ovo eksplicitno potvrdio ("kreni").

## Izvor

`docs/DENTALAND_IMPROVEMENT_BACKLOG.md`, sekcija 2 (Codex-ova analiza).

## Cilj

Ukloniti kontradiktorne/zastarjele statuse i istorijski balast iz
navigacionih fajlova koje svaki agent čita na početku svakog zadatka, bez
gubitka trajno relevantnog pravila ili istorijske validacije.

## Scope

**Allowed paths:** `.agent/CURRENT_STATE.md`, `.agent/TASK_ROUTING.md`,
`agent_reports/`

**Forbidden paths:** `src/`, `desktop/`, `backend/`, `web/`, `migrations/`,
`tests/`

## Fact found

`.agent/CURRENT_STATE.md` ima internu kontradikciju: sekcija "Current
verification baseline" (linije 30–45) navodi izmjereno 2026-08-19 stanje
(pytest 206 passed, mypy 29 fajlova), dok sekcija "Next known work" (linije
76–80), pisana kasnije istog fajla, navodi drugačije brojeve (pytest 222
passed, mypy 31 fajlova, 0 grešaka) bez konteksta datuma mjerenja. Svježe
mjerenje upravo izvršeno u ovom worktree-u (granat od `main`) potvrđuje:
`pytest tests/ -q` → 222 passed, 11 warnings; `ruff check` → All checks
passed; `mypy` → Success, no issues in 31 source files. Broj iz "Next known
work" je tačan trenutni broj; broj iz "Current verification baseline" je
zastario (potiče od prije DENT-020 merge-a).

`.agent/TASK_ROUTING.md` sadrži sekciju "Validacija — da li ovaj sloj
stvarno pomaže" (linije 140–219, ~80 od 219 linija fajla) sa probnom
tabelom (8 redova, svi probni krugovi DENT-016–020 + review krugovi) i tri
"Nalaz" pasusa + finalni "Ukupan zaključak". Ovo je eksperimentalni dnevnik
validacije, ne aktivno routing pravilo — u skladu sa acceptance kriterijem
backloga treba ga premjestiti u zaseban `agent_report`.

## Required changes

- `.agent/CURRENT_STATE.md`: zadržati samo trenutni aktivni fokus, trenutno
  raspoložive agente, jedan nekontradiktoran svjež verification baseline,
  aktivna ograničenja, sljedeći prioritet. Ukloniti "Recently completed
  major work" istoriju (već postoji u pojedinačnim `agent_reports/`
  fajlovima za svaki navedeni task).
- `.agent/TASK_ROUTING.md`: ukloniti cijelu "Validacija" sekciju, premjestiti
  je doslovno (bez parafraziranja) u novi
  `agent_reports/2026-08-20-DENT-AGENT-CONTEXT-validacija-istorija.md`.
  Zadržati samo aktivne routing pakete (Bug, Feature, Desktop GUI,
  Booking/service, Schema/migration, Public web/API, Review).

## Acceptance criteria

- `CURRENT_STATE.md` nema kontradiktorne aktivne statuse.
- `TASK_ROUTING.md` sadrži routing pravila, ne eksperimentalni dnevnik.
- Nijedno važno aktivno pravilo nije izgubljeno.
- Istorijska validacija ostaje sačuvana u `agent_reports/`.
- Svi linkovi iz `AGENTS.md`/`CLAUDE.md` ostaju validni (ne diraju se ciljevi
  ovog zadatka, samo provjera da referentni fajlovi i dalje postoje).

## Verification plan

`git diff --check`; ručna provjera da premješteni tekst u novom
agent_report-u odgovara riječ-za-riječ originalu (word-level diff);
potvrda da svaka putanja referencirana iz `AGENTS.md`/`CLAUDE.md`/
`PROJECT_MAP.md` i dalje postoji.

## Šta je urađeno

- `.agent/CURRENT_STATE.md`: uklonjena kontradikcija (svjež baseline
  izmjeren 2026-08-20: pytest 222 passed, ruff čisto, mypy 0 grešaka u 31
  fajlu — zamijenio zastarjeli 206/29 unos). Uklonjena sekcija "Recently
  completed major work" (4 stavke — svaka već ima svoj `agent_report`).
  Fajl smanjen sa 81 na 47 linija.
- `.agent/TASK_ROUTING.md`: uklonjena sekcija "Validacija — da li ovaj sloj
  stvarno pomaže" (80 linija, probna tabela + 5 "Nalaz"/"Zaključak"
  pasusa), zamijenjena kratkim sažetkom sa linkom na novi report. Fajl
  smanjen sa 219 na 145 linija. Aktivni routing paketi (Bug, Feature,
  Desktop GUI, Booking/service, Schema/migration, Public web/API, Review)
  netaknuti.
- Novi fajl `agent_reports/2026-08-20-DENT-AGENT-CONTEXT-validacija-istorija.md`
  — doslovan (word-for-word) prijenos uklonjene validacione sekcije.

## Verifikacija

```text
pytest tests/ -q
→ 222 passed, 11 warnings, exit 0

ruff check src/dentaland desktop backend tests
→ All checks passed, exit 0

mypy src/dentaland desktop backend
→ Success: no issues found in 31 source files, exit 0

git diff --check
→ prazan izlaz (PASS), exit 0
```

Word-level diff (Python `difflib.SequenceMatcher`) između uklonjene
sekcije u `main`-ovoj verziji `TASK_ROUTING.md` i nove sekcije u
`agent_reports/2026-08-20-DENT-AGENT-CONTEXT-validacija-istorija.md`:
**ratio 1.0** (identičan sadržaj, bez gubitka ili parafraziranja).

Provjera referenciranih putanja: svih 24 taska navedena u premještenoj
tabeli/istoriji imaju odgovarajuće `agent_reports/` fajlove (potvrđeno
`ls` pretragom po `DENT-016`–`020`, `DESKTOP-F`, `AGENT-CONTEXT-002`).
Fajl `agent_reports/2026-08-19-DENT-AGENT-CONTEXT-001-faza1-agent-mapa.md`,
referenciran unutar premještenog teksta, postoji. `AGENTS.md`/`CLAUDE.md`/
`PROJECT_MAP.md` nisu mijenjani u ovom zadatku — reference unutar njih na
`.agent/CURRENT_STATE.md` i `.agent/TASK_ROUTING.md` ostaju validne (samo
sadržaj tih fajlova je promijenjen, ne putanje/nazivi).

## Odbačene opcije

- Brisanje validacione istorije bez premještanja — odbačeno, backlog
  acceptance kriterij eksplicitno traži "Istorijska validacija ostaje
  sačuvana u `agent_reports/`".
- Parafraziranje/skraćivanje validacione istorije pri premještanju —
  odbačeno; ranija Faza 2 review iskustva (Codex Round 1) pokazala da
  parafraziranje pri konsolidaciji gubi sadržaj bez namjere. Doslovan
  prijenos + word-diff provjera je pouzdaniji.

## Integration status

`NOT_MERGED` — implementacija završena, čeka Radovanov human approval
(LOW risk, ali dira ključne navigacione fajlove; konzervativan pristup u
skladu sa obrascem rada u ovoj sesiji).

## Handoff

CILJ: Ukloniti kontradiktorne/zastarjele statuse i istorijski balast iz
`.agent/CURRENT_STATE.md` i `.agent/TASK_ROUTING.md` bez gubitka trajno
relevantnog pravila ili istorijske validacije.

URAĐENO: Oba fajla očišćena (CURRENT_STATE 81→47 linija, TASK_ROUTING
219→145 linija), validaciona istorija doslovno premještena u novi
agent_report, svi acceptance kriteriji zadovoljeni i verifikovani.

NE DIRATI: `src/`, `desktop/`, `backend/`, `web/`, `migrations/`, `tests/`
— nisu dirani, van scope-a ovog zadatka.

SLJEDEĆE: Radovanov review/merge; nakon toga taskovi
`DENT-IMPROVE-002`/`003`/`006` iz `docs/DENTALAND_IMPROVEMENT_BACKLOG.md`.
