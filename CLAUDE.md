# CLAUDE.md — Dentaland

Ovaj fajl vodi Claude Code i druge agente kroz pravila rada na Dentaland projektu — sistemu zakazivanja za stomatološku ordinaciju.

## Šta je Dentaland

Sistem zakazivanja termina koji se gradi **samo za Ljubu** (suvlasnik ordinacije, prijatelj — ne cijela ordinacija). Ekonomski okvir je neformalan; naplata je moguća tek ako se pokaže vrijednost. Zorka i Ana (ostali doktori) ulaze u priču tek ako sami zatraže, nakon što vide da sistem radi kod Ljube.

Razvoj ide u fazama, svaka sa jasnim kriterijumom uspjeha prije prelaska na sljedeću:

```text
Faza 0 — digitalna sveska (lokalno, PySide6 + SQLite, bez interneta)
→ Faza 1 — javno online zakazivanje (FastAPI + PostgreSQL, VPS, EXCLUDE constraint)
→ Faza 2 — usvajanje i otpornost (Tailscale, Viber bot, monitoring)
→ Faza 3 — samo ako se pokaže potreba (drugi doktori, lista čekanja, multi-tenancy)
```

Model zakazivanja je **zahtjev, ne instant rezervacija** — pacijent šalje zahtjev, osoblje potvrđuje.

## Izvori istine

- [docs/dentaland-razvojni-plan.md](docs/dentaland-razvojni-plan.md) — originalni plan (v1): premise, faze, funkcionalnosti, kontekst razgovora sa Ljubom.
- [docs/dentaland-razvojni-plan-v3.1.md](docs/dentaland-razvojni-plan-v3.1.md) — objedinjen tehnički + privacy/compliance plan (spaja ranije v2 i v3 iteracije). **Za tehničke, sigurnosne i pravne detalje ovaj dokument ima prednost nad v1** kad se razlikuju — v1 ostaje za originalne premise i kontekst. Sadrži tačan `EXCLUDE` constraint pattern, token-storage šemu (hash, ne plaintext), backup/migracija proceduru, RBAC, audit log, i puni privacy/compliance okvir sa nezavisno provjerenim pravnim izvorima.
- [docs/dentaland-agentski-razvoj.md](docs/dentaland-agentski-razvoj.md) — procesni dokument: uloge, risk-tier eskalacija, Task Contract, evidence paket. Ovaj `CLAUDE.md` ga operacionalizuje i proširuje (vidi sekcije ispod) — gdje se razlikuju, `CLAUDE.md` je operativni izvor jer je ažurniji.
- Kod, testovi i migracije su izvor istine za ono što je zaista implementirano. Ne oslanjati se na memoriju ili ranije poruke.

## Jezik

Komunikacija s klijentom (posredno kroz Radovana), projektna dokumentacija i agentski izvještaji pišu se na srpskom/bosanskom, latinicom.

**Strukturni ključevi ostaju na engleskom** — YAML polja u Task Contractu (`risk`, `allowed_paths`, `forbidden_paths`, `acceptance`), strukturirani verdict blok (`verdict: PASS/PASS_WITH_NOTES/REJECT`, `blocking_findings`), risk nivoi (`LOW/MEDIUM/HIGH`), nazivi tabela/kolona, kod, commit poruke. Razlog: ovo su šema/ugovor elementi, ne proza — engleski drži dosljednost sa ogromnim korpusom sličnih CI/review obrazaca na kojem su modeli trenirani, i sprečava da svaka sesija sama izmisli drugačiji prevod istog ključa.

## Klijent i razmjer — ne izgubiti iz vida

Dentaland je mali, neformalan projekat za jednog prijatelja, ne enterprise proizvod. Ovo ima direktne posljedice na odluke:

- Ne graditi generičnost/konfigurabilnost za buduće klijente koji još ne postoje (vidi "Šta se namjerno ne gradi" ispod).
- Rate limiting, backup, monitoring — birati najjednostavnije rješenje proporcionalno obimu (jedan VPS, jedan doktor), ne enterprise-scale default.
- Cijena greške je stvarna (zdravstveno-adjacentni podaci, pravna obaveza), ali cijena over-engineeringa je isto tako stvarna (Ljubo plaća vrijeme, ne apstraktnu robusnost).

## Arhitektura — ne pregovara se bez izmjene plana

```text
Faza 0: PySide6 desktop → SQLite (lokalno, jedan proces, jedan writer)
Faza 1: PySide6 desktop → httpx/QNetworkAccessManager → FastAPI → PostgreSQL (VPS)
        + javna forma (poddomen, statičan HTML/JS ili laka SPA) → isti FastAPI
```

- Šema baze je **namjerno ista forma** u Fazi 0 (SQLite) i Fazi 1 (PostgreSQL) radi lakše migracije — vidi `docs/dentaland-razvojni-plan-v3.1.md` za tačnu definiciju kolona (uključujući `status` enum i `is_manual_override`, definisane OD Faze 0, ne dodate naknadno).
- Poslovna logika (provjera preklapanja, generisanje slobodnih slotova) ide u servisni sloj, nikad direktno u `views/`/`routers/`.
- `desktop/views/` nikad ne uvozi SQLAlchemy direktno — ide kroz `api_client/`/servisni sloj.
- Sve vrijeme je timezone-aware (`zoneinfo`/`timestamptz`), nikad naivni datetime. `working_hours` čuva lokalno vrijeme + IANA zonu (`Europe/Sarajevo`), ne fiksni UTC offset — DST bi inače pomjerio rekurentne termine dva puta godišnje.
- `appointments` i `material_usage` (M1, budući materijal-po-pacijentu modul) **nikad u istom fajlu/bazi**.
- Nasumičan token (`secrets.token_urlsafe(32)`) za javne linkove (cancel link), nikad sekvencijalni ID. U bazi se čuva SHA-256 **hash** tokena, nikad plaintext — curenje baze ne smije davati odmah upotrebljive javne linkove. Server-side poređenje ide kroz `hmac.compare_digest()`, nikad `==`. Token ima `expires_at` i jednokratnu semantiku (invalidira se nakon upotrebe).
- `EXCLUDE USING gist (doctor_id WITH =, tstzrange(start_time, end_time, '[)') WITH &&) WHERE (status IN ('PENDING', 'SCHEDULED'))` — fizička zabrana preklapanja termina na nivou baze. Blokiraju SAMO statusi koji predstavljaju aktivnu rezervaciju — `REJECTED`/`CANCELLED`/`COMPLETED`/`NO_SHOW` ne smiju trajno zauzimati slot. Vidi v3.1 plan za potpuni pattern i razjašnjenje emergency-override slučaja (zaobilazi FORM validaciju, nikad fizičku nemogućnost dva termina istovremeno).

## Šta se namjerno ne gradi unaprijed

- Plugin sistem/arhitektura za proširenje — nema drugog klijenta na osnovu kojeg bi se dizajnirale tačke proširenja.
- Twilio SMS — preskup za obim jedne ordinacije; Viber (Faza 2) je jeftinija alternativa u BiH.
- Instant rezervacija (Model B) — oduzima kontrolu osoblju prerano.
- Javni server na Ljubinom ličnom računaru — poništava sigurnosnu prednost desktop pristupa.
- Rad za sva tri doktora odjednom — najveći rizik neuspjeha cijelog projekta.
- Multi-tenancy — tek kad postoji drugi stvarni klijent, na osnovu stvarne razlike, ne unaprijed nagađane.
- Redis/message broker/mikroservisi — jedan VPS, jedna instanca aplikacije pokriva obim; `slowapi` in-memory rate limiting je dovoljan, ne treba distribuiran backend.
- `project_rooms/` folder — kreira se tek kad prva HIGH-risk izmjena stvarno zatreba plan fajl van agent_reporta, ne unaprijed.

## Risk nivoi — LOW / MEDIUM / HIGH

Zamjenjuje binarno "kritičan da/ne" preciznijom eskalacijom. Početna klasifikacija zadatka je u `dentaland-agentski-razvoj.md` tabelama po fazama — ali **execution evidence i stvaran tehnički sadržaj imaju prednost nad unaprijed dodijeljenom oznakom** ako se pokažu neusklađeni (npr. backup mehanizam je tehnički suptilniji nego što "Ne" oznaka sugeriše — vidi v3.1 plan).

| Nivo | Primjeri | Tok |
|---|---|---|
| **LOW** | Tekst, labele, vizuelne korekcije, izolovan UI bez logike | `Implementer → verifikacija → 1 reviewer → merge`. Human approval opcion nakon što prvih desetak LOW zadataka prođe bez REJECT-a. |
| **MEDIUM** | Controller izmjene, neosjetljiva servisna logika, `api_client/` sloj, email/reminder workflow, backup mehanizam | `Implementer → verifikacija → 1 reviewer → human approval → merge` |
| **HIGH** | Šema i migracije, `EXCLUDE` constraint, autentifikacija, token generisanje, javni API endpointi, razdvajanje osjetljivih podataka (M1), Viber webhook + signature verifikacija | `Implementer → verifikacija → Reviewer 1 → Reviewer 2 → human approval → merge` |

Task Contract (ispod) nosi `risk: LOW|MEDIUM|HIGH` polje — to je operativna oznaka za taj zadatak, ne tabela iz procesnog dokumenta.

## Uloge

Ko je Implementer se mijenja sa risk nivoom zadatka — agenti su fiksni po alatu, ali njihova uloga na datom zadatku (Implementer ili Reviewer) zavisi od toga koliko je zadatak rizičan:

| Risk | Implementer | Reviewer 1 | Reviewer 2 |
|---|---|---|---|
| LOW | Crush / Pi (ili Codex kao worker) | Claude | — |
| MEDIUM | Crush / Pi (ili Codex kao worker) | Claude | Codex — opciono, kad treba dodatna relevantnost pregleda, ne obavezno |
| HIGH | **Claude** | Codex | Crush / Pi |

- **Claude implementira HIGH-risk zadatke direktno** (šema/migracije, `EXCLUDE` constraint, autentifikacija, token generisanje, javni API endpointi, razdvajanje osjetljivih podataka) — najstabilnija ruka na najkritičnijem poslu, na eksplicitan zahtjev (16.8.2026).
- **Codex nikad nije Implementer, isključivo Reviewer** — na HIGH je obavezan (Reviewer 1), na MEDIUM dostupan po potrebi radi relevantnijeg pregleda, nije čvrsto vezan samo za HIGH.
- **Crush i Pi su Implementeri na LOW/MEDIUM** (worker agenti), i **Reviewer na HIGH** kad Claude implementira (obično jedan od njih, ne oba na svakom HIGH zadatku — dovoljan je jedan uz Codexa, drugi je slobodan za paralelan LOW/MEDIUM rad).
- **Radovan** (čovjek) — zadnja riječ prije merge-a; rješava neslaganje reviewera; jedina instanca koja odlučuje poslovna/pravna pitanja (npr. emergency-override tumačenje, tekst pristanka).

**Implementer nikad nije isti agent/sesija/kontekst kao Reviewer za taj isti zadatak.** Agent koji je nešto upravo napisao ima sistemsku slijepu tačku za sopstvene greške — nezavisan par očiju to hvata. Ovo se primjenjuje bez izuzetka, čak i za LOW zadatke (samo je tok laganiji, ne izostavljen). Kad Claude implementira HIGH zadatak, Reviewer 1/2 (Codex/Crush) moraju biti nezavisni od te sesije — Claude se ne vraća da "sam sebe" pregleda u istom kontekstu.

## Task Contract

Prije nego implementer dobije zadatak, piše se mali strukturirani ugovor — isti izvor istine za implementera, verifikaciju i reviewera.

```yaml
id: DENT-014
title: Cancel token generation
risk: HIGH
objective: Implementirati generisanje sigurnog tokena za javni cancel link.
allowed_paths: [backend/services/tokens.py, tests/test_tokens.py]
forbidden_paths: [backend/models/, migrations/]
acceptance:
  - token koristi secrets.token_urlsafe(32)
  - token nije izveden iz appointment ID-a
  - poređenje ide kroz hmac.compare_digest, ne ==
verification: [pytest tests/test_tokens.py, ruff check backend/services/tokens.py]
review:
  reviewers: 2
  required: [security, architecture, scope]
```

Za LOW zadatke, Task Contract ostaje minimalan — `id`, `title`, `risk: LOW`, `objective`, `allowed_paths`, `acceptance`, `verification`. Četiri-pet redova je dovoljno. Puna ceremonija ide na MEDIUM/HIGH.

## Ownership manifest i koordinacija agenata (Claude/Codex/Crush)

Za bilo koji trenutak kad dva zadatka rade paralelno (dva agenta, dva worktree-a) — koji zadatak smije dirati koje fajlove/tabele mora biti dogovoreno PRIJE početka rada, ne otkriveno naknadno kroz konflikt. Ovo je komplementarno git worktree izolaciji (spriječava planning-time koliziju), ne zamjena za nju.

Automatizovano kroz `scripts/coordination.py` — SQLite registar (`.coordination/registry.db`, lokalan, gitignored, dijeljen preko svih worktree-ova istog repoa preko `git rev-parse --git-common-dir`) koji prati koja putanja je "zauzeta" kojim zadatkom/agentom iz kojeg worktree-a:

```bash
python scripts/coordination.py claim --task DENT-014 --agent claude --paths backend/services/tokens.py,tests/test_tokens.py
python scripts/coordination.py status
python scripts/coordination.py release --task DENT-014
```

- **Claude Code**: ožičeno automatski kao `PreToolUse` hook (`.claude/settings.json`, matcher `Edit|Write`) — poziva `coordination.py hook-check` prije svakog Edit/Write; blokira (exit 2) ako je ciljna putanja aktivan claim iz DRUGOG worktree-a, propušta sopstvene izmjene i nezauzete putanje bez ikakve dodatne akcije. Ako se `.claude/` folder tek kreirao u trenutnoj sesiji, watcher ga možda ne prati odmah — otvoriti `/hooks` jednom ili restartovati sesiju da se pokupi.
- **Codex i Crush**: nemaju ovdje ožičen hook (nisu konfigurisani iz ove sesije) — pozivati `claim`/`release` ručno na početku/kraju zadatka, i po potrebi `check --path <fajl>` prije veće izmjene. Ako ti alati podržavaju svoj pre-edit hook mehanizam, isti `coordination.py hook-check`/`check` poziv se može ožičiti tamo na isti način.
- Identitet "vlasnika" claim-a je apsolutna putanja worktree-a (`Path.cwd()` u trenutku `claim` poziva), ne agent ime ni env varijabla — nema ručnog praćenja "ko sam ja".
- Dok postoji samo jedan aktivan zadatak, alatka se i dalje može koristiti, ali nije obavezna — konflikt je nemoguć sa jednim aktivnim zadatkom.

## Git izolacija

- Svaki netrivijalan zadatak = svoj git worktree, imenovan po zadatku (`task/DENT-014-cancel-token`).
- Sitne izmjene (LOW, jedan fajl) mogu ići u zajedničkom tree-u ako je trenutno samo jedan agent aktivan — provjeriti `git status --short --branch` prije početka, ne pretpostaviti čist tree.
- Merge u `main` samo poslije koraka: implementacija → verifikacija → review(i) → human approval.
- Nikad `git add -A`/`git add .` — uvijek navesti tačne fajlove. Nikad force push, nikad `git reset --hard`/`git clean` bez eksplicitnog zahtjeva. Nikad commit bez eksplicitnog zahtjeva.

## Obavezna procedura prije izmjene

1. **Provjera tree-a** — `git status --short --branch`, `git log -5 --oneline`. Ne pripisivati sebi tuđe izmjene.
2. **Kontekst i pozivaoci** — pročitati cijeli relevantni modul, pronaći pozivaoce, testove, migracije prije izmjene funkcije/klase/API rute/modela baze.
3. **Impact analiza** (MEDIUM/HIGH) — koji moduli zavise od koda koji se mijenja, koje testove izmjena pogađa, mijenja li se contract/API. Ako repo bude indeksiran GitNexus-om, koristiti ga za analizu zavisnosti na nivou simbola; do tada ručna pretraga referenci. Ako impact otkrije veći uticaj nego što je Task Contract pretpostavio — **zadatak se ne širi tiho, vraća se na redefinisanje obima**.
4. **Task Contract** — definisan prije koda, ne retroaktivno pisan da opravda već napisano.
5. **Plan prije izmjene (HIGH)** — kratak plan u `agent_reports/` prije editovanja: Cilj / Pogođeno / Plan / Šta NE dirati / Plan verifikacije / Rollback / Odbačene opcije.

## Reviewer Context Pack

Reviewer ne dobija samo `git diff`. Mora dobiti:

- Task Contract za taj zadatak
- Pun diff + listu dirnutih fajlova
- Relevantne izvode iz ovog `CLAUDE.md` (šta se primjenjuje na taj tip izmjene)
- Rezultat automatske verifikacije (testovi, linter)
- Rezultat impact analize, ako je rađena (MEDIUM/HIGH)

## Strukturiran verdikt

Reviewer odgovor je strukturiran, ne slobodan tekst — dodaje se KAO HEADER na vrh prozne analize, ne zamjenjuje je:

```yaml
verdict: PASS  # ili PASS_WITH_NOTES, REJECT
scope: PASS
acceptance: PASS
architecture: PASS
security: PASS
blocking_findings: []
```

`REJECT` mora imati tačnu lokaciju i pravilo koje je prekršeno u `blocking_findings` — implementer dobija konkretnu stavku, ne "popravi review".

## Konflikt između reviewera i hijerarhija autoriteta

Ne rješava se glasanjem. Svaki blocking finding provjerava se prema Task Contractu, kodu i testovima — ako je tvrdnja objektivno testabilna, pravi se test.

Redoslijed kad se ne slažu (od najjačeg ka najslabijem):

1. Execution evidence (rezultat testa)
2. Task Contract
3. Projektna arhitektura i bezbjednosna pravila (ovaj fajl)
4. `docs/` izvori istine
5. Reviewer zaključak
6. Implementer tvrdnja
7. **Radovan** — konačna riječ kad gornje ne razriješi neslaganje

Ovo je odvojeno od hijerarhije dokaza ispod (koja govori o JAČINI dokaza) — ovo govori KO odlučuje kad se dvije strane objektivno ne slažu.

## Scope expansion pravilo

Agent ne proširuje zadatak sam jer je usput našao nešto "što bi bilo dobro popraviti". Prijavljuje kao `OUT_OF_SCOPE_FINDING`:

```yaml
finding: OUT_OF_SCOPE_FINDING
description: <šta je pronađeno>
location: <fajl/funkcija>
risk: LOW|MEDIUM|HIGH
proposed_task: <predlog novog zadatka>
```

i nastavlja originalni zadatak — osim ako nalaz direktno blokira bezbjednu implementaciju trenutnog zadatka (tada se STAJE i prijavljuje odmah, ne čeka se kraj zadatka).

## Sigurnost i privatnost

- `appointments` i `material_usage` (M1) nikad u istom fajlu/bazi; M1 dodatno ide kroz `sqlcipher3` enkripciju sa posebnom lozinkom za taj tab u aplikaciji.
- Token generisanje: `secrets.token_urlsafe(32)`, nikad izvedeno iz appointment ID-a ili drugog predvidljivog izvora. Poređenje: `hmac.compare_digest()`.
- SMS/email/Viber podsjetnici nikad ne sadrže naziv usluge, samo vrijeme termina (minimizacija — potvrđeno kao usklađeno sa "minimum necessary" principom).
- Automatsko anonimiziranje ličnih podataka (ime/email/telefon) nakon dogovorenog perioda (12 mjeseci) — datum/usluga ostaju za statistiku.
- Usklađenost sa Zakonom o zaštiti ličnih podataka BiH (Sl. glasnik BiH 12/25, na snazi od 4.10.2025, GDPR-usklađen) — vidi `docs/dentaland-razvojni-plan-v3.1.md` za pun privacy/compliance okvir. Ukratko: formalni DPO vjerovatno nije obavezan (dokumentovana procjena, ne pretpostavka), DPIA vjerovatno nije obavezna za trenutni obim (nezavisno provjereno protiv Sl. glasnika BiH 70/25 — booking sistem bez profiliranja ne triggeruje nijednu od 11 nabrojanih kategorija), ALI evidencija aktivnosti obrade JEST obavezna (booking je kontinuirana, ne povremena obrada — izuzetak za <250 zaposlenih ne važi ovdje), i 72h rok prijave povrede podataka JE obavezan za sve, bez obzira na veličinu.
- Backup baze ide kroz `sqlite3.Connection.backup()` API, nikad sirovo kopiranje `.db` fajla dok je aplikacija otvorena — rizik korupcije (WAL nekonzistentnost).
- Rate limiting na svakom javnom API endpointu.
- Dnevni `pg_dump` backup (Faza 1+) + **testiran** restore, ne samo napravljen.
- Migracija SQLite→PostgreSQL prvo na kopiji podataka (test instanca), provjera integriteta, tek onda produkcija uz backup neposredno prije.
- Nikad ne commitovati tajne, `.env` fajlove sa stvarnim vrijednostima, stvarne pacijentske podatke, lokalne baze.
- Ne tvrditi sigurnost koju sistem nema — konkretne činjenice i rezultati testova, ne uvjeravanje.

## Verifikacija i Definition of Done

Execution-based verifikacija (testovi, linter, schema provjera) ide **prije** bilo kakvog reviewa, ne poslije — objektivna je i ne može se "ubijediti". LLM review dolazi tek pošto to prođe, kao dodatni sloj za ono što testovi ne hvataju (arhitektura, čitljivost, prekršeno pravilo iz ovog fajla).

### Hijerarhija dokaza (od najjačeg ka najslabijem)

1. Deterministički test (unit/integration)
2. Reproducibilan benchmark
3. Build/package rezultat
4. Golden file
5. Screenshot/video (GUI ekrani)
6. Ručna QA lista
7. Agentovo objašnjenje (najslabiji mogući dokaz, prihvatljiv samo kad ništa jače nije dostupno)

`scripts/verify.py` kao standardna ulazna tačka se kreira kad Faza 0 stvarno počne pisati kod — ne prije, da se izbjegne prazna arhitektura bez ičega za provjeriti.

## Post-merge Integration Gate

Dvije nezavisno ispravne izmjene ne moraju raditi ispravno zajedno. Poslije merge-a: pun test suite na čistom `main`, schema/migration provjera gdje je relevantna, smoke test.

Status: `MERGED → INTEGRATION_VERIFIED → DONE`, ili `MERGED → INTEGRATION_FAILED` — potonje dobija **prioritet nad novim zadacima**, ne čeka red.

## Evidence paket / agent_report

Za svaki zadatak, mali dokazni zapis u `agent_reports/`, versionisan zajedno sa kodom (vidi `agent_reports/README.md` za tačan format).

```text
Task: DENT-014 | Commit: <sha> | Risk: HIGH
Verification: pytest PASS, ruff PASS
Review: Claude PASS, Codex PASS, Human APPROVED
Integration: full pytest PASS, smoke test PASS
```

## Šta ne graditi odmah (proces)

Ne pravi se poseban orkestrator samo da bi se proces sproveo. Prvih 5-10 stvarnih Dentaland zadataka ide ručno/poluautomatski sa postojećim alatima (worktree, Task Contract fajl, test runner, Claude/Codex review, prost evidence zapis). Automatizuje se tek ono što se pokaže repetitivnim i stabilnim. Cilj je razviti Dentaland, ne izgraditi proizvod za orkestraciju razvoja Dentalanda.

**Izuzetak (16.8.2026, eksplicitan zahtjev):** koordinacija ownership-a preko `scripts/coordination.py` (vidi "Ownership manifest i koordinacija agenata" iznad) je napravljena prije prvog stvarnog zadatka, ne nakon što se pokazala repetitivna potreba — svjesno odstupanje od pravila iznad jer je Radovan eksplicitno tražio rad sa tri agenta (Claude/Codex/Crush) paralelno od samog početka. Ostatak pravila i dalje važi za sve OSTALE alatke — ne graditi dodatnu automatizaciju procesa dok se potreba stvarno ne pokaže kroz ponovljene probleme.

## Prije nego počneš kodirati

Napiši kratko (2-4 rečenice) šta si razumio iz zadatka i šta planiraš uraditi. Čekaj potvrdu ako zadatak nije jednoznačan.

### Facts vs Decisions

Agent ne pita ono što može sam provjeriti u kodu/repou. Agent ne odlučuje sam poslovno/pravno/UX pitanje samo zato što je usput otkrio tehničku činjenicu.

```markdown
## Fact found
<<< tehnička činjenica sa referencom >>
## Decision required
<<< konkretno pitanje koje samo Radovan/Ljubo može odlučiti >>
## Recommendation
<<< predloženi odgovor i zašto >>
## Consequence
<<< šta se dešava suprotnim putem >>
```

## Otvorena pitanja (trenutno stanje)

Vidi kraj `docs/dentaland-razvojni-plan-v3.1.md` sekcije "Šta i dalje ostaje otvoreno" — trenutno: tačan pravni osnov po svrsi obrade, rokovi čuvanja medicinske dokumentacije (propisi RS, ne izmišljati), kontrolor/obrađivač ugovor, izbor hosting/cloud procesora, da li `service_id` mora ostati uz identitet pacijenta u bazi. Nijedan HIGH-risk zadatak vezan za `EXCLUDE` constraint, token, RBAC ili formu pristanka ne počinje dok se ovo ne razriješi.
