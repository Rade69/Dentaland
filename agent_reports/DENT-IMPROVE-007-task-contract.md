---
task_id: DENT-IMPROVE-007
risk: MEDIUM
implementer: pi
reviewers: [claude]
status: ASSIGNED — dodijeljeno Pi-ju (implementer)
created_at: 2026-08-24
---

# DENT-IMPROVE-007 — Operativni automatski backup (CLI + Windows Task Scheduler)

## Task Contract

**Cilj:** Backup engine (`src/dentaland/backup.py`) postoji i testiran je
(`sqlite3.Connection.backup()`, Fernet enkripcija, rotacija, `create_backup()`,
`restore_backup()`, `rotate_backups()`), ali ne postoji operativni način da
se backup stvarno pokreće dnevno na Windows računaru. Ovaj task dodaje CLI
koji scheduler (Windows Task Scheduler) može pozvati, i dokumentuje setup.

**Risk:** MEDIUM (reliability / operations — dodaje operativni sloj, ne dira
backup engine ni podatke).

Izvor: `docs/DENTALAND_IMPROVEMENT_BACKLOG.md`, sekcija 8.

## Šta uraditi

1. **Novi modul `src/dentaland/backup_cli.py`** sa tri subkomande:

   ```text
   python -m dentaland.backup_cli run
   python -m dentaland.backup_cli restore-test
   python -m dentaland.backup_cli status
   ```

   - `run` — poziva `create_backup()` sa pravim `BackupConfig`-om; na bilo
     kakav failure hvata izuzetak, ispisuje grešku na stderr i vraća
     `sys.exit(1)` (non-zero). Na uspjeh ispisuje putanju enkriptovanog
     backupa.
   - `restore-test` — dekriptuje NAJNOVIJI backup na zasebnu test destinaciju
     (`paths.data_dir()/restore-test/dentaland-test.db`, NIKAD preko aktivne
     baze), verifikuje da je čitljiva SQLite baza (`PRAGMA integrity_check` +
     prebroj redova u `appointments`), obriše plain test fajl na kraju (ne
     ostavlja plaintext tmp DB). Non-zero exit ako restore/verifikacija ne
     uspije.
   - `status` — čita `last_backup.txt` (piše ga engine) i ispisuje kad je
     zadnji uspješan backup bio, plus "STARO" flag ako je stariji od 25h
     (flag, ne hard fail).

2. **Konfiguracija cloud foldera** — `cloud_dir` je po mašini specifičan
   (Google Drive/Dropbox sync folder). Env varijabla
   `DENTALAND_BACKUP_CLOUD_DIR` sa fallback-om na lokalni `paths.backup_dir()`
   ako nije postavljena (isti obrazac kao `DENTALAND_SMTP_*` iz DENT-023 —
   radi odmah bez podešavanja; produkcijska upotreba zahtijeva da se
   varijabla postavi na pravi sync folder). Dokumentovati u `.env.example`
   i README.

3. **Helper u `src/dentaland/paths.py`** — `backup_cloud_dir(env)` (čita
   `DENTALAND_BACKUP_CLOUD_DIR`, fallback `backup_dir()`). `key_path` se
   računa kao `paths.config_dir()/backup.key` (izvan `local_dir` i
   `cloud_dir`).

4. **Windows Task Scheduler dokumentacija** — novi
   `docs/dentaland-backup-operativni-vodic.md`: tačni koraci za dnevni
   zadatak koji zove `python -m dentaland.backup_cli run` (`schtasks
   /create` primjer), uključujući env kontekst (`DENTALAND_BACKUP_CLOUD_DIR`
   / `DENTALAND_DATA_DIR`) — Task Scheduler ne nasljeđuje interaktivni shell
   env automatski, rješava se kroz `setx` ili task akciju sa punom komandnom
   linijom. Plus kratka dopuna u README (3 komande + uput na vodič).

## Requirements (iz backloga, ne pregovara se)

- backup ne ostavlja plaintext tmp DB (engine ovo već radi — CLI ne smije
  pokvariti dodatnim privremenim kopijama),
- key nije u backup folderu,
- exit code je nenula na failure,
- postoji status posljednjeg uspješnog backupa,
- restore test ne prepisuje aktivnu bazu.

## Acceptance kriterijumi

- ručno pokretanje (`run`) kreira enkriptovan backup,
- scheduler (Windows Task Scheduler) može pozvati isti CLI,
- `restore-test` prolazi na zasebnoj destinaciji,
- failure je vidljiv korisniku/logu (nenula exit + jasna poruka).

## Allowed paths

```text
src/dentaland/backup_cli.py
src/dentaland/paths.py          (samo helper za cloud_dir override)
tests/test_backup_cli.py
.env.example                    (dopuna, ne prepis)
README.md                       (dopuna)
docs/dentaland-backup-operativni-vodic.md   (novo)
agent_reports/**
```

## Forbidden paths

```text
src/dentaland/backup.py         (engine — ne dirati bez OUT_OF_SCOPE_FINDING prijave)
desktop/
web/
backend/
```

## Verification

```bash
pytest tests/ -q
ruff check src/dentaland desktop backend tests
mypy src/dentaland desktop backend
```

Plus barem jedan stvaran, uživo pokrenut `run → status → restore-test`
ciklus na test bazi (ne samo mock), sa tačnim tool outputom zabilježenim u
implementer izvještaju.

Baseline (24.8.2026, `main` nakon merge-a DENT-022/DENT-023): provjeriti
tačan broj na svom worktree-u prije početka, ne pretpostaviti.

## Review

Claude, nezavisan od implementera (jedini reviewer za MEDIUM). Nakon PASS-a,
Radovanov human approval je obavezan (MEDIUM tok) prije merge-a.

## Koordinacija — obavezno prije početka

Provjeri `python scripts/coordination.py status` prije `claim`. Radi u
zasebnom git worktree (`Dentaland-worktrees/DENT-IMPROVE-007-backup-cli`,
grana `task/DENT-IMPROVE-007-backup-cli`).
