---
task_id: DENT-018
risk: LOW
implementer: crush
reviewers: [claude]
verdict: PENDING
commits: []
created_at: 2026-08-19
---

# DENT-018 — mypy cleanup u week_view.py

## Probni signal (.agent/ validacija, drugi krug)

- **Fajlova pročitano prije 1. izmjene:** 5 (`DENT-018-task-contract.md`,
  `.agent/PROJECT_MAP.md`, `.agent/TASK_ROUTING.md`, `week_view.py`,
  `day_view.py`) + grep `main_window.py`/`pyproject.toml` za tip/config.
- **Koristio `.agent/`?** DA — direktno iz `main` (sloj sada merge-ovan);
  "Bug task" paket (PROJECT_MAP "Desktop scheduler" → `week_view.py` +
  GUI testovi) me odveo pravo na metu, bez `ls`/`find`.
- **Pitao za pojašnjenje strukture?** NE.
- **Prekršio scope?** NE (samo `week_view.py` izmijenjen; `.agent/` samo
  validacioni red u tabeli, po eksplicitnom probnom protokolu).

## Šta je urađeno

4 mypy greške uklonjene, čisto type-annotation (bez promjene ponašanja):

- `__init__(self, store: Any, week_start: date, parent: QWidget | None = None)`
  — tipovi za `store`/`parent` (konzistentno sa `day_view.py`).
- `mousePressEvent(self, event: QMouseEvent)` / `dropEvent(self, event: QDropEvent)`
  — tipovi za event parametre.
- `self.setDragDropMode(QTableWidget.DragDrop)  # type: ignore[attr-defined]`
  — PySide6 stub gap (postoji u runtime-u, nedostaje u stubovima).

## Verifikacija

| Komanda | Rezultat |
|---|---|
| `MYPYPATH=src mypy desktop/views/week_view.py` | Success (0 grešaka) |
| `MYPYPATH=src mypy desktop backend src/dentaland` | 2 greške (main_window.py — DENT-019, ne ovaj task) |
| `pytest tests/test_gui/test_week_view.py tests/test_gui/test_week_view_combined.py -q` | 25 passed |
| `ruff check desktop/views/week_view.py` | All checks passed |

## Review

PASS — vidi `2026-08-19-DENT-018-review-claude.md`.

## Integration status

`MERGED → INTEGRATION_VERIFIED → DONE` (2026-08-19). Review: Claude PASS.
Human approval: Radovan ("uradi sve kako si mi napisao", 19.8.2026).
Post-merge: `pytest tests/ -q` → 206 passed, `mypy` → 0 grešaka (potpuno
čist, uklj. DENT-019), `ruff` → čisto.
