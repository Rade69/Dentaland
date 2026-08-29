---
task_id: DENT-IMPROVE-016
implementer: claude
created_at: 2026-08-29
---

# DENT-IMPROVE-016 — Produkcijski security/privacy release gate (skraćen obim) — implementerov izvještaj

## Urađeno

1. **`src/dentaland/backup_postgres.py`** — nov modul, `pg_dump`/`pg_restore`
   (subprocess) + Fernet enkripcija (poseban ključ, `backup_postgres.key`)
   + pojednostavljena rotacija ("zadrži zadnjih N", bez SQLite-ovog
   dnevno/mjesečnog sloja) + CLI (`run`/`restore-test`/`status`), po uzoru
   na `dentaland.backup`/`backup_cli`. `restore-test` kreira PRIVREMENU
   bazu (`CREATE DATABASE`), restore-uje u nju, verifikuje, pa je briše —
   nikad ne dira aktivnu bazu.
2. **`tests/test_backup_postgres.py`** — 6 testova, preskaču se ako
   `DATABASE_URL_TEST` nije postavljen (isti obrazac kao
   `test_postgres_migration.py`). Pokrivaju: run→restore-test uspjeh
   + potvrda da privremena baza stvarno nestane, da aktivna baza ostaje
   netaknuta, grešku kad nema backupa, rotaciju, grešku bez
   `DATABASE_URL`, i CLI put (`main()`).
3. **`docs/dentaland-postgres-backup-operativni-vodic.md`** — operativni
   vodič, po uzoru na postojeći SQLite backup vodič.
4. **`docs/dentaland-breach-runbook.md`** — koraci: detekcija,
   containment, procjena, 72h prijava Agenciji, obavještavanje pacijenata,
   interna evidencija, post-incident pregled.
5. **`docs/dentaland-retention-politika.md`** — formalizuje petogodišnji
   rok za booking podatke (ispravljeno sa pogrešnih "12 mjeseci" —
   vidi CLAUDE.md commit `0c83433`), potvrđuje da medicinska
   dokumentacija nije primjenjiva (ostaje na papiru van sistema),
   eksplicitno navodi da automatska anonimizacija/brisanje NIJE
   implementirana u kodu.
6. **`docs/dentaland-politika-produkcijski-podaci.md`** — formalizuje
   pravilo "stvarni podaci nikad u AI/dev dumpove", sa referencom na
   stvaran DENT-IMPROVE-012 presedan (14 pronađenih pacijentskih zapisa,
   ispravno neiskorišteno).

## Audit `web/privacy.html` (stavka 5 — provjera, ne pisanje)

Dokument je **kompletan** naspram CLAUDE.md/v3.1 zahtjeva. Pokriva svih
9 relevantnih tačaka: kontrolor (sekcija 1), koje podatke prikuplja +
eksplicitno upozorenje da ne unositi medicinske podatke (sekcija 2),
svrha (sekcija 3), pravni osnov (sekcija 4), koji podaci su obavezni
(sekcija 5), primaoci/obrađivači (sekcija 6), retention — pet godina
(sekcija 7, **potvrđeno tačno** 29.8.2026, vidi retention politiku
gore), prava lica (sekcija 8), pravo na prigovor Agenciji sa tačnim
kontaktom (sekcija 9), automatizovano odlučivanje (sekcija 10),
maloljetna lica (sekcija 11).

Dodatno potvrđeno: `web/tests/e2e/tests/booking.spec.js` test #7
(DENT-IMPROVE-011) već provjerava da link ka `privacy.html` postoji i
radi sa forme za zakazivanje — nije izolovan, nepovezan fajl.

**Nema stvarnog nalaza koji bi tražio izmjenu dokumenta.** Manja
napomena (nije defekt, samo zapažanje): sekcija 1 identifikuje
kontrolora imenom/adresom, ne formalnim registarskim brojem pravnog
subjekta — ovo je dosljedno sa CLAUDE.md "Otvorena pitanja" stavkom
"kontrolor/obrađivač ugovor" koja ostaje otvorena (potvrditi pravni
subjekt ordinacije). Nije nešto što ovaj task treba/smije mijenjati.

## OUT_OF_SCOPE_FINDING (prijavljen tokom rada, van allowed_paths)

Otkriveno tokom regresionog testiranja (`pytest tests/ -q` sa
`DATABASE_URL_TEST` postavljenim) — **potvrđeno da postoji identično na
`main` prije ovog taska**, nije izazvano ovim radom:

1. `tests/test_postgres_migration.py::test_confirm_preklapanje_vraca_409_nad_postgres`
   puca (401 umjesto 409) — Postgres-mirror test nije ažuriran za RBAC
   kredencijale kad je `DENT-IMPROVE-013` mergovan.
2. Lokalna Postgres instanca ima zastarjel `alembic_version` pečat
   (`d4e5f6a7b8c9`, DENT-022) naspram stvarnog head-a (`f6a7b8c9d0e1`,
   DENT-IMPROVE-014) — tabele postoje jer ih je `Base.metadata.create_all()`
   u test fixture-ima kreirao mimo alembic-a; migracije DENT-IMPROVE-013/014
   nikad nisu stvarno testirane u svom pravom (`alembic upgrade head`)
   obliku protiv ove instance.

Zabilježeno u `.agent/CURRENT_STATE.md` (commit `a373882`), predložen
budući `DENT-IMPROVE-017`. Ne blokira ovaj task.

## Fix runda 1 (Codex REJECT, 29.8.2026) — F1-F4

Codex review (`2026-08-29-DENT-IMPROVE-016-review-codex.md`) je vratio
**REJECT** sa 4 blocking findinga. Sva četiri popravljena, sa novim
regresionim testovima koji reprodukuju TAČNO Codexov adversarni scenario
(ne samo "sad je zeleno"):

- **F1 (HIGH, restore verifikacija ne dokazuje integritet):**
  `_verify_postgres_db` sada provjerava SVIH 8 `CORE_TABLES` (ne samo
  `appointments`) i vraća manifest broja redova po tabeli umjesto da
  odbacuje rezultat. Novi testovi: `test_verify_odbija_nepotpunu_semu`
  (direktna reprodukcija Codexovog adversarnog scenarija — baza sa samo
  praznom `appointments(id integer)` sad ispravno baca
  `RestoreVerificationError`) i
  `test_restore_test_manifest_odgovara_izvornoj_bazi` (manifest broj
  doktora u restore-ovanoj bazi mora TAČNO odgovarati broju u izvornoj).
- **F2 (HIGH, deterministički naziv privremene baze):**
  `_throwaway_db_name` sada dodaje `secrets.token_hex(8)` nasumičan sufiks
  po pozivu — nikad isto ime dva puta, pa je `DROP IF EXISTS` u cleanup-u
  bezbjedan (ime je garantovano kreirano/nepostojeće u OVOM pozivu, ne
  potencijalno tuđa baza). `restore_test` vraća stvarno korišteno ime
  (`RestoreTestResult.throwaway_db_name`) umjesto da ga pozivalac
  pretpostavlja.
- **F3 (MEDIUM, cleanup preskočen na post-create failure):** poziv
  `_create_throwaway_database(...)` premješten UNUTAR istog `try/finally`
  koji radi `_drop_throwaway_database(...)` — sad pokriva i pad tačno
  nakon uspješnog `CREATE DATABASE`. Novi test
  `test_restore_test_cisti_i_kad_pukne_odmah_nakon_create` (monkeypatch
  `_run_pg_restore` da baci odmah nakon create) potvrđuje da privremena
  baza ipak nestane.
- **F4 (MEDIUM, lozinka u argv):** `_url_without_password` (koristi
  `URL.create()` bez password argumenta — NE `set(password=None)`, koji
  je SQLAlchemy sentinel za "ne mijenjaj" i tiho ne bi ništa uklonio,
  otkriveno tokom fixa) + `_pg_subprocess_env` prosljeđuje lozinku kroz
  `PGPASSWORD` env varijablu. Novi test
  `test_run_pg_dump_ne_stavlja_lozinku_u_argv` potvrđuje da lozinka nije
  u argv-u i da je stvarno u env-u.

Usput otkriven i popravljen DODATNI bug (nije bio dio Codexovih nalaza):
`_pg_subprocess_env` je prvobitno gradio subprocess environment iz
pozivaočevog `env` override mapinga (namijenjenog SAMO za
`DENTALAND_PG_BIN_DIR`/config lookup), umjesto iz stvarnog `os.environ`
— u CLI testu sa namjerno minimalnim `env` dictom (samo `DATABASE_URL` +
`DENTALAND_DATA_DIR`) ovo je subprocess-u oduzelo `PATH`/`SYSTEMROOT`,
pa je `pg_dump` pucao na DNS resoluciji za "localhost". Ispravljeno da
`_pg_subprocess_env` uvijek koristi puni `os.environ` kao bazu.

## Verifikacija (nakon fix runde 1)

- `pytest tests/test_backup_postgres.py -v` (sa `DATABASE_URL_TEST`) →
  **10 passed** (6 originalnih + 4 nova regresiona testa za F1-F4).
- `pytest tests/ -q` (sa `DATABASE_URL_TEST`) → **439 passed, 2 failed**
  — ista dva pre-postojeća OUT_OF_SCOPE_FINDING failure-a kao ranije, ne
  nova.
- `ruff check src/dentaland desktop backend tests scripts/agent_sensors.py`
  → **All checks passed**.
- `mypy src/dentaland desktop backend` → **Success: no issues found in
  55 source files**.
- `python scripts/agent_sensors.py --all` → **0 blocking findings**.

## Fix runda 2 (Codex REJECT ponovo, 29.8.2026) — F1/F2/F4 dublje

Codexov re-review je zatvorio F3, ali ispravno pokazao da F1/F2/F4 fix
runde 1 nisu bili dovoljno duboki — svaki sa konkretnim adversarnim
dokazom:

- **F1 (`DIFFERENT_DATA_SAME_MANIFEST_ACCEPTED=True`):** manifest broja
  redova ne dokazuje da je SADRŽAJ identičan — restore koji tiho
  zamijeni vrijednost u redu bez promjene broja redova je prolazio.
  **Fix:** `_compute_manifest` sad računa SHA-256 digest nad kanonski
  poređanim (`ORDER BY id`) sadržajem svakog reda, ne samo broj.
  `create_backup` snima taj digest u novi sidecar fajl
  (`<backup>.manifest.json`, pored enkriptovanog dumpa — nije osjetljiv,
  sadrži samo hash-eve, ne sirove podatke) u trenutku kad je IZVORNA
  baza dumpovana. `restore_test` poredi digest RESTORE-ovane baze sa tim
  snimljenim manifestom (`_verify_content_matches_manifest`) — mismatch
  baca `RestoreVerificationError`. `rotate_backups` briše i sidecar uz
  stari dump. Novi adversarni test
  `test_restore_hvata_izmijenjen_sadrzaj_uz_isti_broj_redova` restore-uje
  STVARAN backup u privremenu bazu, ručno mijenja sadržaj bez mijenjanja
  broja redova, i potvrđuje da poređenje to hvata.
- **F2 (`EXISTING_DB_WAS_DROPPED_AND_RECREATED=True`):** nasumičan sufiks
  je smanjio VJEROVATNOĆU kolizije, ali `_create_throwaway_database` je
  i dalje radila bezuslovan `DROP IF EXISTS` prije `CREATE` — kod
  kolizije bi obrisala tuđu bazu. **Fix:** uklonjen pre-emptive `DROP`;
  `_create_throwaway_database` sad SAMO pokušava `CREATE DATABASE` —
  kolizija (`psycopg2.errors.DuplicateDatabase`) postaje `BackupError`
  ("kolizija imena... nije naša da je brišemo"), ne brisanje. `restore_test`
  postavlja `created = True` TEK nakon uspješnog create-a, a cleanup u
  `finally` poziva `_drop_throwaway_database` SAMO ako je ta zastavica
  `True` — ownership se dokazuje činjenicom da smo mi kreirali bazu, ne
  pretpostavkom. Novi adversarni test
  `test_create_throwaway_ne_brise_postojecu_bazu_kod_kolizije` unaprijed
  kreira "tuđu" bazu sa sentinel tabelom pod imenom koje će
  `restore_test` pokušati koristiti, i potvrđuje da (a) `restore_test`
  baca grešku umjesto da je obriše, (b) sentinel tabela preživi.
- **F4 (`QUERY_PASSWORD_IN_ARGV=True`):** fix runde 1 je čistio lozinku
  SAMO iz authority dijela URL-a (`user:pass@host`) — libpq URL može
  nositi lozinku i kao `?password=...` query parametar, koji je i dalje
  curio u argv. **Fix:** `_extract_password` sad čita OBA oblika;
  `_url_without_password` dodatno zove
  `URL.difference_update_query(["password"])` da ukloni query-param
  formu. Novi parametrizovan test
  `test_pg_dump_i_restore_ne_stavljaju_lozinku_u_argv_ni_jednim_oblikom`
  pokriva oba oblika (authority/query) kroz OBA subprocess puta
  (`pg_dump` i `pg_restore`), ne samo jedan kao ranije.

`RestoreTestResult` proširen sa `content_digests: dict[str, str]` poljem
(pored postojećeg `table_counts`) — dokaz i broja i sadržaja dostupan
pozivaocu.

## Verifikacija (nakon fix runde 2)

- `pytest tests/test_backup_postgres.py -v` (sa `DATABASE_URL_TEST`) →
  **13 passed** (10 iz runde 1 + 3 nova adversarna regresiona testa za
  F1/F2/F4 round 2).
- `pytest tests/ -q` (sa `DATABASE_URL_TEST`) → **442 passed, 2 failed**
  — ista dva pre-postojeća OUT_OF_SCOPE_FINDING failure-a, nepromijenjena.
- `ruff check src/dentaland desktop backend tests scripts/agent_sensors.py`
  → **All checks passed**.
- `mypy src/dentaland desktop backend` → **Success: no issues found in
  55 source files**.
- `python scripts/agent_sensors.py --all` → **0 blocking findings**.

## Fix runda 3 (Codex REJECT treći put, 29.8.2026) — F1 snapshot race + F3 ponovo

Codexova treća re-verifikacija je zatvorila F2 i F4 potpuno, ali otkrila
dva dublja problema — jedan nov (F1), jedan ponovo otvoren (F3):

- **F1 (`VALID_DUMP_REJECTED_AFTER_CONCURRENT_POST_DUMP_WRITE=True`):**
  fix runde 2 je računao manifest iz ŽIVE izvorne baze NAKON što je
  `pg_dump` završio — ako neko upiše podatak u aktivnu bazu baš u tom
  malom vremenskom prozoru, manifest opisuje NOVIJE stanje nego što dump
  stvarno sadrži, pa bi VALIDAN backup lažno pao restore-test kasnije.
  **Fix:** `create_backup` sad računa manifest iz PRIVREMENOG RESTORE-A
  SAMOG DUMPA (isti mehanizam kao `restore_test`), ne iz žive baze —
  garantuje da manifest opisuje TAČNO ono što je u dumpu, bez obzira šta
  se dešava sa izvornom bazom poslije. Cijena: `create_backup` sad radi
  pun restore-ciklus interno (dvostruko sporije nego prije), prihvatljivo
  za obim jedne ordinacije. Novi test
  `test_restore_test_prolazi_i_kad_se_izvorna_baza_promijeni_poslije_backupa`
  direktno reprodukuje Codexov scenario (upis u izvornu bazu POSLIJE
  `create_backup`) i potvrđuje da `restore_test` i dalje prolazi.
- **F3 (`ORIGINAL_POST_CREATE_FAILURE_LEFT_DB=True`, ponovo otvoren):**
  `created` zastavica u pozivaocu se postavljala TEK nakon što je
  `_create_throwaway_database` uredno vratila — ako CREATE uspije
  server-side ali NEŠTO DRUGO (npr. cursor/connection cleanup unutar te
  funkcije) pukne prije povratka, pozivalac nikad nije saznao da treba
  čistiti. **Fix:** `_create_throwaway_database` sad ima sopstveni
  self-cleanup kontrakt — ako baci BILO KOJI izuzetak osim kolizije
  imena, GARANTOVANO nije ostavila bazu iza sebe (sama je čisti prije
  re-raise-a). Pozivaoci (`restore_test`, `create_backup`) više ne prate
  `created` zastavicu — samo pozivaju funkciju izvan svog cleanup
  try/finally-a, koji sad pokriva SAMO korake POSLIJE uspješnog kreiranja.
  Novi adversarni test
  `test_create_throwaway_samocisti_kad_connection_close_pukne_nakon_create`
  koristi tanak proxy oko psycopg2 konekcije (C-extension objekat, `close`
  se ne može direktno monkeypatch-ovati) da simulira tačno taj handoff gap.

## Verifikacija (nakon fix runde 3)

- `pytest tests/test_backup_postgres.py -v` (sa `DATABASE_URL_TEST`) →
  **15 passed** (13 iz runde 2 + 2 nova adversarna regresiona testa za
  F1 snapshot race i F3 handoff gap).
- `pytest tests/ -q` (sa `DATABASE_URL_TEST`) → **444 passed, 2 failed**
  — ista dva pre-postojeća OUT_OF_SCOPE_FINDING failure-a, nepromijenjena.
- `ruff check src/dentaland desktop backend tests scripts/agent_sensors.py`
  → **All checks passed**.
- `mypy src/dentaland desktop backend` → **Success: no issues found in
  55 source files**.
- `python scripts/agent_sensors.py --all` → **0 blocking findings**.

## Fix runda 4 (Codex REJECT četvrti put, 29.8.2026) — F3 caller-gap + F5 (nov, HIGH)

Codexova četvrta re-verifikacija je potvrdila F1/F2/F4 kao trajno
zatvorene, ali pokazala da F3 ima još uži preostali prozor, i otkrila
NOV HIGH nalaz (F5):

- **F3 (`POST_HELPER_RETURN_GAP_LEFT_DB=True`):** self-cleanup UNUTAR
  `_create_throwaway_database` je ispravno pokrivao greške unutar te
  funkcije — ali oba pozivaoca su je pozivala PRIJE uspostavljanja
  SVOG `try/finally` za DROP. Ako bi izuzetak pogodio TAČNO na granici
  između uspješnog povratka helpera i ulaska pozivaoca u svoj `try`
  (npr. signal/`KeyboardInterrupt`), ni jedna strana ne bi imala
  cleanup obavezu aktivnu. **Fix:** `_create_throwaway_database` i
  `_drop_throwaway_database` spojeni u JEDAN `@contextlib.contextmanager`
  (`_temporary_database`) čiji `try/finally` pokriva CIJELI životni vijek
  baze — kreiranje, `yield` pozivaocu, i DROP — bez ijedne praznine
  između faza. Pozivaoci (`create_backup`, `restore_test`) sad koriste
  `with _temporary_database(url, name): ...` umjesto ručnog
  create+try/finally sklopa.
- **F5 (HIGH, nov, `PREVIOUS_VALID_SAME_DAY_BACKUP_PAIR_BROKEN`):**
  fix runde 3 je pisao dump i manifest kao DVA odvojena fajla, svaki
  objavljen svojim `Path.replace()` pozivom — ako DRUGI replace pukne
  nakon što je PRVI uspio, prethodni validan par (dnevno ime se ponavlja)
  biva pokvaren/nekompletan. **Fix:** dump i manifest se sad pakuju u
  JEDAN kombinovan fajl (`_pack_backup_file`/`_unpack_backup_file` —
  `[8B dužina][manifest JSON][enkriptovan dump]`), pisan na STAGING
  putanju i objavljen JEDNIM `Path.replace()` pozivom tek kad SVE uspije
  — stvarna atomičnost, nema prozora između dva koraka jer postoji samo
  jedan. `.manifest.json` sidecar mehanizam iz runde 2/3 je uklonjen u
  potpunosti (zamijenjen ovim).

Novi adversarni regresioni testovi: prošireni
`test_create_throwaway_samocisti_kad_connection_close_pukne_nakon_create`
(sad testira `_temporary_database` direktno) i nov
`test_neuspjesan_drugi_backup_ne_kvari_prethodni_validan_par`
(simulira pad `_compute_manifest` na DRUGOM pokušaju istog dana,
potvrđuje da prvi validan par ostaje bit-za-bit netaknut i i dalje
prolazi `restore_test`, i da nema zaostalih `.staging` fajlova).

## Verifikacija (nakon fix runde 4)

- `pytest tests/test_backup_postgres.py -v` (sa `DATABASE_URL_TEST`) →
  **16 passed** (15 iz runde 3 + 1 nov adversarni regresioni test za F5;
  F3 test prerađen da testira `_temporary_database`).
- `pytest tests/ -q` (sa `DATABASE_URL_TEST`) → **445 passed, 2 failed**
  — ista dva pre-postojeća OUT_OF_SCOPE_FINDING failure-a, nepromijenjena.
- `ruff check src/dentaland desktop backend tests scripts/agent_sensors.py`
  → **All checks passed**.
- `mypy src/dentaland desktop backend` → **Success: no issues found in
  55 source files**.
- `python scripts/agent_sensors.py --all` → **0 blocking findings**.

## Required output

```yaml
verdict: PASS_WITH_NOTES
blocking_findings: []
evidence:
  - src/dentaland/backup_postgres.py (F1-F5 popravljeni kroz cetiri runde - snapshot race, unified cleanup context manager, atomsko jednofajlno objavljivanje)
  - tests/test_backup_postgres.py (16 passed, uklj. 10 adversarnih regresionih testova za F1/F2/F3/F4/F5 kroz sve cetiri runde)
  - docs/dentaland-postgres-backup-operativni-vodic.md
  - docs/dentaland-breach-runbook.md
  - docs/dentaland-retention-politika.md
  - docs/dentaland-politika-produkcijski-podaci.md
  - web/privacy.html audit — kompletan, bez izmjena
open_risks:
  - "HTTPS, processor evidencija, EXCLUDE constraint namjerno van obima - cekaju Radovanovu hosting odluku (kraj projekta)"
  - "Automatska anonimizacija/brisanje nakon 5 godina nije implementirana u kodu - samo politika, buduci implementacioni task"
  - "token sigurnost i minimalna javna forma nisu formalno auditovani ovim gate-om (vjerovatno OK, ranije provjereno indirektno kroz DENT-IMPROVE-011 E2E)"
  - "OUT_OF_SCOPE_FINDING: stale Postgres RBAC test + alembic pecat neusklađenost (buduci DENT-IMPROVE-017), potvrđeno predpostojece na main"
```

## Sljedeće

Codex ponavlja ciljanu verifikaciju F1-F4 (novo pravilo od 29.8.2026 —
jedan reviewer, ne dva, vidi `docs/dentaland-agentski-razvoj.md`). Nakon
PASS-a ide Radovanovo human approval prije merge-a.
