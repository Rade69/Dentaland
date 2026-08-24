# REF-00 — Mapa ključnih ponašanja → testovi

Ova mapa je sigurnosna mreža za REF-01..08: bilježi koje ponašanje koji
postojeći test zaključava, i šta je dodato u REF-00. Ne mijenja produkcioni
kod — samo testovi i ova dokumentacija.

## 1. Workflow → testovi (postojeći)

| Workflow | Štiti ga |
|---|---|
| create appointment | `test_services.py::test_create_*` (bez konflikta, odbija preklapanje, drugi doktor); `test_gui/test_appointment_dialog.py` (editor polja, validacija, get_data); `test_gui/test_main_window.py::test_klik_na_slot_otvara_editor_i_dodaje_termin` |
| edit | `test_services.py::test_update_*` (podaci/doktor/vrijeme/usluga, overlap, exclude self, terminalni); `test_gui/test_appointment_dialog.py::test_edit_*` |
| move | `test_services.py::test_move_*`; `test_gui/test_destructive_dialogs.py::test_move_dialog_*`; `test_gui/test_week_view.py` + `test_day_view.py` drag-drop testovi |
| cancel | `test_services.py::test_cancel_*`; `test_gui/test_destructive_dialogs.py::test_cancel_dialog_*`; `test_main_window.py::test_cancel_na_terminalnom_terminu_prikazuje_poruku` |
| delete | `test_services.py::test_delete_*`; `test_main_window.py::test_delete_akcija_*` / `test_delete_odustani_*` / `test_delete_nepostojeceg_*`; `test_destructive_dialogs.py::test_delete_dialog_*` |
| status transitions | `test_services.py::test_mark_*` (arrived/unarrived/confirmed/completed/no_show, nevalidne tranzicije); `test_main_window.py::test_context_action_confirm/completed`; `test_appointment_details_dialog.py` (akcije po statusu) |
| web request confirm/reject | `test_requests.py::test_confirm_*` / `test_reject_*`; `test_backend.py::test_confirm_*` / `test_reject_*` (201/204/409/404); `test_gui/test_process_request_dialog.py`; `test_gui/test_requests_panel.py`; `test_gui/test_requests_page.py` |
| Day/Week switch | `test_main_window.py::test_dan_dugme_prebacuje_na_day_view` / `test_dan_pa_danas_*`; `test_day_view.py`, `test_week_view.py` |
| doctor filter | `test_week_view_combined.py::test_filter_*`; `test_main_window.py::test_tabovi_za_doktore_postoje` / `test_unos_u_svi_doktori_*`; `test_week_view.py::test_visible_doctor_counts_nezavisno_od_filtera` |
| TimeOff/block rendering | `test_services.py::test_timeoff_i_split_shift_pauza` / `test_create_time_off_*` / `test_list_time_off_*` / `test_delete_time_off_*`; `test_week_view.py::test_blockout_je_spojen_*`; `test_day_view.py::test_day_view_prikazuje_blockout` / `test_klik_na_blockout_*`; `test_blockout_panel.py` |
| print action | `test_print_document.py` (day/week dokumenti, logo, bez kontakt podataka); `test_print_schedule.py`; `test_main_window.py::test_stampaj_dugme_postoji` |
| status summary | `test_main_window.py::test_footer_prikazuje_brojno_stanje_*` / `test_status_legenda_odvojeno_broji_*` / `test_context_action_completed_osvjezava_status_summary`; `test_day_view.py::test_visible_status_counts_za_dan`; `test_week_view.py::test_visible_doctor_counts_*` |

## 2. Nalazi: postojeći testovi koji diraju implementacijski detalj

Ovo NIJE greška koju treba popraviti u REF-00 (ne prepravljamo postojeće) —
nego zabilješka da se REF-03/04/06 ne oslanjaju na ove kao "contract":

- `test_gui/test_main_window.py::test_status_legend_html_je_kompaktan_bez_overflow_regresije`
  provjerava inline HTML (`font-size:10px`, broj `&nbsp;`). To je
  **prezentacijski detalj**, NAMJERNO zaključan poslije FIX-03 (adversarno
  dokazano da deterministički pada na buggy kodu). Nije poslovni contract.
- `test_gui/test_week_view.py::test_status_ikonice` (parametrizovan) zaključava
  mapiranje status → simbol (`✓`, `◷`, `!`, `✗`) — ovo je blizu "contracta"
  (vizuelni identitet), ali za REF-06 treba ostati svjestan da je simbol
  prezentacijska odluka, ne servisni contract.
- Geometrijski testovi (`width()/sizeHint()`): postojeći
  `test_footer_ostaje_vidljiv_na_laptop_visini` i
  `test_legenda_doktora_je_poravnata_sa_desnim_panelima` se oslanjaju na
  geometriju. FIX-03 presedan je pokazao da geometrijsko poređenje može dati
  lažan PASS na buggy kodu — REF-00 **ne dodaje nove** geometrijske testove,
  a REF-paket ne smije tretirati geometriju kao invarijantu bez adversarne
  provjere.
- `day_view.py` uvozi privatni simbol `_status_key` iz `week_view.py`
  (`from desktop.views.week_view import STATUS_META, WeekView, _status_key,
  status_icon`) — prekoračenje granice modula preko privatnog simbola. Ovo
  je poznati "arhitektonski dug" koji REF-06 rješava; NIJE contract, i
  REF-00 ga namjerno NE zaključava kao da jeste.

## 3. Dodato u REF-00

### `tests/test_ref00_overlap_error_contract.py`

Baseline za DVIJE odvojene `OverlapError` klase (najkritičniji nalaz za
REF-01):

- `booking.OverlapError` ≠ `requests.OverlapError` (isto ime, različita klasa);
- `dentaland.services.OverlapError` re-eksportuje `booking` klasu;
- `backend.main.OverlapError` je `requests` klasa (→ confirm overlap vraća
  409, ne 500);
- desktop view-ovi `main_window`/`day_view`/`week_view`/`blockout_panel`
  hvataju `booking` klasu, a `requests_panel` hvata `requests` klasu;
- behavior: `AppointmentService.create` baca `booking` klasu,
  `confirm_request` baca `requests` klasu.

### `tests/test_ref00_service_api_contract.py`

Javni API surface koji REF-03 (razbijanje `booking.py`) mora očuvati:

- imena javnih metoda `AppointmentService` (bez vodećeg underscore-a);
- polja svih javnih DTO-ova;
- `dentaland.services.__all__` re-eksport;
- vrijednosti `AppointmentStatus` enum-a.

Namjerno NIJE zaključano: privatne metode (`_check_overlap`, `_to_dto`,
`_require_doctor`, ...), redoslijed importa, interne SQL upite.

## 4. Granica za reviewer-e

- **Codex** (test kvalitet): svaki novi test je "invariant koji se može
  pokvariti" — `OverlapError` testovi padaju ako REF-01 objedini klase na
  pogrešan način (npr. backend počne hvatati booking klasu); API contract
  testovi padaju ako REF-03 izgubi/renomira javnu metodu ili DTO polje.
- **Claude** (arhitektura): novi testovi zaključavaju SAMO javni contract
  (imena metoda/DTO polja/status enum), ne privatne detalje; OverlapError
  testovi dokumentuju **trenutno** (namjerno) stanje koje REF-01 treba da
  SVJESNO promijeni — oni su mjera "šta se mijenja", ne zabrana promjene.
