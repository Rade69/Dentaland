# Dentaland — operativni backup (DENT-IMPROVE-007)

Ovaj vodič opisuje kako se dnevni backup Dentaland baze pokreće ručno i kroz
Windows Task Scheduler. Backup koristi postojeći engine
(`src/dentaland/backup.py`): konzistentna kopija kroz SQLite online backup
API, Fernet enkripcija, rotacija (30 dnevnih + 3 mjesečna). CLI
(`src/dentaland/backup_cli.py`) je tanak sloj koji scheduler poziva.

## Tri komande

```text
python -m dentaland.backup_cli run          — kreiraj enkriptovan backup odmah
python -m dentaland.backup_cli restore-test — dekriptuj najnoviji backup na
                                              zasebnu destinaciju i provjeri da
                                              je čitljiva SQLite baza
python -m dentaland.backup_cli status       — kad je zadnji uspješan backup
```

Sve tri vraćaju **non-zero exit kod** (1) kad nešto ne uspije, i ispisuju
jasnu poruku na stderr — to je ono što Task Scheduler/log vidi kao failure.

## Preduslovi

- Python 3.12+ sa `cryptography` (već u `pyproject.toml`).
- Pokretanje iz korijena repoa (`Dentaland/`), uz `PYTHONPATH=src` (paket
  `dentaland` živi u `src/`, nije nužno pip-instaliran):

```powershell
cd C:\Users\<korisnik>\Desktop\Dentaland
$env:PYTHONPATH = "src"
python -m dentaland.backup_cli run
```

Ako je paket instaliran (`pip install -e .`), `PYTHONPATH` nije potreban.

## Gdje idu podaci

Centralne putanje su u `src/dentaland/paths.py`:

| Putanja | Default | Override |
|---|---|---|
| Baza | `%LOCALAPPDATA%\Dentaland\dentaland.db` | `DENTALAND_DATA_DIR` |
| Lokalni backup folder | `%LOCALAPPDATA%\Dentaland\backups` | — |
| **Cloud/sync folder** | lokalni backup folder (fallback) | `DENTALAND_BACKUP_CLOUD_DIR` |
| Ključ za enkripciju | `%LOCALAPPDATA%\Dentaland\config\backup.key` | — |

**Ključ za enkripciju** (`backup.key`) je namjerno **izvan** backup foldera
— nikad ga ne kopiraj u backup/cloud folder. Bez njega se backup ne može
dekriptovati; sačuvaj ga na sigurnom mjestu odvojeno od backupa.

## Cloud folder — zašto env varijabla

Google Drive/Dropbox sync folder je **specifičan po mašini** (npr.
`C:\Users\Ljubo\Google Drive\Dentaland-backup`), pa se ne može hardkodovati.
Ako `DENTALAND_BACKUP_CLOUD_DIR` nije postavljena, backup ide u lokalni
`data_dir()/backups` — **radi odmah bez podešavanja**, ali nema off-site
kopiju (ako disk umre, umire i backup). Za produkciju postavi varijablu na
pravi sync folder.

Primjer (PowerShell, samo za trenutnu sesiju):

```powershell
$env:DENTALAND_BACKUP_CLOUD_DIR = "C:\Users\Ljubo\Google Drive\Dentaland-backup"
```

Trajno (zapisuje u korisnički env, vidljivo novim procesima):

```powershell
setx DENTALAND_BACKUP_CLOUD_DIR "C:\Users\Ljubo\Google Drive\Dentaland-backup"
```

## Ručni ciklus provjere (jednom sedmično/mjesečno)

```powershell
cd C:\Users\<korisnik>\Desktop\Dentaland
$env:PYTHONPATH = "src"
python -m dentaland.backup_cli run
python -m dentaland.backup_cli status
python -m dentaland.backup_cli restore-test
```

- `run` ispiše putanju enkriptovanog fajla (`.db.enc`).
- `status` ispiše zadnji uspješan backup + `STARO` ako je stariji od 25h.
- `restore-test` dekriptuje najnoviji backup u
  `data_dir()/restore-test/dentaland-test.db`, pokrene `PRAGMA
  integrity_check` i prebroji redove u `appointments`, pa **obriše** test
  fajl. Nikad ne dira aktivnu bazu.

## Windows Task Scheduler

Task Scheduler **ne nasljeđuje** env varijable iz tvoje interaktivne
PowerShell sesije (`$env:` vrijedi samo u toj sesiji). Dva načina da task
vidi `DENTALAND_BACKUP_CLOUD_DIR` i `PYTHONPATH`:

1. **`setx` (trajno, preporučeno za cloud folder)** — trajna korisnička env
   varijabla; novi procesi (uključujući task, nakon sljedećeg logon-a ili
   restarta servisa Task Scheduler) je vide:

   ```powershell
   setx DENTALAND_BACKUP_CLOUD_DIR "C:\Users\Ljubo\Google Drive\Dentaland-backup"
   ```

2. **Puna komandna linija u samoj task akciji** (eksplicitno, ne zavisi od
   registry env-a) — koristi `cmd /c` sa `set`:

   ```text
   cmd /c "set PYTHONPATH=C:\Users\Ljubo\Desktop\Dentaland\src && set DENTALAND_BACKUP_CLOUD_DIR=C:\Users\Ljubo\Google Drive\Dentaland-backup && C:\Users\Ljubo\AppData\Local\Programs\Python\Python312\python.exe -m dentaland.backup_cli run"
   ```

   (putanju do `python.exe` provjeri sa `(Get-Command python).Source`.)

### Kreiranje dnevnog zadatka

Primjer sa `schtasks` (pokreni u PowerShell-u kao administrator), dnevno u
02:00 pod korisničkim nalogom (mora biti korisnički nalog da bi imao pristup
Google Drive/Dropbox folderu — NE `SYSTEM`):

```powershell
schtasks /create /tn "DentalandBackup" `
  /tr "cmd /c \"set PYTHONPATH=C:\Users\Ljubo\Desktop\Dentaland\src && set DENTALAND_BACKUP_CLOUD_DIR=C:\Users\Ljubo\Google Drive\Dentaland-backup && C:\Users\Ljubo\AppData\Local\Programs\Python\Python312\python.exe -m dentaland.backup_cli run\"" `
  /sc daily /st 02:00 /ru Ljubo
```

Windows će tražiti lozinku za `/ru Ljubo` (ili koristi `/rp`). Alternativa
bez komandne linije: **Task Scheduler GUI** → *Create Basic Task* → *Daily* →
*Start a program* → u *Program/script* upiši `cmd`, a u *Add arguments*:
`/c "set PYTHONPATH=... && set DENTALAND_BACKUP_CLOUD_DIR=... && ...python.exe -m dentaland.backup_cli run"`.

### Provjera da task radi

```powershell
schtasks /query /tn "DentalandBackup" /v /fo LIST
schtasks /run /tn "DentalandBackup"    # pokreni odmah, jednom
python -m dentaland.backup_cli status  # provjeri da li je backup svjež
```

## Šta se NE smije desiti (garancije iz koda)

- **Nema plaintext tmp DB** — engine pravi privremeni plain `.db` samo kao
  međukorak i briše ga u `finally`; CLI ne dodaje nove privremene kopije, a
  `restore-test` briše svoj test fajl u `finally`.
- **Ključ nije u backup folderu** — `backup.key` je u `config/`, odvojeno od
  `backups/` i cloud foldera.
- **Restore test ne prepisuje aktivnu bazu** — dekriptuje isključivo u
  `data_dir()/restore-test/`, nikad preko `dentaland.db`.

## Rješavanje problema

| Simptom | Uzrok / rješenje |
|---|---|
| `ModuleNotFoundError: No module named 'dentaland'` | `PYTHONPATH=src` nije postavljen (vidi Preduslovi) |
| Backup ide u lokalni folder, ne u Drive | `DENTALAND_BACKUP_CLOUD_DIR` nije vidljiva tasku — koristi `setx` ili punu komandnu liniju |
| `status` kaže `STARO` | Task se ne izvršava — provjeri `schtasks /query` i da li je task enabled |
| Restore-test pada `Neispravan ključ ili oštećen backup` | `backup.key` se ne poklapa sa onim kojim je backup enkriptovan — ne regeneriši ključ bez razloga |
