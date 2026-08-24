---
task_id: DENT-IMPROVE-009
risk: MEDIUM
reviewer: claude
implementer: pi
verdict: PASS
created_at: 2026-08-24
---

# DENT-IMPROVE-009 — nezavisan MEDIUM-risk review (Claude)

```yaml
verdict: PASS
scope: PASS
acceptance: PASS
architecture: PASS
security: PASS
blocking_findings: []
```

```text
CILJ: Nezavisno provjeriti da je Windows build stvarno reproducibilan,
      ne zavisi od source checkout-a, i da resursi/baza rade kroz
      sys._MEIPASS bundle layout — ne samo čitanjem Pi-jevog izvještaja.
URAĐENO: PASS — build ponovljen od nule (rm -rf build/dist), exe pokrenut
      iz izolovanog foldera van repoa/worktree-a, sa svježim
      DENTALAND_DATA_DIR i bez PYTHONPATH-a; rezultat identičan
      Pi-jevoj tvrdnji (ista šema tabela).
NE DIRATI: aplikacijski kod — nedirano, potvrđeno diff-om.
SLJEDEĆE: Radovanov human approval (MEDIUM tok), pa merge.
```

## 1. Scope

`git status --short` u worktree-u: `README.md`, `pyproject.toml`
(dopune), plus novi `packaging/dentaland.spec`, `web/assets/dentaland.ico`,
`docs/dentaland-windows-packaging.md`, `agent_reports/**`. Nema izmjena u
`src/dentaland/services/**`, `models.py`, `migrations/`, `backend/`,
`desktop/views/**` — potvrđeno (nijedan od tih fajlova se ne pojavljuje u
`git status`). `scope: PASS`.

## 2. Nezavisan build — od nule, ne Pi-jev dist folder

Zatečen lingering proces `Dentaland.exe` (PID 19460) iz Pi-jevog vlastitog
smoke testa, još uvijek živ i držao je file-lock na
`_internal/base_library.zip` (spriječio `rm -rf dist`). Identifikovan preko
`Get-CimInstance Win32_Process` (potvrđena tačna komandna linija —
`dist\Dentaland\Dentaland.exe` u ovom worktree-u), pa ubijen ciljano
(`Stop-Process -Id 19460`) — isti bezbjedan obrazac korišten ranije u
sesiji (ciljani PID, ne blanket taskkill). **Non-blocking napomena za
implementera**: vlastiti test proces bi trebalo eksplicitno terminirati u
skripti, ne ostaviti ga da visi nakon `process alive after 12s: True`
provjere.

Nakon toga, `rm -rf build dist` pa čist build:

```text
python -m PyInstaller packaging/dentaland.spec --noconfirm
...
INFO: Build complete! The results are available in: ...\dist
```

Uspješan, bez grešaka/warninga specifičnih za ovaj spec. Resursi fizički
prisutni u `_internal/` (provjereno `find`): `web/assets/logo.png`,
`web/assets/dentaland.ico`, `desktop/assets/doctors/{ana,ljubo,zorka}.png`.

## 3. Nezavisna clean-machine simulacija (stvaran tool output)

Cijeli `dist/Dentaland/` folder kopiran u IZOLOVANI scratch folder VAN
repoa (`.../scratchpad/dent009-review/run/`), pokrenut kroz PowerShell
`Start-Process` (ne bash — izbjegnut isti path-translation rizik koji je
ranije u sesiji pokvario jedan adversarni pokušaj kod DENT-IMPROVE-007
reviewa), sa `DENTALAND_DATA_DIR` na svjež scratch folder,
`QT_QPA_PLATFORM=offscreen`, i eksplicitno uklonjenom `PYTHONPATH`
varijablom iz te sesije:

```text
process alive after 8s: True
Test-Path .../data/dentaland.db → True
```

Inspekcija baze (zaseban Python skript, van bash path-prevoda):

```text
tables: ['appointments', 'doctors', 'services', 'time_off', 'working_hours']
```

Identično Pi-jevoj tvrdnji u implementer izvještaju — nezavisno
reprodukovano, ne prepisano. Proces sam ubijen na kraju provjere
(`Stop-Process`), za razliku od Pi-jevog leftover procesa iz sekcije 2 —
potvrđeno da nakon mog testa nema zaostalih `Dentaland.exe` procesa
(`Get-CimInstance` prazan rezultat).

## 4. Spec fajl — pregled

`packaging/dentaland.spec`: `Analysis(['desktop/app.py'], pathex=[ROOT,
ROOT/"src"])` — ispravno uključuje i `desktop/` (korijen) i `src/`
(gdje živi `dentaland` paket) na path, što se poklapa sa Pi-jevim
zabilježenim nalazom (prvi build bez `src/` u `pathex` je pucao sa
`ModuleNotFoundError: No module named 'dentaland'` — realan bug,
popravljen isključivo u spec fajlu, ne u aplikacijskom kodu — u skladu sa
allowed_paths). `datas` layout se tačno poklapa sa
`paths.resource_path()` pozivima u `main_window.py`/`sidebar.py`
(`web/assets/...`, `desktop/assets/doctors/...`). `console=False`,
`onedir` (`exclude_binaries=True` + `COLLECT`), `icon=dentaland.ico` — sve
u skladu sa Task Contractom. `architecture: PASS`.

## 5. Ikonica — manja kozmetička napomena (non-blocking)

`web/assets/logo.png` je 863×871 (ne savršeno kvadratan). Pillow-ov ICO
export sa `sizes=[(s,s)...]` čuva aspect ratio izvornika, pa generisani
`.ico` ima frejmove blago izvan tačnih kvadratnih dimenzija (npr. 63×64
umjesto 64×64, 254×256 umjesto 256×256) — provjereno direktno
(`Image.open(...).info["sizes"]`). Vizuelno gotovo neprimjetno, ne
blokira PASS; ako se ikad radi novi logo, vrijedi izvorno praviti
kvadratan asset.

## 6. Dokumentacija i out-of-scope disciplina

`docs/dentaland-windows-packaging.md` tačno razdvaja "na stvarno čistoj
mašini (Radovan)" od "simulacija bez čiste mašine" — ne tvrdi više nego
što je stvarno dokazano. Ispravno objašnjava SmartScreen/AV/code-signing
ograničenja kao poznata, van obima. `pyproject.toml` dopuna je minimalna
(`pyinstaller`, `pillow` u postojećoj `dev` grupi, bez nove grupe —
proporcionalno obimu projekta). `.gitignore` već pokriva `build/`/`dist/`
— provjereno da build artefakti ne završe u git statusu.

## 7. Puna verifikacija (ponovljena nezavisno)

```text
pytest tests/ -q                              → 298 passed, 11 warnings
ruff check src/dentaland desktop backend tests → All checks passed!
mypy src/dentaland desktop backend             → Success: no issues found in 37 source files
```

## 8. Requirements/acceptance iz backloga — provjera

- build ne zavisi od source checkout-a — potvrđeno živo (izolovan folder,
  bez PYTHONPATH).
- baza se piše u user data folder — potvrđeno (`DENTALAND_DATA_DIR`
  ekvivalent `%LOCALAPPDATA%\Dentaland`, isti kod put preko `paths.py`,
  nedirano).
- resursi se učitavaju — potvrđeno fizičkim prisustvom u `_internal/` +
  nedirana `resource_path()` `_MEIPASS` grana.
- testirana druga mašina/VM — **djelimično**, iskreno i eksplicitno
  označeno kao simulacija na istoj mašini u i implementer izvještaju i u
  dokumentaciji, ne kao lažna tvrdnja o pravoj drugoj mašini. Ovo je
  najbolje što je izvodivo bez fizičkog pristupa drugoj mašini/VM-u u
  ovoj sesiji — stvarna druga mašina ostaje Radovanova provjera prije ili
  poslije merge-a, ne blokira review PASS.

## Zaključak

PASS. Build je reproducibilan, resursi i baza rade kroz stvarni
PyInstaller bundle layout, aplikacijski kod je nedirana, a jedini
pronađeni bug (nedostajući `src/` u `pathex`) je ispravno popravljen
unutar build konfiguracije, ne aplikacije. Sve provjereno nezavisno
(vlastiti build od nule, vlastita izolovana simulacija, vlastita
inspekcija baze) — ne samo prepisano iz implementer izvještaja. Dvije
non-blocking napomene (leftover test proces, blago nekvadratna ikonica)
ne zahtijevaju izmjenu. Nema blokirajućih nalaza. Čeka Radovanov human
approval (MEDIUM tok) prije merge-a.
