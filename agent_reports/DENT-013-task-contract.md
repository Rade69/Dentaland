---
id: DENT-013
title: Obavještenje o obradi ličnih podataka
risk: LOW
objective: Dodati zasebnu, responzivnu privacy stranicu u Dentaland stilu i povezati je sa javnom formom bez netačnih tvrdnji o obradi.
allowed_paths:
  - web/index.html
  - web/style.css
  - web/privacy.html
  - web/tests/privacy.html
  - agent_reports/DENT-013-task-contract.md
  - agent_reports/2026-08-17-DENT-013-privacy-page.md
forbidden_paths:
  - backend/
  - src/
  - migrations/
acceptance:
  - Link iz kartice "Vaši podaci" otvara privacy.html u novom tabu.
  - Kartica ne tvrdi da se podaci nikada ne dijele sa trećim stranama.
  - Checkbox potvrđuje upoznavanje sa obavještenjem i nije predstavljen kao univerzalna saglasnost.
  - Privacy stranica koristi postojeći header, footer, boje, logo i mobilni stil.
  - Tekst opisuje stvarna polja javne forme i ne izmišlja produkcijske obrađivače.
verification:
  - Statička provjera HTML linkova i obaveznih sekcija.
  - Browser smoke test desktop i mobilnog prikaza.
---
