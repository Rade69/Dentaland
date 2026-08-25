---
task_id: REF-08
risk: LOW
implementer: pi
reviewers: [codex, claude]
status: "DONE — MERGED u main (merge commit ce2d270, 2026-08-25), post-merge integration gate PASS (355 pytest, ruff, mypy). POSLJEDNJI pojedinačni task u REF-00..08 paketu."
review_summary: >-
  Codex runda 1: REJECT (F1 - PROJECT_MAP.md netacno tvrdio da je
  timezone.py JEDINA SARAJEVO definicija, iako 9 poznatih legacy mjesta
  i dalje postoji). Pi popravio formulaciju (iskljucivo dokumentacija).
  Codex runda 2: PASS. Claude: PASS - theme.py/timezone.py potvrdjeni
  cisti, F1 fix potvrdjen kao iskljucivo dokumentacijski. QSS
  "byte-identican" tvrdnja korigovana (identican tek nakon dedent
  normalizacije, ne blocking). 9 legacy timezone redefinicija ostaju
  poznat, posteno opisan dug (REF-09 kandidat).
created_at: 2026-08-25
merged_at: 2026-08-25
---

# REF-08 — Theme/QSS, timezone dependency i završni cleanup

## Task Contract

**Cilj:** Posljednji cleanup prije finalnog arhitektonskog acceptance
review-a (plan sekcija 20):
1. globalni QSS izlazi iz `main_window.py` u `desktop/presentation/theme.py`;
2. produkcijski View kod prestaje uvoziti timezone iz `desktop.fake_data` —
   nova jedina definicija u `src/dentaland/timezone.py`;
3. PyInstaller build i dalje radi (dokazano stvarnim buildom);
4. `.agent/PROJECT_MAP.md` opisuje finalnu arhitekturu.

**Risk:** `LOW` — behavior-preserving ekstrakcija QSS-a + premještanje
timezone konstante (bez logike, bez baze, bez API contracta). Dvostruki
review (Codex + Claude) po dogovoru za REF paket, nezavisno od risk oznake.

Izvor: `docs/DENTALAND_VIEW_CONTROLLER_SERVICES_REFACTOR_PLAN.md`, sekcija 15.

Zavisnost: REF-04..07 — potvrđeno MERGED (main HEAD `8948d9c`).

## Dio 1 — Theme/QSS

`main_window.py:_apply_style()` (~194 linije QSS + QPalette) → novi
`desktop/presentation/theme.py` (peti fajl u paketu iz REF-06).

**Oblik (moj izbor, obrazloženje):** `theme.py` izlaže:
- `GLOBAL_STYLESHEET: str` — QSS kao čista module-level konstanta
  (lako testabilna, bez Qt instanci);
- `apply_theme(window: QWidget) -> None` — postavlja QPalette na
  `QApplication.instance()` (zadržava postojeći `isinstance` guard) i
  `window.setStyleSheet(GLOBAL_STYLESHEET)`.

`MainWindow._apply_style()` postaje jednoredna delegacija `apply_theme(self)`.
Razlog za ovaj oblik: jedna ulazna tačka, `main_window.py` ne mora znati
detalje palete, a QSS je razdvojen kao konstanta radi testova/čitanja.

## Dio 2 — Timezone (scope EKSPLICITNO ograničen)

`src/dentaland/timezone.py` (novo): `SARAJEVO = ZoneInfo("Europe/Sarajevo")`
— jedina definicija.

Zamijeniti **6** uvoza `from desktop.fake_data import SARAJEVO` →
`from dentaland.timezone import SARAJEVO` (grep potvrđen):

```text
desktop/controllers/schedule_controller.py
desktop/views/blockout_panel.py
desktop/views/day_view.py
desktop/views/dialogs/blockout_delete_confirm.py
desktop/views/main_window.py
desktop/views/week_view.py
```

`desktop/fake_data.py` importuje iz `dentaland.timezone` (plan: "fake_data.py
zatim importuje iz tog modula, ne obrnuto") — ovo NIJE širenje scope-a,
fake_data.py je dio istog problema.

## Dio 3 — PyInstaller build provjera

Stvaran build (`pyinstaller packaging/dentaland.spec`) + pokretanje exe iz
praznog foldera van repoa (bez src/PYTHONPATH, obrazac DENT-IMPROVE-009),
potvrditi da proces ostaje živ (nema ImportError). Provjeriti da
`dentaland.timezone` i `desktop.presentation.theme` ne trebaju eksplicitan
spomen u spec-u (očekivano NE trebaju — `pathex=[ROOT, ROOT/src]` + statički
importi; provjera kroz warn fajl + živ proces).

## Dio 4 — MainWindow cilj poslije REF-08

Provjeriti da nema OČIGLEDNOG propuštenog posla osim theme/timezone. Ako
nađem nešto → `OUT_OF_SCOPE_FINDING`, ne popravljati usput.

## Dio 5 — .agent/PROJECT_MAP.md

Ažurirati da opisuje finalnu arhitekturu: `desktop/controllers/`
(appointment/schedule/request/print), `desktop/presentation/`
(schedule_status/schedule_palette/theme), `src/dentaland/services/`
(appointments/availability/settings/requests/notifications/print_schedule),
`src/dentaland/timezone.py`.

## Acceptance

- [ ] globalni theme više nije ugrađen u MainWindow workflow kod;
- [ ] production view (6 mjesta) ne zavisi od fake_data za timezone;
- [ ] PyInstaller build i dalje radi — dokazano stvarnim buildom;
- [ ] `.agent/PROJECT_MAP.md` opisuje stvarno stanje;
- [ ] preostalih 9 SARAJEVO redefinicija prijavljeno kao OUT_OF_SCOPE_FINDING, ne dirano.

## Allowed paths

```text
desktop/presentation/theme.py                (novo)
desktop/views/main_window.py
desktop/views/day_view.py
desktop/views/week_view.py
desktop/views/blockout_panel.py
desktop/views/dialogs/blockout_delete_confirm.py
desktop/controllers/schedule_controller.py
desktop/fake_data.py
src/dentaland/timezone.py                     (novo)
.agent/PROJECT_MAP.md
agent_reports/**
```

## Forbidden paths

```text
desktop/views/dialogs/appointment_details.py
desktop/views/dialogs/appointment_editor.py
desktop/views/dialogs/cancel_appointment.py
desktop/views/dialogs/delete_appointment.py
desktop/views/dialogs/move_appointment.py
desktop/views/dialogs/process_request.py
desktop/views/requests_page.py
src/dentaland/services/notifications.py
src/dentaland/services/print_schedule.py
desktop/controllers/appointment_controller.py
desktop/controllers/request_controller.py
desktop/controllers/print_controller.py
models.py
migrations/**
backend/**
```

## OUT_OF_SCOPE_FINDING (prijavljeno, ne diram)

`SARAJEVO = ZoneInfo("Europe/Sarajevo")` je NEZAVISNO REDEFINISANA (ne
uvezena — doslovno ista linija kopirana) na 9 dodatnih mjesta:

```text
src/dentaland/services/notifications.py:40
src/dentaland/services/print_schedule.py:27
desktop/views/dialogs/appointment_details.py:21
desktop/views/dialogs/appointment_editor.py:32
desktop/views/dialogs/cancel_appointment.py:17
desktop/views/dialogs/delete_appointment.py:23
desktop/views/dialogs/move_appointment.py:27
desktop/views/dialogs/process_request.py:20
desktop/views/requests_page.py:23
```

Ovo je veći problem od onoga što plan opisuje (redundancija, ne samo pogrešan
izvor), ali konsolidacija svih 9 bi dramatično proširila scope LOW taska
(servisni sloj + svi dialozi). Predloženi budući task: REF-09 ili poseban
cleanup — konsolidovati preostalih 9 u `dentaland.timezone`. NE diram ta 9
mjesta u ovom tasku.

## Verification

```bash
pytest tests/ -q
ruff check src/dentaland desktop backend tests
mypy src/dentaland desktop backend
pyinstaller packaging/dentaland.spec --noconfirm   # stvaran build + smoke
```

Baseline izmjeren na ovom worktree-u prije koda: **355 passed**.

## Review

Codex (test kvalitet, prvi) pa Claude (arhitektura) — posljednji
pojedinačni REF review prije finalnog paketnog acceptance review-a. Radovan
human approval obavezan prije merge-a.

## Koordinacija

Worktree `Dentaland-worktrees/REF-08-theme-timezone-cleanup`, grana
`task/REF-08-theme-timezone-cleanup` (sa main-a `8948d9c`). Claim postavljen
prije koda.
