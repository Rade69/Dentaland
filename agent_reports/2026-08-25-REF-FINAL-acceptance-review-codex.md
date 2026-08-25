# REF-00..08 — Codex finalni arhitektonski acceptance audit

```yaml
package_assessment: NOT_FULLY_ACCEPTED
package_goal: PARTIALLY_ACHIEVED
controller_to_sqlalchemy_findings: 0
known_accepted_debt_confirmed: 4
new_findings:
  - F1: drag_and_drop_move_bypasses_controller
  - F2: blockout_mutations_bypass_controller
  - F3: settings_mutations_bypass_controller
  - F4: dashboard_status_mutations_bypass_controller
recommended_follow_up: REF-09+
```

## CILJ

Nezavisno provjeriti cijeli rezultat REF-00..08 na `main` HEAD-u
`ed692ea`, bez oslanjanja na pojedinačne implementer/reviewer tvrdnje i bez
implementacije popravki. Paket je znatno popravio strukturu, ali planov
arhitektonski acceptance nije u potpunosti ostvaren: četiri aktivna UI toka
i dalje rade mutaciju `View -> Service -> View refresh` bez Controllera.

## METODA I STANDARDNA VERIFIKACIJA

- Audit je urađen na `main` HEAD-u `ed692ea14d374e7ceadbcd9bd7a82c5fb9adb144`.
- `python -m pytest tests/ -q`, sa `TEMP`/`TMP` usmjerenim u workspace:
  **355 passed**, 12 warnings, 14.66 s.
- Prvi pytest pokušaj sa sistemskim tempom dao je 284 passed / 71 setup
  error, svi zbog `PermissionError: [WinError 5]` nad
  `%TEMP%/pytest-of-radovan`; to nije test ili produktni kvar.
- `ruff check src desktop backend tests`: **All checks passed**.
- `mypy src desktop backend`: **Success: no issues found in 50 source files**.
- `ruff check .` nije projektni aplikacijski scope i nalazi pet postojećih
  lint nalaza u `scripts/coordination.py`; to ne mijenja traženi rezultat za
  `src/`, `desktop/`, `backend/` i `tests/`, ali je zabilježeno radi potpune
  reproduktivnosti.

## 12 STVARNIH TOKOVA

Legenda: `OK` znači da je primarni tok slojevit; `FAIL` znači da postoji
stvaran korisnički put koji preskače Controller. Linije su na `ed692ea`.

| # | Tok i stvarna putanja | Provjera granice / duplikacije |
|---|---|---|
| 1 | **Create** — `main_window.py:257` ili prazan slot (`day_view.py:345`, `week_view.py:413`) -> signali na `main_window.py:182,185` -> `AppointmentController.on_slot_selected` (`appointment_controller.py:68`) -> `AppointmentService.create` (`booking.py:70`) -> `appointments.create_appointment` (`appointments.py:64`; session/overlap/add/commit `75-90`) -> `AppointmentDTO` -> controller refresh (`appointment_controller.py:102`) -> `MainWindow._refresh_dashboard` (`main_window.py:383-389`) -> `ScheduleController.refresh` (`schedule_controller.py:99-105`). | **OK.** Nema View->Service mutacije, Controller SQL-a ni druge create odluke. `main_window.py:404-408` je samo compatibility delegacija. |
| 2 | **Edit** — context signal (`day_view.py:298`, `week_view.py:422`) -> veze `main_window.py:184,187` -> `handle_appointment_action`/`edit_appointment` (`appointment_controller.py:156,104`) -> `AppointmentService.update` (`booking.py:93`) -> `appointments.update_appointment` (`appointments.py:94`; DB `113-132`) -> DTO -> controller refresh (`appointment_controller.py:142`) -> scheduler refresh. | **OK.** Jedna business odluka u appointment modulu; facade i Controller delegiraju. |
| 3 | **Move** — modalni tok: context signal -> `AppointmentController.move_appointment` (`appointment_controller.py:198`) -> facade `booking.py:206` -> `appointments.move_appointment` (`appointments.py:355`; overlap/DB/commit `361-373`) -> DTO -> refresh (`appointment_controller.py:212`). Drag&drop tok, međutim, ide `DayView.move_appointment_to_slot` (`day_view.py:349`) -> `store.get`/`store.move` (`350,363`) -> signal tek poslije mutacije (`366`) -> MainWindow samo poziva `ScheduleController.refresh` (`main_window.py:130-134`). Week ekvivalent je `week_view.py:464,465,474,477`. | **FAIL — F1.** View direktno mutira servis, a Controller dobija samo post-factum refresh. Postoje dva koordinatora iste move odluke: AppointmentController za modal i oba View-a za drag&drop. |
| 4 | **Cancel** — scheduler context -> `AppointmentController.cancel_appointment` (`appointment_controller.py:214`) -> facade `booking.py:148` -> `appointments.cancel_appointment` (`appointments.py:261`; DB/DTO `263-270`) -> controller refresh (`227`). Dashboard dugme, ipak, poziva `RequestsPanel._cancel_scheduled` -> `self.store.cancel` direktno (`requests_panel.py:138,148-151`) -> `changed` -> `MainWindow._refresh_dashboard` (`main_window.py:142`). | **FAIL — dio F4.** Ista cancel poslovna akcija ima Controller put i direktan View put. |
| 5 | **Status confirm/arrived/completed/no_show** — scheduler context -> `AppointmentController.handle_appointment_action` (`appointment_controller.py:156`) -> facade status metode (`booking.py:139-157`) -> `appointments.py` status funkcije (`219-315`) -> DTO -> refresh. Dashboard potvrda ide direktno `RequestsPanel._confirm_scheduled` -> `self.store.mark_confirmed` (`requests_panel.py:144-146`) -> `changed` -> refresh. | **FAIL — F4.** Controller put je ispravan, ali dashboard duplira status koordinaciju bez Controllera. |
| 6 | **Delete** — context signal -> `AppointmentController.delete_appointment` (`appointment_controller.py:229`) -> facade `booking.py:151` -> `appointments.delete_appointment` (`appointments.py:274`; DB `285-290`) -> `None` -> controller refresh (`appointment_controller.py:242`) -> scheduler. | **OK.** Nema drugog aktivnog delete workflow-a. |
| 7 | **Web request pending -> confirm/reject** — `RequestsPage`/dashboard action (`requests_page.py:231`, `requests_panel.py:154`) -> `RequestController.process_pending_request` (`request_controller.py:28`) -> facade `confirm_pending`/`reject_pending` (`booking.py:169,174`) -> `requests.confirm_request`/`reject_request` (`requests.py:77,117`; DB/overlap/commit `85-128`) -> bool/DTO rezultat -> Controller -> `changed` (`requests_page.py:233`, `requests_panel.py:157`) -> MainWindow refresh (`main_window.py:142,158`). | **OK za processing odluku.** Jedna while/dialog/error-handling implementacija. Panel i puna stranica dijele isti Controller. |
| 8 | **Day refresh** — Dan dugme (`main_window.py:245,356`) -> `ScheduleController.show_day_view` (`schedule_controller.py:132`) -> `refresh` (`99`) -> `_active_range` (`68-75`) -> facade `appointments_for_range` (`booking.py:129`) -> `appointments.appointments_for_range` (`appointments.py:180`; `selectinload` `197-198`) -> DTO lista + blokovi -> `DayView.render_schedule` (`day_view.py:115`) -> status/doctor callbacks (`schedule_controller.py:103-105`). | **OK.** Jedan appointment snapshot; skriveni View se ne renderuje. |
| 9 | **Week refresh** — Sedmica dugme (`main_window.py:250,362`) -> `ScheduleController.show_week_view` (`schedule_controller.py:136`) -> isti range/facade/service/DTO tok -> `WeekView.render_schedule` (`week_view.py:214`) -> callbacks. | **OK.** Day/Week više ne fetchuju raspored u `render_schedule`; isti snapshot hrani render i brojače. |
| 10 | **Print** — meni/dugme (`main_window.py:179,262`) -> `PrintController.on_print` (`print_controller.py:46`) -> `build_week_schedule`/`build_day_schedule` (`print_controller.py:60,67`; `print_schedule.py:96,105`) -> `AppointmentService.all_combined`/doctors/time-off reads (`print_schedule.py:120` i helperi) -> SQLAlchemy samo u servisima -> `PrintSchedule` -> Controller -> `build_*_document`/`preview_document` (`print_controller.py:61,68,76-78`). | **OK.** Print nema View->Service zaobilaženje ni Controller SQL; nema UI refresh jer je rezultat preview/PDF. `all_combined()` je namjerno zadržan print read API. |
| 11 | **TimeOff/blockout** — panel forma -> `BlockoutPanel` direktno poziva `store.create_time_off`/`delete_time_off` (`blockout_panel.py:181,195`) -> facade (`booking.py:189-204`) -> `availability.create_time_off`/`delete_time_off` (`availability.py:153,203`) -> DB/result -> panel `changed` (`187,200`) -> MainWindow refresh (`main_window.py:162`) -> ScheduleController čita blokove (`schedule_controller.py:85-95`) -> View render. | **FAIL — F2.** Ne postoji blockout Controller; mutacija ide View->Service. |
| 12 | **Settings doctor/service/working-hours** — SettingsPanel UI handleri direktno pozivaju `set_doctor_active`, `add_service`, `update_service`, `set_working_hours` (`settings_panel.py:161,224,242,338`) -> facade (`booking.py:209-236`) -> `settings.py:65,78,101,152` -> DB/DTO -> `changed` (`settings_panel.py:165,229,247,343`) -> MainWindow refresh (`main_window.py:166`). | **FAIL — F3.** Settings business granica u servisu je dobra, ali nema SettingsController i View koordinira mutacije. |

## MJERLJIVI KRITERIJUMI IZ SEKCIJE 21

| Kriterijum | Nezavisni rezultat |
|---|---|
| `grep -rn "sqlalchemy\|select(\|session\." desktop/views/` | Doslovni obrazac daje **2 lažna pozitivna** pogotka u `sidebar.py:199,202` zbog lokalne metode `_select(`. Posebna provjera `sqlalchemy` i `session.` daje 0; u View-ovima nema SQLAlchemy importa/API poziva. Semantički kriterijum je **PASS**, doslovno očekivanje „0 grep pogodaka“ nije ostvareno zbog imena `_select`. |
| `grep -rn "from PySide6" src/dentaland/services/` | **0 pogodaka — PASS.** |
| Controller -> SQLAlchemy | `rg "sqlalchemy|select\(|session\." desktop/controllers`: **0 — PASS.** |
| Jedan overlap source of truth | Kanonski `availability.validate_appointment_overlap` je `availability.py:64`; koriste ga `appointments.py:76,123,368` i `requests.py:100`. Nema druge appointment-overlap SQL odluke. `_check_timeoff_overlap` (`availability.py:213`) je drugi domen/invarijant, ne duplikat. **PASS.** |
| MainWindow ne implementira CRUD/status | REF-04 commit `06dfd4f` je izvukao workflow; trenutno MainWindow samo konstruiše/povezuje Controller (`main_window.py:116,182-187`) i zadržava tanke compatibility delegacije (`404-420`). **PASS.** |
| Settings nije u appointment servisu | Mutacije i working-hours su u `settings.py`; `appointments.py` ostaje appointment CRUD/status/read sloj. Facade samo delegira. **PASS.** |
| DayView ne koristi WeekView kao utility | `rg week_view desktop/views/day_view.py`: **0 — PASS.** Shared status/palette su u `desktop/presentation/`. |
| Day/Week koriste range query | `ScheduleController._fetch_appointments` (`schedule_controller.py:77-83`) koristi `appointments_for_range`; service implementacija `appointments.py:180`. **PASS**, uz postojeći fallback `all()` za kompatibilne fake store-ove. |
| Nema N+1 doctor/service | `selectinload(Appointment.doctor/service)` na `appointments.py:197-198`; REF-02 query-count test ostaje u punom prolazu. **PASS.** |
| Jedan scheduler refresh = jedan dataset | `ScheduleController.refresh` fetchuje appointment listu jednom (`schedule_controller.py:99-103`) i istim render cache-om računa oba summary-ja (`104-105`). Real Day/Week integracijski query-count testovi prolaze. **PASS.** |
| pytest / Ruff / mypy | **355 passed; Ruff aplikacijski scope čist; mypy 50 fajlova čist.** |

## POZNATI, RANIJE PRIHVAĆENI DUG — POTVRĐENO

Ovo nisu novi nalazi i nisu razlog ocjene `NOT_FULLY_ACCEPTED`:

1. **Lazy pogled Controllera nazad u View:** `AppointmentController` uvozi
   dialog klase iz `desktop.views.main_window` unutar metoda na
   `appointment_controller.py:69,105,145,199,215,230`. Opis u
   `.agent/CURRENT_STATE.md:56` je tačan.
2. **Čitanje privatnog MainWindow stanja:** `getattr` za `_doctors`,
   `_has_doctors`, `_current_doctor_id` je na `appointment_controller.py:48-54`.
   Opis u `CURRENT_STATE.md:58` je tačan.
3. **Duplirana doctor-filter kopija:** MainWindow drži
   `_current_doctor_id` (`main_window.py:101,443`), ScheduleController svoju
   (`schedule_controller.py:56,140`). Opis u `CURRENT_STATE.md:59` je tačan.
4. **Devet legacy timezone definicija:** pored kanonskog
   `dentaland/timezone.py`, modulsku konstantu i dalje definišu
   `notifications.py`, `print_schedule.py`, `requests_page.py` i šest dialog
   fajlova. To je tačno devet kako piše u `CURRENT_STATE.md:66-67`.
   Dodatni lokalni `ZoneInfo(...)` izrazi postoje u drugim funkcijama, ali
   nisu dio dokumentovane tvrdnje o devet modulskih `SARAJEVO` redefinicija.

## NOVI CROSS-TASK NALAZI

### F1 — HIGH: drag&drop move zaobilazi AppointmentController

REF-04 je centralizovao modalni move, a REF-05 je promijenio redraw u signal,
ali zajedno su ostavili DB mutaciju u oba scheduler View-a. Signal
`appointment_moved` ne prenosi zahtjev Controlleru; emituje se tek nakon
`store.move`, a MainWindow ga veže direktno na refresh. Zbog toga test da se
View ne re-fetchuje može proći dok View i dalje mutira bazu.

**Preporuka:** novi task koji uvodi request signal (`appointment_move_requested`)
ili drugi Controller callback; jedino Controller treba pozvati `store.move`,
obraditi `OverlapError` i pokrenuti refresh. Oba View-a treba svesti na
računanje drop cilja i emitovanje namjere.

### F2 — HIGH: TimeOff create/delete nema Controller

`BlockoutPanel` direktno donosi odluku da pozove create/delete servis i tek
zatim emituje `changed`. Ovo je eksplicitni `View -> Service -> View` tok iz
sekcije 20.

**Preporuka:** `BlockoutController` (ili širi AvailabilityController) koji
preuzima create/delete workflow, greške i refresh signalizaciju.

### F3 — HIGH: Settings mutacije nemaju Controller

Iako je REF-03 dobro razdvojio `settings.py` od appointments servisa, četiri
aktivna SettingsPanel handlera i dalje direktno mutiraju store. Servisna
granica jeste bolja, ali puna View->Controller->Service arhitektura nije
uspostavljena.

**Preporuka:** `SettingsController` za doctor activation, service CRUD i
working-hours mutation. Panel treba emitovati namjeru/unos i renderovati
rezultat.

### F4 — MEDIUM/HIGH: dashboard duplira appointment status/cancel koordinaciju

REF-07 je uveo RequestController samo za web pending zahtjeve. Isti
`RequestsPanel` zadržava direktne `mark_confirmed` i `cancel` pozive za već
zakazane termine, dok AppointmentController već implementira te odluke za
scheduler. To je i zaobilaženje i dvije koordinacijske implementacije iste
business akcije.

**Preporuka:** proslijediti dashboard appointment akcije kroz zajednički
AppointmentController/API (ili zaseban Controller koji delegira istom
workflow-u), bez direktnog store poziva u panelu.

## ZAVRŠNA OCJENA

REF paket je ostvario većinu tehničkih ciljeva: monoliti su razbijeni,
MainWindow više ne nosi appointment workflow, booking je tanak facade,
Controlleri nemaju SQLAlchemy, servisi nemaju PySide6, overlap je
centralizovan, range/eager-load/snapshot read put je ispravan, a kompletna
test/lint/type provjera prolazi.

Ipak, plan daje binaran acceptance uslov: ako ijedan application workflow
ide `View -> Service -> View` bez Controllera, plan nije završen. Takvi putevi
postoje u četiri mjesta i obuhvataju četiri od traženih 12 tokova (Move,
Cancel/Status alternativa, TimeOff i Settings). Zato cilj paketa nije potpuno
ostvaren i finalni arhitektonski acceptance trenutno ne treba proglasiti
PASS-om.

Preporuka je otvoriti najmanje jedan novi REF-09+ task (po mogućnosti
odvojene taskove za scheduler drag&drop, blockout/settings i dashboard
appointment akcije), uz characterization testove koji eksplicitno dokazuju
da nijedan View ne poziva mutacijske metode store-a. Četiri već dokumentovana
kompromisa iz `CURRENT_STATE.md` ostaju prihvaćen dug i ne treba ih miješati
sa ovim novim nalazima.

## NE DIRATI

- Ovaj audit nije implementirao niti mijenjao produkcijski kod/testove.
- Ne tretirati četiri potvrđena `CURRENT_STATE.md` kompromisa kao novootkrivene
  blockere.
- Ne vraćati appointment read path na `all_combined`; range + eager-loading +
  jedan ScheduleController snapshot su potvrđeno ispravni.

## SLJEDEĆE

Claude radi zaseban nezavisan paketni audit. Nakon poređenja oba nalaza,
Radovan odlučuje scope REF-09+ korekcija; human acceptance cijelog paketa
treba sačekati zatvaranje novih F1-F4 ili eksplicitnu promjenu kriterijuma iz
plana.
