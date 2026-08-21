---
task_id: DENT-IMPROVE-006
risk: LOW/MEDIUM
implementer: codex
reviewers: [claude]
verdict: PASS_WITH_NOTES
created_at: 2026-08-21
---

# DENT-IMPROVE-006 — nezavisan review (Claude)

## Metod

Nezavisna provjera od nule (`independent-review` skill) — Codex-ov
izvještaj (`agent_reports/2026-08-21-DENT-IMPROVE-006-codex.md`) tretiran
kao tvrdnja, ne dokaz. Sve niže je nezavisno rekonstruisano, ponovo
pokrenuto i adversarno testirano u worktree-u
`Dentaland-worktrees/DENT-IMPROVE-006-requests`
(`task/DENT-IMPROVE-006-requests`, granat od `main` `4e679f2`).

## Scope

```text
git diff --stat
 desktop/views/main_window.py       |  9 ++-
 desktop/views/requests_panel.py    | 49 ++++++++++++++-----
 tests/test_gui/test_main_window.py |  7 +++
+ desktop/views/requests_page.py (novo)
+ tests/test_gui/test_requests_page.py (novo)
```

`requests_panel.py` je MODIFIKOVAN, ne samo netaknut — na prvi pogled
odstupanje od "postojeći dashboard panel ne gubi funkcionalnost", ali
provjerio sam da je izmjena direktna posljedica eksplicitnog Task
Contract pravila "ne duplirati business logiku iz DashboardPanels" —
Codex je logiku IZDVOJIO u zajedničku `process_pending_request()`
funkciju koju sada koriste i `DashboardPanels._confirm` i novi
`RequestsPage._process`. Ovo je namjeran refactor, ne scope creep.
`backend/`, `web/`, `models.py`, servisna business pravila — nedirani.

## Verdikt: PASS_WITH_NOTES

### Refaktor `_confirm` — provjerio bit-za-bit ekvivalentnost, ne pretpostavio

Ovo je najrizičniji dio ovog taska (dijeljena logika, postojeći dashboard
tok). Ručno sam uporedio staru i novu granu za svih 5 mogućih ishoda:

| Scenario | Staro ponašanje | Novo ponašanje | Ekvivalentno? |
|---|---|---|---|
| nema doktora/usluga | `return` (bez refresh/changed) | `None` → `_confirm` vraća | DA |
| confirm uspješan | pada na `break`, pa refresh+changed | `return True` → refresh+changed | DA |
| confirm sa `OverlapError`/`ValueError` | `show_error` + `continue` (retry) | identično, `continue` u helperu | DA |
| reject | `store.reject_pending`, `break`, refresh+changed | `return True` → refresh+changed | DA |
| dijalog zatvoren bez akcije | ni jedna grana, `break`, **ipak** refresh+changed (postojeća, pomalo čudna osobina) | `return False`; `_confirm` provjerava `is None` (False nije None) → **ipak** refresh+changed | DA |

Sve pet grana su bit-za-bit ekvivalentne originalu. Refaktor je čist.

### Acceptance

| Kriterij | Status | Dokaz |
|---|---|---|
| sidebar route više nije stub | PASS | `main_window.py`: `zahtjevi` → `RequestsPage`; test potvrđuje |
| pending count se podudara sa servisom | PASS | `count_label` iz `pending_requests()`, isti izvor kao Dashboard |
| confirm/reject radi | PASS | isti `process_pending_request` helper kao Dashboard, testiran |
| nakon obrade lista se osvježi | PASS | `_process` refresh+changed na `True`; potvrđeno adversarno da se NE refreshuje na `False` (vidi napomenu) |
| postojeći dashboard panel ne gubi funkcionalnost | PASS | refaktor bit-za-bit ekvivalentan (tabela gore); postojeći dashboard/process-dialog testovi i dalje prolaze nepromijenjeni |

### Reprodukcija (nezavisna, ne prepisana)

```text
pytest tests/ -q → 254 passed, 11 warnings (identično Codex-ovoj tvrdnji)
ruff check src/dentaland desktop backend tests → All checks passed
mypy src/dentaland desktop backend → Success, 35 source files
```

### Pokušaj obaranja (Korak 4) — adversarni testovi, uklonjeni nakon review-a

1. **Dijalog zatvoren bez akcije u `RequestsPage`** — `RequestsPage._process`
   koristi `if process_pending_request(...):` (truthy check), NE `is None`
   check kao `DashboardPanels._confirm`. Testirao sam: kad helper vrati
   `False` (dijalog zatvoren bez akcije), `if False:` je falsy →
   `RequestsPage` NE zove refresh/`changed.emit()`. **Potvrđeno testom.**
   Ovo je STVARNA asimetrija naspram `DashboardPanels` (koji refreshuje i
   na `False`, "čudna" ali bezopasna postojeća osobina) — vidi napomenu.
2. **Fallback za nedostajući kontakt** (`"Kontakt nije naveden"` kad nema
   ni telefona ni email-a) — nije eksplicitno testiran u Codex-ovom setu
   (samo slučaj sa oba kontakta popunjena). **PASS** kad sam testirao
   ručno.

### `blocking_findings`

Nijedan.

### Napomena (ne blokira)

**Asimetrija refresh-semantike između `DashboardPanels` i `RequestsPage`
za "dijalog zatvoren bez akcije" slučaj.** `DashboardPanels._confirm`
zadržava staru osobinu da UVIJEK refreshuje/emituje `changed` nakon
zatvaranja dijaloga (čak i bez stvarne promjene stanja) jer koristi
`is None` provjeru. `RequestsPage._process` koristi truthy provjeru, pa
NE refreshuje kad se ništa nije promijenilo. Objektivno gledano,
`RequestsPage` ponašanje je ISPRAVNIJE (nepotreban refresh bez promjene
stanja nema smisla) — ali su dva ekrana koja dijele isti helper sada
blago nekonzistentna. Ne utiče na ispravnost (requests_page se svakako
refreshuje pri sljedećem otvaranju rute, `_show_route` to eksplicitno
radi), samo vrijedi da Radovan zna za tu razliku ako se ikad očekuje
identično ponašanje između dva ekrana.

## Probni signal — `.agent/` sloj (potvrđeno protiv Codex-ovog izvještaja)

Konzistentno sa stvarnim scope-om. Codex je pročitao više fajlova (18)
nego prosjek dosadašnjih probnih krugova, ali to odgovara stvarnoj
složenosti zadatka (refaktor dijeljene logike zahtijeva razumijevanje i
`DashboardPanels` i `ProcessRequestDialog` toka prije izmjene). Task
Contract nije imao eksplicitan `allowed_paths` — Codex je scope sam
izveo iz cilja i acceptancea, i ostao unutar njega (potvrđeno kroz `git
diff --stat`: samo GUI/GUI-test/report fajlovi, ništa iz `backend/`,
`web/`, `models.py`, servisne business logike).

## Integration status

`REVIEWED → PASS_WITH_NOTES` — čeka Radovanov human approval, zatim
merge i post-merge integration gate na `main`.

## Handoff

CILJ: zamijeniti sidebar stub stvarnim ekranom za pending online zahtjeve,
bez dupliranja postojeće `DashboardPanels` logike.

URAĐENO: PASS_WITH_NOTES — dedicated `RequestsPage` + izdvojen
`process_pending_request()` helper koji dijele Dashboard i nova stranica;
refaktor `_confirm` provjeren bit-za-bit ekvivalentan originalu. Nema
blocking findings.

NE DIRATI: istorija zahtjeva, CRM/profile/analytics, servisna business
logika, `backend/`/`web/`/`models.py` — nisu dirani, van scope-a.

SLJEDEĆE: Radovanov human approval → merge → post-merge integration gate
na `main`. Ovo je posljednja Prioritet A stavka backloga — nakon merge-a
slijedi Prioritet B (`DENT-IMPROVE-007` backup, `009` packaging).
