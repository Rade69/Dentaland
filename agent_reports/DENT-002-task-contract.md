---
task_id: DENT-002
risk: MEDIUM
implementer: pi
reviewer: claude
status: REVIEWED — vidi 2026-08-16-DENT-002-gui-shell.md za pun izvještaj
created_at: 2026-08-16
---

# Task Contract — DENT-002

```yaml
id: DENT-002
title: Faza 0 — Desktop GUI ljuska (sedmični kalendar + unos termina), bez baze
risk: MEDIUM
objective: >
  PySide6 GUI ljuska prema Faza 0 funkcionalnostima iz
  docs/dentaland-razvojni-plan.md: sedmični pregled kao početni ekran (ne
  dnevni), klik na prazan slot odmah otvara unos termina bez međuekrana,
  prevlačenje termina mišem mijenja vrijeme, slobodno tekstualno polje za
  napomenu bez agresivne validacije, dugme "Štampaj raspored za dan/sedmicu"
  (sama štampa može biti stub). Raditi ISKLJUČIVO nad privremenim in-memory
  fake podatkovnim slojem (plain Python dataclass), NE SQLAlchemy — pravilo
  "desktop/views/ nikad ne uvozi SQLAlchemy direktno" važi od prvog reda koda.
allowed_paths: [desktop/**, tests/test_gui/**]
forbidden_paths: [pyproject.toml, src/dentaland/**, migrations/**, CLAUDE.md, AGENTS.md, docs/**]
acceptance:
  - Sedmični prikaz je početni ekran.
  - Klik na prazan slot → dijalog (ime, telefon, email, usluga, napomena), bez međuekrana.
  - Prevlačenje termina mišem ažurira prikazano vrijeme (na fake podacima).
  - Napomena je slobodan tekst.
  - Dugme "Štampaj raspored" postoji (funkcija štampe može biti TODO).
  - Nula importa SQLAlchemy/DB koda unutar desktop/views/ — provjerljivo grep-om.
  - Osnovni GUI testovi (pytest-qt ili ekvivalent) za klik-za-unos i prevlačenje.
verification:
  - pytest tests/test_gui
  - ruff check desktop
  - "grep -r sqlalchemy desktop/views  # očekivano prazno"
review:
  reviewers: 1
  required: [architecture, scope]
```

## Odgovori na pitanja iz blokera (16.8.2026)

**1. Obim "GUI ljuske" — nije čist skelet.** Uključuje stvarne Faza 0 interakcije: sedmični prikaz, klik-za-unos dijalog (ime/telefon/email/usluga/napomena — ovo je Faza 0 STAFF-facing desktop app gdje Ljubo/Zorka/Ana direktno unose termin, različito od javne web forme o kojoj se pričalo u drugom kontekstu), prevlačenje mišem, dugme za štampu. Jedino ograničenje: sve nad fake/in-memory dataclass podacima, ne pravim modelima. Claim (`desktop/`, `tests/test_gui/`) je ispravan i dovoljan — nije nagovještavao prazan skelet, nego samo da GUI ne dira DB sloj.

**2. Zavisnost od DENT-001 — zaključak je tačan, nastavi tako.** Ne uvoziti `src/dentaland` ni dirati `pyproject.toml` (oba su eksplicitno u `forbidden_paths`). Definisati privremeni fake podatkovni sloj (plain `@dataclass`) unutar `desktop/` (npr. `desktop/fake_data.py` ili slično, po tvom nahođenju gdje unutar `desktop/**`). PySide6 zavisnost u `pyproject.toml` dodaje Claude kao dio DENT-001 (schema zadatak) — ne treba da čekaš niti da to sam diraš. Kad DENT-001 bude mergovan, GUI se накнadno žica na prave modele kroz servisni sloj (poseban budući zadatak), ne kroz DENT-002.

## Napomena o procesu

Ovaj fajl je napisan NAKNADNO u odnosu na trenutak kad je claim registrovan (proces greška — Task Contract je trebalo postojati kao fajl od početka, ne samo kao poruka u razgovoru koja se nije prenijela). Sadržaj YAML bloka iznad je identičan onome što je usmeno dogovoreno prije dodjele zadatka — ništa nije izmišljeno retroaktivno da opravda već napisan kod, jer kod još nije pisan (potvrđeno: implementer je stao i tražio kontrakt prije prve linije).
