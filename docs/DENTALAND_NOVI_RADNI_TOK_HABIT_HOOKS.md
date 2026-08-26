# Dentaland — prijedlog novog agentskog radnog toka
## Sensors + Habit Hooks + nezavisni review

**Status:** odobreno za P0 pilot (Radovan, 26.8.2026) — vidi
`agent_reports/DENT-IMPROVE-010-task-contract.md` za konkretan implementacioni
scope (A1+A2 iz sekcije 23 ovog dokumenta).
**Repo:** `Rade69/Dentaland`
**Pregledano stanje:** `main`, HEAD `42f180d8e6f1b96944e7485bbf68cc81ff5f7bd8` (26.08.2026.)

## 1. Zaključak nakon pregleda repoa

Dentalandu ne treba zamjena postojećeg workflowa. Postojeći sistem već ima važne
zaštite: Task Contract, LOW/MEDIUM/HIGH risk, worktree izolaciju,
`coordination.py`, `.agent/PROJECT_MAP.md`, `.agent/TASK_ROUTING.md`,
execution evidence, nezavisni review, human approval i CI sa
`pytest + Ruff + mypy`.

Slabost je drugdje: **postojeći testovi i generic CI mogu biti zeleni dok je
arhitektonska namjera prekršena**.

To je dokazano u samom repou:

- finalni audit REF-00..08 pronašao je četiri aktivna `View -> Service`
  bypass-a iako su pytest, Ruff i mypy bili zeleni;
- REF-09 i REF-11 su prošli implementaciju, ali ih je Codex odbio jer
  postojeći GUI testovi nisu razlikovali novi Controller put od starog
  direktnog `View -> Service` puta;
- adversarna provjera je vratila stari pogrešan put i postojeći testovi su
  i dalje prolazili.

Zato predlažem novi sloj između implementacije i reviewa:

```text
SENSOR
  ↓
strukturisan nalaz
  ↓
HABIT GUIDE
  ↓
agent popravlja uzrok, ne metriku
  ↓
ponovna deterministička provjera
```

Ovaj sloj **ne zamjenjuje** testove, CI ili nezavisnog reviewera.

---

## 2. Šta zadržati bez promjene

### D1 — Task Contract ostaje source of truth

Ne praviti novi paralelni "Habit Contract". Postojeći Task Contract već ima:

- objective;
- risk;
- allowed/forbidden paths;
- acceptance;
- verification;
- review.

U prvoj fazi dovoljno je u postojeći `verification` dodati:

```bash
python scripts/agent_sensors.py --changed
```

Tek ako se pilot pokaže korisnim, može se razmotriti opcionalno:

```yaml
guards:
  - ARCH-VIEW-001
  - TEST-PATH-001
```

### D2 — `.agent/PROJECT_MAP.md` i `.agent/TASK_ROUTING.md` ostaju

Repo istorija već pokazuje da routing sloj smanjuje lutanje po repou kada je
task brief "lean". Ne treba ga zamijeniti ogromnim promptom.

Pravilo za Habit Hooks:

```text
GLOBAL CONTEXT = kratka trajna pravila
TRIGGERED CONTEXT = samo vodič za senzor koji se upravo aktivirao
```

### D3 — Independent review ostaje obavezan

Senzori mogu uhvatiti samo poznate klase problema. Reviewer ostaje potreban za:

- novu klasu greške;
- semantic loophole;
- loš test;
- UX regresiju;
- security ili architecture problem koji senzor ne zna prepoznati.

---

## 3. Novi workflow

```text
Task Contract
    ↓
Task Routing / Project Map
    ↓
Worktree + coordination claim
    ↓
Implementacija
    ↓
FAST SENSORS --changed
    ↓
ako postoji finding
    ↓
Habit Guide: signal + pravilo + kako reagovati
    ↓
agent popravlja stvarni uzrok
    ↓
targeted / adversarial test
    ↓
pytest + Ruff + mypy
    ↓
Evidence Pack
    ↓
Independent Review
    ↓
Human approval prema risk nivou
    ↓
Merge
    ↓
CI + integration gate
```

Ključ: **CI je enforcement, hook je samo ergonomija.**

To je važno jer je Claude Code coordination hook potvrđen, dok repo trenutno
eksplicitno vodi `.codex/hooks.json` kao `UNVERIFIED`.

---

## 4. Sloj S0 — postojeći hard guards

Zadržati:

- worktree po netrivijalnom tasku;
- `scripts/coordination.py claim/check/release`;
- allowed/forbidden paths;
- čist git state;
- zabranu tihog scope expansion-a.

Ne treba tu uvoditi Habit Hook logiku.

---

## 5. Sloj S1 — postojeći quality senzori

Zadržati:

```text
pytest
Ruff
mypy
```

Ali promijeniti interpretaciju:

```text
green CI = standardni kvalitet provjeren
green CI ≠ arhitektura automatski potvrđena
```

REF final audit je direktan dokaz za ovu razliku.

---

## 6. Sloj S2 — novi arhitektonski senzori

Ovo je najbolji prvi pilot.

### ARCH-VIEW-001 — View ne smije direktno mutirati store/service

**Scope:** `desktop/views/**`
**Severity:** BLOCK

AST senzor traži direktne mutacijske pozive tipa:

```python
self.store.move(...)
self.store.cancel(...)
self.store.create_time_off(...)
self.store.delete_time_off(...)
self.store.set_working_hours(...)
```

i definisan skup drugih mutacijskih metoda.

Habit Guide:

```text
Signal:
View direktno poziva mutacijsku store/service metodu.

Arhitektonska namjera:
View izražava korisničku namjeru.
Controller koordinira mutaciju.
Service sadrži poslovnu/DB logiku.

Nemoj samo:
- preimenovati atribut;
- sakriti isti poziv u View helper;
- premjestiti prekršaj u drugi View;
- dodati allowlist bez opravdanja.

Uradi:
1. pronađi postojeći Controller za domen;
2. provjeri postoji li ista akcija već kroz Controller;
3. dodaj najmanju potrebnu Controller granicu;
4. sačuvaj postojeće UX ponašanje;
5. dodaj test koji pada ako se stari direktni put vrati.
```

Ovaj guard je direktno izveden iz F1-F4 nalaza finalnog REF audita.

### ARCH-CONTROLLER-001 — Controller ne smije koristiti SQLAlchemy/session

**Scope:** `desktop/controllers/**`
**Severity:** BLOCK

Tražiti:

- SQLAlchemy import;
- `select(...)`;
- Session;
- `.execute`, `.commit`, direktne DB operacije.

Guide:

```text
Controller koordinira UI workflow, ali ne implementira persistence.
Ne sakrivaj SQL u Controller helper.
Koristi postojeći service/facade API.
Ako servisni API nedostaje, prijavi potreban scope umjesto tihog širenja taska.
```

### ARCH-SERVICE-001 — Service ne smije zavisiti od PySide6

**Scope:** `src/dentaland/services/**`
**Severity:** BLOCK

Guide:

```text
Service mora biti UI-neutralan.
QWidget, QMessageBox, signal ili dialog ne pripadaju service sloju.
UI podatke transformiši prije ulaska u service.
```

### ARCH-TIMEZONE-001 — kanonska Sarajevo zona

Aktivirati **tek nakon REF-13**, jer trenutni repo svjesno još ima legacy
`SARAJEVO = ZoneInfo(...)` definicije.

Poslije REF-13:

```text
ZoneInfo("Europe/Sarajevo")
```

izvan `src/dentaland/timezone.py` postaje BLOCK.

### ARCH-FACADE-001 — `booking.py` ostaje facade

Repo već ima AST-based arhitektonski test za `booking.py`.
Ne praviti drugi mehanizam; postojeći test samo uključiti u zajednički katalog
arhitektonskih guardova.

---

## 7. Sloj S3 — test-quality Habit Hooks

Ovo je posebno važno zbog REF-09 i REF-11.

### TEST-PATH-001 — dokazati put, ne samo rezultat

Ako Task Contract kaže da se mijenja:

```text
View -> Service
```

u:

```text
View -> Controller -> Service
```

test koji samo provjerava krajnji store rezultat nije dovoljan.

Minimalni obrazac:

```python
panel._controller = SpyController(...)

# direktni stari put mora eksplodirati ako ga View pokuša koristiti
store.direct_mutation = forbidden_direct_call

# pokreni stvarnu UI akciju
# potvrdi da je pozvan Controller
```

Habit Guide:

```text
Acceptance nije samo "rezultat je dobar".
Acceptance je i "rezultat ide kroz novu arhitektonsku granicu".

Test mora pasti ako se vrati stari direktni put.
Ne dodaj više testova koji svi posmatraju isti krajnji rezultat.
Dodaj najmanji test koji razlikuje ispravnu i pogrešnu implementaciju.
```

### TEST-ADVERSARIAL-001 — poznato loša varijanta mora dati crveno

Koristiti za:

- architecture bypass fix;
- security invariant;
- slučaj gdje je test ranije davao false PASS.

Procedura:

```text
1. privremeno vrati poznato pogrešan put;
2. pokreni relevantni novi test;
3. test MORA pasti;
4. vrati ispravan kod;
5. isti test MORA proći.
```

REF-11 je stvarni primjer zašto je ovaj dokaz vrijedan.

### TEST-REGRESSION-001 — bug mora prvo biti reprodukovan

Ovo već pripada `prime-bug` načinu rada. Ne duplirati pravilo.
Habit sloj samo podsjeća kada implementer tvrdi "fixed", a nema pre-fix
reprodukcijskog dokaza.

---

## 8. Sloj S4 — complexity / smell senzori

Ne uvoditi odmah hard limit.

Repo ima veće fajlove poput:

- `desktop/views/week_view.py`;
- `desktop/views/main_window.py`;
- `desktop/views/day_view.py`;
- `src/dentaland/services/appointments.py`;
- `desktop/views/settings_panel.py`.

Veličina sama po sebi nije dokaz lošeg dizajna.

Zato ne uvoditi pravila tipa:

```text
funkcija > 12 linija = FAIL
fajl > 500 linija = FAIL
```

To podstiče metric gaming.

Kasniji pilot može koristiti Ruff `C901` ili Radon, ali prvo samo kao `WARN`.

Habit Guide:

```text
Povišena kompleksnost je signal, ne cilj.

Prvo utvrdi:
- da li funkcija radi više odgovornosti;
- da li miješa nivoe apstrakcije;
- da li grananja predstavljaju različite poslovne odluke;
- da li postoje kohezivne cjeline koje imaju vlastito ime.

Ne cijepaj funkciju samo da broj postane zelen.
```

Tek poslije baseline mjerenja na Dentalandu odrediti ima li smisla threshold.

---

## 9. Mašinski format nalaza

`agent_sensors.py` treba da može vratiti strukturisan nalaz:

```json
{
  "code": "ARCH-VIEW-001",
  "severity": "BLOCK",
  "file": "desktop/views/day_view.py",
  "line": 363,
  "signal": "direct mutating store call: self.store.move(...)",
  "rule": "View -> Controller -> Service",
  "guide": "ARCH-VIEW-001"
}
```

Agent zatim dobija samo odgovarajući guide.

---

## 10. Minimalna implementaciona struktura

Ne praviti framework.

Prva verzija može biti samo:

```text
.agent/
└── HABIT_GUIDES.yaml

scripts/
└── agent_sensors.py

tests/
└── test_architecture_contracts.py
```

`HABIT_GUIDES.yaml` sadrži samo tri architecture guida i TEST-PATH guide.

Ako kasnije postane prevelik, razdvojiti ga u `.agent/habits/*.md`.

---

## 11. CLI interfejs

Brza provjera izmijenjenih fajlova:

```bash
python scripts/agent_sensors.py --changed
```

Puna CI/pre-review provjera:

```bash
python scripts/agent_sensors.py --all
```

Mašinski output:

```bash
python scripts/agent_sensors.py --changed --json
```

Primjer human-readable outputa:

```text
[BLOCK] ARCH-VIEW-001
desktop/views/day_view.py:363

Direct mutating store call: self.store.move(...)

Rule: View -> Controller -> Service

Result: 1 blocking finding
```

---

## 12. Integracija sa risk nivoima

### LOW

```text
Implementer
→ --changed sensors
→ targeted verification
→ 1 reviewer
→ merge
```

Ne dodavati novu ceremoniju.

### MEDIUM

```text
Implementer
→ --changed sensors
→ targeted/adversarial tests
→ full pytest/Ruff/mypy
→ architecture --all ako je relevantno
→ reviewer
→ human approval
→ merge
```

REF-10 je dobar pilot jer Task Contract već eksplicitno upozorava na test
koji mora zaključati Controller put.

### HIGH

```text
Implementer
→ relevantni architecture/security sensors
→ targeted tests
→ full verification
→ Reviewer 1
→ Reviewer 2
→ human approval
→ merge
→ post-merge integration gate
```

Sensors ne smanjuju broj reviewera.

---

## 13. Evidence Pack

Postojeći `agent_reports/README.md` već traži stvaran tool output.
Dovoljno je dodati mali blok:

```yaml
verification_evidence:
  sensors:
    command: "python scripts/agent_sensors.py --changed"
    result: PASS
    blocking_findings: []

  targeted_tests:
    command: "pytest ..."
    result: PASS

  full_suite:
    command: "pytest tests/ -q"
    result: PASS

adversarial_proof:
  required: true
  bad_variant_result: FAIL
  good_variant_result: PASS

not_verified: []
```

Implementerov evidence nije autoritet. Reviewer i dalje nezavisno provjerava
ključne tvrdnje.

---

## 14. Pravilo protiv gaming-a

Agent ne smije radi prolaska senzora:

- preimenovati atribut da ga senzor ne vidi;
- sakriti isti prekršaj u helper;
- dodati suppression/allowlist bez opravdanja;
- podići complexity threshold;
- oslabiti ili obrisati test;
- promijeniti acceptance kriterijum;
- mijenjati senzor u istom tasku samo zato što blokira njegov kod.

Ako je nalaz stvarni false positive:

```text
SENSOR_FALSE_POSITIVE
code: ARCH-...
location: ...
reason: ...
```

Za trajni allowlist ili promjenu senzora treba nezavisna potvrda; za
MEDIUM/HIGH i human approval.

---

## 15. Hook integracija

Ne počinjati hookovima.

### Faza 1

Svi agenti koriste isti CLI:

```bash
python scripts/agent_sensors.py --changed
```

CI koristi:

```bash
python scripts/agent_sensors.py --all
```

### Faza 2

Ako se runner pokaže stabilnim:

- Claude može dobiti automatski hook;
- Codex tek nakon stvarne potvrde da njegov hook radi;
- Pi/Crush ostaju na CLI-u gdje nema pouzdanog hook lifecycle-a.

**Hook nije source of truth.**

---

## 16. CI promjena

Sada:

```text
pytest
ruff
mypy
```

Predloženo:

```text
agent_sensors --all
pytest
ruff
mypy
```

Važna napomena: finalni Codex audit je zabilježio da `ruff check .` nalazi
postojeće nalaze u `scripts/coordination.py`, dok trenutni aplikacijski scope
prolazi.

Zato ne širiti usput:

```bash
ruff check src/dentaland desktop backend tests
```

na cijeli repo.

Ako novi runner treba lint:

```bash
ruff check src/dentaland desktop backend tests scripts/agent_sensors.py
```

`coordination.py` cleanup je poseban task.

---

## 17. Pilot plan

### P0 — implementirati samo tri architecture guarda

Bez nove dependency:

- `ARCH-VIEW-001`
- `ARCH-CONTROLLER-001`
- `ARCH-SERVICE-001`

Koristiti Python `ast`.

### P1 — TEST-PATH-001 kao Habit Guide

Ne pokušavati automatski ocijeniti svaki test.
Za architecture routing task, Task Contract/runner aktivira vodič da test mora
dokazati put.

### P2 — replay na poznatoj istoriji

Prije CI gate-a novi senzor mora biti testiran na poznatim commitima.

**Test A — REF-00..08 finalno stanje**

`ARCH-VIEW-001` treba uhvatiti poznatu F1-F4 klasu problema.

**Test B — poslije REF-09 i REF-11**

Treba pokazati da su F4 i F2 nestali, dok neriješeni bypass-i ostaju vidljivi.

**Test C — poslije REF-10/12 i ostalih follow-up taskova**

Očekivanje: 0 blocking architecture findinga.

Ako senzor ne može reproducirati poznatu istoriju ili ima mnogo false positive
nalaza, ne stavljati ga u CI.

---

## 18. Reviewer workflow nakon pilota

Reviewer Context Pack dobija još samo:

```text
Sensor report
```

Reviewer treba:

- provjeriti da je senzor relevantan;
- napasti test kvalitet;
- tražiti semantic loophole;
- provjeriti da agent nije "game-ao" guard;
- provjeriti acceptance i UX ponašanje;
- za MEDIUM/HIGH ponoviti ključne komande.

Postojeći strukturirani verdict ostaje:

```yaml
verdict: PASS|PASS_WITH_NOTES|REJECT
scope: PASS
acceptance: PASS
architecture: PASS
security: PASS
blocking_findings: []
```

Ne uvoditi novi paralelni verdict format.

---

## 19. Mjerenje uspjeha

Pratiti narednih 10 relevantnih taskova:

| Metrika | Cilj |
|---|---|
| architecture findings uhvaćeni prije review-a | raste |
| reviewer REJECT zbog već poznatih architecture obrazaca | pada |
| reviewer REJECT zbog slabog test kvaliteta | pada |
| false positives senzora | vrlo malo |
| suppression/allowlist zahtjevi | vrlo malo |
| ponovna pojava riješenog architectural smell-a | 0 |
| dodatno vrijeme LOW taska | minimalno |
| context/token overhead | nizak |

### KEEP

Širiti ako sistem stvarno hvata probleme prije review-a uz mali broj false
positive nalaza.

### MODIFY

Promijeniti ako je koristan, ali previše bučan ili agenti počnu
optimizovati samo za metriku.

### KILL / ROLLBACK

Ne širiti ako:

- većina nalaza bude false positive;
- LOW zadaci postanu osjetno sporiji;
- reviewer i dalje nalazi iste probleme istom stopom;
- maintenance Habit sistema postane veći od koristi;
- prompt/context overhead značajno poraste.

U tom slučaju zadržati samo korisne AST testove kao običan CI guard.

---

## 20. Premortem

### R1 — previše pravila

Napravi se 30 senzora i 30 guide-ova prije dokaza koristi.

**Mitigacija:** početi sa 3 architecture guarda.

### R2 — metric gaming

Agent zadovolji senzor, ali pogorša dizajn.

**Mitigacija:** sensor + semantic guide + adversarial test + independent review.

### R3 — alat-specifičan workflow

Radi u Claudeu, ne radi u Codex/Pi/Crush.

**Mitigacija:** CLI + CI su kanonski; hook je opcionalan.

### R4 — dupliranje pravila

Isto pravilo živi u CLAUDE.md, agent guide-u, Task Contractu i testu sa različitim
tekstom.

**Mitigacija:** Habit Guide ne redefiniše arhitekturu; referencira kanonsko
pravilo i opisuje samo kako reagovati na konkretan signal.

### R5 — senzor nikad nije testiran protiv poznatog kvara

Izgleda dobro, ali ne bi uhvatio F1-F4.

**Mitigacija:** obavezni replay na istorijskim commitima prije CI gate-a.

---

## 21. Red Team senzora

Prije prihvatanja `ARCH-VIEW-001`, pokušati ga probiti:

```python
store2 = self.store
store2.move(...)

getattr(self.store, "move")(...)
```

i probati:

- helper unutar View-a koji skriva mutaciju;
- alias importe;
- Controller koji direktno koristi SQLAlchemy;
- service koji indirektno povuče PySide6;
- test koji spy-a pogrešan objekat i ipak prolazi;
- preširok allowlist.

Ne mora verzija 1 hvatati svaku obfuskaciju, ali moramo znati granice senzora.

---

## 22. Šta ne bih radio

Ne bih:

- zamijenio postojeći review;
- pravio novi servis/bazu za harness;
- pokretao full pytest poslije svakog edit-a;
- stavio sve Habit Guides u globalni prompt;
- postavio univerzalni limit linija po funkciji;
- pretvorio svaki complexity smell u blocker;
- vjerovao Codex hooku dok nije testiran;
- generisao guidance LLM-om svaki put;
- mijenjao Task Contract, routing i CI sve u jednom velikom tasku.

---

## 23. Konkretan redoslijed uvođenja

### A1 — jedan mali pilot task

Dodati samo:

```text
scripts/agent_sensors.py
tests/test_architecture_contracts.py
.agent/HABIT_GUIDES.yaml
```

sa tri architecture guarda.

### A2 — validacija na istoriji

Dokazati da senzor prepoznaje stare F1-F4 obrasce i da nestaju nakon odgovarajućih
fixeva.

### A3 — tek tada CI

Dodati `agent_sensors --all` u CI i `--changed` u standardni pre-review
verification.

### A4 — poslije 10 taskova evaluacija

Tek ako se dokaže korist, razmotriti complexity Habit Hook i hook automatizaciju.

---

## 24. Konačna preporuka

Dentaland već ima dobar agentski proces. Njegova sljedeća slabost nije
nedostatak još jednog review koraka, nego nedostatak **determinističkih senzora
za projektne invarijante** i **smjernica koje agentu kažu šta signal zaista
znači**.

Predloženi dodatak je:

```text
DETERMINISTIČKI SENSOR
        +
KONTEKSTUALNI HABIT GUIDE
        +
PATH / ADVERSARIAL TEST
        +
POSTOJEĆI NEZAVISNI REVIEW
```

Najvažniji kriterijum uspjeha:

> problemi poput REF-09/REF-11 test-quality REJECT-a i F1-F4 arhitektonskih
> bypass-a moraju početi biti uhvaćeni prije reviewera, a ne tek u završnom
> auditu.

Ako pilot to ne pokaže mjerljivo, ne treba ga širiti.

---

## Pregledani izvori u repou

Za ovaj prijedlog pregledani su:

- `CLAUDE.md`
- `AGENTS.md`
- `.agent/PROJECT_MAP.md`
- `.agent/TASK_ROUTING.md`
- `.agent/CURRENT_STATE.md`
- `.claude/settings.json`
- `.codex/hooks.json`
- `docs/dentaland-agentski-razvoj.md`
- `pyproject.toml`
- `.github/workflows/ci.yml`
- `scripts/`
- `agent_reports/README.md`
- `agent_reports/REF-10-task-contract.md`
- `agent_reports/2026-08-25-REF-11-review-codex.md`
- `agent_reports/2026-08-25-REF-FINAL-acceptance-review-codex.md`
- `agent_reports/2026-08-25-REF-FINAL-acceptance-review-claude.md`
- `agent_reports/2026-08-20-DENT-AGENT-CONTEXT-validacija-istorija.md`
- trenutna struktura repoa i noviji REF commitovi.
