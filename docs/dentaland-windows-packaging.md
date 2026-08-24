# Dentaland — Windows packaging (DENT-IMPROVE-009)

Ovaj vodič opisuje kako se desktop aplikacija gradi u samostalan Windows
build (bez development environmenta) i kako se pokreće clean-machine smoke
test.

## Odluke

- **PyInstaller** (ne Nuitka) — najstandardnija, najbolje dokumentovana
  opcija za PySide6; dovoljno za obim jedne desktop aplikacije.
- **`--onedir`** (ne `--onefile`) — onefile raspakuje sve u temp pri svakom
  pokretanju (sporiji cold-start) i češće izaziva false-positive antivirus
  detekcije. Onedir je operativno pouzdaniji za app koji se pokreće svaki dan.
- **Samo desktop app** — backend (FastAPI) i web/ javna forma nisu u obimu
  (Faza 0 je čisto lokalni desktop, bez interneta).

## Preduslovi (na build mašini)

```powershell
pip install pyinstaller pillow pyside6
```

(`pyinstaller` i `pillow` su i u `[project.optional-dependencies].dev`.)

## Build

Iz korijena repoa:

```powershell
pyinstaller packaging/dentaland.spec
```

Build je idempotentan: PyInstaller prvo čisti `build/Dentaland`, pa
`dist/Dentaland`. Rezultat:

```text
dist/Dentaland/Dentaland.exe          ← pokrećeš ovo
dist/Dentaland/_internal/             ← sve ostalo (Qt DLL-ovi, Python, resursi)
```

**Distribuira se cijeli `dist/Dentaland/` folder**, ne samo `Dentaland.exe`
(`--onedir` — exe zavisi od `_internal/`).

## Šta je uključeno

- `web/assets/` (logo, benefit slike) → `_internal/web/assets/`
- `desktop/assets/doctors/` (fotografije doktora) → `_internal/desktop/assets/doctors/`
- Ikonica aplikacije `web/assets/dentaland.ico` (generisana iz `logo.png`)

Layout u bundle-u se poklapa sa `paths.resource_path()` (`sys._MEIPASS`
grana) — resursi se učitavaju iz `_internal/`, ne iz source checkout-a.

Regeneracija ikonice ako se `logo.png` promijeni:

```powershell
python -c "from PIL import Image; img = Image.open('web/assets/logo.png').convert('RGBA'); img.save('web/assets/dentaland.ico', format='ICO', sizes=[(s,s) for s in (16,24,32,48,64,128,256)])"
```

## Gdje se piše baza

Pokrenuta (instalirana) aplikacija piše bazu u user data folder:

```text
%LOCALAPPDATA%\Dentaland\dentaland.db
```

Dev fallback (`dentaland.db` u cwd-u ako postoji) ostaje, ali na čistoj
mašini taj fajl ne postoji pa se koristi `%LOCALAPPDATA%\Dentaland`. Prvi
start sam kreira šemu (`Base.metadata.create_all`) — bez ručnog `alembic
upgrade` za osnovni rad.

## Clean-machine smoke test

8 koraka iz backloga:

1. instalirati/pokrenuti aplikaciju,
2. otvoriti scheduler,
3. kreirati termin,
4. zatvoriti aplikaciju,
5. ponovo otvoriti,
6. potvrditi da podatak postoji,
7. otvoriti print preview,
8. potvrditi da resursi (logo, ikonice doktora) rade.

### Na stvarno čistoj mašini (Radovan)

1. Kopiraj cijeli `dist/Dentaland/` folder na ciljnu mašinu.
2. Pokreni `Dentaland.exe`.
3. Aplikacija se otvara na scheduler-u; kreiraj termin (npr. za Ljubu).
4. Zatvori aplikaciju.
5. Ponovo pokreni `Dentaland.exe`.
6. Termin iz koraka 3 mora biti vidljiv (podaci u `%LOCALAPPDATA%\Dentaland\dentaland.db`).
7. Klikni "Štampa" → otvori se print preview sa logo-om.
8. Potvrdi da su logo i fotografije doktora vidljivi (nema praznih/izlomljenih ikonica).

### Simulacija bez čiste mašine (ono što je automatizovano u ovom tasku)

Pošto nema fizičke čiste mašine/VM-a, najbliža simulacija je pokretanje
`Dentaland.exe` iz PRAZNOG foldera VAN repoa, sa `DENTALAND_DATA_DIR` na
svjež scratch folder — dokazuje da prvi start kreira bazu i učitava resurse
bez ijednog fajla iz dev environment-a. Detalji i tačan rezultat su u
implementer izvještaju (`agent_reports/2026-08-24-DENT-IMPROVE-009-...`).

## Poznata ograničenja

- `--onedir` build nije jedan samostalan `.exe` — distribuira se cijeli folder.
- Antivirus može i dalje zastajati kod PyInstaller build-ova (rjeđe kod
  `--onedir` nego `--onefile`); ako se desi, dodati izuzetak za
  `dist/Dentaland/`.
- Ovo nije code-signed build (nema sertifikata) — Windows SmartScreen će pri
  prvom pokretanju na drugoj mašini pokazati upozorenje "More info → Run
  anyway". To je očekivano i van obima (out of scope: enterprise deployment).

## Out of scope

- auto-update,
- enterprise deployment,
- telemetry.
