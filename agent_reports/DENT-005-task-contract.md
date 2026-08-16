---
task_id: DENT-005
risk: MEDIUM
implementer: codex
reviewer: claude
status: REVIEWED (PASS, poslije jednog REJECT ciklusa) — vidi 2026-08-16-DENT-005-javna-forma-frontend.md
created_at: 2026-08-16
---

# Task Contract — DENT-005

```yaml
id: DENT-005
title: Faza 1 (priprema) — Javna forma zakazivanja, frontend
risk: MEDIUM
objective: >
  Implementirati statičan HTML/CSS/JS frontend za javnu formu zakazivanja
  TAČNO prema docs/dentaland-javna-forma-spec.md — jedini izvor istine za
  ovaj zadatak, ne mokap slike iz chat istorije (spec je precizniji i
  ažurniji od bilo koje ranije slike). Tri koraka (Datum → Vaši podaci →
  Potvrda), bez izbora usluge/doktora, bez polja za napomenu, bez izbora
  tačnog vremena — sve prema spec fajlu, uključujući tačan tekst za
  korak 3 ("ZAHTJEV PRIMLJEN!" / "Datum je rezervisan...", NE jezik
  instant potvrde).

  Ovo je FRONTEND SAMO — nema pravog backend-a jer Faza 1 API još ne
  postoji. Forma pri submit-u NE šalje nikuda stvarno (može simulirati
  uspješan submit lokalno u JS-u, npr. prelazak na korak 3 bez pravog
  network poziva, ili poziv na placeholder/mock endpoint koji očigledno
  ne postoji — po tvom nahođenju, dokumentuj izbor). Ovo NIJE zadatak za
  server, bazu, token generisanje niti bilo šta HIGH-risk — to ide kroz
  Claude kao poseban budući zadatak.

  Radi u novom `web/` folderu u korijenu repoa (ne desktop/, ne
  src/dentaland/ — potpuno odvojena vertikala od Faza 0 desktop app-a).
allowed_paths: [web/**, agent_reports/DENT-005-task-contract.md]
forbidden_paths: [desktop/**, src/dentaland/**, migrations/**, CLAUDE.md, AGENTS.md, docs/**, pyproject.toml]
acceptance:
  - Tri koraka tačno: Datum → Vaši podaci → Potvrda (provjeri checklist na kraju docs/dentaland-javna-forma-spec.md — svaka stavka mora biti ispunjena).
  - Korak 1: mjesečni kalendar, samo izbor datuma, info okvir sa tekstom o naknadnoj potvrdi vremena, prošli datumi i neradni dani onemogućeni.
  - Korak 2: Ime i prezime* / Telefon* (sa +387 pozivnim brojem) / Email (opcionalno) — BEZ polja za napomenu. Kvačica pristanka obavezna (nije pre-čekirana), link na "Obavještenje o obradi ličnih podataka" (može biti placeholder link/anchor ako stranica još ne postoji, ali link element mora postojati). Dugme "Nastavi" neaktivno dok ime/telefon/kvačica nisu popunjeni.
  - Korak 3: naslov "ZAHTJEV PRIMLJEN!", podnaslov "Datum je rezervisan, javićemo vam se dan ranije sa tačnim vremenom." — TAČNO ovaj tekst, ne parafraza koja implicira potvrđeno vrijeme.
  - Header bez punog sajt-menija (fokusirana stranica, ne dio šire navigacije).
  - Brend boja `#3fbbc0` teal, bijela pozadina.
  - Responzivan dizajn (funkcioniše na mobilnom i desktop širinama — ordinacija ima realne pacijente koji zakazuju sa telefona).
  - Nigdje na stranici tekst ne implicira potvrđeno vrijeme termina prije nego što ga osoblje stvarno potvrdi.
verification:
  - Ručna QA lista — svaka stavka iz "Provjera prije nego se mokap smatra gotovim" u docs/dentaland-javna-forma-spec.md, sa screenshot-ima ili jasnim opisom rezultata za svaku.
  - Otvoriti stranicu u browseru, proći kompletan tok (Datum → Vaši podaci → Potvrda), potvrditi da submit ne baca grešku u konzoli.
review:
  reviewers: 1
  required: [architecture, scope]
```

## Napomena o procesu

Ovo je prvi zadatak gdje je Codex Implementer, ne Reviewer — dozvoljeno 16.8.2026 (vidi CLAUDE.md "Uloge") na osnovu ponovljenog iskustva da Codex dobro radi frontend/GUI posao. Isto pravilo i dalje važi: Implementer nikad nije isti agent/sesija/kontekst kao Reviewer za taj zadatak — ako Codex kasnije dobije zadatak reviewa NEČEG DRUGOG, to je u redu, ali ne smije reviewati sopstveni DENT-005 diff.

`docs/dentaland-javna-forma-spec.md` je jedini izvor istine za sadržaj/tekst/tok — ne prethodni mokapi iz chat istorije, ni prva verzija koju je Codex ranije napravio (ta je imala pogrešan jezik "instant rezervacije" koji je ispravljen u spec fajlu).
