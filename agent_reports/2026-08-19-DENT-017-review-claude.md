# Review — DENT-017 (email podsjetnik)

Reviewer: claude | Implementer: pi | Datum: 2026-08-19

Nezavisan review — rekonstruisano od nule (kod pročitan direktno, ne samo
Pi-jev izvještaj), sa stvarnim ponovnim pokretanjem verifikacije.

```yaml
verdict: PASS
scope: PASS
acceptance: PASS
architecture: PASS
security: PASS
blocking_findings: []
```

## Šta je provjereno nezavisno

- **Diff**: `src/dentaland/services/notifications.py` (+31),
  `tests/test_notifications.py` (+54). Nijedan `forbidden_path` diran
  (potvrđeno `git status`, ne samo Pi-jeva tvrdnja).
- **Implementacija**: `send_appointment_reminder` prati identičan obrazac
  kao postojeći `send_appointment_confirmed` (`_dispatch`, best-effort,
  `try/except` sa `logger.warning`, nikad ne baca) — konzistentno sa
  ostatkom modula, nije novi paralelan pattern.
- **Minimizacija podataka (ključni acceptance kriterij)**: NE vjerujem
  komentaru u kodu — provjerio sam test
  `test_poruka_podsjetnik_sadrzi_tacno_vrijeme_ali_ne_uslugu_ni_doktora`
  direktno. Test stvarno provjerava odsustvo zabranjenih riječi
  (`kontrola`, `ljubo`, `zorka`, `usluga`, `doktor`) u renderovanom tijelu
  poruke, ne samo da funkcija ne baca. Ovo je konkretan dokaz, ne
  pretpostavka.
- **Timezone**: test provjerava UTC 09:00 → `20.08.2026.` `11:00`
  (Europe/Sarajevo ljetno, +2h DST) — tačno.
- **Verifikacija, ponovo pokrenuto nezavisno** (ne prepisano iz Pi-jevog
  izvještaja):
  ```
  pytest tests/test_notifications.py -q → 14 passed
  ruff check src/dentaland tests        → All checks passed!
  mypy src/dentaland                    → Success: no issues found in 8 source files
  ```
  Slaže se sa Pi-jevim navodom (14 passed, ruff/mypy čisto).

## Odbačena hipoteza (pokušaj obaranja)

Pokušao sam pronaći put kojim bi `send_appointment_reminder` mogao procuriti
uslugu/doktora — provjerio da li funkcija ima pristup tim poljima uopšte.
Potpisi (`to_email: str, start_time: datetime`) strukturno ne primaju ta
polja, pa ih ni greškom ne mogu proslijediti dalje — nije samo disciplina
autora, nego tip-nivo garancija. Nisam našao slabost.

## Napomena van scope-a review-a (validacija `.agent/` sloja)

Pi-jev nalaz da `.agent/PROJECT_MAP.md`/`TASK_ROUTING.md` NE postoje u
`main` je potvrđen nezavisno (`git show main:.agent/PROJECT_MAP.md` →
"does not exist"). Ovo nije defekt DENT-017 rada — Pi je i pored toga
ispravno našao "Notifications" sekciju i implementirao tačno traženo. Vidi
`.agent/TASK_ROUTING.md` validacionu tabelu za pun probni signal.

## Integration status

`VERIFIED, ne merge-ovano` — čeka human approval (Radovan) prije merge-a,
po standardnom procesu (LOW risk, jedan reviewer dovoljan).
