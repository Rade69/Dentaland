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
| DENT-016 (štampa, ispalo: već gotov) | crush | 2 (samo da nađe `.agent/`, pa odustao) | DA, ali ručnim lutanjem (3 dodatna poziva) — nije u `main` | NE (sam pronašao) | NE |
| DENT-017 (email podsjetnik) | pi | 5 | DA — direktno uputio na tačnu sekciju, bez `ls`/`find` | NE | NE |
| DENT-016/017 review | claude | 2 review-a, sve gore navedeno + nezavisna reprodukcija testova/tvrdnji | DA (Reviewer Context Pack, TASK_ROUTING "Review task" sekcija) | NE | NE |
| DENT-018 (mypy cleanup week_view) | crush | 5 | DA — direktno iz `main`, "Bug task" paket → `week_view.py` + GUI testovi, bez `ls`/`find` | NE | NE |
| DENT-019 (mypy cleanup main_window) | pi | 4 | DA — direktno iz `main`, nula `ls`/`find` poziva | NE | NE |
| DENT-018/019 review (drugi krug) | claude | 2 review-a, nezavisna reprodukcija svih tvrdnji (uklj. `store: Any` opravdanje provjereno protiv `day_view.py`) | DA | NE | NE |
| DENT-AGENT-CONTEXT-002 review (Faza 2, treći krug — Codex) | codex | 3 review runde, 4/3/3 fajla prije svake (skill + CLAUDE.md + task izvještaji) | **NE** — eksplicitno priznao da nije koristio "Review task" sekciju ni u jednom krugu (paket redundantan uz vrlo detaljan task brief prompt) | NE | NE |

Referentna vrijednost (before, bez `.agent/` sloja, izmjereno
2026-08-19 pri pisanju `PROJECT_MAP.md` od nule): **6 istraživačkih
poziva** (`ls`/`find` po repou) prije nego što je struktura bila jasna, uz
jednu grešku usput (plitka pretraga je propustila `desktop/views/dialogs/`).
Cilj: manje od toga, bez pitanja "gdje je X", bez scope grešaka.

**Nalaz nakon 3 popunjena reda (2026-08-19):** ideja radi kad je sloj
dostupan — Pi je otišao PRAVO na tačnu sekciju (0 istraživačkih poziva,
nasuprot 6 u before baseline-u). Ali ISPORUKA je bila loša: `.agent/` sloj
nikad nije bio merge-ovan u `main` prije nego što su probni taskovi
dodijeljeni (`git worktree add ... main` ne nosi granu
`task/DENT-AGENT-CONTEXT-001`) — oba agenta su morala ručno tražiti drugi
worktree da bi uopšte došla do fajlova, tačno onaj "lutati po repou" trošak
koji sloj treba da eliminiše. Dodatno, DENT-016 se ispostavio već završen
prije dodjele (moja greška u pripremi, ne u konceptu sloja). Zaključak:
koncept POTVRĐEN, potreban je merge u `main` prije sljedeće probe da se
mjeri stvarna korist bez ovog proceduralnog šuma.

**Nalaz nakon drugog kruga (2026-08-19, `.agent/` sada merge-ovan u
`main`):** bez proceduralnog šuma iz prvog kruga, oba agenta (Crush,
Pi) su prijavila **nula `ls`/`find` istraživačkih poziva** — "Bug task"
routing paket ih je odveo direktno na ciljni fajl. Naspram before
baseline-a od 6 istraživačkih poziva, ovo je izmjeren, ponovljiv rezultat
u dva nezavisna slučaja, ne jednokratna slučajnost. Nijedno pitanje za
pojašnjenje strukture, nijedan scope prekršaj, u ukupno 5 taskova (2
implementaciona + 1 probni + 2 bug-fix) kroz dva različita tipa zadatka
(feature, bug) i dva različita implementera.

**Zaključak nakon Faze 1 (drugi krug):** `.agent/` sloj ima smisla za
implementacione zadatke. Faza 1 se smatra validiranom.

**Nalaz iz Faze 2 review-a (Codex, treći krug, 2026-08-20) — djelimično
negativan, ne skriven:** za review-tip zadatke sa VEĆ detaljnim task brief
promptom, "Review task" routing paket nije korišten ni u jednom od tri
kruga — reviewer ga je smatrao redundantnim jer je prompt sam isporučio
sve što bi paket dao (tačan worktree/commit/fajlovi/komande). Nije
dokazano da paket ŠTETI ili da NIKAD ne pomaže — dokazano je da postojanje
fajla nije garancija upotrebe kad je alternativni izvor (precizan prompt)
već dovoljan. Reviewer-ov predlog: obavezna eksplicitna referenca u
handoff-u/root start sekvenci bi bila pouzdanija za mjerenje stvarne
upotrebe nego pretpostavka da će agent sam routing fajl potražiti.

**Ukupan zaključak (4 signala, 2 tipa zadatka, 3 agenta):** `.agent/` sloj
mjerljivo pomaže kad task brief NE navodi eksplicitno šta čitati (Crush/Pi
implementacioni krugovi — 0 istraživačkih poziva naspram 6 baseline).
Kad je task brief već precizan (Codex review krugovi), routing paket
postaje redundantan, ne štetan — signal je o UPOTREBI, ne o vrijednosti
sadržaja paketa samog. Otvoreno za Fazu 2 (sad u toku,
`DENT-AGENT-CONTEXT-002`) uz ovu napomenu za budući rad: ako se želi
izmjeriti stvarna upotreba routing paketa u review kontekstu, task brief
promptovi ne bi trebali sami navoditi sve što bi paket dao.
