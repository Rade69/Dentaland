# REF-10 — Codex independent review (test kvalitet)

```yaml
verdict: REJECT
scope: PASS
acceptance: FAIL
architecture: PASS
security: PASS
blocking_findings:
  - F1: Aktuelni origin/main + REF-10 pada na test_architecture_contracts.py jer sensor jos ocekuje da drag/drop F1 postoji.
```

## CILJ

Provjeriti da DayView/WeekView drag-and-drop mutacija stvarno ide kroz
`AppointmentController`, da je postojeće tiho overlap ponašanje sačuvano, da
weakref promjena ne kvari ostale konzumente i da novi testovi zaista hvataju
povratak direktnog `store.move` poziva.

## URAĐENO

- Potvrđeni branch `task/REF-10-scheduler-drag-drop`, lokalni i remote commit
  `50bad91`.
- Scope commita je šest fajlova: implementer izvještaj, controller, dva view-a
  i dva odgovarajuća GUI test fajla. `desktop/views/main_window.py` nije diran.
- `rg "self\.store\.move" desktop/views/day_view.py desktop/views/week_view.py`:
  nema pogodaka.
- Čista task grana: `pytest tests/ -q` daje **364 passed**, 11 warnings.
- `python -m ruff check src/dentaland desktop backend tests`: **All checks
  passed**.
- `python -m mypy src/dentaland desktop backend`: **Success**, 51 source file.

### Arhitektonska ruta i ponašanje

Oba view-a konstruišu privatni `AppointmentController` i njihov
`move_appointment_to_slot` poziva isključivo
`controller.move_appointment_slot(appt_id, new_start, new_end)`. Controller
delegira jednom na `store.move`; hvata samo kanonski `OverlapError` i vraća
`False`, bez `QMessageBox` ili refresh callbacka. View emituje
`appointment_moved` samo na `True`; `dropEvent` zatim poziva `event.accept()`
na uspjeh, odnosno `event.ignore()` na neuspjeh. Ovo je isto ponašanje kao u
roditeljskom commitu, uz promijenjen receiver mutacije.

`OverlapError` re-export nije mrtav kod: REF-00 contract testovi eksplicitno
provjeravaju identitet `day_view.OverlapError is BookingOverlapError` i isto za
`week_view`. Zadržavanje importa sa `# noqa: F401` je zato opravdano odstupanje
od teksta REF-10 contracta.

Weakref promjena je opravdana i kompatibilna:

- privremeno vraćanje jake closure reference reproducira prijavljenu Qt
  regresiju: prvi pravi-view schedule test prolazi tijelo, zatim teardown pada
  sa `RuntimeError: libshiboken: Internal C++ object (WeekView) already
  deleted`; drugi test potom ne može pravilno početi (`1 passed, 2 errors`);
- sa weakref implementacijom puna task grana prolazi, uključujući
  `test_main_window.py`, `test_requests_panel.py`, controller testove i oba
  stvarna-view schedule testa;
- fallback za ne-weakref-able test roditelje zadržava postojeće
  `SimpleNamespace` controller testove.

### Adversarna provjera novih testova

Privremeno sam u oba view-a vratio direktni `self.store.move(...)`, bez poziva
Controllera. Tačno dva nova route testa tada daju **2 failed**: oba spy-ja
ostaju bez poziva (`calls == []`). Nakon vraćanja produkcijskog koda ista dva
testa daju **2 passed**. Asserti su strogi: provjeravaju tačne argumente
Controller poziva i dodatno dokazuju da spy nije promijenio stanje store-a.

### F1 — integracija sa aktuelnim mainom nije zelena (blocking)

Remote provjera nakon `git fetch origin --prune` pokazuje da je aktuelni
`origin/main` na `4d91141`, a nije ancestor REF-10 commita. Zato broj 372 nije
moguće dobiti na samoj task grani: ona sadrži 364 testa.

U privremenom detached worktree-u sam na `origin/main` primijenio commit
`50bad91` i pokrenuo cijeli suite. Stvarni rezultat je:

```text
373 passed, 1 failed
FAILED tests/test_architecture_contracts.py::test_c_trenutni_main_samo_f1_ostaje
```

Test uveden kroz DENT-IMPROVE-010 i dalje namjerno očekuje nalaze u
`desktop/views/day_view.py` i `desktop/views/week_view.py`, uz komentar da se
očekivanje mora ažurirati kada REF-10 uđe u main. REF-10 upravo uklanja te
nalaze, pa sensor vraća prazan skup i test pada. Ukupan integrisani suite ima
**374**, ne 372 testa (372 na trenutnom mainu + dva REF-10 testa).

Potrebna popravka: u REF-10 scope dodati odgovarajuću izmjenu
`tests/test_architecture_contracts.py` tako da post-REF-10 očekivanje bude
prazan skup, zatim ponoviti puni suite na aktuelnom mainu i dobiti 374 passed.
Ovo nije produkcijska regresija, ali je blocking acceptance nalaz jer se task
trenutno ne može spojiti na main sa zelenim testovima.

Sve privremene mutacije i integracijski worktree su uklonjeni; produkcijski
fajlovi su vraćeni byte-identično commitu `50bad91`.

## NE DIRATI

- Ne uklanjati `OverlapError` re-export dok REF-00 javni contract postoji.
- Ne vraćati jaku View→Controller→View referencu; adversarna provjera
  reproducira stvarni Shiboken teardown kvar.
- Ne mijenjati tihi drag/drop overlap UX niti uvoditi dijalog u
  `move_appointment_slot`.

## SLJEDEĆE

REF-10 ostaje **REJECT** samo zbog F1 integracijskog contract testa. Nakon
minimalne izmjene sensor očekivanja i zelenih **374** testova potreban je
kratak Codex re-review. Tek poslije Codex PASS-a ide Reviewer 2, pa Radovan
human approval.
