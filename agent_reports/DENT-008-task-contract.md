---
task_id: DENT-008
risk: MEDIUM
implementer: codex
reviewer: claude
status: READY_FOR_REVIEW
created_at: 2026-08-17
---

# Task Contract — DENT-008

```yaml
id: DENT-008
title: Web forma — desktop trokolonski layout + mobilni sekvencijalni tok
risk: MEDIUM
objective: >
  Uskladiti javnu formu sa odobrenim desktop i mobilnim referencama. Desktop
  prikazuje sva tri panela istovremeno i cijela stranica staje u viewport bez
  skrola, uz čitljive proporcije i bez praznog rastezanja panela. Mobilni
  prikazuje samo aktivni panel i dozvoljava normalan vertikalni skrol.
allowed_paths: [web/index.html, web/styles.css, web/tests/desktop.html, docs/dentaland-javna-forma-spec.md, agent_reports/DENT-008-task-contract.md]
acceptance:
  - Na desktopu su vidljiva sva tri panela u tri jednake kolone.
  - Na desktopu nema vertikalnog ni horizontalnog skrola na 1366x768 i 1920x1080.
  - Paneli imaju prirodnu/ujednačenu kompaktnu visinu bez velikih praznih površina i bez nečitljive tipografije.
  - Ispod panela su traka sa četiri prednosti i puni footer, sve unutar desktop viewporta.
  - Na mobilnom je vidljiv samo aktivni panel i vertikalni skrol je dozvoljen.
  - Login se ne prikazuje ni na jednoj rezoluciji.
verification: [browser smoke web/tests/desktop.html, browser smoke web/tests/flow.html]
```
