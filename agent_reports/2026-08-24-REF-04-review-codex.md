# REF-04 — Codex independent review (test kvalitet)

```yaml
verdict: PASS_WITH_NOTES
scope: PASS
acceptance: PASS
architecture: PASS
security: PASS
blocking_findings: []
```

## CILJ

Nezavisno provjeriti da REF-04 stvarno premješta appointment workflow iz
`MainWindow` u `AppointmentController` bez promjene ponašanja, narušavanja
slojeva ili slabljenja postojećeg GUI safety net-a.

## URAĐENO

- Potvrđena grana `task/REF-04-appointment-controller`, implementacijski commit
  `06dfd4f` i base `3e3d11b`.
- `pytest tests/ -q`: **341 passed**, 11 warnings.
- `pytest tests/test_gui/test_main_window.py -q` na REF-04: **32 passed**.
- Isti fajl na izolovanom base stanju `3e3d11b`: **32 passed**. Postojeći GUI
  safety net nije mijenjan niti smanjen.
- `ruff check`: čist.
- `mypy`: čist, 42 source fajla.
- Scope diff sadrži samo ugovor/izvještaj, novi controller paket i test,
  `appointment_controller.py` te očekivanu izmjenu `main_window.py`.
  Zabranjeni `desktop/views/dialogs/**`, day/week view, servisni sloj, backend,
  modeli i migracije nisu dirani.
- `appointment_controller.py` nema `sqlalchemy`, `select(` niti `session.`
  pristup. Podacima pristupa isključivo kroz postojeći store/facade.
- Reverse import dijaloga je zaista lazy: svaki `from
  desktop.views.main_window import ...` nalazi se unutar workflow metode.
  `main_window.py` može zato top-level uvesti controller bez cikličnog importa
  tokom inicijalizacije modula.
- Potvrđen konkretan razlog za late binding. U
  `test_delete_akcija_trajno_uklanja_termin_kroz_pravi_servis` `MainWindow` se
  konstruira prije `monkeypatch.setattr(main_window_mod,
  "DeleteAppointmentDialog", FakeDeleteDialog)`. Privremena mutacija koja je
  dijalog vezala u konstruktoru Controllera uzrokovala je da taj test pozove
  pravi modal i ne završi u nametnutom roku od 8 sekundi. Mutacija je vraćena.
- Čistiji constructor DI sa jednom rano spremljenom klasom zato nije
  kompatibilan sa zabranom izmjene postojećih GUI testova. Provider/lambda ili
  zaseban dialog registry mogli bi zadržati late lookup bez povratnog importa,
  ali bi dodali novu infrastrukturu izvan cilja ovog taska. Trenutni lazy
  import je razuman ograničeni kompatibilnosni kompromis; Claude treba
  procijeniti njegov dugoročni arhitektonski trošak.
- Tanke `MainWindow` delegacije nisu proizvoljne: postojeći testovi direktno
  pozivaju `_handle_appointment_action`, `_cancel_appointment` i
  `_delete_appointment`. Potpuno premještene metode nemaju isti direktni legacy
  testni poziv.
- `on_slot_selected` retry-on-`OverlapError` petlja poređena je s baznim kodom:
  konstrukcija dijaloga, `exec`, `get_data`, provjera doktora i poruka,
  računanje kraja, `set_doctor`, `create`, `show_error`, retry/break i završni
  refresh zadržani su istim redoslijedom. Razlike su samo receiveri prilagođeni
  Controlleru (`self._store`, parent i refresh callback).
- Pet novih controller testova direktno pokrivaju create+refresh, stvarni
  overlap retry, status delegaciju, mapiranje `ValueError` u warning i
  delete+refresh. Zajedno s neizmijenjena 32 `MainWindow` testa daju adekvatan
  testni dokaz za ovaj extraction task.

### Napomena o procesu

Task Contract postoji i njegov `allowed_paths`/`forbidden_paths` sadržaj odgovara
stvarnom diff-u, ali je po priznanju implementera napisan retroaktivno. To krši
pravilo „Task Contract prije koda“, ali nije promijenilo scope niti acceptance
rezultat, pa nije blocking finding. Dodatno, implementer izvještaj tvrdi da je
ugovor „napisan PRIJE koda“; tu netačnu procesnu tvrdnju treba ispraviti radi
audit traga.

## NE DIRATI

- Ne mijenjati postojeće `tests/test_gui/test_main_window.py` samo radi čišćeg
  DI obrasca u ovom tasku.
- Ne premještati dijaloge niti uvoditi novi registry/provider bez zasebnog
  ugovorenog arhitektonskog taska.
- Ne dirati servisni sloj, day/week view, backend, modele ili migracije u okviru
  REF-04.

## SLJEDEĆE

Claude radi Reviewer 2 arhitektonski pregled, posebno dugoročne granice
Controller/View i lazy-import kompromisa. Radovan human approval dolazi tek
nakon oba review-a.
