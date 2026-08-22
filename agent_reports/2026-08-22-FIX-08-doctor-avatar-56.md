---
task_id: FIX-08
risk: LOW
implementer: codex
reviewers: [independent-codex]
verdict: PASS_WITH_NOTES
commits: []
created_at: 2026-08-22
---

# FIX-08 — avatari doktora 56 px

## Task Contract

Vidi [FIX-08-task-contract.md](FIX-08-task-contract.md).

## Šta je urađeno

Zajednička konstanta `DOCTOR_AVATAR_SIZE` povećana je sa 48 na 56 px.
Ista konstanta i dalje upravlja fiksnom QLabel veličinom i kružnim skaliranjem
pixmapa, pa su sva tri portreta jednako velika i poravnata. Postojeće ime,
brojčana značka, fotografije i DashboardPanels nisu mijenjani.

## Reprodukcija prije izmjene

Precizirani test zahtijeva konstantu i sva tri QLabel/pixmapa tačno 56×56.
Prije izmjene pao je očekivano sa `48 != 56`.

## Verifikacija implementera

- Tačan FIX-08 test → **1 passed** nakon izmjene.
- `pytest tests/test_gui/test_main_window.py -q` → **32 passed**.
- `pytest tests -q -p no:cacheprovider` → **276 passed**, 11 postojećih
  dependency/deprecation upozorenja.
- `ruff check src/dentaland desktop backend tests` → **All checks passed**.
- `mypy src/dentaland desktop backend` → **Success: no issues found in 35
  source files**.
- Qt smoke render na 1536×760 →
  `C:/Users/38765/Desktop/Dentaland/output/fix08-doctor-avatar-56.png`.

## Review

```yaml
verdict: PASS_WITH_NOTES
scope: PASS
acceptance: PASS
architecture: PASS
security: PASS
blocking_findings: []
```

Nezavisni reviewer je realnim `AppointmentService` scenarijem potvrdio sva
tri QLabel-a i pixmapa 56×56, identične vertikalne centre avatar/ime/badge,
horizontalni razmak 9 px i panel 285×225 sa 6 px razmaka prije dashboarda na
1536×760. Adversarni scenario sa 18 termina kroz šest statusa aktivira
scrollbar bez preklapanja, uključujući visinu 720. Store bez aktivnih doktora
i dalje skriva legendu.

Neblokirajuća napomena: postojeći `minimumSizeHint` glavnog prozora traži oko
1516 px širine čak i sa avatarima 48 px; ista vrijednost je izmjerena sa 56
px, pa FIX-08 nije napravio regresiju. Pravi 1280-wide layout je zaseban,
postojeći problem van scope-a.

## Integration status

Implementirano u zasebnom worktree-u i branchu
`task/FIX-08-doctor-avatar-56`; nije commitovano niti merge-ovano i čeka
human approval.

## Odbačene opcije

- 60/64 px — odbačeno zbog većeg vertikalnog pritiska na operativne panele.
- Promjena širine sidebara — nepotrebna za 56 px i van odobrenog scope-a.

## OUT_OF_SCOPE_FINDING

Postojeći minimum širine glavnog prozora oko 1516 px nije uzrokovan FIX-08.
