---
task_id: DENT-IMPROVE-007
risk: MEDIUM
reviewer: claude
implementer: pi
verdict: PASS
created_at: 2026-08-24
---

# DENT-IMPROVE-007 — nezavisan MEDIUM-risk review (Claude)

```yaml
verdict: PASS
scope: PASS
acceptance: PASS
architecture: PASS
security: PASS
blocking_findings: []
```

```text
CILJ: Nezavisno provjeriti da backup_cli.py stvarno omogućava operativan
      dnevni backup (run/status/restore-test) bez izmjene backup engine-a,
      da ne ostavlja plaintext trag i da restore-test ne dira aktivnu bazu.
URAĐENO: PASS — sve provjereno vlastitim (ne Pi-jevim) live ciklusom i
      adversarnim testom, ne samo čitanjem izvještaja.
NE DIRATI: backup.py (engine, nedirano), desktop/, web/, backend/.
SLJEDEĆE: Radovanov human approval (MEDIUM tok), pa merge.
```

## 1. Scope

`git diff --stat` u worktree-u: samo `.env.example` (+7), `README.md`
(+19), `src/dentaland/paths.py` (+15), plus novi fajlovi
(`backup_cli.py`, `tests/test_backup_cli.py`,
`docs/dentaland-backup-operativni-vodic.md`, `agent_reports/**`).

`git diff src/dentaland/backup.py` je prazan — engine potvrđeno netaknut.
`git status --short | grep desktop/|web/|backend/` — prazno, nema
forbidden izmjena. `scope: PASS`.

## 2. Nezavisna live provjera (stvaran tool output, ne prepisan iz
   implementer izvještaja)

Vlastita, svježa test baza (`AdversarialClaude` red u `appointments`),
`DENTALAND_DATA_DIR` na privremeni folder, poziv `dentaland.backup_cli.main()`
direktno iz Pythona:

```text
=== RUN ===
Backup uspješan: ...\dent007-review-py\backups\dentaland-2026-08-24.db.enc
exit= 0

enc files: ['...\\backups\\dentaland-2026-08-24.db.enc']
```

Backup folder sadržao je isključivo `.db.enc` + `last_backup.txt` — nema
plaintext `.db`. Ključ (`config/backup.key`) potvrđeno u ODVOJENOM
folderu od `backups/`.

## 3. Adversarna provjera — korumpiran backup mora genuinski pasti

Backup fajl ručno prepisan proizvoljnim bajtovima (nevažeći Fernet
token), pa pozvan `restore-test`:

```text
=== RESTORE-TEST on corrupted backup (should FAIL, exit 1) ===
exit= 1
restore-test dir leftover (should be empty): []
```

Stderr poruka: `Neispravan ključ ili oštećen backup: ...dentaland-2026-08-24.db.enc`
— jasna, čitljiva greška. Restore-test folder ostao prazan i nakon
FAILURE puta (ne samo success puta) — `finally: dest.unlink(missing_ok=True)`
pokriva oba slučaja, potvrđeno živo, ne samo čitanjem koda.

(Napomena: prvi pokušaj ove provjere je propao zbog greške u MOM
adversarnom skriptu — git-bash POSIX putanja `/c/Users/...` proslijeđena
nativnom Windows Python-u kroz `glob.glob()` nije pronašla fajl, pa
korupcija nikad nije stvarno upisana. Ponovljeno čisto u Pythonu
(`os.path`/`sys.path`, bez shell path prevoda) — rezultat iznad je
ispravan i pouzdan. Zabilježeno da ne bih ponovio istu grešku kao u
DENT-022 rundi 1 gdje je netačna adversarna tvrdnja prošla neprovjerena.)

## 4. Cloud folder / env override

`paths.backup_cloud_dir()`: `DENTALAND_BACKUP_CLOUD_DIR` override,
fallback `backup_dir()`. Provjerio sam da `local_dir` (uvijek
`paths.backup_dir(env)`) NIKAD ne prati cloud override — u produkciji
(env var postavljena na pravi Google Drive folder) `local_dir` ostaje
lokalni, ne-sinhronizovan folder, a plaintext privremeni fajl se piše
samo tu i briše prije nego što `cloud_dir` uopšte vidi bilo šta osim
enkriptovanog fajla. U fallback slučaju (env var nepostavljena)
`local_dir` i `cloud_dir` se poklapaju, ali tada taj folder nije stvarno
sinhronizovan ni sa čim (čist lokalni `%LOCALAPPDATA%` fallback), pa
nema stvarnog rizika curenja plaintext-a u cloud. `architecture: PASS`.

## 5. Testovi (`tests/test_backup_cli.py`, 9 novih)

Pregledani pojedinačno — pokrivaju: uspješan `run` (+ provjera da
folder ne sadrži `.db`, + ključ van foldera), cloud env override,
`run` failure (stvaran `sqlite3.connect` na direktorijumu umjesto
fajla — realan failure, ne mock), `restore-test` uspjeh (plaintext
obrisan, aktivna baza netaknuta), `restore-test` bez backupa, `restore-test`
na korumpiranom backupu (isti scenario koji sam ja ponovio nezavisno u
sekciji 3), `status` bez evidencije / svjež / star. Nema mock-ovanih
SMTP/mrežnih poziva jer CLI nema takvih zavisnosti — sve testira stvaran
fajl-sistem kroz `tmp_path`. `acceptance: PASS`.

## 6. Requirements iz backloga — provjera jedno po jedno

- backup ne ostavlja plaintext tmp DB — potvrđeno živo (sekcija 2, 3).
- key nije u backup folderu — potvrđeno živo (sekcija 2) i testom.
- exit code nenula na failure — potvrđeno živo (sekcija 3, `run`
  failure test).
- status posljednjeg uspješnog backupa — `status` komanda, testirano.
- restore test ne prepisuje aktivnu bazu — dest je uvijek
  `data_dir()/restore-test/`, nikad `dentaland.db`; potvrđeno kodom i
  testom `test_restore_test_prolazi_na_zasebnoj_destinaciji`
  (`_appointment_count` na aktivnoj bazi ostaje 1 nakon restore-testa).

Svih pet zahtjeva ispunjeno. `security: PASS` (ključ odvojen, enkripcija
nedirana, nema novih kredencijala/mrežnih poziva).

## 7. Puna verifikacija (ponovljena nezavisno)

```text
pytest tests/ -q                              → 298 passed, 11 warnings
ruff check src/dentaland desktop backend tests → All checks passed!
mypy src/dentaland desktop backend             → Success: no issues found in 37 source files
```

## 8. Dokumentacija

`docs/dentaland-backup-operativni-vodic.md` — tačna i operativno
korisna: ispravno objašnjava da Task Scheduler ne nasljeđuje
interaktivni `$env:`, daje i `setx` i punu-komandnu-liniju alternativu,
i ispravno insistira da task mora raditi pod korisničkim nalogom (ne
`SYSTEM`) da bi imao pristup Google Drive/Dropbox folderu — bitan,
lako-propustljiv detalj za Windows scheduled taskove koji pristupaju
korisničkim cloud folderima. README dopuna je kratka i upućuje na vodič
umjesto da duplira sadržaj.

## Non-blocking napomena (ne zahtijeva izmjenu)

U `_cmd_restore_test`, `finally: dest.unlink(missing_ok=True)` je unutar
istog `try` bloka čiji `except Exception` hvata i grešku iz samog
`unlink()`-a. Da `unlink()` neuspješno baci (npr. permission error) NAKON
uspješnog restore+verify, funkcija bi pogrešno prijavila failure iako je
restore stvarno uspio. Vrlo nizak rizik (lokalni fajl-sistem, netom
kreiran fajl), ne blokira PASS — za zapis, ne za akciju.

## Zaključak

PASS. Implementacija ispravno wrapuje postojeći, netaknuti backup engine
operativnim CLI slojem; sve garancije iz zahtjeva (nema plaintext traga,
ključ odvojen, non-zero exit na failure, status vidljiv, restore-test
izolovan) su potvrđene i kodom i nezavisnim živim/adversarnim testiranjem,
ne samo implementerovim izvještajem. Dokumentacija je tačna i operativno
upotrebljiva. Nema blokirajućih nalaza. Čeka Radovanov human approval
(MEDIUM tok) prije merge-a.
