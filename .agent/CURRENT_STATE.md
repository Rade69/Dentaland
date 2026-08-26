# Current State

Last updated: 2026-08-25

Ovaj fajl drži KRATKOTRAJNE informacije — stvari koje realno mogu zastarjeti
za nekoliko dana/sedmica. Trajna pravila ostaju u `CLAUDE.md`/`AGENTS.md`/
`docs/dentaland-agentski-razvoj.md`. Ako nešto ovdje piše starije od par
sedmica, provjeriti da li je i dalje tačno prije oslanjanja na njega.

Stariji istorijski detalji (korektivni paket FIX-01..09, DENT-021, Prioritet
A/B backloga, DENT-022/023 email-audit) su uklonjeni odavde 25.8.2026 —
svi su DONE, trajno zabilježeni u git log-u i `agent_reports/` po task ID-u,
i nisu operativno relevantni za trenutni rad.

## Current development focus

**View/Controller/Services arhitektonski refaktor je KOMPLETAN na nivou
pojedinačnih taskova** — `docs/DENTALAND_VIEW_CONTROLLER_SERVICES_REFACTOR_PLAN.md`,
REF-00 do REF-08, svi MERGED. Implementeri Pi i Crush naizmjenično, oba
reviewera (Codex i Claude) obavezna na svaki task, human approval prije
svakog merge-a.

| Task | Šta | Merge |
|---|---|---|
| REF-00 | Characterization testovi (sigurnosna mreža) | `ce8d65a` |
| REF-01 | Availability/overlap invarijanta centralizovana | `fa53340` |
| REF-02 | Range-based reads + eager loading | `d4b09e7` |
| REF-03 | Razbijen `booking.py` monolit | `a02f31f` |
| REF-04 | `AppointmentController` (prvi task u `desktop/`) | `3e0a0c2` |
| REF-05 | `ScheduleController` + refresh orchestration | `a422c40` |
| REF-06 | Shared presentation logika (WeekView/DayView) | `858b836` |
| REF-07 | `RequestController`/`PrintController` | `f541e0a` |
| REF-08 | Theme/QSS + timezone konsolidacija (zadnji task) | `ce2d270` |

Post-merge integration gate na `main` nakon REF-08: **355 pytest passed**,
ruff/mypy čisti, 50 source fajlova (vidi "Current verification baseline").

**Vrijedni procesni presedani iz paketa (za buduće slične situacije):**
- **REF-03**: arhitektonski test je prošao TRI Codex REJECT runde — kad je
  Radovan naredio da Codex sam završi fix, Codex više nije bio nezavisan
  reviewer za taj dio; **Pi je preuzet kao FRESH Reviewer 1** (ne čita
  prethodno rezonovanje prije sopstvene provjere). Pouka: kontaminiran
  reviewer se zamjenjuje fresh reviewerom, review se ne preskače.
- **REF-02, REF-05**: Codex REJECT→PASS ciklusi bili su o KVALITETU TESTOVA
  (lažan PASS na slabom fixture-u/fake objektu), ne o arhitekturi — implementer
  je popravio test, ne produkcijski kod.
- **REF-01**: uvijek provjeriti da je zavisni task STVARNO mergovan u `main`
  prije početka rada, ne samo da postoji kao grana.
- **REF-06+REF-07**: prvi PARALELAN par REF taskova (Pi i Crush istovremeno,
  bez ukrštenih zavisnosti/fajlova, `coordination.py claim` bez konflikta) —
  dokazuje da paralelni rad ima smisla kad se to eksplicitno provjeri prije
  starta, ne kao default pretpostavka.

**Otvoren, dokumentovan tehnički dug (NIJE riješen REF-08, ostaje za buduću
odluku):** Controller "gleda nazad" u View na tri mjesta — (1) REF-04
`AppointmentController` lazy-uvozi Dialog klase iz `main_window` modula
unutar metoda (zbog GUI test monkeypatch-timinga), (2) REF-04
`AppointmentController` čita `MainWindow` privatno stanje preko `getattr`,
(3) REF-05 `ScheduleController` drži svoju kopiju `_current_doctor_id` —
tri mjesta drže "isti" podatak, sinhronizovana kroz jednu disciplinovanu UI
putanju, nije bug sada, ali svaki budući način promjene doktora mora
ažurirati sve tri lokacije. **REF-07-ov `week_start_provider: Callable[[], date]`
DI je dokazan, čistiji model** za rješavanje istog problema — vrijedi kao
referenca za taj budući task.

Dodatni poznat, prijavljen dug: **9 nezavisnih `SARAJEVO = ZoneInfo(...)`
redefinicija** (servisni sloj: `notifications.py`, `print_schedule.py`;
6 dialog fajlova; `requests_page.py`) — REF-08 je konsolidovao samo 6
`fake_data`-uvezenih mjesta u `src/dentaland/timezone.py`, ovih 9 NIJE
dirano (namjerno, van scope-a). Kandidat za REF-09 ili poseban cleanup.

**F1-F4 PAKET ZATVOREN** (26.8.2026) — finalni acceptance review REF-00..08
(25.8.2026, Codex+Claude nezavisno) našao 4 nalaza (F1-F4) gdje View
poziva store mutaciju direktno, mimoilazeći Controller. Radovanova odluka:
nema prihvaćenog duga — svaki nalaz odmah postaje task. Svi zatvoreni:

| Task | Nalaz | Šta | Merge |
|---|---|---|---|
| REF-09 | F4 | Dashboard confirm/reject → privatna `AppointmentController` instanca u `DashboardPanels` | `115e86f` |
| REF-10 | F1 | Scheduler drag&drop → nova `AppointmentController.move_appointment_slot`, weakref fix za dijeljenu klasu | `bdca30d` |
| REF-11 | F2 | Nov `BlockoutController` (facade, self-contained u `BlockoutPanel`) | `a87d423` |
| REF-12 | F3 | Nov `SettingsController` (facade, self-contained u `SettingsPanel`) | `b5006c9` |
| REF-13 | — | Preostalih 9 `SARAJEVO` redefinicija → `dentaland.timezone` (REF-08 dug) | `383745d` |

**Potvrđeno deterministički**: `python scripts/agent_sensors.py --all` →
**0 blocking findings** na trenutnom `main` (prvi put da `ARCH-VIEW-001`
senzor iz DENT-IMPROVE-010 potvrđuje čisto stanje, ne samo ručni audit).

**Vrijedni procesni presedani iz ovog kruga:**
- **Paralelizacija dokazana dva puta**: REF-09+REF-11 (prvi krug), REF-10+REF-12
  (drugi krug) — nulto preklapanje `allowed_paths`, self-contained
  Controller-per-panel obrazac (REF-07 presedan) namjerno izabran da se
  izbjegne `main_window.py` kao usko grlo.
- **REF-09/REF-11 REJECT ciklusi** (test kvalitet — testovi provjeravali
  samo krajnje stanje, ne PUT kroz Controller) su naučili implementere da
  REF-12/kasniji taskovi pišu adversarne testove proaktivno — REF-12 je
  prošao Codex review na prvi pokušaj.
- **REF-10 integracijski REJECT** (F1) — dva paralelna taska (REF-10 i
  DENT-IMPROVE-010) su nezavisno razvijena i mergovana van redosleda, pa
  je senzor test iz jednog očekivao staro stanje koje je drugi upravo
  uklonio. Riješeno sekvencijalno (implementer merge-ovao svjež main,
  ažurirao test očekivanje) — pouka: kad dva paralelna taska mijenjaju
  ISTU test-datoteku iz različitih razloga (jedan je piše, drugi mijenja
  stanje koje ta datoteka provjerava), integracijski red je bitan čak i
  bez preklapanja `allowed_paths`.
- **Weakref fix u REF-10**: implementer je otkrio da kontraktov predloženi
  oblik (`AppointmentController` konstruisan sa `self` iz View-a) pravi
  referentni ciklus koji ruši PySide6/shiboken teardown — Claude je ovo
  lično nezavisno reprodukovao (privremeno vratio strong-ref, potvrdio
  isti crash) PRIJE nego što je fix commitovan. Vrijedi kao podsjetnik:
  Task Contract je pretpostavka, ne nepromjenjiv zakon — implementer smije
  odstupiti UZ `OUT_OF_SCOPE_FINDING` i nezavisnu potvrdu.

**REF-00..15 PAKET POTPUNO ZATVOREN** (26.8.2026) — Radovanova odluka
"nema prihvaćenog duga" je do kraja ispoštovana, uključujući nalaze
otkrivene USPUT tokom samog zatvaranja duga:

| Task | Šta | Merge |
|---|---|---|
| REF-14 | Doctor-state provider callable-ovi umjesto `getattr`-fishing (REF-04/05 dug). `ScheduleController._current_doctor_id` bio je mrtav kod (nikad se nije čitao) — uklonjen. | `32dafbd` |
| REF-15 | Preostala 4 inline `ZoneInfo("Europe/Sarajevo")` poziva → `dentaland.timezone` (REF-13 out-of-scope finding) | `32dafbd` |

**Codex REF-14 review:** precizna napomena da su default provideri
identični starom ponašanju samo po FALLBACK VRIJEDNOSTI, ne po
implicitnom ugovoru — to je namjera taska (uklanjanje implicitnog
Controller→View ugovora), ne slabost.

**Claude REF-14 review — konkretna arhitektonska istraga:** nove provider
lambda-e u `main_window.py` strukturno zatvaraju `self`, isti obrazac kao
referentni ciklus koji je REF-10 popravio weakref-om za `_parent_widget`.
Provjereno da NIJE nov rizik — `refresh_callback` je već (od REF-04)
prosljeđivan kao bound metoda koja isto zatvara `self`, za 2 od 4
potrošača, prije REF-14. 32 `test_main_window.py` testa
(construct+teardown) prolaze bez simptoma — REF-10-ov crash je
vjerovatno bio specifičan za scenario dvostruke-konstrukcije
(week_view+day_view zajedno u istom testu), ne generička prisutnost
ciklusa. Preporučena preventivna dokumentacija u
`AppointmentController` docstringu (nije još urađena — sitan follow-up
ako neko dira taj fajl, ne zaslužuje task).

**Preostalo, poznato, namjerno ne-dirano (nije "dug" po Radovanovoj
definiciji jer nema dokaza o stvarnom kvaru):**
- Kozmetički: `test_c_trenutni_main_samo_f1_ostaje` naziv zastario nakon
  REF-10 (Claude review napomena).
- Preventivna docstring napomena o refresh_callback/provider closure
  obrascu (Claude REF-14 review N1) — dokumentovano ovdje, nije još u
  kodu.

Nijedan od ova dva NIJE task-worthy — oba su "ako neko već dira taj
fajl", ne aktivan rizik.

REF-00..15 paket je funkcionalno kompletan i bez poznatog duga.

**Prioritet C napredak (26.8.2026):** `DENT-IMPROVE-010` (overlap logika)
i `DENT-IMPROVE-011` (Playwright E2E za javnu formu, merge `f9de00e`) su
DONE. `DENT-IMPROVE-011` je prošao Codex REJECT→PASS ciklus — F1 nije bio
test-kvalitet nego stvaran sigurnosni propust
(`reuseExistingServer: !process.env.CI` bi tiho reuse-ovao bilo koji
proces na portu 8000, rizikujući upis sintetskih E2E podataka u
stvarnu dev/produkcijsku bazu; Claude je LIČNO reprodukovao adversarni
scenario prije commit-a fixa, Codex nezavisno ponovio poslije). Novi
sitan nalaz (OUT_OF_SCOPE_FINDING, ne task još): generička "Failed to
fetch" poruka na backend-nedostupan scenario u `web/app.js` — kandidat
za budući mali DENT-IMPROVE.

## `DENT-IMPROVE-012` (SQLite→PostgreSQL) — U TOKU, BLOKIRANO (26.8.2026)

`DENT-IMPROVE-012` je sad jedini neblokiran Prioritet C task
(`DENT-IMPROVE-013/014/015` čekaju njega). **Task contract još NIJE
napisan** — obim i pristup su dogovoreni, implementacija čeka pristup
bazi.

**Dogovoren obim (Radovan potvrdio 26.8.2026):**

1. **Podijeljen zbog pravnog blokera.** `CLAUDE.md` eksplicitno zabranjuje
   HIGH-risk rad na EXCLUDE constraint-u dok se ne riješe otvorena pravna
   pitanja (`docs/dentaland-razvojni-plan-v3.1.md`, "Šta i dalje ostaje
   otvoreno" — pravni osnov obrade, rokovi čuvanja medicinske
   dokumentacije, kontrolor/obrađivač ugovor, hosting lokacija —
   **potvrđeno i dalje otvoreno**, ne pretpostaviti da su riješena bez
   provjere). Zato ovaj task radi SAMO migraciju SQLite→PostgreSQL BEZ
   EXCLUDE constraint-a, zadržava postojeću aplikacionu overlap zaštitu
   (`validate_appointment_overlap`, REF-01/DENT-IMPROVE-010) nepromijenjenu.
   EXCLUDE constraint ide u poseban, budući, eksplicitno blokiran task —
   ne otvarati ga dok se pravna pitanja ne riješe.
2. **Implementer je Claude, ne Pi/Crush** — `CLAUDE.md`: "šema/migracije i
   dalje isključivo HIGH kroz Claude". Pi/Crush ostaju nezavisni revieweri
   uz Codexa.
3. **Tehnički nalazi već provjereni u kodu (grounding za task contract):**
   - `src/dentaland/models.py`-ov `TZDateTime` tip je već portabilan
     (generički `DateTime`, radi identično na SQLite/Postgres) — šema je
     namjerno dizajnirana za ovu migraciju od početka.
   - `backend/main.py:47` ima HARDKODIRANU `sqlite:///{db_path}` konekciju
     — treba `DATABASE_URL` konfigurabilnost.
   - 3 od 5 Alembic migracija (`migrations/versions/`) koriste
     `batch_alter_table(recreate="always")` — SQLite-specifičan obrazac,
     bezopasan na PRAZNOJ Postgres bazi (nema podataka za rekreiranje),
     ali reviewer treba eksplicitno provjeriti da Alembic replay ispravno
     gradi šemu na svježoj Postgres instanci.
   - `src/dentaland/backup.py`/`backup_cli.py` ostaju SQLite-specifični za
     desktop (Faza 0) — VAN scope-a ovog taska. Postgres backup ide kroz
     `pg_dump` (CLAUDE.md), poseban budući task.
   - `.env.example` potvrđeno prazan po pitanju baze — Dentaland nikad
     nije imao ništa PostgreSQL-vezano postavljeno prije ovoga.

**BLOKIRANO NA:** pristup PostgreSQL bazi za testiranje. Na mašini postoji
lokalni `postgresql-16` Windows servis (running), ali pripada **drugom
projektu** (`deklarant_pro`) — potvrđeno od Radovana. Dentaland treba svoju
IZOLOVANU bazu na istom servisu (isti servis, potpuno odvojena baza —
nema dodira sa deklarant_pro podacima), ali Claude nema kredencijale i ne
smije ih pogađati.

**Tačan sljedeći korak:** zatražiti od Radovana PostgreSQL kredencijale sa
pravom kreiranja nove baze (superuser `postgres` ili uloga sa
`CREATEDB`) za lokalni `postgresql-16` servis — host/port/korisnik/lozinka
— da se kreira izolovana `dentaland_dev`/`dentaland_test` baza i posebna,
ograničena Dentaland uloga, PRIJE pisanja i implementacije task contracta.

## Agent availability

**Codex dostupan (od 19.8.2026).** Standardna raspodjela: Codex opciono na
LOW/MEDIUM implementaciji, obavezan Reviewer 1 na HIGH (uz Crush ili Pi
kao Reviewer 2), po tabeli uloga u `docs/dentaland-agentski-razvoj.md` —
kanonski procesni dokument. `CLAUDE.md` je thin router, ne sadrži tabelu
uloga.

## Current verification baseline

Izmjereno 26.8.2026 na `main`, post-merge gate nakon DENT-IMPROVE-011
(merge `f9de00e`):

- `pytest tests/ -q` → **374 passed**, 11 warnings (deprecation warnings
  iz `httpx`/`slowapi`/`alembic` zavisnosti, ne iz projektnog koda),
  ~10-20s.
- `ruff check src/dentaland desktop backend tests scripts/agent_sensors.py` →
  **All checks passed**.
- `mypy src/dentaland desktop backend` → **Success: no issues found in 52
  source files.**
- `python scripts/agent_sensors.py --all` → **0 blocking findings**.
- `web/tests/e2e` (`npx playwright test`) → **6 passed** (novo od
  DENT-IMPROVE-011 — zahtijeva `npm install` jednokratno, Node v24+).

Ne tretirati broj testova kao trajno pravilo — raste sa svakim novim
taskom. Prilikom sljedeće provjere, izmjeriti ponovo, ne kopirati ovaj broj
napamet.

## Novi pilot: Agent Sensors (Habit Hooks)

Radovan je 26.8.2026 odobrio `docs/DENTALAND_NOVI_RADNI_TOK_HABIT_HOOKS.md`
(prijedlog: AST arhitektonski senzori + kontekstualni "Habit Guide" +
adversarni test, kao sloj IZMEĐU implementacije i reviewa, ne zamjena za
review). Motivacija: F1-F4 bypass-evi i REF-09/11 test-quality REJECT
runde su pokazale da zeleni pytest/ruff/mypy ne garantuju poštovanje
arhitekture.

**`DENT-IMPROVE-010`** — **DONE, merged `1ef2889`, 26.8.2026.** Implementer
Crush, Claude review PASS (jedini reviewer, standardan proces). Pokriva
SAMO P0+A2 fazu iz dokumenta (sekcija 23): tri AST guarda
(`ARCH-VIEW-001`/`ARCH-CONTROLLER-001`/`ARCH-SERVICE-001`, `scripts/agent_sensors.py`)
plus genuinska replay validacija (`tests/test_architecture_contracts.py`,
koristi `git show` na pinovanim commit-ima ce2d270/a87d423, ne mock) —
Test A našao tačno F1-F4, Test B pokazao F2/F4 nestale, Test C pošteno
pokazao 2 preostala nalaza (F1, jer REF-10 tada još nije bio mergovan)
umjesto forsiranog "0 nalaza". Red Team dokumentovao poznate granice
(alias/`getattr` se ne hvataju). **CI wiring (A3) je i dalje NAMJERNO
van scope-a** — sljedeći korak je odvojena odluka, ne automatski nastavak.
Kad REF-10 uđe u main, `test_c_trenutni_main_samo_f1_ostaje` treba
ažurirati na prazan skup (sitan follow-up, ne nov task).

## Active known constraints

- `.codex/hooks.json` postoji ali je njegovo automatsko ponašanje
  **UNVERIFIED** — Claude Code hook (`.claude/settings.json`) je potvrđeno
  automatski aktivan, Codex ekvivalent nije testiran. Ne pretpostaviti da
  Codex automatski blokira konflikt.
- Više paralelnih worktree-ova trenutno postoji pod
  `Dentaland-worktrees/` — provjeriti `git worktree list` u glavnom repou
  za tačan trenutni popis prije pretpostavke da je neki task
  završen/aktivan. Stari REF-00..08 worktree-ovi su ostavljeni netaknuti,
  ukloniti po potrebi.
- Fizičan clean-machine test za `DENT-IMPROVE-009` (Windows packaging, na
  drugoj mašini) ostaje Radovanova provjera — implementacija/review su
  samo simulirali to lokalno na istoj mašini.

## Next known work

**REF-09/11/12/13 spremni za dodjelu implementerima (Pi/Crush), mogu ići
paralelno** — vidi tabelu i paralelizacijsku analizu gore. REF-10 čeka
REF-09 merge (dijeli `appointment_controller.py`), REF-14 čeka oba
(arhitektonska odluka). Tek nakon zatvaranja F1-F4 i starog duga ima smisla
razmatrati Prioritet C (`DENT-IMPROVE-010`..`015`, Faza 1 priprema) —
Radovanova odluka.
