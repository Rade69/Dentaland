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

**Finalni acceptance review ZAVRŠEN** (25.8.2026) — Codex i Claude su
nezavisno audit-ovali paket bez implementacije, oba potvrdila
`NOT_FULLY_ACCEPTED`/`PARTIALLY_ACHIEVED` (`agent_reports/2026-08-25-REF-FINAL-acceptance-review-codex.md`,
`-claude.md`): 4 nova nalaza (F1-F4) gdje View poziva store mutaciju
direktno, mimoilazeći Controller. Radovanova odluka (25.8.2026): **nema
prihvaćenog duga** — svaki nalaz (F1-F4, plus prethodno "dokumentovan" dug
ispod) odmah postaje task, ne odlaže se.

**REF-09..14 backlog (zatvaranje F1-F4 + starog duga):**

| Task | Nalaz | Šta | Status |
|---|---|---|---|
| REF-09 | F4 | Dashboard confirm/reject → privatna `AppointmentController` instanca u `DashboardPanels` (REF-07 `RequestController` obrazac) | **DONE — merged `115e86f`, 26.8.2026.** Codex REJECT→PASS (test kvalitet, F1), Claude PASS_WITH_NOTES (N1: privatna Controller instanca implicitno scoped na confirm/reject, ne-blokirajuća napomena za budući comment) |
| REF-10 | F1 | Scheduler drag&drop (`day_view`/`week_view`) → nova `AppointmentController.move_appointment_slot` (self-contained instanca po view-u, no-op refresh_callback) | Implementirano (Pi), pušovano `50bad91`, Codex review u toku. Implementer našao i ispravio 2 nalaza u samom kontraktu (nezavisno potvrđeno): OverlapError re-eksport mora ostati (REF-00 contract test), `_parent_widget` mora biti weakref (strong-ref pravio referentni ciklus, rušio GUI teardown test) |
| REF-11 | F2 | Nov `BlockoutController` (facade, self-contained u `BlockoutPanel`) | **DONE — merged `a87d423`, 26.8.2026.** Codex REJECT→PASS (test kvalitet, F1), Claude PASS bez rezervi (čist facade, bez REF-09-ovog implicit-scope rizika) |
| REF-12 | F3 | Nov `SettingsController` (facade, self-contained u `SettingsPanel`) | **DONE — merged `b5006c9`, 26.8.2026.** Codex PASS na prvi pokušaj (testovi dodati proaktivno), Claude PASS bez rezervi |
| REF-13 | — | Preostalih 9 `SARAJEVO` redefinicija → `dentaland.timezone` (REF-08 out-of-scope finding, sad zatvaramo) | **DONE — merged `383745d`, 26.8.2026.** Codex PASS_WITH_NOTES (bez blocking, dvije dokumentacione napomene), Claude PASS. Novi dug nađen: 4 inline `ZoneInfo(...)` poziva bez `SARAJEVO` konstante (`appointments.py`, `availability.py`×2, `requests_panel.py`) — budući REF-XX kandidat |
| REF-14 | — | 3-lokacijski Controller↔View state sync (REF-04/05 dug) → `week_start_provider`-stil DI (REF-07 obrazac) | Nije napisan — arhitektonska odluka, čeka da REF-10 slegne prije dizajna |

**Paralelizacija (provjereno preko `allowed_paths`, isti standard kao
REF-06+REF-07 presedan): REF-09, REF-11, REF-12 i REF-13 imale su NULTO
preklapanje fajlova međusobno** — svi izbjegavaju `main_window.py`
(self-contained Controller-per-panel obrazac, REF-07 presedan) i
međusobno različite View/Controller fajlove. Dokazano u praksi: REF-09+REF-11
prvi paralelan krug, REF-10+REF-12 drugi. REF-14 dijeli
`appointment_controller.py`/`schedule_controller.py`/`main_window.py` sa
više njih → posljednji, poslije svega.

**Napomena arhitekturi (Claude, REF-12 review, 26.8.2026):** sad kad
postoje TRI instance istog self-contained facade Controller obrasca
(`RequestController`/`BlockoutController`/`SettingsController`) — svaka
konstruisana unutar sopstvenog panela, bez `parent_widget` stanja —
vrijedi ga eksplicitno dokumentovati u planu/`PROJECT_MAP.md` kao imenovan
DRUGI Controller-oblik (prvi je "MainWindow-owned sa parent-widget
stanjem", npr. `AppointmentController`/`ScheduleController`). Follow-up,
ne blokira ništa.

Sljedeći korak: Radovan dodjeljuje implementere (Pi/Crush) za prvi
paralelan krug.

## Agent availability

**Codex dostupan (od 19.8.2026).** Standardna raspodjela: Codex opciono na
LOW/MEDIUM implementaciji, obavezan Reviewer 1 na HIGH (uz Crush ili Pi
kao Reviewer 2), po tabeli uloga u `docs/dentaland-agentski-razvoj.md` —
kanonski procesni dokument. `CLAUDE.md` je thin router, ne sadrži tabelu
uloga.

## Current verification baseline

Izmjereno 26.8.2026 na `main`, post-merge gate nakon REF-13 (merge
`383745d`, poslije DENT-IMPROVE-010 merge-a `1ef2889`):

- `pytest tests/ -q` → **372 passed**, 11 warnings (deprecation warnings
  iz `httpx`/`slowapi`/`alembic` zavisnosti, ne iz projektnog koda),
  ~10-20s.
- `ruff check src/dentaland desktop backend tests scripts/agent_sensors.py` →
  **All checks passed**.
- `mypy src/dentaland desktop backend` → **Success: no issues found in 52
  source files.**

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
