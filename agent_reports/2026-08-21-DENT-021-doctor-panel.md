---
task_id: DENT-021
risk: LOW
implementer: codex
reviewers: [independent-codex]
verdict: PASS_WITH_NOTES
commits: []
created_at: 2026-08-21
---

# DENT-021 — panel doktora sa fotografijama

## Task Contract

Vidi [DENT-021-task-contract.md](DENT-021-task-contract.md).

## Šta je urađeno

- Jednoredna legenda doktora zamijenjena je karticom `Doktori` u desnoj
  koloni rasporeda.
- Panel prikazuje Dr Ljubu, Dr Zorku i Dr Anu u zasebnim redovima sa kružnim
  lokalnim fotografijama i indikatorima postojećih boja doktora.
- Dodani su lokalni resursi `desktop/assets/doctors/{ljubo,zorka,ana}.png`;
  aplikacija ne zavisi od interneta.
- Kada store nema doktore, cijeli panel ostaje sakriven.

## Verifikacija

- `pytest tests/test_gui/test_main_window.py -q -p no:cacheprovider` →
  **24 passed**.
- `pytest tests -q -p no:cacheprovider` → **259 passed**, 11 postojećih
  dependency/deprecation upozorenja.
- `ruff check src/dentaland desktop backend tests` → **All checks passed**.
- `mypy src/dentaland desktop backend` → **Success: no issues found in 35
  source files**.
- Qt offscreen smoke render na 1536×760 → panel staje iznad postojećih
  dashboard panela; snimak je `output/thumbnail/dent021-live-ui.png`.
- Windows `computer-use` nije bio dostupan zbog greške inicijalizacije
  njegovog lokalnog runtime-a; umjesto njega korišten je deterministički Qt
  render istog widget koda.

## Review

```yaml
verdict: PASS_WITH_NOTES
scope: PASS
acceptance: PASS
architecture: PASS
security: PASS
blocking_findings: []
```

Nezavisni reviewer je ponovio targeted i puni test suite, Ruff, mypy i
`git diff --check`; provjerio je tri različita PNG resursa (600×600), kružni
crop (38×38, transparentni uglovi), realni GUI layout 1536×760, tačan
redoslijed imena i edge case bez doktora.

Neblokirajuća napomena: ako se isporučeni PNG ručno ukloni, aplikacija se ne
ruši, ali avatar ostaje prazan. Fallback za oštećene instalacijske resurse je
van obima ovog LOW UI zadatka.

## Integration status

Nije commitovano niti merge-ovano; human approval/commit ostaju sljedeći
korak.

## Odbačene opcije

- Fotografije sa interneta pri svakom pokretanju — odbačeno zbog offline
  desktop rada i nepouzdanosti mreže.
- Velike promotivne kartice iznad rasporeda — odbačeno jer korisnik traži
  kompaktan panel poput `Provider Load` primjera.

## OUT_OF_SCOPE_FINDING

Nema.
