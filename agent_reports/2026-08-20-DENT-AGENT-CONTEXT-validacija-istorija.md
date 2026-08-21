---
task_id: DENT-AGENT-CONTEXT-validacija
risk: LOW
implementer: claude
reviewers: []
created_at: 2026-08-20
---

# Validacija `.agent/` navigacionog sloja — istorija probnih krugova

Premješteno doslovno (word-for-word) iz `.agent/TASK_ROUTING.md`, sekcija
"Validacija — da li ovaj sloj stvarno pomaže", kao dio `DENT-IMPROVE-001`
(Context Debt cleanup). Ovo je eksperimentalni dnevnik, ne aktivno routing
pravilo — zadržan ovdje radi istorijske evidencije, ne briše se.

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
| DENT-020 (email reminder scheduler, Codex prvi implementacioni test) | codex | 15 (13 projektnih + 2 globalna skilla; 1 ciljani `rg` inventory, bez `ls`/`find` repo-wide) | **DA** — PROJECT_MAP "Notifications" sekcija direktno pokazala servis+test, TASK_ROUTING "feature/service" routing spriječio desktop/web/docs lutanje | NE | NE |
| DENT-020 review | claude | 1 review, nezavisna reprodukcija svih tvrdnji (uklj. detached-session teoriju testiranu protiv stvarnog testa) | DA | NE | NE |

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

**Ukupan zaključak (6 signala, implementacija + review, 3 agenta):**
`.agent/` sloj mjerljivo pomaže kad task brief NE navodi eksplicitno šta
čitati — potvrđeno kod SVA TRI agenta na implementacionim zadacima
(Crush, Pi, i sada Codex/DENT-020), ne samo kod Crush/Pi. Ovo razrješava
neizvjesnost nakon Codex review krugova: nije "Codex specifično
ignoriše sloj" (hipoteza koja bi značila da je sloj beskoristan za njega)
— kad je Codex Implementer sa kratkim promptom, koristio je `.agent/`
sloj i eksplicitno rekao da mu je pomogao odrediti "šta prvo otvoriti".
Pravi razlog za redundantnost u review krugovima bio je MOJ stil pisanja
task brief-a (previše detaljan), ne tip zadatka niti agent.

**Zaključak:** koncept je potvrđen preko implementacija (LOW istraživačkih
poziva naspram 6 baseline, ponovljeno 3x, 3 agenta). Praktična pouka za
budući rad: kad se piše task brief, NE navoditi unaprijed tačne
fajlove/putanje ako je cilj da agent stvarno koristi routing sloj —
navesti samo cilj i uputiti na `.agent/TASK_ROUTING.md`, ostaviti agentu
da sam odredi put. Faza 2 (`DENT-AGENT-CONTEXT-002`) je mergovana na
osnovu ovog i ranijih nalaza.

## Nastavak validacije — DENT-IMPROVE-002 do 006 (2026-08-20/21)

Nakon Faze 1/2 zaključka, praksa "lean" task brief-a (cilj + uputa na
`.agent/TASK_ROUTING.md`, bez unaprijed navedenih tačnih fajlova) je
primijenjena dosljedno na svih pet backlog taskova, uklj. dva nova tipa
zadatka (CI/tooling, desktop path/infrastructure) i jedan refaktor
zadatak sa dijeljenom logikom:

| Task | Implementer | Tip zadatka (nov?) | Fajlova prije 1. izmjene | Koristio `.agent/`? | Scope prekršaj? |
|---|---|---|---|---|---|
| DENT-IMPROVE-002 (CI) | pi | CI/tooling (NOV) | 11 | DA — nema namjenskog paketa, primijenio najbliži obrazac | NE |
| DENT-IMPROVE-003 (paths) | pi | desktop path/infra (NOV) | 10 | DA — Entry points + Desktop scheduler sekcije | NE |
| DENT-IMPROVE-004 (blockout) | pi | feature (servis+GUI) | 11 | DA — kombinovao Booking + Desktop GUI pakete | NE |
| DENT-IMPROVE-005 (postavke) | crush | feature (servis+GUI) | 6 | DA — isti paketi, najmanji broj fajlova dosad | NE |
| DENT-IMPROVE-006 (zahtjevi) | codex | feature + refaktor dijeljene logike | 18 | DA — najveći broj fajlova, ali odgovara stvarnoj složenosti (refaktor zahtijeva razumijevanje dva postojeća toka) | NE |

Svih 5 taskova: nula scope prekršaja, nula pitanja za pojašnjenje
strukture (Codex je "tražio pojašnjenje" u smislu ciljanog `git
diff`/postojeće pokriće provjere, ne strukturnog pitanja Radovanu).

**Nalaz:** koncept se potvrđuje i na tipovima zadataka koji nisu bili
testirani u Fazi 1/2 (CI, path/infrastructure, refaktor dijeljene
logike) — `.agent/` sloj daje koristan polazni obrazac čak i kad
`TASK_ROUTING.md` nema namjenski paket za taj tačan tip (implementer
sam generalizuje najbliži postojeći paket, umjesto `ls`/`find`
istraživanja). Broj pročitanih fajlova prirodno raste sa stvarnom
složenošću zadatka (6 za samostalan CRUD feature, 18 za refaktor koji
dira dijeljenu logiku dva ekrana) — to je očekivano i ne ukazuje na
lutanje, jer je scope u svih pet slučajeva ostao čist.

**Specifično za Codex (DENT-IMPROVE-006):** ovo je drugi Codex
implementacioni probni signal (nakon `DENT-020`), sada na zadatku van
njegove ranije privremene "odstupanje od uloge" situacije — ovo je
njegova redovna LOW/MEDIUM implementer uloga. Signal je konzistentan sa
`DENT-020`: kratak, lean task brief → Codex koristi `.agent/` sloj bez
poziva da mu se to eksplicitno kaže.
