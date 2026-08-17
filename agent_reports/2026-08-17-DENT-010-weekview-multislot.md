---
task_id: DENT-010
risk: MEDIUM
implementer: crush
reviewers: [claude]
verdict: PASS
commits: []
created_at: 2026-08-17
---

# DENT-010 — WeekView: termini duži od jednog slota prikazani preko svih ćelija

Porijeklo: `OUT_OF_SCOPE_FINDING` prijavljen tokom DENT-003 review-a.

## Task Contract

Pun tekst u `agent_reports/DENT-010-task-contract.md`. Suština: termin duži od
`SLOT_MINUTES` mora biti vizuelno spojen preko svih ćelija koje pokriva
(`setSpan`) i sve te ćelije tretirane kao zauzete za klik i drag&drop — ne samo
prva. Backend provjera preklapanja (`booking.py`) je već tačna, ne dira se.

## Šta je urađeno

Samo `desktop/views/week_view.py` + testovi:

- `_cell_span(appt)` — izračunava početnu ćeliju i broj slotova (`span`) koje
  termin pokriva, ograničen na raspoložive redove (`min(span, rowCount - row)`).
- `_visible_appointments()` — filtrirani termini sa (ćelija, span).
- `_appointments_by_cell()` — sada mapira SVE ćelije koje termin pokriva (ne
  samo početnu), tako da klik/drag provjera vidi "sredinu" termina kao zauzetu.
- `refresh()` — `clearSpans()` + `setSpan(row, col, span, 1)` za termine duže od
  slota; grupiše termine po početnoj ćeliji (max span, više doktora u istoj
  ćeliji).
- `move_appointment_to_slot()` — vraćena GUI-side provjera da je drop cilj
  slobodan (isključujući sam termin), uz postojeći `OverlapError` catch.
- `mousePressEvent`/`dropEvent` — koriste `rowAt`/`columnAt` + `_appointments_by_cell`
  umjesto `itemAt`, da drag/drop radi na cijelom spojenom regionu, ne samo na
  prvoj ćeliji.

## Verifikacija (stvarni rezultati)

| Komanda | Rezultat |
|---|---|
| `pytest tests/ -q` | 76 passed |
| `ruff check desktop tests` | All checks passed |
| `grep -ri sqlalchemy desktop/views/*.py` | prazno (OK) |

## Odbačene opcije

- Prikaz termina kao zasebni item na svakoj ćeliji (bez `setSpan`) — odbačeno:
  contract traži vizuelno spajanje; `setSpan` je traženi pristup.
- Oslanjanje na `itemAt` za drag na spojenom regionu — odbačeno: Qt ponašanje
  za item unutar spana je ambiguitet; `rowAt`/`columnAt` + `_appointments_by_cell`
  je determinističko.

## Review

```yaml
verdict: PASS
scope: PASS
acceptance: PASS
architecture: PASS
security: PASS
blocking_findings: []
```

Prvobitni blocking finding (mypy regresija, `week_view.py:176`) ispravljen
od strane Crush-a — `self.item(row, col)` rezultat preimenovan u
`cell_item` + `assert cell_item is not None` odmah nakon dodjele.
Nezavisno provjereno (ne samo implementerova tvrdnja): `mypy src/dentaland
desktop` → 8 grešaka (baseline vraćen, bilo 9), `pytest tests/ -q` → 76
passed, `ruff check desktop tests` → All checks passed. Popravka je
jednoredna i mehanička, nije otvorila novi rizik — nije bio potreban novi
krug reviewa.

Sve ostalo prošlo bez primjedbi (iz prvobitnog reviewa): `_cell_span`/`setSpan` pristup je tačno
ono što je contract tražio, `_appointments_by_cell` sada ispravno mapira
SVE pokrivene ćelije (rješava i klik-usred-termina i drag-u-sredinu),
`rowAt`/`columnAt` zamjena za `itemAt`/`indexAt` je ispravna reakcija na
Qt-ovu ambigvitet oko hit-testinga unutar spojenog regiona. Testovi
pokrivaju sve acceptance stavke (60/90/30-min slučajevi, klik na
pokrivenu ćeliju, drag u pokrivenu ćeliju), uključujući i kombinovani
prikaz (DENT-006 multi-doctor). Nula SQLAlchemy importa potvrđeno
(`grep -ri sqlalchemy desktop/views/*.py` prazno). Backend/servisni sloj
nedirnut, kako je i traženo.

Poslije jednoreda popravke, zadatak ide na human approval (Radovan) —
nije potreban novi krug reviewa za ovu veličinu ispravke.

## Integration status

NOT_MERGED — čeka human approval (Radovan) prije merge-a u `main`.
