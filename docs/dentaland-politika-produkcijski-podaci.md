# Dentaland — politika: produkcijski podaci van AI/dev dumpova (DENT-IMPROVE-016)

Pravilo: **stvarni podaci pacijenata se nikad ne kopiraju u dev/test
baze, lokalne dumpove, agent radne prostore, niti pokazuju AI agentima**
(uključujući ovaj i buduće Claude Code/Codex/Pi/Crush sesije).

## Zašto ovo pravilo postoji — stvaran presedan

Tokom `DENT-IMPROVE-012` (27.8.2026, SQLite→PostgreSQL migracija),
implementer je otvorio glavni repo lokalni SQLite fajl
(`C:\Users\38765\Desktop\Dentaland\dentaland.db`) radi provjere prije
pisanja migracionog skripta, i pronašao **14 stvarnih pacijentskih
zapisa** (ime/telefon/email koji se poklapaju sa vlasnikom projekta) —
ne sintetske test podatke.

Implementer je ispravno prepoznao rizik i **nije koristio taj fajl** za
testiranje migracionog skripta — umjesto toga, migracioni skript
(`scripts/migrate_sqlite_to_postgres.py`) je dizajniran da izvor prima
generički (`--source-sqlite` argument), i testiran je isključivo nad
svježe generisanom SINTETSKOM SQLite bazom (vidi docstring tog
skripta). Nalaz je zabilježen kao `OUT_OF_SCOPE_FINDING` u
`agent_reports/2026-08-27-DENT-IMPROVE-012-plan.md` i finalnom
izvještaju tog taska. Radovan je naknadno obrisao tih 14 zapisa i
pokrenuo `VACUUM` na fajlu.

Ovo je bilo ispravno postupanje BEZ formalnog pravila koje bi ga
zahtijevalo — ovaj dokument formalizuje ono što je tad urađeno
neformalno/instinktivno, da se ne oslanja na to da svaki budući agent
sam prepozna isti rizik.

## Pravilo — konkretno

1. **Prije bilo kakvog rada nad lokalnom bazom** (SQLite fajl ili
   PostgreSQL instanca), provjeriti da li sadrži stvarne podatke prije
   nego što se koristi kao izvor testiranja, migracije, ili se njen
   sadržaj citira/pokazuje AI agentu. Provjera je jeftina (npr. `SELECT
   COUNT(*)`, spot-check da li imena/telefoni liče na stvarne kontakte
   naspram očigledno sintetskih poput "Test Pacijent") i mora se raditi
   PRIJE upotrebe, ne poslije.
2. **AI agenti (Claude Code, Codex, Pi, Crush) nikad ne smiju dobiti na
   uvid stvaran sadržaj pacijentskih redova** — ni kroz direktan upit
   nad bazom, ni kroz copy-paste u chat, ni kroz snimljen
   `agent_reports/` izvještaj. Ako je provjera iz tačke 1 pokazala
   stvarne podatke, prijaviti to Radovanu (kao `OUT_OF_SCOPE_FINDING`,
   po uzoru na DENT-IMPROVE-012 presedan) i STATI — ne nastavljati rad
   nad tim fajlom dok Radovan ne odluči (obrisati, izuzeti iz obima,
   itd.).
3. **Migracije/backup/restore skriptovi koji dotiču bazu moraju raditi
   generički** (izvor/odredište kao parametar, ne hardkodovan put do
   glavnog repo fajla) — isti obrazac kao
   `scripts/migrate_sqlite_to_postgres.py`. Ovo sprečava da skript sam
   po sebi postane rizik ako se pokrene bez razmišljanja.
4. **Testovi (uklj. `tests/test_backup_postgres.py`, DENT-IMPROVE-016)
   rade isključivo nad IZOLOVANIM test bazama** (`DATABASE_URL_TEST`,
   `dentaland_test` na portu 5433 — nikad `dentaland_dev` niti bilo koja
   buduća produkcijska baza) i sami kreiraju/čiste sopstvene marker-
   tagovane test podatke (obrazac iz `tests/test_postgres_migration.py`
   — imena poput `"Test Doktor <marker>"`), nikad ne pretpostavljaju da
   je baza već prazna niti ostavljaju svoje podatke iza sebe.
5. **Repo je javno vidljiv kroz git istoriju** (GitHub) — nijedan
   commit, `agent_reports/` izvještaj, test fixture ili dokumentacija ne
   smije sadržati stvaran pacijentski podatak, čak ni u primjeru/citatu.

## Provjera za ovaj task (DENT-IMPROVE-016)

Prije pisanja `tests/test_backup_postgres.py`, provjerena je
`dentaland_dev` baza (`SELECT COUNT(*) FROM appointments` /
`SELECT COUNT(*) FROM doctors`) — oba vratila 0. Baza je prazna, nema
rizika. Testovi rade nad `DATABASE_URL_TEST` (`dentaland_test`) sa
marker-tagovanim sintetskim podacima (`"Test Doktor Backup Postgres
Test"`), čišćenim u teardown-u.
