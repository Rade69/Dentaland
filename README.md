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

## Lokalno testiranje javne forme (bez interneta, bez Netlify-ja)

Javna forma (`web/`) šalje zahtjeve na `http://127.0.0.1:8000` — to je
backend koji trenutno radi **isključivo lokalno** (nema javnog
hostinga, vidi `CLAUDE.md`). Netlify hostuje samo statične fajlove
(HTML/CSS/JS) — bez lokalno pokrenutog backend-a, forma na Netlify-ju
ne može stvarno sačuvati zahtjev.

Za pun lokalni test (forma → backend → baza), jednom komandom:

```bash
python scripts/dev_local.py
```

Ovo pokreće:
- backend na `http://127.0.0.1:8000`
- javnu formu na `http://127.0.0.1:8080/index.html`

Otvori formu, pošalji test-zahtjev, provjeri da treći korak ("ZAHTJEV
PRIMLJEN!") stvarno bude prikazan. Ctrl+C zaustavlja oba servera.

Backend automatski kreira `dentaland.db` (i tabele) ako ne postoji —
nije potreban ručni `alembic upgrade` za osnovno testiranje.

## Desktop aplikacija

Odvojeno, u drugom terminalu (blokirajući GUI proces, ne server):

```bash
python -m desktop.app
```

Koristi istu `dentaland.db` bazu kao backend — zahtjev poslat preko
javne forme dok je backend pokrenut treba da bude vidljiv u desktop
aplikaciji (panel "Novi zahtjevi", kad taj dio dashboarda bude gotov).

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
