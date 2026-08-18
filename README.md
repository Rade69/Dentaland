# Dentaland

Sistem zakazivanja termina za stomatološku ordinaciju. Puni kontekst,
arhitektura i pravila rada su u [CLAUDE.md](CLAUDE.md) — ovaj fajl je
samo praktično uputstvo za lokalno pokretanje i testiranje.

## Preduslovi

- Python 3.13+ (`pip install -r requirements.txt` ako postoji, ili
  ručno: `sqlalchemy`, `alembic`, `fastapi`, `uvicorn`, `slowapi`,
  `cryptography`, `pyside6`, `pytest`, `ruff`, `mypy`)
- Sve komande pokretati iz korijena repoa (`Dentaland/`), ne iz
  podfoldera — backend i desktop app dijele istu `dentaland.db` SQLite
  bazu preko relativne putanje.

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

## Testovi i provjera koda

```bash
pytest tests/ -q
ruff check src/dentaland desktop backend tests
mypy src/dentaland desktop backend
```

## Migracije

```bash
alembic upgrade head
```

Koristi se za desktop app produkcijsku bazu ili kad treba tačna
alembic istorija (ne samo `create_all` koji backend radi automatski za
lokalni test).
