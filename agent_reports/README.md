# agent_reports/ — konvencija

Ovaj folder je prazan na početku projekta — puni se čim prvi zadatak bude urađen.

## Naziv fajla

```text
YYYY-MM-DD-DENT-<broj>-<kratak-slug>.md
```

npr. `2026-08-20-DENT-001-sqlalchemy-schema.md`

## Format (front matter)

```yaml
---
task_id: DENT-001
risk: HIGH
implementer: <agent/model>
reviewers: [claude, codex]  # ili samo [claude] za LOW/MEDIUM
verdict: PASS
commits: [<sha>]
created_at: <ISO 8601 timestamp>
---
```

## Obavezne sekcije u telu

- **Task Contract** (kopiran ili linkovan iz zadatka)
- **Šta je urađeno** — kratko, konkretno
- **Verifikacija** — stvaran rezultat testova/linter-a, ne tvrdnja da su "vjerovatno prošli"
- **Review** — strukturiran verdikt blok (vidi `CLAUDE.md` — Strukturiran verdikt) + prozno obrazloženje
- **Integration status** — `MERGED → INTEGRATION_VERIFIED → DONE` ili `INTEGRATION_FAILED`
- **Odbačene opcije** (ako ih ima) — opcija / zašto razmatrana / zašto odbačena
- **`OUT_OF_SCOPE_FINDING`** zapisi (ako ih ima tokom rada na ovom zadatku)

Vidi `CLAUDE.md` — "Evidence paket / agent_report" za sažet primjer i "Reviewer Context Pack" za šta reviewer treba dobiti prije nego napiše verdikt.

Ne tvrditi da je test prošao ako nije pokrenut. Jasno razlikovati "nije pokrenuto", "nije dostupno" i "palo".
