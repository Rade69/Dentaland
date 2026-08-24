---
task_id: DENT-IMPROVE-009
risk: MEDIUM
implementer: pi
reviewers: [claude]
status: "DONE — MERGED u main (merge commit cb980a6, 2026-08-24), post-merge integration gate PASS (298 pytest, ruff, mypy). Clean-machine test na fizički drugoj mašini ostaje Radovanova provjera (vidi review napomenu)."
created_at: 2026-08-24
merged_at: 2026-08-24
---

# DENT-IMPROVE-009 — Windows packaging + clean-machine test

## Task Contract

**Cilj:** Reproducibilan Windows build desktop aplikacije koji se može
pokrenuti na računaru bez development environmenta (bez source checkout-a),
sa uključenim resursima (logo, fotografije doktora, ikonica) i baza koja se
piše u user data folder. Plus clean-machine smoke test (simuliran, jer nema
fizičke čiste mašine).

**Risk:** MEDIUM (distribution — dodaje build konfiguraciju i dokumentaciju,
ne mijenja runtime logiku).

Izvor: `docs/DENTALAND_IMPROVEMENT_BACKLOG.md`, sekcija 10.

## Odluke (već donesene — ne otvarati ponovo, obrazloženje se zapisuje)

- **PyInstaller, ne Nuitka** — najstandardnija i najbolje dokumentovana opcija
  za PySide6; dovoljno za obim jedne desktop aplikacije (CLAUDE.md: ne
  over-engineering za klijenta koji ne postoji).
- **`--onedir`, ne `--onefile`** — onefile ima sporiji cold-start
  (raspakivanje u temp pri svakom pokretanju) i češće false-positive
  antivirus detekcije; onedir je operativno pouzdaniji za app koji se
  pokreće svaki dan.
- **Samo desktop app se pakuje** — backend (FastAPI) i web/ javna forma su
  van obima (Faza 0 je čisto lokalni desktop, bez interneta).

## Šta uraditi

1. **Build config** — `packaging/dentaland.spec` (PyInstaller spec, izbor:
   spec fajl umjesto programatskog build skripta, jer je deklarativan,
   čitljiv i standardan za PyInstaller):
   - `Analysis(['desktop/app.py'])`, `EXE(console=False)` (GUI app);
   - `datas` uključuju `web/assets/` i `desktop/assets/doctors/` tako da se
     poklapaju sa `paths.resource_path()` layout-om (`sys._MEIPASS` grana) —
     testirati da grana stvarno radi, ne samo da kod postoji;
   - `icon` = generisani `.ico` (iz `web/assets/logo.png`, kroz Pillow);
   - ime build-a `Dentaland`.
2. **Ikonica** — generisati `web/assets/dentaland.ico` iz postojećeg
   `web/assets/logo.png` (Pillow, već dostupan; dodati ga kao dev dependency
   za reproducibilnost). Referencirati ga u spec-u.
3. **`pyproject.toml`** — dodati `pyinstaller` i `pillow` u
   `[project.optional-dependencies].dev` (nova build grupa nije potrebna —
   mali projekat, dev grupa je dovoljna).
4. **Dokumentacija** — `docs/dentaland-windows-packaging.md` (isti stil kao
   `docs/dentaland-backup-operativni-vodic.md`): tačna build komanda, gdje
   exe završi, clean-machine test koraci, poznata ograničenja. Plus kratka
   dopuna u README (link na vodič).
5. **Clean-machine smoke test (simuliran)** — pokrenuti izgrađen `.exe` iz
   PRAZNOG foldera VAN repoa (bez src/PYTHONPATH dostupnih), sa
   `DENTALAND_DATA_DIR` na svjež scratch folder, i dokazati prvi start
   (kreiranje baze + resursi). Pošto nema fizičke čiste mašine/VM-a, jasno
   dokumentovati ŠTA je stvarno testirano vs. šta ostaje za Radovana da
   potvrdi na drugoj mašini — ne tvrditi "clean machine potvrđeno".

## Out of scope (eksplicitno iz backloga)

- auto-update,
- enterprise deployment,
- telemetry.

Ne dodavati ništa od toga.

## Allowed paths

```text
pyproject.toml
packaging/dentaland.spec
docs/dentaland-windows-packaging.md
web/assets/dentaland.ico      (novi generisani fajl)
README.md                     (kratka dopuna + link)
agent_reports/**
```

## Forbidden paths

```text
src/dentaland/services/**
src/dentaland/models.py
migrations/
backend/
web/                          (osim novog dentaland.ico)
desktop/views/**              (nema UI izmjena — samo pakovanje postojećeg)
```

Izuzetak (prijaviti eksplicitno ako se desi): ako `resource_path()` ili
`_resolve_db_path()` trebaju genuinsku izmjenu da bi bundle radio — jedini
opravdan izuzetak, prijaviti šta i zašto.

## Acceptance kriterijumi (backlog)

- build ne zavisi od source checkout-a,
- baza se piše u user data folder,
- resursi se učitavaju,
- testirana je druga mašina/VM (ovdje: najbliža realna simulacija na istoj
  mašini, jasno označena kao simulacija).

## Verification

```bash
pytest tests/ -q
ruff check src/dentaland desktop backend tests
mypy src/dentaland desktop backend
```

Plus stvaran, uživo izgrađen `.exe` i stvaran, uživo pokrenut smoke test
ciklus (svih 8 backlog koraka), sa tačnim, neparafraziranim zapisom šta se
desilo u svakom koraku.

Baseline (24.8.2026, `main`): provjeriti tačan broj na svom worktree-u prije
početka, ne pretpostaviti.

## Review

Claude, nezavisan od implementera (jedini reviewer za MEDIUM). Nakon PASS-a,
Radovanov human approval je obavezan (MEDIUM tok) prije merge-a.

## Koordinacija — obavezno prije početka

Provjeri `python scripts/coordination.py status` prije `claim`. Radi u
zasebnom git worktree (`Dentaland-worktrees/DENT-IMPROVE-009-windows-packaging`,
grana `task/DENT-IMPROVE-009-windows-packaging`).
