---
task_id: DENT-012
reviewer: pi
review_number: 2
risk: HIGH
verdict: REJECT
date: 2026-08-17
---

# Review 2 (Pi) — DENT-012: confirmed_at / arrived_at

```yaml
verdict: REJECT
scope: FAIL
acceptance: PASS
architecture: PASS
security: PASS
blocking_findings:
  - location: "CLAUDE.md (kraj fajla, blok '<!-- gitnexus:start --> ... <!-- gitnexus:end -->', +44 linije)"
    rule: "Task Contract forbidden_paths eksplicitno uključuje CLAUDE.md — fajl je izmijenjen u radnom drvetu (git status: M CLAUDE.md)."
    fix: "git restore CLAUDE.md prije merge-a. GitNexus integraciju, ako je namjerna, izdvojiti u poseban zadatak/commit van DENT-012."
  - location: "AGENTS.md (kraj fajla, isti GitNexus blok, +44 linije)"
    rule: "Task Contract forbidden_paths eksplicitno uključuje AGENTS.md — fajl je izmijenjen u radnom drvetu (git status: M AGENTS.md)."
    fix: "git restore AGENTS.md prije merge-a. Isto kao gore."
  - location: ".claude/skills/ (untracked folder)"
    rule: "Van allowed_paths — nije task artefakt DENT-012, a nije ni u allowed_paths."
    fix: "Ukloniti iz worktree-a prije merge-a (ili izdvojiti kao poseban infrastrukturni zadatak)."
```

## Prozna analiza

### Scope — FAIL (jedini blokator)

`git status --short` u worktree-u `DENT-012-status-tracking` pokazuje, pored
dozvoljenih fajlova, tri stavke van obima:

- `M CLAUDE.md` — dodat GitNexus "Code Intelligence" blok od 44 linije na
  kraj fajla (auto-insert GitNexus alata prilikom indeksiranja).
- `M AGENTS.md` — isti blok od 44 linije na kraj fajla.
- `?? .claude/skills/` — untracked folder sa GitNexus skillovima.

Sva tri su van `allowed_paths`, a CLAUDE.md i AGENTS.md su čak i eksplicitno u
`forbidden_paths` Task Contracta. Ovo je HIGH-risk šema zadatak gdje je scope
disciplina najstroža, a CLAUDE.md je operativni izvor istine za SVE agente —
mijenjanje mu se u ovom kontekstu ne smije provući kao nuspojava. Nalaz je
objektivno testabilan (`git status`/`git diff -- CLAUDE.md AGENTS.md`) i ne
zavisi od namjere: dok su ti fajlovi modifikovani u radnom drvetu, merge bi ih
povukao u `main`, čime bi forbidden fajlovi ušli kroz zadatak koji ih je
izričito zabranio dirati.

Kod samog zadatka je ispravan (vidi ispod) — ovo je čisto higijena worktree-a,
ne kvalitet implementacije.

### Acceptance — PASS

Sve stavke nezavisno potvrđene:

- `confirmed_at` i `arrived_at` su `Mapped[datetime | None]` preko `TZDateTime()`,
  `nullable=True` (models.py, uz ispravan docstring o nezavisnosti od statusa).
- `AppointmentStatus` enum NIJE mijenjan (vrijednosti SCHEDULED/CANCELLED/
  COMPLETED/NO_SHOW/PENDING/REJECTED netaknute).
- `src/dentaland/services/requests.py` NIJE diran (`git diff --stat` prazan za
  `src/dentaland/services/`); `confirm_request` ne popunjava `confirmed_at`,
  što je namjerno i dokumentovano kao follow-up.
- Migracija `c3d4e5f6a7b8` je batch-mode (`recreate="always"`), `add_column` x2
  nullable, bez `server_default`; downgrade drop-uje obje kolone obrnutim
  redoslijedom.
- Postojeći redovi poslije upgrade-a dobijaju NULL u oba polja — pokriveno
  determinističkim testom (vidi Verifikacija).

### Architecture — PASS

- Aditivne nullable kolone, nezavisne od status enuma — ne diraju
  `EXCLUDE`/overlap logiku. Nezavisno potvrđeno da overlap-check i dalje
  filtrira ISKLJUČIVO po statusu: `booking.py:209` i `requests.py:128` oba
  `Appointment.status == AppointmentStatus.SCHEDULED`. `confirmed_at`/`arrived_at`
  ne ulaze ni u jedan filter, pa ne mogu uticati na overlap ni sada ni kasnije.
- `TZDateTime()` je dosljedan ostatku šeme (timezone-aware pravilo iz CLAUDE.md).
  Migracija koristi `sa.DateTime()` umjesto custom TypeDecorator-a — ispravno,
  jer TypeDecorator živi u `models.py` i migracije ga ne trebaju importovati
  (u bazi je ionako običan DateTime).
- Batch-mode + `recreate="always"` je ispravan SQLite pattern za alter table
  (SQLite ne podržava `DROP COLUMN`/`ADD COLUMN` na isti način kao PG).

### Security — PASS

- Nema ličnih podataka, kredencijala, tokena ni tajni u izmjeni — dvije
  timestamp kolone za interne radne tokove.
- `TZDateTime` garantuje timezone-aware vrijednosti (naivan datetime se
  odbacuje), što je u skladu sa sigurnosnim/vremenskim pravilima CLAUDE.md.
- Migracija ne dira podatke destruktivno: downgrade drop-uje samo dvije nove
  kolone, ostatak redova/kolona ostaje netaknut.

## Verifikacija (nezavisno izvršena)

```
pytest tests/ -q
74 passed, 11 warnings in 4.19s

pytest tests/test_models.py::test_migracija_cuva_postojece_termine_pri_upgrade_i_downgrade \
       tests/test_models.py::test_alembic_migracija_dodaje_confirmed_arrived_at -v
2 passed

ruff check src/dentaland tests migrations
All checks passed!

mypy src/dentaland desktop
Found 8 errors in 3 files (checked 13 source files)
— svih 8 u desktop/ (appointment_dialog.py x1, week_view.py x4, main_window.py x2);
  nula novih grešaka iz DENT-012 (src/dentaland čist).
```

Migracioni test za očuvanje podataka sam POKRENUO (ne samo pročitao da
postoji) — prolazi: upgrade do `b2c3d4e5f6a7` → upis stvarnog SCHEDULED
termina raw SQL-om → upgrade na `head` (oba nova polja NULL, status i ime
netaknuti) → downgrade na `b2c3d4e5f6a7` (termin i status očuvani, kolone
uklonjene). To je deterministički dokaz (hijerarhija: test > ručna provjera)
za acceptance stavke "postojeći termini ostaju" i "NULL default".

## Zaključak

Implementacija (models.py, migracija, testovi) je tehnički ispravna i spremna.
REJECT se odnosi ISKLJUČIVO na scope: GitNexus side-effect je izmijenio
`CLAUDE.md` i `AGENTS.md` (forbidden) i ostavio `.claude/skills/` (van obima)
u radnom drvetu. Nakon `git restore CLAUDE.md AGENTS.md` i uklanjanja
`.claude/skills/` (ili izdvajanja GitNexus integracije u poseban zadatak),
zadatak je spreman za human approval i merge.
