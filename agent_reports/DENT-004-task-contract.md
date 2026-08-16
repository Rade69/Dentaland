---
task_id: DENT-004
risk: MEDIUM
implementer: pi
reviewer: claude
status: REVIEWED — vidi 2026-08-16-DENT-004-backup.md za pun izvještaj
created_at: 2026-08-16
---

# Task Contract — DENT-004

```yaml
id: DENT-004
title: Faza 0 — Backup mehanizam (SQLite backup API + enkripcija)
risk: MEDIUM
objective: >
  Implementirati automatski backup SQLite baze prema
  docs/dentaland-razvojni-plan-v3.1.md sekcija "Backup mehanizam":
  backup ide isključivo kroz sqlite3.Connection.backup() API, NIKAD
  sirovo kopiranje .db fajla (rizik korupcije zbog WAL nekonzistentnosti).
  Backup se prvo lokalno kreira kroz taj API, ZATIM enkriptuje, pa se tek
  enkriptovana kopija stavlja u cloud sync folder (Google Drive/Dropbox
  lokalni folder — sam sync nije u obimu, samo priprema fajla za njega).
  Ključ za dekripciju NE smije biti u istom folderu kao backup.

  Minimalni zahtjevi: dnevni automatski backup (funkcija koja se može
  pozvati iz schedulera — sam scheduler/cron nije u obimu ovog zadatka),
  rotacija (npr. zadrži 30 dnevnih + nekoliko mjesečnih, stariji se
  brišu), evidencija zadnjeg uspješnog backupa (npr. timestamp fajl),
  funkcija za restore (dekriptuje + vraća bazu) sa testom koji dokazuje
  round-trip (backup pa restore daje identičnu bazu).

  Izbor biblioteke za enkripciju je na tebi — zaključaj PONAŠANJE
  (simetrična enkripcija, ključ odvojen od podataka, autentifikovana
  enkripcija ako moguće), ne referenciraj konkretnu biblioteku kao
  cilj. Predlog: `cryptography` (Fernet) je razuman default za ovaj
  obim, ali opravdaj izbor u Odbačenim opcijama ako biraš nešto drugo.
allowed_paths: [src/dentaland/backup.py, pyproject.toml, tests/test_backup.py, agent_reports/**]
forbidden_paths: [src/dentaland/models.py, migrations/**, desktop/**, CLAUDE.md, AGENTS.md, docs/**]
acceptance:
  - Backup ide isključivo kroz sqlite3.Connection.backup(), nikad shutil.copy ili slično.
  - Backup fajl je enkriptovan PRIJE nego što bi bio stavljen u sync folder — plain .db nikad ne izlazi iz lokalnog koraka.
  - Ključ za dekripciju je odvojen od backup foldera (testabilno — putanja ključa != putanja backup foldera).
  - Rotacija stara backupe po pravilu, testabilna logika čišćenja.
  - Restore funkcija postoji, test dokazuje round-trip (backup → restore → identična baza, provjereno npr. preko sadržaja tabela).
  - Evidencija zadnjeg uspješnog backupa (timestamp zapisan negdje čitljivo).
verification:
  - pytest tests/test_backup.py -v
  - ruff check src/dentaland/backup.py
review:
  reviewers: 1
  required: [security, scope]
```

## Napomena

`pyproject.toml` je u `allowed_paths` SAMO za dodavanje biblioteke za enkripciju (jedan red u dependencies) — ne dirati SQLAlchemy/PySide6/alembic redove koji već postoje. Ako DENT-003 paralelno takođe traži pyproject.toml (ne bi trebalo, provjeri `python scripts/coordination.py status` prije nego dirneš taj fajl), zaustavi se i javi.
