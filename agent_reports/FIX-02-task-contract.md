---
task_id: FIX-02
risk: LOW
implementer: pi
reviewers: [claude]
status: "Implementacija (Pi) + review (Claude): PASS. Vidi agent_reports/2026-08-21-FIX-02-pi.md i .../2026-08-21-FIX-02-review-claude.md. Čeka commit + human approval prije merge-a."
created_at: 2026-08-21
---

# FIX-02 — Popraviti edit trajanja termina

## Task Contract

**Cilj:** U `AppointmentEditorDialog` edit mode ispravno prefilluje
stvarno trajanje postojećeg termina (`_prefill()`, iz `end - start`), ali
odmah nakon toga konstruktor bezuslovno poziva
`_apply_service_duration(self.service_combo.currentIndex())` (linija
~132–134 u `desktop/views/dialogs/appointment_editor.py`), što prepisuje
upravo prefillovano trajanje default trajanjem trenutno izabrane usluge.

Primjer greške: usluga "Plomba" ima default 60 min, postojeći termin
traje 90 min (ručno produženo). Otvaranje "Uredi termin" bi trebalo
pokazati 90 min, ali trenutno pokazuje 60 min.

**Root cause (već lociran, ne treba ponovo istraživati):**
`desktop/views/dialogs/appointment_editor.py`, `__init__`:
- linija 91: `self._prefill(appointment)` — ispravno postavlja
  `duration_edit` na stvarnih 90 min (linije 168–180).
- linije 132–135: bezuslovni poziv
  `self._apply_service_duration(self.service_combo.currentIndex())` prije
  `connect()`-a na `currentIndexChanged` — ovaj poziv se dešava i u edit
  modu i prepisuje duration nazad na default usluge.

**Risk:** LOW

**Izvor:** `docs/dentaland-desktop-korektivni-plan.md`, sekcija 2
(PRIORITET 2). Pun kontekst korektivnog plana (FIX-01 do FIX-06) tamo —
ovaj task pokriva SAMO FIX-02, ne šire.

## Pravilo (create vs edit mode)

- **Create mode**: početno trajanje dolazi iz odabrane (prve) usluge;
  promjena usluge ažurira trajanje. Ovo već radi ispravno — ne mijenjati.
- **Edit mode**: početno trajanje mora ostati stvarno postojeće trajanje
  termina (iz `_prefill()`); konstruktor ga NE SMIJE odmah prepisati
  defaultom usluge. Tek ako korisnik naknadno ručno promijeni uslugu u
  combo-u, `_apply_service_duration` (već povezan na
  `currentIndexChanged`) smije predložiti novo default trajanje — to
  ponašanje već postoji i mora ostati netaknuto.

**Predložen minimalan fix:** uslovi inicijalni poziv
`_apply_service_duration(...)` sa `if not is_edit and ...` (varijabla
`is_edit` već postoji u `__init__`, linija 57). `connect()` na
`currentIndexChanged` ostaje bezuslovan u oba moda — to je ispravno i ne
treba ga dirati.

Ne implementirati alternativni pristup (npr. flag `_suppress_duration_sync`)
ako gornji jednostavan uslov rješava problem — ne komplikovati bez razloga.

## Allowed paths

```text
desktop/views/dialogs/appointment_editor.py
tests/test_gui/test_appointment_dialog.py
```

## Forbidden paths

```text
src/dentaland/models.py
migrations/
src/dentaland/services/booking.py
desktop/views/dialogs/base_dialog.py
desktop/views/week_view.py
desktop/views/day_view.py
desktop/views/main_window.py
```

## Obavezni regression testovi

1. Edit mode ne gubi ručno trajanje:
   ```text
   usluga "Plomba" default = 60
   postojeći termin duration = 90
   otvori edit dialog → duration_edit.value() == 90
   ```
2. Ručna promjena usluge u edit modu i dalje radi (postojeće ponašanje,
   ne smije regresirati):
   ```text
   otvoren edit dialog (duration prefilled na 90)
   korisnik ručno promijeni service_combo na uslugu sa default 45
   duration_edit.value() == 45
   ```
3. Create mode i dalje bira default trajanje prve usluge pri otvaranju
   (postojeći test ne smije regresirati — provjeriti da već postoji, ako
   ne postoji dodati ga).

## Acceptance criteria

- [ ] Edit mode: `duration_edit` pri otvaranju pokazuje stvarno trajanje
      termina, ne default usluge.
- [ ] Edit mode: ručna promjena usluge i dalje ažurira trajanje na novi
      default (postojeće ponašanje netaknuto).
- [ ] Create mode: ponašanje potpuno nepromijenjeno (default trajanje
      prve usluge pri otvaranju, ažuriranje pri promjeni usluge).
- [ ] Nema izmjena van `allowed_paths`.
- [ ] Nema izmjena šeme/migracija.

## Verification

```bash
pytest tests/ -q
ruff check src/dentaland desktop backend tests
mypy src/dentaland desktop backend
```

Baseline za poređenje (izmjereno 21.8.2026 na `main` nakon
`DENT-IMPROVE-006`): pytest 254 passed, ruff clean, mypy clean (0 issues,
35 fajlova). Novi testovi treba da povećaju taj broj, ne smanje ga; ruff
i mypy moraju ostati čisti.

## Review

Claude, nezavisan od implementera (implementer piše `agent_report`,
Claude review sa stvarnom reprodukcijom prije human approval-a — LOW
risk ne zahtijeva obavezan human approval prema tabeli u
`docs/dentaland-agentski-razvoj.md`, ali Radovan ipak odlučuje da li ga
traži za ovaj task).

## Koordinacija — obavezno prije početka

Provjeri `python scripts/coordination.py status` prije `claim` na
`desktop/views/dialogs/appointment_editor.py`. Radi u zasebnom git
worktree (`Dentaland-worktrees/FIX-02-<slug>`, grana `task/FIX-02-<slug>`).
