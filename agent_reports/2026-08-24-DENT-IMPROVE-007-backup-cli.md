---
task_id: DENT-IMPROVE-007
risk: MEDIUM
implementer: pi
reviewers: [claude]
status: IMPLEMENTATION_COMPLETE
created_at: 2026-08-24
---

# DENT-IMPROVE-007 — Operativni automatski backup (CLI + Task Scheduler)

## Task Contract

Izvor: `agent_reports/DENT-IMPROVE-007-task-contract.md` (napisan PRIJE koda).
Cilj: dodati operativni sloj za postojeći, testiran backup engine
(`src/dentaland/backup.py`) — CLI sa tri subkomande koji Windows Task
Scheduler može pozvati, plus dokumentacija. MEDIUM risk; jedan nezavisan
reviewer (Claude), human approval obavezan prije merge-a.

## Šta je urađeno

1. **`src/dentaland/backup_cli.py`** (novi) — `python -m dentaland.backup_cli`
   sa subkomandama:
   - `run` — poziva `create_backup()` sa pravim `BackupConfig`-om; na uspjeh
     ispisuje putanju enkriptovanog fajla, na failure ispisuje grešku na
     stderr i vraća `1` (non-zero).
   - `restore-test` — dekriptuje NAJNOVIJI backup u
     `data_dir()/restore-test/dentaland-test.db` (nikad preko aktivne baze),
     verifikuje `PRAGMA integrity_check` + `SELECT COUNT(*) FROM
     appointments`, i **briše** plain test fajl u `finally` (ne ostavlja
     plaintext). Non-zero ako nema backupa, dekripcija padne ili verifikacija
     ne prođe.
   - `status` — čita `last_backup.txt`, ispisuje zadnji uspješan backup +
     `STARO` flag ako je stariji od 25h (flag, ne hard fail). Non-zero samo
     ako je evidencija neispravna/ne-timezone-aware.
2. **`src/dentaland/paths.py`** — dodana `backup_cloud_dir(env)`: čita
   `DENTALAND_BACKUP_CLOUD_DIR`, fallback na lokalni `backup_dir()`. `key_path`
   se računa u CLI kao `paths.config_dir()/backup.key` — izvan lokalnog i
   cloud backup foldera.
3. **`.env.example`** — dopunjen sa `DENTALAND_BACKUP_CLOUD_DIR` (komentar +
   prazna vrijednost, isti obrazac kao SMTP).
4. **`README.md`** — novi odjeljak "Operativni backup (CLI)" sa tri komande,
   napomenom o `PYTHONPATH` i uputom na vodič.
5. **`docs/dentaland-backup-operativni-vodic.md`** (novi) — ručne komande,
   env konfiguracija (`setx` vs `$env:`), ključ, `schtasks /create` primjer,
   GUI koraci, i objašnjenje da Task Scheduler ne nasljeđuje interaktivni
   shell env (rješenje: `setx` ili puna komandna linija u task akciji).

## Changed files

- `src/dentaland/backup_cli.py` — novi modul (CLI, 3 subkomande).
- `src/dentaland/paths.py` — `ENV_BACKUP_CLOUD_DIR` + `backup_cloud_dir()`.
- `tests/test_backup_cli.py` — 9 novih testova.
- `.env.example` — dopuna `DENTALAND_BACKUP_CLOUD_DIR`.
- `README.md` — odjeljak "Operativni backup (CLI)".
- `docs/dentaland-backup-operativni-vodic.md` — novi operativni vodič.
- `agent_reports/DENT-IMPROVE-007-task-contract.md` — Task Contract.
- `agent_reports/2026-08-24-DENT-IMPROVE-007-backup-cli.md` — ovaj izvještaj.

`src/dentaland/backup.py` (engine) NIJE diran. `desktop/`, `web/`,
`backend/` nisu dirani.

## Verifikacija (rezultati)

```text
pytest tests/ -q
→ 298 passed, 11 warnings   (289 baseline + 9 novih test_backup_cli)

ruff check src/dentaland desktop backend tests
→ All checks passed!, exit 0

mypy src/dentaland desktop backend
→ Success: no issues found in 37 source files
```

Warnings su postojeći dependency deprecation warning-i (httpx/slowapi/
alembic), ne vezani za ovaj task.

## Živi ciklus (stvaran tool output, ne parafraza)

Na test bazi (`appointments` tabela sa 1 redom), `DENTALAND_DATA_DIR` →
temp folder, `PYTHONPATH=src`, `PYTHONUTF8=1`:

```text
=== RUN ===
Backup uspješan: C:\Users\38765\AppData\Local\Temp\dent007-live2\backups\dentaland-2026-08-24.db.enc
exit=0

=== STATUS ===
Zadnji uspješan backup: 2026-08-24T05:58:10.918303+02:00 (OK, 0.0 h).
exit=0

=== RESTORE-TEST ===
Restore-test uspješan (dekriptovano i verifikovano): C:\Users\38765\AppData\Local\Temp\dent007-live2\backups\dentaland-2026-08-24.db.enc
exit=0

=== backup dir ===
dentaland-2026-08-24.db.enc
last_backup.txt

=== restore-test dir (broj stavki) ===
0
```

Živi failure slučaj (restore-test bez backupa):

```text
=== RESTORE-TEST bez backupa ===
Nema backupa za testiranje u: C:\Users\38765\AppData\Local\Temp\dent007-empty\backups
restore-test exit=1
```

Dokazano: backup folder sadrži SAMO enkriptovan `.db.enc` + `last_backup.txt`
(nema plaintext `.db`); restore-test test fajl je obrisan (0 stavki);
failure je vidljiv kroz nenula exit + stderr poruku.

## Requirements iz backloga (provjera)

- **backup ne ostavlja plaintext tmp DB** — engine briše `local_tmp` u
  `finally`; CLI ne dodaje privremene kopije; `restore-test` briše test fajl
  u `finally`. Potvrđeno živo (restore-test dir prazan).
- **key nije u backup folderu** — `key_path = config_dir()/backup.key`,
  izvan `backups/` i cloud foldera; pokriveno testom
  `test_run_kreira_enkriptovan_backup`.
- **exit code nenula na failure** — `run`/`restore-test` vraćaju `1` na
  bilo koji izuzetak (pokriveno testovima + živim failure primjerom).
- **status posljednjeg uspješnog backupa** — `status` čita `last_backup.txt`
  (pokriveno testovima `test_status_*`).
- **restore test ne prepisuje aktivnu bazu** — dest je
  `data_dir()/restore-test/dentaland-test.db`, nikad `dentaland.db`
  (pokriveno testom + živo).

## Unresolved risks

- `setx` trajna env varijabla postaje vidljiva novim procesima tek nakon
  re-logon-a ili restarta Task Scheduler servisa — dokumentovano u vodiču
  (alternativa je puna komandna linija u task akciji). Nije blokirajuće.
- `status` vraća `0` kad `last_backup.txt` ne postoji (informacija, ne
  failure) — namjerno, u skladu sa "flag, ne hard fail".

## Review

`PENDING` — implementer nije reviewer. Claude radi nezavisan MEDIUM-risk
review; Radovanov human approval obavezan prije merge-a.

## Integration status

`NOT_MERGED` — čeka nezavisan review.

## Handoff

CILJ: operativni dnevni backup kroz CLI + Windows Task Scheduler, bez
izmjene backup engine-a.

URAĐENO: `backup_cli.py` (run/restore-test/status), `paths.backup_cloud_dir`,
testovi, `.env.example`/README dopuna i operativni vodič.

NE DIRATI: `src/dentaland/backup.py` (engine), `desktop/`, `web/`,
`backend/`.

SLJEDEĆE: Claude nezavisan review, pa Radovanov human approval (MEDIUM).
