# Current State

Last updated: 2026-08-29

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

## `DENT-IMPROVE-012` (SQLite→PostgreSQL) — DONE, merged `824590f`, 27.8.2026

Implementer Claude (HIGH schema/migracija, kako `CLAUDE.md` nalaže).
Obim namjerno sužen naspram originalnog backlog opisa (Radovanova odluka
26.8.2026): SAMO `DATABASE_URL` konfigurabilnost (`backend/main.py`,
`migrations/env.py`), Alembic migracija na Postgres, jednokratan
migracioni skript (`scripts/migrate_sqlite_to_postgres.py`, FK-safe,
integrity provjera), i potvrda da postojeća aplikaciona overlap zaštita
(`validate_appointment_overlap`, REF-01/DENT-IMPROVE-010) radi
nepromijenjeno nad Postgres dijalektom. **Bez EXCLUDE/`btree_gist`** —
taj dio ostaje poseban, eksplicitno blokiran budući task dok se pravna
pitanja iz `CLAUDE.md` "Otvorena pitanja" ne riješe.

**Pristup bazi riješen 26.8.2026:** izolovana lokalna PostgreSQL 16
instanca SAMO za Dentaland, port **5433**, data-dir
`C:\Users\38765\AppData\Local\Dentaland\pgdata16` — NIJE isti servis kao
Windows `postgresql-16` na portu 5432 (`deklarant_pro`, drugi projekat).
Zaseban proces, ne pokreće se automatski pri restartu — provjeriti
`pg_ctl status` prije rada. Kredencijali u `.env` (gitignored) u root-u
projekta.

**Dva fix kruga tokom review-a (oba stvarni defekti, ne test-kvalitet):**
- **Fix runda 1 (Codex F1):** `migrations/env.py` je pucao na
  percent-encoded karakteru u `DATABASE_URL` (npr. lozinka sa `%25`) zbog
  Alembic `ConfigParser` interpolacije — popravljeno standardnim
  `%` → `%%` escape-om, regresioni test dodat (ide kroz stvarni subprocess
  `alembic current`, ne ručno konstruisan engine).
- **Fix runda 2 (Pi nalaz, nezavisno potvrdio Crush):** `DATABASE_URL`
  override je bio bezuslovan — pregazio je URL koji 4 POSTOJEĆA testa
  (`test_models.py` ×3, `test_requests.py` ×1) eksplicitno postave na
  svoju izolovanu `tmp_path` SQLite bazu prije `command.upgrade()`. Kad bi
  proces imao `DATABASE_URL` I `DATABASE_URL_TEST` postavljene istovremeno
  (prirodan scenario, oba su u `.env`), Alembic bi tiho migrirao/downgrade
  Postgres umjesto SQLite tmp baze — ta 4 testa bi pukla sa
  `NoSuchTableError`. Ovo NIJE bio scenario koji je ijedna ranija
  verifikacija testirala (samo `DATABASE_URL_TEST` je izvožena, nikad
  oba istovremeno). Popravljeno guard uslovom: override se primjenjuje
  samo ako pozivalac još nije eksplicitno postavio drugačiji URL od
  `alembic.ini` defaulta — bez diranja test fajlova.

**Review:** Codex (Reviewer 1, obavezan, PASS_WITH_NOTES na oba fix
kruga), Pi (Reviewer 2, PASS_WITH_NOTES, otkrio Fix rundu 2 koristeći
novoinstalirane `review-code`/`verify-before-complete` skill-ove), Crush
(PASS_WITH_NOTES, nezavisno potvrdio isti nalaz kao Pi — vrijedna
triangulacija). Radovan human approval 27.8.2026.

**Usputan nalaz (PII, riješen, ne kodni):** implementacija je otkrila da
lokalni dev `dentaland.db` sadrži stvarne lične podatke (Radovanov
identitet + porodični zapisi), ne samo sintetske test podatke — implementer
je ispravno stao i koristio isključivo sintetske podatke za sve testove
(critical constraint iz task contracta). Radovan je naknadno obrisao svih
14 ne-sintetskih zapisa iz tog fajla i pokrenuo `VACUUM` — fajl sad sadrži
samo očigledno sintetske podatke. Ovaj fajl nikad nije bio dio git
trackinga niti ovog taska.

**Rezidualna napomena (Codex, ne blokira, nije task-worthy):** guard u
`migrations/env.py` teorijski ne bi razlikovao "pozivalac eksplicitno
postavio baš isti string kao ini default" od "nedirano" — trenutno nema
takvog pozivaoca u kodu, čisto teorijska granica.

## `DENT-IMPROVE-013` (Autentifikacija + RBAC) — DONE, merged `da67027`, 27.8.2026

Implementer Claude (HIGH security, dva nezavisna reviewera po
`docs/dentaland-razvojni-plan-v3.1.md` principu #7). Individualni
korisnički nalozi (Argon2id password hash — v3.1 eksplicitan zahtjev, ne
bcrypt), server-side sesije (`secrets.token_urlsafe(32)`, SHA-256 hash,
`hmac.compare_digest`, `expires_at` + eksplicitna invalidacija — isti
obrazac kao planirani cancel-link token), RBAC zaštita na tri ranije
potpuno nezaštićena staff endpointa (`GET /api/booking-requests`,
`confirm`, `reject`) — **samo `RECEPTION` uloga prolazi**, `ADMIN` i
`DENTIST` eksplicitno testirani da dobijaju 403 (Radovanova odluka:
ADMIN ne dobija automatski operativne privilegije, v3.1).

**Namjerno van obima** (Radovanove odluke, 27.8.2026, prije implementacije):
nema signup UI (nalozi preko `scripts/create_user.py`, CLI + `getpass` —
nema još stvarnog staff-facing klijenta koji bi UI koristio; desktop app
ne zove backend uopšte, radi direktno preko SQLAlchemy/SQLite), nema pune
audit DB tabele (`LOGIN_SUCCESS`/`LOGIN_FAILURE` idu u `logging` modul —
prava append-only audit infrastruktura je `DENT-IMPROVE-014`), nema
OAuth/SSO/2FA. Cookie-based sesija (`HttpOnly`+`Secure`+`SameSite=Strict`),
CSRF pokriven `SameSite=Strict` uz grep-potvrđeno odsustvo bilo kakvog
cross-origin staff klijenta u kodu — mora se ponovo razmotriti ako se
ikad doda browser-based admin panel.

**Fix runda 1 (Codex F1, HIGH, stvaran defekt):** `change_password` je
koristio DVIJE odvojene transakcije/commit-e (hash lozinke, pa zaseban
opoziv sesija) — kvar u drugom koraku bi ostavio novu lozinku upisanu dok
bi stare (potencijalno kompromitovane) sesije ostale validne, direktno
rušeći razlog zbog kojeg je invalidacija tražena. Popravljeno spajanjem u
jednu transakciju/jedan commit; adversarni regresioni test dodat
(monkeypatch simulira tačan kvar, potvrđuje potpuni rollback). Codex je
nezavisno reprodukovao adversarni scenario u re-review-u, ne samo
prihvatio tvrdnju.

**Pi N1 (kozmetički):** nedostajao trajan test da `hash_password` stvarno
proizvodi Argon2id hash (samo ručno potvrđeno) — dodat
`test_hash_password_koristi_argon2id`.

**Nužna posljedica, ne proširenje obima:** `tests/test_backend.py` i
`tests/test_models.py` izmijenjeni — postojeći testovi su pozivali sad
zaštićene endpointe bez autentifikacije, i `test_sve_tabele_su_kreirane`
je provjeravao tačan skup naziva tabela (sad uključuje `users`/`sessions`).
Oba nalaza je nezavisno potvrdio i Crush kao vidljiv, opravdan deviation.

**Usput popravljen i stari propust iz `DENT-IMPROVE-012`:**
`.github/workflows/ci.yml` je koristio hardkodiranu listu paketa (ne
`pyproject.toml`) i falio je i `psycopg2-binary` (dormant od 012) i
`argon2-cffi` (bio bi odmah aktivan pad na ovoj grani) — popravljeno
odvojeno na `main` (`0c038d8`) prije merge-a.

**Review:** Codex (Reviewer 1, obavezan, PASS_WITH_NOTES na obje runde),
Pi (Reviewer 2, PASS_WITH_NOTES), Crush (dodatna nezavisna provjera,
PASS_WITH_NOTES, nezavisno potvrdio Codex-ov fix). Radovan human approval
27.8.2026.

Otvara `DENT-IMPROVE-014` (append-only audit log) kao sljedeći neblokiran
Prioritet C task.

## `DENT-IMPROVE-014` (append-only audit log) — podijeljen u 3 dijela

**Jezgro DONE, merged `41cb94e`, 27.8.2026.** Implementer Claude (HIGH
schema). `AuditEvent`/`AuditAction` tačno po v3.1 šemi (9 polja, 7 akcija
iz backlog "Minimum events" liste — `CHANGE_ROLE` namjerno dormant,
šira v3.1 lista `VIEW_PATIENT`/`EXPORT_PERSONAL_DATA`/itd. van obima jer
nema odgovarajuće funkcionalnosti). `write_audit_event` prima opcioni
već-otvoren `session=` parametar (isti obrazac kao `_revoke_active_sessions`
iz DENT-IMPROVE-013) za buduću atomsku upotrebu. **Nula instrumentacije**
stvarnih poziva — namjerno, to rade dva paralelna dependent taska.
Review: Codex + Pi, oba PASS_WITH_NOTES, Pi nezavisno reprodukovao
atomski `session=` scenario sopstvenom probom (3 scenarija: rollback/
commit/vidljivost-prije-commit-a). Radovan human approval 27.8.2026.

**Arhitektonsko ograničenje (Radovanova odluka, prihvaćeno):** desktop
app nema koncept ulogovanog korisnika → appointment CRUD audit zapisi
(`DENT-IMPROVE-014C`) će uvijek imati `actor_user_id=NULL`. Samo LOGIN
događaji (`DENT-IMPROVE-014B`, iz backend auth-a) imaju pravi actor. Ne
graditi desktop login da se ovo "riješi" — van obima.

**`DENT-IMPROVE-014C` DONE, merged `886467c`, 28.8.2026.**
CREATE/UPDATE/CANCEL/DELETE_APPOINTMENT instrumentacija
(`src/dentaland/services/appointments.py`), atomsko preko `session=`
(dijeli transakciju sa samom izmjenom termina). Codex (2 runde,
PASS_WITH_NOTES — runda 1 tražila trajan adversarni test za atomičnost,
implementer ga dodao i lično reprodukovao pad/prolaz) + Pi
(PASS_WITH_NOTES). Claude (koordinator) nezavisno potvrdio.
**Atribucija:** kontrakt je izvorno pretpostavio implementer=crush, ali
je Claude session sam implementirao — Radovan je tražio ispravku
atribucije (implementer: claude), ne ponovno pisanje koda (kod je
nezavisno verifikovan prije zadržavanja).

**`DENT-IMPROVE-014B` DONE, merged `74a1bce`, 28.8.2026.**
LOGIN_SUCCESS/FAILURE instrumentacija (`src/dentaland/services/auth.py`
+ `backend/main.py` za `source_ip`). Ista atribucijska ispravka kao 014C
(kontrakt pretpostavio implementer=pi, stvarno implementer=claude,
Radovanova odluka da se zadrži kod uz ispravljenu atribuciju).

**N1 (Crush review) → Radovanova odluka → fix, sve u jednom ciklusu:**
Crush je našao da `LOGIN_FAILURE` metadata sa pokušanim username-om nosi
drugačiju težinu od rotirajućeg `logger.info` traga jer je
`audit_events` append-only (nikad se ne briše) — ako neko greškom ukuca
lozinku u username polje, ona bi TRAJNO ostala u bazi. Radovan je (nakon
objašnjenja tradeoffa: trajnost naspram izgubljene istražne vrijednosti
u sistemu sa šačicom naloga) odlučio da metadata bude PRAZNA. Claude je
uradio fix lično (jednostavna, mehanička izmjena — ne obavezno kroz
Pi/Crush ciklus za ovako malu izmjenu na već-postojećem HIGH tasku).
Codex + Crush oba potvrdila `PASS` na re-review-u (N1 riješen, nema
novih nalaza).

**Merge napomena:** auto-merge sa `DENT-IMPROVE-015` na `backend/main.py`
i `tests/test_auth.py` (oba taska su nezavisno dirala te fajlove u
različitim, ne-preklapajućim regijama) — git je riješio bez konflikta,
Claude nezavisno verifikovao da je REZULTAT semantički ispravan (ne samo
tekstualno bez konflikta) čitanjem merged koda + punim post-merge gate-om
prije nego što je prihvaćen kao završen.

**`REF-16` DONE, merged `3c51856`, 29.8.2026.** Kidanje cirkularnog
importa `main_window ↔ appointment_controller` (implementer Pi — stvaran
Pi ovaj put, ne atribucijska ispravka). `AppointmentController` lazy-uvozi
dijaloge preko postojećeg `desktop/views/dialogs/__init__.py` registry-a
umjesto preko `main_window.py`, koji više ne re-eksportuje 5 dijalog
klasa. `OverlapError` re-eksport (REF-00 baseline) ostaje. Dublji,
zaseban lanac (`dialogs → week_view → appointment_controller`) ostaje
priznat kao van scope-a, nije preuveličana tvrdnja o potpuno acikličnom
grafu. Codex + Claude PASS bez rezervi — oba nezavisno provjerila da
`main` nije dirao nijedan od 4 REF-16 fajla otkako je grana odvojena
(bezbjedan merge bez rebase-a).

**Ovim je skoro cijeli Prioritet C backlog
(`docs/DENTALAND_IMPROVEMENT_BACKLOG.md`) funkcionalno završen** —
DENT-IMPROVE-010 do 015 (uklj. 014B/014C podzadatke) i REF-16 su svi
DONE. **Izuzetak (otkriven 29.8.2026): druga ID kolizija.** Backlogov
originalni `DENT-IMPROVE-015` NIJE rate limiting task koji je upravo
mergovan pod tim brojem — originalni 015 je "Produkcijski
security/privacy release gate" (HIGH, C6), nikad urađen ni pod jednim
ID-jem. Backlog dokument ispravljen (commit `a59d02c`): taj task sada
nosi broj `DENT-IMPROVE-016`. Vidi "Next known work" ispod za detalje i
status svake stavke checklist-a.

**`DENT-IMPROVE-015` DONE, merged `ee52587`, 28.8.2026.** Rate limiting
na preostala 4 backend endpointa (`logout` 10/min, `get_pending_requests`
30/min, `confirm`/`reject` 20/min svaki) — zatvara stvaran propust
CLAUDE.md pravila ("rate limiting na svakom javnom endpointu"), 4 od 6
endpointa su bila nezaštićena. Implementer Pi, Claude jedini reviewer
(LOW risk) PASS_WITH_NOTES. Brojevi limita su bili neizmjerene procjene
— Radovan ih potvrdio 28.8.2026 nakon obrazloženja (auto-refresh
dashboard `AUTO_REFRESH_INTERVAL_MS=20_000` × do 3 otvorene instance
≈ 9/min baseline, limiti ostavljaju rezervu).

**Napomena o sesijskom kontinuitetu (28.8.2026):** REF-16, DENT-IMPROVE-014B/014C
i DENT-IMPROVE-015 su svi pronađeni kao NECOMMITOVAN, već-implementiran
rad u worktree-ovima (paralelna Claude Code sesija je implementirala i
djelimično review-ovala, ali nikad nije prošla kroz commit/push/merge
korak). Isto se desilo i sa DENT-IMPROVE-012/013/014 (jezgro) ranije istog
dana — čitava ta serija je bila mergovana ispravno (human approval
potvrđen u merge porukama) ali task contract `status:` polja su ostala
neažurirana. **Pouka za ubuduće:** na početku nove sesije UVIJEK provjeriti
`git worktree list` + `git status --short` u SVAKOM worktree-u (ne samo
glavnom repou) prije pretpostavke da je "sljedeći korak" ono što task
contract-i tvrde — status polja mogu zaostajati za stvarnošću ako je
prethodna sesija prekinuta prije finalnog koraka.

## Agent availability

**Codex dostupan (od 19.8.2026).** Standardna raspodjela: Codex opciono na
LOW/MEDIUM implementaciji, obavezan Reviewer 1 na HIGH (uz Crush ili Pi
kao Reviewer 2), po tabeli uloga u `docs/dentaland-agentski-razvoj.md` —
kanonski procesni dokument. `CLAUDE.md` je thin router, ne sadrži tabelu
uloga.

## Current verification baseline

Izmjereno 29.8.2026 na `main`, post-merge gate nakon REF-16 (merge
`3c51856`, POSLJEDNJI merge do sada — zatvara cijeli Prioritet C
backlog):

- `pytest tests/ -q` (bez `DATABASE_URL`/`DATABASE_URL_TEST`) → **429
  passed, 2 skipped**, 16 warnings, ~25s. Skip su i dalje dva
  `tests/test_postgres_migration.py` testa (Postgres env nije postavljen
  u ovoj komandi).
- `ruff check src/dentaland desktop backend tests scripts/agent_sensors.py` →
  **All checks passed**.
- `mypy src/dentaland desktop backend` → **Success: no issues found in 54
  source files.**
- `python scripts/agent_sensors.py --all` → **0 blocking findings**.
- `web/tests/e2e` (`npx playwright test`) → **6 passed** (od
  DENT-IMPROVE-011 — zahtijeva `npm install` jednokratno, Node v24+; nije
  ponovo mjereno u ovom krugu).

**Sve poslato na review je sada mergovano — nema otvorenih grana koje
čekaju review/approval.**

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

## Riješen incident: GitHub Actions CI bio crven 3 dana (otkriveno i popravljeno 29.8.2026)

`.github/workflows/ci.yml` je koristio `actions/checkout@v4` bez
`fetch-depth: 0` — plitak checkout (samo zadnji commit). Otkad je
`tests/test_architecture_contracts.py` uveden (DENT-IMPROVE-010, merge
`1ef2889`, 26.8.2026 ~13:12), taj test treba `git ls-tree`/`git show` na
starijim pinovanim commit-ima (`ce2d270`, `a87d423`) — bez pune istorije
puca sa exit 128. **CI je bio crven na SVAKOM pushu na `main` od tog
trenutka, tri dana, desetine commit-a** — niko nije primijetio jer su svi
agenti (uklj. mene) pokretali `pytest tests/ -q` LOKALNO (puna git
istorija u lokalnom checkout-u prolazi normalno) i nikad nisu provjerili
stvaran GitHub Actions status.

**Popravljeno:** `fetch-depth: 0` dodan u checkout korak (commit `3d76051`
na `main`, potvrđeno zeleno na `main` i na `task/DENT-IMPROVE-016-release-gate`
nakon merge-a fixa).

**Pouka za ubuduće:** "post-merge integration gate" opisan u
`docs/dentaland-agentski-razvoj.md` se DOSAD provjeravao isključivo
lokalnim pytest pokretanjem — to NIJE isto što i provjera stvarnog CI
statusa (`gh run list`/`gh run view`). Lokalni test-run ne otkriva greške
specifične za CI okruženje (plitak checkout, drugačiji OS/dependency
verzije, environment varijable). Povremeno provjeriti `gh run list
--branch main --limit 5` kao dio "gdje smo trenutno" provjere, ne
pretpostaviti da zeleni lokalni pytest znači zelen CI.

## Next known work

**`DENT-IMPROVE-016` DONE, merged `06b8009`, 29.8.2026.** Skraćeni
produkcijski security/privacy release gate (originalno pogrešno
numerisan kao 015 — kolizija, vidi gore). PostgreSQL backup+restore
(`src/dentaland/backup_postgres.py`, `pg_dump`/`pg_restore`, Fernet
enkripcija, atomsko jednofajlno objavljivanje), 4 nova compliance
dokumenta (breach runbook, retention politika — pet godina, politika
produkcijskih podataka, Postgres backup vodič), audit `web/privacy.html`
(kompletan, bez izmjena). Implementer Claude, reviewer Codex — **7 REJECT
rundi** prije čistog PASS-a (F1-F5, svi stvarni: sadržajni
integritet/snapshot race, ownership/kolizija privremene baze, cleanup
lifecycle uklj. `BaseException` handling, lozinka u argv, atomsko
objavljivanje backup para) — vidi
`agent_reports/2026-08-29-DENT-IMPROVE-016-release-gate.md` i
`2026-08-29-DENT-IMPROVE-016-review-codex.md` za pun trag. Radovanovo
human approval potvrđeno, post-merge integration gate PASS.

**Namjerno van obima, čeka Radovanovu hosting odluku (odgođeno do kraja
projekta):** HTTPS, processor evidencija/kontrolor-obrađivač ugovor,
`EXCLUDE` constraint (PostgreSQL concurrency protection). Ovo je jedino
što dijeli Dentaland od punog production-readiness gate-a (13/13 stavki
iz `docs/DENTALAND_IMPROVEMENT_BACKLOG.md` sekcije 16) — 10 od 13 je
sad DONE.

**`DENT-IMPROVE-017` DONE, merged `bc20eb3`, 29.8.2026.** Zatvorio oba
nalaza (OUT_OF_SCOPE_FINDING iz `DENT-IMPROVE-016`) — "nema dugova"
politika:

1. `tests/test_postgres_migration.py::test_confirm_preklapanje_vraca_409_nad_postgres`
   — dodat `pg_reception_session` fixture (isti obrazac kao
   `test_backend.py`) + `base_url="https://testserver"` na `client`
   fixture (`secure=True` cookie problem, dodatni prethodno neprepoznat
   dio uzroka). Usput otkriven i popravljen pravi FK cleanup bug —
   brisanje test korisnika je pucalo na `sessions`/`audit_events` foreign
   key, cleanup sad briše oba prije `User` reda.
2. Lokalna Postgres instanca (port 5433) — `dentaland_dev`/`dentaland_test`
   drop-ovane i rekreirane (provjereno prazne/sintetičke prije brisanja),
   pa stvaran `alembic upgrade head` pokrenut od nule na obje — svih 6
   migracija primijenjeno čisto, `alembic current` sad ispisuje tačan
   head na obje baze umjesto ranijeg zastarjelog pečata.

Implementer Claude, Codex PASS_WITH_NOTES na prvi pokušaj (bez blocking
nalaza — u odnosu na 7 REJECT rundi za `DENT-IMPROVE-016`). Puni suite sa
`DATABASE_URL_TEST`: **449 passed, 0 failed** — prvi put ove sesije da je
kompletno čisto (nema više poznatih pre-postojećih failure-a). Vidi
`agent_reports/2026-08-29-DENT-IMPROVE-017-postgres-fixes.md` i
`2026-08-29-DENT-IMPROVE-017-review-codex.md`.

**Odvojen, nepovezan nalaz — riješen:** GitHub Actions CI je bio crven na
SVAKOM pushu na `main` tri dana (od DENT-IMPROVE-010, 26.8.2026, plitak
checkout) — popravljeno `3d76051`, potvrđeno zeleno, vidi "Riješen
incident" sekciju iznad.

## Test VPS (Contabo) — pristup uspostavljen, HTTPS stvarno testiran (29.8.2026)

Radovan je naveo da ima poseban Contabo VPS (nekorišten za zvanični sajt
ordinacije, vidi CLAUDE.md "Dopuna") koji se u istoj sesiji stvarno
koristio za prvi test deploymenta. **Ovo je i dalje samo test
infrastruktura — NE produkcijska hosting odluka**, ta ostaje odvojena i
otvorena (vidi CLAUDE.md "Otvorena pitanja").

**Server:**
- Contabo Cloud VPS 6 (2026), instanca `vmi3521908`, IP `169.58.208.91`,
  region EU. 200GB disk (187GB slobodno), 12GB RAM, 6 CPU cores. Ubuntu
  24.04.4 LTS.
- Server već hostuje `ffplayout` (streaming/emitovanje softver, aktivan,
  **NAMJERNO netaknut** — Radovanova eksplicitna odluka 29.8.2026, ne
  dirati taj servis). Zauzima portove `80`, `1935`, `1936`, `8080`,
  `8088`, `8181`, `8787` — Dentaland testiranje ih izbjegava.
- Postoji korisnik `danga` (sudo grupa) — koristi se za pristup, ne
  `root` direktno (osim preko VNC konzole za hitne slučajeve).

**SSH pristup:**
- Poseban ključ generisan lokalno (`~/.ssh/dentaland_vps_ed25519` na
  Radovanovoj mašini, van repoa, nikad komitovan) i dodat u
  `danga` naloga `~/.ssh/authorized_keys` na serveru.
- **Poznat problem otkriven usput:** `~/.ssh/authorized_keys` na serveru
  je bio u vlasništvu `root` umjesto `danga` (ostatak neke ranije
  administracije) — blokiralo je dodavanje ključa dok se nije popravilo
  sa `chown danga:danga`.
- Lozinke (Contabo nalog, root/danga lozinka na serveru) su NAMJERNO
  izvan ovog dokumenta — postoje samo u Radovanovoj lokalnoj bilješci
  (`Contabo šifra.txt` na Desktopu) i nikad nisu upisane ni u jedan
  git-praćen fajl.

**Firewall (`ufw`):**
- Default: `deny incoming`. Otvoreni portovi zatečeni pri dolasku: `22`, `80`,
  `8080`, `8787`, i `443` — ali `443` je bio otvoren SAMO za jednu
  specifičnu IP adresu, sa komentarom `"temporary Codex SSH"` (ostatak
  neke ranije, nepovezane administracije — ne od ove Dentaland sesije).
  To je blokiralo Let's Encrypt validaciju (dolazi sa drugih IP adresa).
- **Ispravljeno:** `sudo ufw allow 443/tcp` — port 443 sad otvoren javno
  (potrebno za HTTPS testiranje).
- Kontabov "free Firewall" (mrežni nivo, poseban od `ufw`) nije diran —
  nije bio uzrok problema, `ufw` na samom serveru jeste bio.

**HTTPS — stvaran Let's Encrypt sertifikat izdat:**
- Domena: `169-58-208-91.nip.io` (besplatan wildcard DNS servis, nema
  registracije — razrješava se automatski na IP iz imena). Privremeno
  rješenje dok se ne izabere prava domena uz finalnu hosting odluku.
- `certbot` (već instaliran alat) nije podržavao TLS-ALPN-01 izazov u
  ovoj instalaciji (samo `standalone`/`webroot`, oba zahtijevaju port 80
  koji je zauzet od `ffplayout`-a) — prebačeno na `acme.sh`
  (`curl https://get.acme.sh | sh`), koji ima ugrađenu podršku za
  TLS-ALPN-01 (samo port 443, ne dira port 80).
- Komanda koja je uspjela: `sudo /home/danga/.acme.sh/acme.sh --issue -d
  169-58-208-91.nip.io --alpn --server letsencrypt`.
- Sertifikat: `/root/.acme.sh/169-58-208-91.nip.io_ecc/` na serveru
  (`.cer`, `.key`, `fullchain.cer`). Važi do ~28.11.2026, `acme.sh` cron
  već podešen za automatsko obnavljanje.

**Šta ovo dokazuje:** HTTPS mehanika (Let's Encrypt izdavanje sertifikata
na stvarnom javnom serveru) sad je stvarno demonstrirana, ne samo
teoretski opisana u planu — jedna od tri stavke koje su čekale hosting
odluku (uz `EXCLUDE` constraint i processor evidenciju) sad ima realan
tehnički dokaz da radi. Ne mijenja status preostale dvije stavke niti
finalnu produkcijsku hosting odluku.

### Backend deployment na test VPS — DONE, potvrđeno end-to-end (29.8.2026)

Isti dan, nastavak gornjeg. Cijeli Faza 1 lanac (HTTPS → nginx → FastAPI
→ PostgreSQL → RBAC) je stvarno proradio zajedno na ovom serveru — prvi
put u projektu, ne više samo plan.

**PostgreSQL:**
- Instaliran PostgreSQL 16 (`apt-get install postgresql postgresql-contrib`).
- Nova, odvojena baza/nalog: rola `dentaland_app` (CREATEDB), baza
  `dentaland_vpstest` (ime namjerno signalizira "test", ne produkcija).
  Sluša samo na `127.0.0.1` — port 5432 NIJE otvoren u `ufw`, nema
  spoljnog pristupa bazi.
- Migracije: pravi `alembic upgrade head` (isto pravilo kao
  `DENT-IMPROVE-017`) — svih 6 migracija primijenjeno čisto na praznoj
  bazi.

**Aplikacija:**
- Repo kloniran u `/opt/dentaland` (`git clone --depth 1`, javan GitHub
  repo, bez potrebe za kredencijalima). Trenutno na commit-u `c1bd372`.
- Python venv (`/opt/dentaland/venv`), instalirane SAMO backend
  zavisnosti (FastAPI/SQLAlchemy/alembic/psycopg2/argon2/slowapi/uvicorn)
  — bez `PySide6`/desktop zavisnosti, server je headless.
- `systemd` servis `dentaland-backend` (`/etc/systemd/system/dentaland-backend.service`):
  `uvicorn backend.main:app` na `127.0.0.1:8000`, `User=danga`,
  `Restart=on-failure`, omogućen (`enable --now`) — preživljava reboot.
  `DATABASE_URL` je u service fajlu (na disku servera, root-only
  čitljiv fajl, nikad u repou).

**nginx (reverse proxy):**
- Nov site config `/etc/nginx/sites-available/dentaland` (simlink u
  `sites-enabled/`) — **ne dira** postojeće `default`/`ffplayout`
  konfiguracije (port 80/8080).
- `listen 443 ssl` sa sertifikatom instaliranim preko `acme.sh
  --install-cert` na stabilnu lokaciju (`/etc/dentaland/ssl/`, sa
  `--reloadcmd "systemctl reload nginx"` za automatsko obnavljanje).
- `root /opt/dentaland/web` servira statičnu booking formu direktno;
  `location /api/` proxy-uje na `127.0.0.1:8000`.
- `sub_filter` injektuje `window.DENTALAND_API_BASE = window.location.origin;`
  prije `app.js` učitavanja — rješava isti-origin API poziv BEZ diranja
  committovanog `web/index.html` (test-deployment-specifično, ostaje
  samo u nginx konfiguraciji na serveru).

**Verifikacija (izvana, preko pravog interneta, ne samo sa servera):**
- `https://169-58-208-91.nip.io/` → HTTP 200 (booking forma).
- `GET /api/booking-requests` bez prijave → HTTP 401 (RBAC ispravno
  odbija).
- `POST /api/booking-requests` sa sintetičkim podacima
  (`"ime": "Test VPS Deployment"`) → HTTP 201, zapis stvarno upisan u
  `dentaland_vpstest` bazu (id=1, status PENDING) — ostavljen u bazi
  kao dokaz, jasno markiran, sintetički (vidi
  `docs/dentaland-politika-produkcijski-podaci.md`).
- Sertifikat nezavisno provjeren (`openssl s_client`): `subject=CN=169-58-208-91.nip.io`,
  `issuer=Let's Encrypt`, važi do 28.11.2026.

**Šta NIJE urađeno (namjerno, van obima ove test runde):**
- Nema automatizovanog deployment skripta u repou — sve urađeno ručno,
  interaktivno, uz Radovanovo direktno učešće (kredencijali, VNC
  pristup) — nije prošlo kroz formalni Task Contract proces jer nije
  mijenjalo nijedan fajl u repou (samo stanje servera). Ako se ovo
  ponavlja/formalizuje, vrijedi razmotriti pisanje pravog deployment
  vodiča/skripte u `docs/`.
- Email/SMTP nije podešen na serveru — `notifications.py` best-effort
  tiho preskače slanje bez `DENTALAND_SMTP_HOST`, pa to nije blokiralo
  test.
- Viber webhook testiranje — **na pauzi** (Radovan, 30.8.2026), vidi
  CLAUDE.md "Šta se namjerno ne gradi unaprijed" — otkrivena moguća
  ~€100/mjesec fiksna cijena po botu (neverifikovan izvor) je dovela u
  pitanje raniju "jeftinija alternativa" pretpostavku. Tehnički sad
  moguće (prava HTTPS domena postoji) kad/ako se nastavi.
- `EXCLUDE` constraint — i dalje eksplicitno odgođen (CLAUDE.md
  "Otvorena pitanja"), ne testiran ovom rundom.
