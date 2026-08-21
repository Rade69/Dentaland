---
task_id: DENT-021
reviewer: claude
risk: LOW
verdict: PASS_WITH_NOTES
date: 2026-08-21
---

# Review — DENT-021 (panel doktora sa fotografijama, LOW)

```yaml
verdict: PASS_WITH_NOTES
scope: PASS
acceptance: PASS
architecture: PASS
blocking_findings: []
```

Napomena o prethodnom review-u: `agent_reports/2026-08-21-DENT-021-doctor-panel.md`
sadrži sopstveni "Review" blok implementera potpisan `reviewers:
[independent-codex]` sa `verdict: PASS_WITH_NOTES`. To NIJE nezavisan
review u smislu `CLAUDE.md` ("Implementer nikad nije isti agent/sesija
kao Reviewer") — tretiran je ovdje kao tvrdnja implementera, ne kao
obavljen review. Ovaj dokument je stvarni nezavisan review.

## Scope — PASS

`git diff --stat` (necommitovano, u glavnom checkout-u): samo
`desktop/views/main_window.py` (92 linije), `tests/test_gui/test_main_window.py`
(19 linija), + 3 nova PNG resursa u `desktop/assets/doctors/`. Sve
unutar `allowed_paths` iz `agent_reports/DENT-021-task-contract.md`.
Nema dodira modela/servisa/migracija (forbidden paths netaknuti).

## Acceptance (prema pisanom Task Contractu) — PASS

- Panel je u desnoj koloni iznad `DashboardPanels` — potvrđeno u diff-u
  (`right_column.addWidget(self.doctor_legend)` prije
  `right_column.addWidget(self.dashboard_panels, 1)`, nepromijenjeno).
- Prikazuje tačno Dr Ljubo/Zorka/Ana sa lokalnim fotografijama —
  potvrđeno testom i sopstvenom provjerom (`_circular_doctor_pixmap`
  učitava iz `paths.resource_path("desktop","assets","doctors",...)`,
  ispravna reupotreba centralnog path helpera iz DENT-IMPROVE-003, ista
  šema kao postojeći `logo.png` poziv).
- Svaki red ima kružni avatar + indikator u postojećoj boji doktora
  (`WeekView._DOCTOR_PALETTE`) — potvrđeno u kodu i testom.
- Panel se sakriva kad store nema doktore — potvrđeno testom
  `test_panel_doktora_je_sakriven_kad_store_nema_doktore`, ponovo
  pokrenut nezavisno, PASS.
- Raspored/filter tabovi/DashboardPanels nepromijenjeni — potvrđeno:
  diff ne dira ništa van `doctor_legend` bloka i stylesheet-a.

**Zaključak: implementacija ispunjava TAČNO ono što piše u pisanom Task
Contractu.** Vidi napomenu ispod za razliku između kontrakta i
referentnog screenshot-a.

## Adversarna provjera (nezavisna reprodukcija)

1. `pytest tests/test_gui/test_main_window.py -v` → 24/24 passed.
2. `pytest tests/ -q` → 259 passed (258 FIX-01 baseline + 1 novi test),
   `ruff` all checks passed, `mypy` 0 grešaka (35 fajlova).
3. Live edge-case provjera koju je implementer prijavio ali nije
   pokrio testom: privremeno premješten `ljubo.png` van foldera,
   konstruisan pravi `MainWindow` sa praznom SQLite bazom (`from_sqlite(":memory:")`)
   → **prozor se kreira bez pucanja**, `doctorAvatarLjubo` QLabel
   postoji, `pixmap().isNull() == True` (prazan avatar, ne crash).
   Potvrđuje implementerovu tvrdnju nezavisno. Fajl vraćen odmah nakon
   provjere.

## Nalazi (ne blokiraju merge, ali zahtijevaju Radovanovu odluku)

### 1. Vizuelni razmimoilaženje sa referentnim screenshot-om — NIJE blocking, ALI je značajno

Radovan je u razgovoru poslao screenshot ciljanog izgleda: desni panel
"Doktori" sa kružnim fotografijama i **obojenim brojčanim značkama**
pored svakog doktora (zeleno "3", crveno "1", plavo "1"). Isprobao sam
`output/thumbnail/dent021-live-ui.png` (Codex-ov offscreen render) i
sopstveni offscreen render — implementacija prikazuje kružni avatar +
ime + **prazan obojen kvadratić bez broja** (samo indikator boje,
`"●"`/QLabel bez teksta osim boje).

Ovo NIJE regresija naspram pisanog Task Contracta — kontrakt eksplicitno
traži samo "indikator u postojećoj boji doktora", ne brojčanu značku, i
Codex je to tačno implementirao. Ali ne odgovara vizuelnom cilju koji je
Radovan pokazao. Nejasno je da li je Codex uopšte vidio taj konkretan
screenshot ili je radio isključivo po tekstualnom kontraktu — nisam u
mogućnosti to provjeriti iz ovog konteksta.

**Preporuka:** Radovan treba eksplicitno da odluči — (a) prihvatiti
ovako kako jeste (indikator boje bez broja) i zatvoriti DENT-021 kakav
jeste, ili (b) tražiti brz follow-up (isti risk nivo) koji dodaje
brojčanu značku sa jasno definisanim značenjem broja (npr. broj
"Čekaju potvrdu" po doktoru — treba definisati PRIJE follow-up taska,
ne nagađati).

### 2. Proces — implementer je radio direktno u glavnom checkout-u, ne u worktree-u

`CLAUDE.md` non-negotiable pravilo: "Svaki netrivijalan zadatak = svoj
git worktree." DENT-021 je rađen direktno u `C:\Users\38765\Desktop\Dentaland`
(potvrđeno: `coordination.py status` je pokazivao `paths:
desktop/views/main_window.py, ...` sa working directory jednakim
glavnom checkout-u, ne pod `Dentaland-worktrees/`). Ovo je odstupanje
od procesa — u ovom slučaju nije napravilo stvarnu štetu (izmjene su
ostale izolovane, staging je rađen pažljivo fajl-po-fajl kroz ostatak
sesije dok su Codex-ove izmjene sjedile necommitovane), ali je bio
realan rizik za slučajan konflikt sa paralelnim FIX-01/FIX-02/FIX-03
radom na `main`-u koji se dešavao u isto vrijeme. Ne blokira ovaj
merge, ali vrijedi zabilježiti za sljedeći put.

### 3. Manja, već priznata napomena (implementer)

Ako se isporučeni PNG ručno ukloni sa instalacije, avatar ostaje prazan
bez fallback-a — nezavisno potvrđeno gore, ne ruši aplikaciju. Van
obima ovog LOW UI zadatka, prihvatljivo.

## Verifikacija (ponovljena nezavisno, na finalnom necommitovanom stanju)

```text
pytest tests/test_gui/test_main_window.py -v  → 24 passed
pytest tests/ -q                              → 259 passed, 11 warnings
ruff check src/dentaland desktop backend tests → All checks passed!
mypy src/dentaland desktop backend             → Success: no issues found in 35 source files
```

## Zaključak

Implementacija ispunjava pisani Task Contract u potpunosti — scope čist,
testovi tačni i prošireni, arhitektura ispravna (reupotreba
`paths.resource_path`, nema SQLAlchemy u `views/`). **PASS_WITH_NOTES**
zbog dva neblokirajuća nalaza: (1) vizuelno ne odgovara u potpunosti
referentnom screenshot-u (nema brojčane značke) — Radovanova odluka da
li treba follow-up; (2) rađeno van worktree-a — proceduralna napomena,
bez stvarne štete ovog puta.

## Handoff

```text
CILJ: Zamijeniti jednorednu tekstualnu legendu doktora vizuelnim
      panelom sa fotografijama, imenima i indikatorima boje.
URAĐENO: PASS_WITH_NOTES — tačno prema pisanom kontraktu, testovi i
      gate zeleni, adversarno potvrđeno (missing-photo edge case ne
      ruši aplikaciju). Vizuelno NE odgovara u potpunosti referentnom
      screenshot-u (nema brojčanih znački) — nije regresija naspram
      kontrakta, ali Radovan treba da odluči da li je to prihvatljivo
      ili treba brz follow-up.
NE DIRATI: booking.py, models.py, migracije — ništa od toga nije ni
      dirano.
SLJEDEĆE: Radovanova odluka — (a) commit + human approval kako jeste,
      ili (b) commit ovoga PLUS nov mali follow-up task za brojčane
      znake (definisati značenje broja prije nego što se dodijeli).
      Zatim FIX-03 se može dodijeliti Pi-ju (main_window.py/
      test_main_window.py claim je sad oslobođen).
```
