# Dentaland

Sistem zakazivanja termina za stomatološku ordinaciju. Puni kontekst,
arhitektura i pravila rada su u [CLAUDE.md](CLAUDE.md) — ovaj fajl je
samo praktično uputstvo za lokalno pokretanje i testiranje.

## Preduslovi

- Python 3.12+ (vidi `pyproject.toml` — `requires-python`, `ruff`/`mypy`
  target su takođe 3.12) (`pip install -r requirements.txt` ako postoji, ili
  ručno: `sqlalchemy`, `alembic`, `fastapi`, `uvicorn`, `slowapi`,
  `cryptography`, `pyside6`, `pytest`, `ruff`, `mypy`)
- Sve komande pokretati iz korijena repoa (`Dentaland/`), ne iz
  podfoldera — backend i desktop app dijele istu `dentaland.db` SQLite
  bazu preko relativne putanje.

## Gdje se čuvaju podaci

Centralne putanje su u `src/dentaland/paths.py` (može se override-ovati
kroz env `DENTALAND_DATA_DIR`). U development modu (`scripts/dev_local.py`)
desktop i backend dijele `dentaland.db` iz korijena repoa; instalirana
desktop aplikacija koristi user data folder `%LOCALAPPDATA%\Dentaland\`
(Windows), ne Program Files.

## Lokalno testiranje — SVE jednom komandom

Javna forma (`web/`) šalje zahtjeve na `http://127.0.0.1:8000` — to je
backend koji trenutno radi **isključivo lokalno** (nema javnog
hostinga, vidi `CLAUDE.md`). Netlify hostuje samo statične fajlove
(HTML/CSS/JS) — bez lokalno pokrenutog backend-a, forma na Netlify-ju
ne može stvarno sačuvati zahtjev.

Za pun lokalni test (forma → backend → baza → desktop app), jednom
komandom, iz korijena repoa:

```bash
python scripts/dev_local.py
```

Ovo pokreće SVE troje odjednom, sa ispravnim PYTHONPATH za svako:
- backend na `http://127.0.0.1:8000`
- javnu formu na `http://127.0.0.1:8080/index.html`
- desktop aplikaciju (poseban prozor)

Sve troje dijele istu `dentaland.db` u tom folderu — zahtjev poslat
kroz formu treba da bude vidljiv u desktop aplikaciji (panel "Novi
zahtjevi", kad taj dio dashboarda bude gotov). Backend automatski
kreira `dentaland.db` (i tabele) ako ne postoji — nije potreban ručni
`alembic upgrade` za osnovno testiranje.

Ctrl+C zaustavlja backend i web server (desktop prozor zatvoriti ručno
ako je i dalje otvoren). Za samo backend + forma, bez desktop app-a:

```bash
python scripts/dev_local.py --no-desktop
```

**Testiranje zadatka koji je još u toku (git worktree, npr. DENT-009):**
pokreni potpuno istu komandu, ali iz tog worktree-a
(`cd Dentaland-worktrees\DENT-009-...` pa `python scripts/dev_local.py`)
— skripta sama računa putanje u odnosu na svoju lokaciju, pa automatski
koristi kod i `dentaland.db` IZ TOG worktree-a, ne iz `main`-a. Nema
potrebe ručno mijenjati foldere/PYTHONPATH između testiranja različitih
grana.

## Email obavještenja (SMTP)

Email obavještenja (potvrda primljenog zahtjeva, potvrda termina, podsjetnik)
su **opciona** — aplikacija radi normalno i bez njih, samo tiho preskače
slanje ako SMTP nije konfigurisan. Postavke se čitaju iz env varijabli
`DENTALAND_SMTP_HOST`, `DENTALAND_SMTP_PORT`, `DENTALAND_SMTP_USER`,
`DENTALAND_SMTP_PASSWORD` i `DENTALAND_SMTP_FROM`
(`src/dentaland/services/notifications.py`). Sve su dokumentovane u
[.env.example](.env.example).

Varijable moraju biti postavljene u **istom terminalu/procesu** koji
pokreće `dev_local.py` — `_build_env()` u toj skripti kopira `os.environ`
u trenutku poziva i ne čita `.env` fajl automatski. `.env.example` je samo
referenca za ručno kucanje; automatsko učitavanje `.env` fajla trenutno
nije implementirano.

PowerShell, prije pokretanja:

```powershell
$env:DENTALAND_SMTP_HOST = "smtp.gmail.com"
$env:DENTALAND_SMTP_PORT = "587"
$env:DENTALAND_SMTP_USER = "tvoja.adresa@gmail.com"
$env:DENTALAND_SMTP_PASSWORD = "tvoj-app-password"
$env:DENTALAND_SMTP_FROM = "tvoja.adresa@gmail.com"
python scripts/dev_local.py
```

Za Gmail je obavezan **App Password** (16 znakova, generisan na
`myaccount.google.com/apppasswords` uz uključenu 2-Step Verification), NE
obična Gmail lozinka — obična lozinka vraća grešku
`534 5.7.9 Application-specific password required`.

## Operativni backup (CLI)

Dnevni backup baze radi se kroz CLI, obično zakazan u Windows Task
Scheduler:

```bash
python -m dentaland.backup_cli run          # kreiraj enkriptovan backup
python -m dentaland.backup_cli restore-test # provjeri da je najnoviji backup čitljiv
python -m dentaland.backup_cli status       # kad je zadnji uspješan backup
```

Backup ide u cloud/sync folder iz env varijable
`DENTALAND_BACKUP_CLOUD_DIR`; ako nije postavljena, fallback je lokalni
`data_dir()/backups` (radi odmah, ali bez off-site kopije). U development
checkout-u prije komande postavi `$env:PYTHONPATH = "src"`. Sve varijable
(`DENTALAND_BACKUP_CLOUD_DIR`, `DENTALAND_DATA_DIR`), ključ i tačni Windows
Task Scheduler koraci su u
[docs/dentaland-backup-operativni-vodic.md](docs/dentaland-backup-operativni-vodic.md).

## Testovi i provjera koda

```bash
pytest tests/ -q
ruff check src/dentaland desktop backend tests
mypy src/dentaland desktop backend
```

## CI (GitHub Actions)

`pytest`, `ruff` i `mypy` se automatski pokreću na svaki `push` i
`pull_request` kroz [.github/workflows/ci.yml](.github/workflows/ci.yml) —
iste komande kao gore.

## Migracije

```bash
alembic upgrade head
```

Koristi se za desktop app produkcijsku bazu ili kad treba tačna
alembic istorija (ne samo `create_all` koji backend radi automatski za
lokalni test).
