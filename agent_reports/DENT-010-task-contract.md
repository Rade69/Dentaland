---
task_id: DENT-010
risk: MEDIUM
implementer: crush
reviewer: claude
status: ASSIGNED
created_at: 2026-08-17
---

# Task Contract — DENT-010

Porijeklo: `OUT_OF_SCOPE_FINDING` prijavljen tokom DENT-003 review-a (vidi
`agent_reports/2026-08-16-DENT-003-servisni-sloj.md`).

```yaml
id: DENT-010
title: WeekView — termini duži od jednog slota prikazani preko svih ćelija koje pokrivaju
risk: MEDIUM
objective: >
  WeekView._appointments_by_cell() trenutno mapira termin na SAMO JEDNU
  ćeliju (početni 30-min slot), bez obzira na stvarno trajanje. Termin od
  npr. 60 min (Plomba) vizuelno "zauzima" samo prvi slot — naredni slot
  izgleda prazan iako ga termin realno pokriva. Backend (AppointmentService)
  ispravno odbija preklapanje bez obzira na ovo (testirano u DENT-003), ali
  GUI prikaz ne odgovara stvarnosti — korisnik vidi "prazan" slot koji
  zapravo nije slobodan dok ga ne pokuša zauzeti.

  Popraviti da termin duži od SLOT_MINUTES bude vizuelno spojen preko svih
  ćelija koje pokriva (npr. QTableWidget.setSpan za vertikalno spajanje
  ćelija u istoj koloni), i da _appointments_by_cell() (ili ekvivalent)
  tretira SVE te ćelije kao zauzete — ne samo prvu — za potrebe klika
  (spriječiti unos u "sredini" postojećeg termina) i drag&drop provjere.

  Ne mijenjati servisni sloj (booking.py) — problem je isključivo u GUI
  prikazu, backend provjera preklapanja je već tačna i testirana.
allowed_paths: [desktop/views/week_view.py, tests/test_gui/test_week_view.py, tests/test_gui/test_week_view_combined.py, agent_reports/**]
forbidden_paths: [desktop/fake_data.py, desktop/views/main_window.py, desktop/views/sidebar.py, desktop/views/requests_panel.py, desktop/views/stub_page.py, desktop/views/appointment_dialog.py, src/dentaland/services/booking.py, src/dentaland/services/requests.py, src/dentaland/models.py, migrations/**, backend/**, web/**, CLAUDE.md, AGENTS.md, docs/**]
acceptance:
  - Termin od 60 min (2 slota) je vizuelno spojen preko obje ćelije u svojoj koloni.
  - Termin od 90 min (3 slota) je vizuelno spojen preko sve tri ćelije.
  - Klik na BILO KOJU ćeliju koju pokriva postojeći termin (ne samo prvu) NE otvara dijalog za novi unos.
  - Drag&drop i dalje radi za termine bilo kojeg trajanja (regresija se ne smije desiti — postojeći testovi iz DENT-003/006 moraju i dalje proći).
  - Termini od tačno jednog slota (30 min, najčešći slučaj) izgledaju identično kao prije — nema vizuelne regresije za osnovni slučaj.
  - Nula SQLAlchemy importa u desktop/views/.
verification:
  - pytest tests/ -q
  - ruff check desktop tests
  - "grep -ri sqlalchemy desktop/views/*.py  # očekivano prazno"
review:
  reviewers: 1
  required: [architecture, scope]
```

## Napomena

Ne diraj `desktop/views/main_window.py` ni ostale DENT-009 fajlove —
Codex tamo paralelno radi na sidebar redizajnu. `week_view.py` je jedini
fajl koji ovaj zadatak dira, i eksplicitno je van DENT-009 obima
(forbidden_paths tamo), tako da nema preklapanja.
