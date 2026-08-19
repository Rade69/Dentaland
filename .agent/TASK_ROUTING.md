# Task Routing

Za dati tip zadatka — šta tačno učitati, i šta NE učitati po defaultu. Cilj:
manje lutanja, manje nepotrebnog čitanja cijelog repoa.

Globalni skillovi `prime-bug`, `prime-feature`, `independent-review` (žive u
`~/.claude/skills/`, ne u ovom repou) se aktiviraju automatski po tipu
zadatka — ako već rade dobro, ne pravi repo-local duplikat. Ovaj fajl im
daje Dentaland-specifičan "routing paket" (koje fajlove/testove/dokumente da
učitaju za OVAJ repo), ne zamjenjuje njihovu metodu.

## Bug task

Aktiviraj skill `prime-bug` (reprodukcija prije popravke).

Dentaland routing paket:
1. `AGENTS.md`
2. `CLAUDE.md`
3. `.agent/PROJECT_MAP.md` — pronađi domenu kojoj bug pripada
4. `.agent/CURRENT_STATE.md` — provjeri da nije već poznat/aktivan problem
5. konkretan Task Contract (ako postoji za taj bug)
6. samo fajl(ove) direktno povezan(e) sa simptomom
7. najbliži test fajl

NE učitavaj po defaultu cijeli `docs/`, nepovezane domene, cijelu istoriju
`agent_reports/`.

## Feature task

Aktiviraj skill `prime-feature` (obim prije koda).

Dentaland routing paket zavisi od domene — vidi sekcije ispod za tačan
read-set po domeni (Desktop GUI / Booking-service / Public web-API /
Schema-migration).

## Desktop GUI task

Za task koji dira:

```text
desktop/views/
desktop/print_document.py
tests/test_gui/
```

učitaj:

1. `AGENTS.md`
2. `CLAUDE.md`
3. `.agent/PROJECT_MAP.md`
4. `.agent/CURRENT_STATE.md`
5. konkretni Task Contract
6. samo relevantne `desktop/` fajlove (vidi `PROJECT_MAP.md` "Desktop
   scheduler" sekciju za tačnu listu — npr. akcija nad postojećim terminom
   ide kroz `desktop/views/dialogs/`, ne `appointment_dialog.py`, koji je
   samo za kreiranje novog termina)
7. samo relevantne GUI testove iz `tests/test_gui/`
8. design doc (`docs/istrazivanje-dentalni-scheduler-gui.md`,
   `docs/redizajn/`) SAMO ako task zavisi od dizajn odluke

NE učitavaj po defaultu: `docs/dentaland-razvojni-plan-v3.1.md` u cjelini,
`migrations/`, `backend/`, `web/`, cijeli `agent_reports/`.

## Booking / service task

Ako task dira:

```text
src/dentaland/services/booking.py
```

učitaj:

1. `.agent/PROJECT_MAP.md`
2. konkretan Task Contract
3. `booking.py`
4. `models.py` ako je potreban model/relationship kontekst
5. `tests/test_services.py`
6. `tests/test_models.py` kad je schema/status semantika relevantna
7. relevantnu sekciju `docs/dentaland-razvojni-plan-v3.1.md` SAMO ako task
   to zahtijeva

Ne čitaj cijeli desktop GUI ako se GUI ne mijenja.

## Schema / migration task — HIGH risk

Učitaj (ovdje je širi kontekst opravdan — ne primjenjivati LEAN pristup na
task čija sigurnost zavisi od šire schema slike):

1. Task Contract
2. `.agent/PROJECT_MAP.md`
3. `.agent/CURRENT_STATE.md`
4. relevantne schema/security sekcije `docs/dentaland-razvojni-plan-v3.1.md`
5. `src/dentaland/models.py`
6. relevantne fajlove u `migrations/`
7. `tests/test_models.py`
8. relevantne service testove
9. HIGH-risk proceduru iz `docs/dentaland-agentski-razvoj.md`

## Public web / API task

Za:

```text
web/
backend/main.py
src/dentaland/services/requests.py
```

učitaj:

1. `.agent/PROJECT_MAP.md`
2. Task Contract
3. `docs/dentaland-javna-forma-spec.md` kad je relevantan UX/API contract
4. `web/app.js` / `index.html` / stylovi — samo prema tasku
5. `backend/main.py` ako se API contract dira
6. `requests.py` ako se booking request semantika dira
7. `tests/test_backend.py` / `tests/test_requests.py` / relevantni fajlovi
   u `web/tests/` (statični HTML preview, ručna vizuelna provjera)

## Review task

Reviewer NE dobija cijeli repo ni cijelu implementer sesiju.

Aktiviraj skill `independent-review` — čita Dentaland-ov postojeći
`verdict`/`blocking_findings` format (vidi `docs/dentaland-agentski-razvoj.md`,
sekcija "Strukturiran verdikt") i koristi TAJ format, ne generički PASS/FAIL.

Dentaland Reviewer Context Pack (šta reviewer dobija):

1. Task Contract
2. `git diff` + lista dirnutih fajlova
3. rezultat verifikacije (testovi, linter)
4. relevantnu `.agent/PROJECT_MAP.md` sekciju
5. relevantno arhitektonsko/sigurnosno pravilo
6. impact analizu za MEDIUM/HIGH zadatke

Ne pravi drugi paralelni review sistem pored postojećeg.

## Validacija — da li ovaj sloj stvarno pomaže

Dok se ne potvrdi kroz par stvarnih taskova (vidi Fazu 1 report,
`agent_reports/2026-08-19-DENT-AGENT-CONTEXT-001-faza1-agent-mapa.md`),
svaki agent koji dobije task PRIJE prve izmjene koda kratko zapiše u svoj
`agent_report` (par redova, ne poseban dokument):

| Task | Implementer | Fajlova pročitano prije 1. izmjene | Koristio `.agent/`? | Pitao za pojašnjenje strukture? | Prekršio scope? |
|---|---|---|---|---|---|
| _(popuniti po tasku)_ | | | DA / NE | DA / NE | DA / NE |

Referentna vrijednost (before, bez `.agent/` sloja, izmjereno
2026-08-19 pri pisanju `PROJECT_MAP.md` od nule): **6 istraživačkih
poziva** (`ls`/`find` po repou) prije nego što je struktura bila jasna, uz
jednu grešku usput (plitka pretraga je propustila `desktop/views/dialogs/`).
Cilj: manje od toga, bez pitanja "gdje je X", bez scope grešaka.

Kad se saberu 2-3 popunjena reda, ovu tabelu pregledati i odlučiti da li
`.agent/` sloj ima smisla prije nego što se ide na Fazu 2 (konsolidacija
`docs/dentaland-agentski-razvoj.md` + stanjenje `CLAUDE.md`/`AGENTS.md`).
