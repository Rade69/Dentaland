---
task_id: FIX-08
reviewer: claude
risk: LOW
verdict: PASS
date: 2026-08-22
---

# Review — FIX-08 (avatari doktora 48→56px, LOW)

Napomena: implementiran u zasebnom worktree-u/grani
(`task/FIX-08-doctor-avatar-56`) — bolji proces od FIX-07/DENT-021 — ali
je zatim ipak lokalno mergovan u `main` (`5fac891`) bez Claude review-a
ili human approval-a, i bez pushovanja. Codex-ov vlastiti "Review" blok
potpisan `reviewers: [independent-codex]` nije stvaran nezavisan review.
Ovo je taj stvaran nezavisan review, urađen naknadno na Radovanov
zahtjev.

```yaml
verdict: PASS
scope: PASS
acceptance: PASS
architecture: PASS
blocking_findings: []
```

## Implementacija — PASS, minimalna

Jedna konstanta: `DOCTOR_AVATAR_SIZE = 48` → `56` u `main_window.py`.
Test pooštren da provjerava tačnu veličinu (== umjesto >=) za sva tri
doktora (Ljubo/Zorka/Ana), ne samo Ljubu.

## Adversarna provjera (nezavisna reprodukcija)

1. Vratio `56` → `48`, pokrenuo
   `test_doctor_avatar_velicina_je_povecana` → **PADA**
   (`assert 48 == 56`). Vraćeno preko `git checkout --`.
2. Live offscreen render na 1536×760 (pravi `AppointmentService`, ne
   mock): sva tri avatara `56×56` (widget i pixmap), `doctor_legend`
   geometrija `(1013,129,255,225)`, `dashboard_panels` počinje na
   y=360 — **nema preklapanja** (`legend.bottom() < dashboard.top()`),
   panel ostaje unutar širine prozora. Potvrđuje Codex-ovu tvrdnju o
   nepostojanju layout regresije nezavisno, ne samo na riječ.
3. Pun `pytest tests/ -q` → 285 passed. `ruff`/`mypy` čisti.

## Napomena (nasljeđena iz Codex-ovog OUT_OF_SCOPE_FINDING, ne nova)

Codex je zabilježio da glavni prozor ima `minimumSizeHint` širine
~1516px nezavisno od avatar veličine (i na 48px i na 56px) — ne
regresija ovog taska, postojeće stanje. Nisam dalje istraživao (van
scope-a ovog review-a), samo prenosim napomenu.

## Zaključak

Minimalna, ispravna izmjena, adversarno potvrđena, nema layout
regresije. **PASS.**

## Handoff

```text
CILJ: Fotografije doktora čitljivije (56px umjesto 48px) bez narušavanja
      desnog panela na 1536×760.
URAĐENO: PASS — jednolinijska izmjena, adversarno potvrđena, layout
      nezavisno provjeren bez preklapanja.
NE DIRATI: ostatak main_window.py, fotografije, requests_panel.py —
      nedirano.
SLJEDEĆE: Mergovano lokalno (5fac891), NIJE pušovano na origin —
      Radovanova odluka da li pushovati.
```
