# REF-11 — Codex independent review (test kvalitet)

```yaml
verdict: REJECT
scope: PASS
acceptance: REJECT
architecture: PASS
security: PASS
blocking_findings:
  - F1: blockout GUI testovi ne razlikuju Controller delegaciju od starog direktnog View -> Service poziva
```

## CILJ

Provjeriti da novi `BlockoutController` ostaje čista delegacija, da su
create/delete error i refresh tokovi ponašajno identični ranijem kodu, da
View više nema direktne mutacije i da testovi genuinski zaključavaju
Controller put.

## URAĐENO

- Potvrđeni grana `task/REF-11-blockout-controller`, commit `9bd105c` i ista
  pušovana remote grana.
- Commit dira samo dozvoljene putanje: novi
  `desktop/controllers/blockout_controller.py`,
  `desktop/views/blockout_panel.py`, Task Contract status i implementer
  izvještaj. `main_window.py` i svi forbidden paths nisu dirnuti.
- `BlockoutController` ima samo `_store` assignment i dva delegacijska
  poziva. Nema validacije, grananja, hvatanja izuzetaka, transformacije
  podataka, refresh-a ili PySide6/SQLAlchemy zavisnosti.
- Diff `blockout_panel.py` mijenja samo import, konstrukciju privatnog
  Controllera i receiver dvije mutacijske metode:
  `self.store.X` -> `self._blockout_controller.X`. `try`, isti exception
  tipovi, `_show_error(str(exc))`, `return`, `refresh()` i `changed.emit()`
  ostali su byte-for-byte isti u diff kontekstu.
- `_on_save` i dalje hvata `(OverlapError, ValueError)`; `_on_delete` i dalje
  hvata `ValueError`. Inline error label/layout nije mijenjan.
- `rg "self\.store\." desktop/views/blockout_panel.py`: **0 pogodaka**.
  Read-only `doctors` i `list_time_off` ostaju kroz postojeći
  `getattr(self.store, ...)`, a ne `self.store.<metoda>` sintaksu.
- Jedini produkcijski slušalac `blockout_panel.changed` ostaje
  `MainWindow._refresh_dashboard` (`main_window.py:162`); signalna topologija
  nije mijenjana.

## BLOCKING FINDING

### F1 — postojeći create/delete testovi daju lažni PASS na starom putu

`test_save_validan_poziva_create_time_off` i
`test_delete_uz_potvrdu_poziva_delete_time_off`
(`tests/test_gui/test_blockout_panel.py:77-127`) provjeravaju samo krajnji
fake-store zapis i osvježen panel. Nema testa koji posmatra
`BlockoutController`, niti testa koji bi zabranio direktnu View mutaciju.

Adversarna provjera je privremeno vratila oba originalna poziva:

```python
self.store.create_time_off(doctor_id, start, end, reason)
self.store.delete_time_off(block.id)
```

Na toj pokvarenoj verziji pokrenuti su baš relevantni create/delete GUI
testovi:

```text
2 passed in 0.23s
```

Testovi bi zato prihvatili povratak F2 nalaza zbog kojeg REF-11 postoji.
Mutacija je potpuno vraćena; `blockout_panel.py` ponovo ima isti Git blob
hash kao HEAD (`f56bbe0a...`).

Kao i REF-09, trenutna produkcijska implementacija jeste ispravna, ali nema
regresijsku sigurnosnu mrežu za ključni acceptance invarijant. Prema REF
test-quality standardu ovo je blocking finding i verdict ostaje `REJECT`.

Minimalan robustan runtime test treba zamijeniti
`panel._blockout_controller` spy/fake objektom, postaviti direktne store
mutacijske metode da odmah bace `AssertionError`, zatim kroz stvarni klik
potvrditi:

- `create_time_off(doctor_id, start, end, reason)` ide tačno Controlleru;
- `delete_time_off(block_id)` ide tačno Controlleru;
- uspješan Controller poziv i dalje radi `refresh` + `changed.emit`;
- Controller izuzetak i dalje daje isti inline error i ne emituje `changed`.

Odvojen mali unit test za `BlockoutController` treba dokazati transparentnu
delegaciju i propagaciju izuzetaka bez obrade. Statička AST zabrana
mutacijskih `self.store.*` poziva u View-u može biti dopunska zaštita, ali
runtime delegacijski test je važniji.

## STANDARDNA VERIFIKACIJA

Na čistom commitu `9bd105c`, poslije vraćanja mutacije:

```text
python -m pytest tests/ -q --basetemp=.tmp-ref11-full
355 passed, 11 warnings in 14.71s

ruff check src desktop backend tests --no-cache
All checks passed!

mypy src desktop backend --no-incremental
Success: no issues found in 51 source files
```

## NE DIRATI

- Ne premještati inline prezentaciju greške ili refresh/signal logiku u
  Controller; Task Contract eksplicitno zahtijeva tanak facade.
- Ne mijenjati `main_window.py` ili REF-09/10/12 putanje.
- Ne mijenjati servisni sloj, modele, migracije ili backend.
- Reviewer nije implementirao test popravku.

## SLJEDEĆE

Implementer treba dodati runtime delegacijske testove koji padaju kada
`BlockoutPanel` ponovo direktno pozove store, ponoviti obje mutacije i punu
verifikaciju, pa vratiti REF-11 Codexu na re-review. Claude review i Radovan
human approval dolaze nakon Codex PASS-a.
