---
task_id: DENT-002
risk: MEDIUM
implementer: pi
reviewers: [claude]
verdict: PASS_WITH_NOTES
commits: []
created_at: 2026-08-16
---

# DENT-002 — Desktop GUI ljuska (sedmični kalendar + unos termina)

## Task Contract

Vidi `agent_reports/DENT-002-task-contract.md` za pun tekst (napisan naknadno zbog izgubljenog konteksta — vidi napomenu o procesu u tom fajlu).

## Šta je urađeno

- `desktop/fake_data.py` — `@dataclass Appointment` + `FakeStore` (in-memory repo), IANA zona `Europe/Sarajevo` (aware datetime), `FakeStore.seeded()` za demo podatke.
- `desktop/views/week_view.py` — `WeekView(QTableWidget)`: 7 kolona (dani) × 20 redova (08:00–18:00, 30-min slotovi), klik na prazan slot emituje `slot_selected`, prevlačenje zauzetog slota poziva `move_appointment_to_slot`.
- `desktop/views/appointment_dialog.py` — `AppointmentDialog`: ime/telefon/email/usluga/napomena, bez validacije (namjerno, slobodna forma).
- `desktop/views/main_window.py` — `MainWindow`: `WeekView` kao centralni widget, akcija "Štampaj raspored" (TODO stub sa status bar porukom), povezuje `slot_selected` → dijalog → `store.create()`.
- `desktop/app.py` — ulazna tačka (`QApplication` + seed podaci).
- `tests/test_gui/` — `conftest.py` (offscreen QPA platforma, fixtures) + 3 test fajla, 9 testova.

## Verifikacija (nezavisno ponovo pokrenuto od strane reviewera, ne preuzeto iz izvještaja)

| Komanda | Rezultat |
|---|---|
| `pytest tests/test_gui -v` (QT_QPA_PLATFORM=offscreen) | 9 passed |
| `ruff check desktop tests/test_gui` | All checks passed |
| `grep -ri sqlalchemy desktop/` | Samo u docstring komentaru (`fake_data.py`), nula stvarnih importa |

## Review (Claude, 16.8.2026)

```yaml
verdict: PASS_WITH_NOTES
scope: PASS
acceptance: PASS
architecture: PASS
security: PASS
blocking_findings: []
```

Svih sedam acceptance stavki iz Task Contracta nezavisno potvrđeno čitanjem koda i ponovnim pokretanjem testova:

1. Sedmični prikaz je početni ekran (`MainWindow.setCentralWidget(self.week_view)` direktno u konstruktoru) — ✓
2. Klik na prazan slot → dijalog bez međuekrana (`_on_slot_selected` direktno otvara `AppointmentDialog`) — ✓
3. Prevlačenje ažurira vrijeme na fake podacima (`move_appointment_to_slot`, testirano) — ✓
4. Napomena slobodan tekst (`QPlainTextEdit`, eksplicitno bez validacije) — ✓
5. Dugme "Štampaj raspored" postoji, štampa je TODO stub — ✓
6. Nula SQLAlchemy importa u `desktop/` — ✓ (arhitekturno pravilo poštovano od prve linije)
7. GUI testovi za klik-za-unos i prevlačenje (`pytest-qt`, offscreen) — ✓

Scope čist: dirano samo `desktop/**` i `tests/test_gui/**`, ništa iz `forbidden_paths`.

**Napomene (ne blokiraju, LOW):**
- Test prevlačenja (`test_prevlacenje_termina_azurira_vrijeme`) poziva `move_appointment_to_slot()` direktno, ne simulira stvaran Qt mouse-drag gest kroz `dropEvent`. Standardna i razumna praksa (end-to-end drag simulacija je krhka u headless testovima), ali znači da `mousePressEvent`/`dropEvent` wiring nije direktno pokriven testom — samo logika koju oni pozivaju.
- `pyproject.toml` i dalje nema `PySide6`/`pytest-qt` kao deklarisanu zavisnost (Pi je ispravno pratio `forbidden_paths` i nije to dirao) — testovi trenutno prolaze samo zato što je PySide6 globalno instaliran na ovoj mašini (6.11.1). Ovo mora biti dodano u `pyproject.toml` prije merge-a, inače projekat nije reproducibilan na drugoj mašini. Dodaje se zajedno sa DENT-001 zavisnostima prije zajedničkog merge-a (dogovoreno sa Radovanom).

Verdikt: **PASS_WITH_NOTES**. Jedan reviewer je dovoljan za MEDIUM — pregled završen.

## Integration status

NOT_MERGED — čeka DENT-001 (zajednički merge dogovoren sa Radovanom) i dodavanje PySide6/pytest-qt zavisnosti u `pyproject.toml`.
