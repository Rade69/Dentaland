# REF-07 — Codex independent review (test kvalitet)

```yaml
verdict: PASS_WITH_NOTES
scope: PASS
acceptance: PASS
architecture: PASS
security: PASS
blocking_findings: []
```

## CILJ

Provjeriti da su request-processing i print workflow premješteni u controllere
bez promjene ponašanja, lomljenja REF-00 compatibility ugovora ili uvođenja
direktnog persistence pristupa u controller sloj.

## URAĐENO

- Potvrđeni remote branch `task/REF-07-request-print-controllers`, commit
  `fcf58a3` i base `e251ad4` kao ancestor.
- `pytest tests/ -q`: **355 passed**, 11 warnings.
- Zasebni REF-00 safety net (`test_ref00_service_api_contract.py` +
  `test_ref00_overlap_error_contract.py`): **19 passed**, 1 warning;
  testovi su neizmijenjeni.
- `ruff check src/dentaland desktop backend tests`: čist.
- `mypy src/dentaland desktop backend`: čist, **45 source fajlova**.
- Scope odgovara allowed paths. `day_view.py`, `week_view.py`, presentation,
  dialogs, services, backend, modeli i migracije nisu dirani.
- `request_controller.py` i `print_controller.py` nemaju `sqlalchemy`,
  `select(` niti `session.` pristup.
- Adversarna provjera OverlapError re-exporta: privremeno uklanjanje importa iz
  `requests_panel.py` uzrokovalo je očekivani pad
  `test_desktop_requests_panel_hvata_requests_klasu` sa `AttributeError`.
  Mutacija je vraćena. Re-export je stvarni compatibility ugovor, ne mrtav kod.
- `RequestController.process_pending_request` poređen je sa baznim
  `requests_panel.process_pending_request`: dohvat doktora/usluga, early
  `None`, konstrukcija dijaloga, `while True`, čitanje akcije/vrijednosti,
  `confirm_pending`, zajednički `OverlapError`/`ValueError` handling,
  `show_error`+retry, reject i cancel return vrijednosti preneseni su istim
  redoslijedom. Promijenjen je samo receiver `store` → `self._store`.
- Retry nije ostao bez testa: postojeći
  `test_requests_panel.py` pravi overlap kroz stvarni servis, potvrđuje dva
  `dialog.exec()` poziva, jednu inline grešku i zatim reject. Monkeypatch je
  mehanički premješten na novi controller modul.
- Print metode su sadržajno prenesene iz MainWindow-a: iste menu opcije i
  grananje, isti week/day build redoslijed, isti landscape flagovi, isti PDF
  dijalog i isti `_pick_day` Qt tok. MainWindow sada samo konstruiše controller
  i veže oba print triggera na `on_print`.

### Napomene koje ne blokiraju

- Task Contract je, po priznatom zapisu u samom ugovoru, napisan nakon početka
  implementacije. To je proceduralno kršenje pravila „contract prije koda“,
  ali stvarni scope odgovara naknadno zapisanom ugovoru.
- Novi PrintController testovi direktno pokrivaju `print_week` i oba
  `save_pdf` ishoda, ali ne pokrivaju `on_print` routing, `print_day` i
  `_pick_day`. Statičko poređenje potvrđuje identičan prijenos, pa ovo nije
  blocking za behavior-preserving extraction, ali su ti tokovi slabije
  zaštićeni od budućih regresija.

## NE DIRATI

- Ne uklanjati `requests_panel.OverlapError` re-export dok REF-00 ugovor i
  postojeći potrošači zahtijevaju tu putanju.
- Ne premještati request business rules ili print data pripremu iz servisnog
  sloja u controllere.
- Ne dirati REF-06 Day/Week/presentation teritoriju u REF-07.

## SLJEDEĆE

Claude radi zaseban REF-07 Reviewer 2 arhitektonski pregled. Radovan human
approval dolazi nakon oba review-a. Dodatno print test pokriće može se dodati
u budućem test-hardening tasku bez blokiranja REF-07.
