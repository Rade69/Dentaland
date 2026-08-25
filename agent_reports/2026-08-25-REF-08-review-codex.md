# REF-08 — Codex independent review (test kvalitet)

```yaml
verdict: PASS
scope: PASS
acceptance: PASS
architecture: PASS
security: PASS
blocking_findings: []
```

## CILJ

Provjeriti behavior-preserving izdvajanje theme/QSS-a, ograničenu timezone
konsolidaciju, stvarni PyInstaller build/smoke i tačnost završne projektne
mape.

## URAĐENO

- Potvrđeni branch `task/REF-08-theme-timezone-cleanup`, commit `3949172` i
  base `8948d9c` kao ancestor.
- Scope je tačno **12 fajlova, 586 additions, 207 deletions** i poklapa se sa
  allowed paths. Forbidden fajlovi nisu dirani; jedini dozvoljeni dialog je
  `blockout_delete_confirm.py`.
- `pytest tests/ -q`: **355 passed**, 11 warnings.
- `ruff check src/dentaland desktop backend tests`: čist.
- `mypy src/dentaland desktop backend`: čist, **50 source fajlova**.

### F1 — riješeno u `41937cf`

`.agent/PROJECT_MAP.md` sada kaže:

> `src/dentaland/timezone.py` — jedina definicija `SARAJEVO` IANA zone;
> produkcijski kod importuje odavde.

To nije stvarno stanje repoa. Grep potvrđuje da devet produkcijskih fajlova
i dalje nezavisno definiše `SARAJEVO = ZoneInfo("Europe/Sarajevo")`:

- `src/dentaland/services/notifications.py`;
- `src/dentaland/services/print_schedule.py`;
- šest fajlova u `desktop/views/dialogs/`;
- `desktop/views/requests_page.py`.

Implementer ih je korektno prijavio kao OUT_OF_SCOPE_FINDING i nije ih dirao,
ali mapa ne može istovremeno tvrditi da postoji samo jedna definicija.
Acceptance eksplicitno zahtijeva da PROJECT_MAP opisuje stvarno stanje.
Fix je dokumentacijski i mijenja samo `.agent/PROJECT_MAP.md`. Nova
formulacija opisuje `dentaland.timezone` kao kanonsku definiciju za sedam
migriranih fajlova (šest produkcijskih potrošača + `fake_data.py`) i
eksplicitno navodi devet legacy redefinicija kao poznat out-of-scope dug.

Nezavisni grep na `41937cf` potvrđuje:

```text
CANONICAL_IMPORT_FILES=7
LEGACY_DEFINITION_FILES=9
```

Drugi broj isključuje samu kanonsku definiciju u `src/dentaland/timezone.py`;
ukupno grep nalazi deset `SARAJEVO = ZoneInfo(...)` definicija. Scope fix
commita je tačno jedan dokumentacijski fajl. F1 je zatvoren.

### QSS poređenje

AST poređenje stvarnih runtime stringova iz
`8948d9c:desktop/views/main_window.py` i novog `GLOBAL_STYLESHEET` dalo je:

```text
OLD_CHARS 6978
NEW_CHARS 4866
RAW_EQUAL False
```

Razlika je isključivo uklonjena uvlaka triple-quoted stringa. Nakon
`textwrap.dedent` oba stringa imaju 4866 znakova i 176 linija, a rezultat je
`DEDENT_EQUAL True`. QSS sadržaj i ponašanje su zato sačuvani, ali izraz
„byte-identičan originalu“ nije doslovno tačan za raw runtime stringove;
tačno je „identičan nakon normalizacije uvlake“. Ovo nije blocking jer je QSS
whitespace-insensitive i sadržaj pravila je identičan.

### Timezone provjera

- `rg "from desktop.fake_data import.*SARAJEVO" desktop src`: nema rezultata.
- `desktop/fake_data.py` uvozi `SARAJEVO` iz `dentaland.timezone` i više nema
  svoju `ZoneInfo` definiciju.
- Svih devet OUT_OF_SCOPE redefinicija i dalje postoji, na tačno prijavljenim
  mjestima; diff potvrđuje da nisu mijenjane.

### PyInstaller build i izolovani smoke

- `python -m PyInstaller packaging/dentaland.spec --noconfirm`: uspješan
  build, PyInstaller 6.20.0.
- `dist/Dentaland` kopiran je u novi temp folder izvan repoa.
- `Dentaland.exe` pokrenut je sa temp working/data folderom,
  `QT_QPA_PLATFORM=offscreen` i bez `PYTHONPATH`.
- Proces je ostao živ nakon **12 sekundi** i kreirao `dentaland.db` veličine
  24576 bajta; zatim je zaustavljen kao review proces.
- `build/dentaland/warn-dentaland.txt` postoji i ima **0** pogodaka za
  `dentaland.timezone`, `desktop.presentation.theme` ili
  `desktop.presentation` missing-module upozorenja.

## NE DIRATI

- Ne konsolidovati preostalih devet timezone definicija u F1 fixu; ostaju
  zaseban out-of-scope cleanup.
- Ne mijenjati QSS sadržaj, modele, migracije, backend ili ostale controllere.
- Ne mijenjati PyInstaller spec; stvarni build dokazuje da novi statički
  importi rade bez spec izmjene.

## SLJEDEĆE

Codex test-quality review je PASS. Claude sada radi Reviewer 2 arhitektonski
pregled; Radovan human approval dolazi nakon oba review-a. Finalni paketni
acceptance review nije dio ovog zadatka.
