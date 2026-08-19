# Agentski razvojni plan — Dentaland zakazivanje

**Svrha ovog dokumenta:** kanonski, detaljan opis kako se zadaci dijele na
AI agente koji pišu kod, i kako se taj kod kontroliše prije nego uđe u
glavnu granu. Ne mijenja arhitekturu ni faze (vidi
`dentaland-razvojni-plan-v3.1.md` za to) — samo definiše proces rada.

**Odnos sa `CLAUDE.md`:** `CLAUDE.md` u korijenu projekta je thin router —
projektne premise (šta je Dentaland, arhitektura, sigurnost) i navigacija
ka ovom dokumentu za pun proces. Ako se procesni sadržaj ovdje i u
`CLAUDE.md` ikad razmimoiđe, to je greška koju treba popraviti (jedan
izvor istine), ne signal da jedan od njih "pobjeđuje" — provjeri git
istoriju da vidiš koja verzija je novija prije nego pretpostaviš.

---

## Osnovni princip

**Agent koji piše kod nikad ne pregleda sopstveni rad.** Pregled uvijek
radi neko drugi — drugi agent, drugi model, ili čovjek. Ovo nije
formalnost; agent koji je nešto upravo napisao ima sistemsku slijepu tačku
za sopstvene greške. Nezavisan par očiju to hvata. Primjenjuje se bez
izuzetka, čak i za LOW zadatke (samo je tok laganiji, ne izostavljen).

**Automatska (execution-based) provjera ide prije bilo kakvog pregleda, ne
poslije.** Testovi, provjera šeme, linter — objektivni su i ne mogu se
"ubijediti". LLM pregled dolazi tek pošto to prođe, kao dodatni sloj za
ono što testovi ne hvataju (čitljivost, arhitektura, kršenje pravila iz
ovog dokumenta) — ne kao zamjena za testove.

**Svaki zadatak je mali, izolovan i ima jasan kriterijum "gotovo".**

---

## Risk nivoi — LOW / MEDIUM / HIGH

Zamjenjuje raniji binarni "kritičan da/ne". Početna klasifikacija zadatka
je okvirna — **execution evidence i stvaran tehnički sadržaj imaju
prednost** nad unaprijed dodijeljenom oznakom ako se pokažu neusklađeni
(npr. backup mehanizam je tehnički suptilniji nego što bi "nekritično"
sugerisalo — vidi v3.1 plan).

| Nivo | Primjeri | Tok |
|---|---|---|
| **LOW** | Tekst, labele, vizuelne korekcije, izolovan UI bez logike | `Implementer → verifikacija → 1 reviewer → merge`. Human approval opcion nakon što prvih desetak LOW zadataka prođe bez REJECT-a. |
| **MEDIUM** | Controller izmjene, neosjetljiva servisna logika, `api_client/` sloj, email/reminder workflow, backup mehanizam | `Implementer → verifikacija → 1 reviewer → human approval → merge` |
| **HIGH** | Šema i migracije, `EXCLUDE` constraint, autentifikacija, token generisanje, javni API endpointi, razdvajanje osjetljivih podataka (M1), Viber webhook + signature verifikacija | `Implementer → verifikacija → Reviewer 1 → Reviewer 2 → human approval → merge` |

Task Contract nosi `risk: LOW|MEDIUM|HIGH` polje — operativna oznaka za taj
konkretan zadatak.

---

## Uloge

Ko je Implementer se mijenja sa risk nivoom zadatka — agenti su fiksni po
alatu, ali njihova uloga na datom zadatku zavisi od rizika:

| Risk | Implementer | Reviewer 1 | Reviewer 2 |
|---|---|---|---|
| LOW | Crush / Pi | Claude | — |
| MEDIUM | Crush / Pi | Claude | — |
| HIGH | **Claude** | Crush ili Pi | Pi ili Crush (onaj koji nije Reviewer 1) |

Tabela iznad odražava tabelu uloga u trenutnoj upotrebi — dostupnost
pojedinog agenta (npr. privremena odsutnost, isticanje kredita) je
kratkotrajna informacija koja se mijenja nezavisno od ovog procesnog
dokumenta. **Provjeri `.agent/CURRENT_STATE.md` za trenutni status prije
pretpostavke** — ne pretpostavljati da je gornja tabela nepromijenjena bez
te provjere.

- **Claude implementira HIGH-risk zadatke direktno** — najstabilnija ruka
  na najkritičnijem poslu.
- **Crush i Pi su Implementeri na LOW/MEDIUM.** Na HIGH zadacima, oba
  (Crush i Pi) rade kao nezavisni Reviewer 1/2.
- **Radovan** — zadnja riječ prije merge-a; rješava neslaganje reviewera;
  jedina instanca koja odlučuje poslovna/pravna pitanja.

**Implementer nikad nije isti agent/sesija/kontekst kao Reviewer za taj
isti zadatak.** Kad Claude implementira HIGH zadatak, Reviewer 1/2 moraju
biti nezavisni od te sesije — Claude se ne vraća da "sam sebe" pregleda u
istom kontekstu.

---

## Task Contract

Prije nego implementer dobije zadatak, piše se mali strukturirani ugovor —
isti izvor istine za implementera, verifikaciju i reviewera.

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

Za LOW zadatke, Task Contract ostaje minimalan — `id`, `title`,
`risk: LOW`, `objective`, `allowed_paths`, `acceptance`, `verification`.
Četiri-pet redova je dovoljno. Puna ceremonija ide na MEDIUM/HIGH.

---

## Ownership manifest i koordinacija agenata

Za bilo koji trenutak kad dva zadatka rade paralelno (dva agenta, dva
worktree-a) — koji zadatak smije dirati koje fajlove/tabele mora biti
dogovoreno PRIJE početka rada, ne otkriveno naknadno kroz konflikt. Ovo je
komplementarno git worktree izolaciji (spriječava planning-time koliziju),
ne zamjena za nju.

Automatizovano kroz `scripts/coordination.py` — SQLite registar
(`.coordination/registry.db`, lokalan, gitignored, dijeljen preko svih
worktree-ova istog repoa) koji prati koja putanja je "zauzeta" kojim
zadatkom/agentom iz kojeg worktree-a:

```bash
python scripts/coordination.py claim --task DENT-014 --agent claude --paths backend/services/tokens.py,tests/test_tokens.py
python scripts/coordination.py status
python scripts/coordination.py release --task DENT-014
```

- **Claude Code**: automatski `PreToolUse` hook (`.claude/settings.json`)
  — blokira (exit 2) ako je ciljna putanja aktivan claim iz DRUGOG
  worktree-a.
- **Codex, Crush, Pi**: nemaju ožičen hook — `claim`/`release` disciplina
  je ručna, ne automatska.
- Identitet "vlasnika" claim-a je apsolutna putanja worktree-a
  (`Path.cwd()` u trenutku `claim` poziva), ne agent ime.
- Dok postoji samo jedan aktivan zadatak, alatka nije obavezna, ali se
  preporučuje radi navike.
- `agent_reports/` je dijeljen folder — ne claimuj ga u cjelini, claimuj
  konkretan fajl.

---

## Git izolacija

- Svaki netrivijalan zadatak = svoj git worktree, imenovan po zadatku
  (`task/DENT-014-cancel-token`).
- Sitne izmjene (LOW, jedan fajl) mogu ići u zajedničkom tree-u ako je
  trenutno samo jedan agent aktivan — provjeriti `git status --short
  --branch` prije početka, ne pretpostaviti čist tree.
- Merge u `main` samo poslije koraka: implementacija → verifikacija →
  review(i) → human approval.
- Nikad `git add -A`/`git add .` — uvijek navesti tačne fajlove. Nikad
  force push, nikad `git reset --hard`/`git clean` bez eksplicitnog
  zahtjeva. Nikad commit bez eksplicitnog zahtjeva.

---

## Obavezna procedura prije izmjene

1. **Provjera tree-a** — `git status --short --branch`, `git log -5
   --oneline`. Ne pripisivati sebi tuđe izmjene.
2. **Kontekst i pozivaoci** — pročitati cijeli relevantni modul, pronaći
   pozivaoce, testove, migracije prije izmjene funkcije/klase/API
   rute/modela baze.
3. **Impact analiza** (MEDIUM/HIGH) — koji moduli zavise od koda koji se
   mijenja, koje testove izmjena pogađa, mijenja li se contract/API. Ako
   repo bude indeksiran GitNexus-om, koristiti ga; do tada ručna pretraga
   referenci. Ako impact otkrije veći uticaj nego što je Task Contract
   pretpostavio — **zadatak se ne širi tiho, vraća se na redefinisanje
   obima**.
4. **Task Contract** — definisan prije koda, ne retroaktivno pisan da
   opravda već napisano.
5. **Plan prije izmjene (HIGH)** — kratak plan u `agent_reports/` prije
   editovanja: Cilj / Pogođeno / Plan / Šta NE dirati / Plan verifikacije
   / Rollback / Odbačene opcije.

---

## Reviewer Context Pack

Reviewer ne dobija samo `git diff`. Mora dobiti:

- Task Contract za taj zadatak
- Pun diff + listu dirnutih fajlova
- Relevantne izvode iz `CLAUDE.md` (šta se primjenjuje na taj tip izmjene)
- Rezultat automatske verifikacije (testovi, linter)
- Rezultat impact analize, ako je rađena (MEDIUM/HIGH)

## Strukturiran verdikt

Reviewer odgovor je strukturiran, ne slobodan tekst — dodaje se KAO HEADER
na vrh prozne analize, ne zamjenjuje je:

```yaml
verdict: PASS  # ili PASS_WITH_NOTES, REJECT
scope: PASS
acceptance: PASS
architecture: PASS
security: PASS
blocking_findings: []
```

`REJECT` mora imati tačnu lokaciju i pravilo koje je prekršeno u
`blocking_findings` — implementer dobija konkretnu stavku, ne "popravi
review".

Za samo izvršenje Reviewer uloge (metoda, ne proces) koristiti globalni
skill `independent-review` — čita ovaj format i koristi ga umjesto
generičkog PASS/FAIL, proaktivno se aktivira kad se rad proglasi gotovim.
Za Implementer stranu postoje `prime-bug`/`prime-feature` (minimalan
kontekst + podsjetnik na reprodukciju/obim prije koda), takođe automatski.

---

## Konflikt između reviewera i hijerarhija autoriteta

Ne rješava se glasanjem. Svaki blocking finding provjerava se prema Task
Contractu, kodu i testovima — ako je tvrdnja objektivno testabilna, pravi
se test.

Redoslijed kad se ne slažu (od najjačeg ka najslabijem):

1. Execution evidence (rezultat testa)
2. Task Contract
3. Projektna arhitektura i bezbjednosna pravila (`CLAUDE.md`)
4. `docs/` izvori istine (ovaj dokument, `dentaland-razvojni-plan-v3.1.md`)
5. Reviewer zaključak
6. Implementer tvrdnja
7. **Radovan** — konačna riječ kad gornje ne razriješi neslaganje

Ovo je odvojeno od hijerarhije dokaza ispod (koja govori o JAČINI dokaza)
— ovo govori KO odlučuje kad se dvije strane objektivno ne slažu.

---

## Scope expansion pravilo

Agent ne proširuje zadatak sam jer je usput našao nešto "što bi bilo dobro
popraviti". Prijavljuje kao `OUT_OF_SCOPE_FINDING`:

```yaml
finding: OUT_OF_SCOPE_FINDING
description: <šta je pronađeno>
location: <fajl/funkcija>
risk: LOW|MEDIUM|HIGH
proposed_task: <predlog novog zadatka>
```

i nastavlja originalni zadatak — osim ako nalaz direktno blokira bezbjednu
implementaciju trenutnog zadatka (tada se STAJE i prijavljuje odmah, ne
čeka se kraj zadatka).

---

## Verifikacija i Definition of Done

Execution-based verifikacija (testovi, linter, schema provjera) ide
**prije** bilo kakvog reviewa, ne poslije — objektivna je i ne može se
"ubijediti". LLM review dolazi tek pošto to prođe, kao dodatni sloj za ono
što testovi ne hvataju.

### Hijerarhija dokaza (od najjačeg ka najslabijem)

1. Deterministički test (unit/integration)
2. Reproducibilan benchmark
3. Build/package rezultat
4. Golden file
5. Screenshot/video (GUI ekrani)
6. Ručna QA lista
7. Agentovo objašnjenje (najslabiji mogući dokaz, prihvatljiv samo kad
   ništa jače nije dostupno)

`scripts/verify.py` kao standardna ulazna tačka se kreira kad Faza 0
stvarno počne pisati kod — ne prije.

---

## Post-merge Integration Gate

Dvije nezavisno ispravne izmjene ne moraju raditi ispravno zajedno.
Poslije merge-a: pun test suite na čistom `main`, schema/migration
provjera gdje je relevantna, smoke test.

Status: `MERGED → INTEGRATION_VERIFIED → DONE`, ili `MERGED →
INTEGRATION_FAILED` — potonje dobija **prioritet nad novim zadacima**, ne
čeka red.

---

## Evidence paket / agent_report

Za svaki zadatak, mali dokazni zapis u `agent_reports/`, versionisan
zajedno sa kodom (vidi `agent_reports/README.md` za tačan format).

```text
Task: DENT-014 | Commit: <sha> | Risk: HIGH
Verification: pytest PASS, ruff PASS
Review: Claude PASS, Codex PASS, Human APPROVED
Integration: full pytest PASS, smoke test PASS
```

---

## Šta ne graditi odmah (proces)

Ne pravi se poseban orkestrator samo da bi se proces sproveo. Prvih 5-10
stvarnih Dentaland zadataka ide ručno/poluautomatski sa postojećim
alatima (worktree, Task Contract fajl, test runner, review, prost evidence
zapis). Automatizuje se tek ono što se pokaže repetitivnim i stabilnim.
Cilj je razviti Dentaland, ne izgraditi proizvod za orkestraciju razvoja
Dentalanda.

**Izuzetak (16.8.2026, eksplicitan zahtjev):** koordinacija ownership-a
preko `scripts/coordination.py` je napravljena prije prvog stvarnog
zadatka, ne nakon što se pokazala repetitivna potreba — svjesno odstupanje
jer je Radovan eksplicitno tražio rad sa više agenata paralelno od samog
početka. Ostatak pravila i dalje važi za sve OSTALE alatke.

---

## Prije nego počneš kodirati

Napiši kratko (2-4 rečenice) šta si razumio iz zadatka i šta planiraš
uraditi. Čekaj potvrdu ako zadatak nije jednoznačan.

### Facts vs Decisions

Agent ne pita ono što može sam provjeriti u kodu/repou. Agent ne odlučuje
sam poslovno/pravno/UX pitanje samo zato što je usput otkrio tehničku
činjenicu.

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

---

## Istorijski dodatak — ranija podjela zadataka po fazama (napuštena numeracija)

**Status: NEAKTIVNO, samo referenca.** Ova tabela je koristila numeraciju
(0.1, 1.2, M1.1...) koja je u praksi zamijenjena `DENT-XXX` sistemom —
provjereno `grep` kroz `agent_reports/`: nijedan od 48 postojećih zadataka
ne referencira ovu numeraciju. Zadržana ovdje kao istorijski kontekst
prvobitnog planiranja, ne kao operativni izvor. Za trenutno stanje
zadataka vidi `.agent/CURRENT_STATE.md` i `agent_reports/`.

### Faza 0 — lokalna desktop aplikacija
| Zadatak | Kritičan? |
|---|---|
| 0.1 SQLAlchemy modeli + Alembic za šemu | Da |
| 0.2 Servisni sloj — provjera preklapanja, generisanje slobodnih slotova | Da |
| 0.3 Views/controllers — sedmični prikaz, klik-unos, prevlačenje termina | Ne |
| 0.4 Štampa dnevnog/sedmičnog rasporeda | Ne |
| 0.5 Backup mehanizam | Ne (MEDIUM zbog SQLite backup API zahtjeva) |

### Faza 1 — server i javno zakazivanje
| Zadatak | Kritičan? |
|---|---|
| 1.1 FastAPI skelet | Da |
| 1.2 Migracija SQLite → PostgreSQL, `EXCLUDE` constraint | Da |
| 1.3 Javni endpoint — slobodni slotovi + zahtjev za termin | Da |
| 1.4 Token generisanje za cancel link | Da |
| 1.5 Admin autentifikacija | Da |
| 1.6 Rate limiting na javnom API-ju | Da |
| 1.7 Desktop klijent — `api_client/` sloj | Ne (blago sklon MEDIUM-u) |
| 1.8 Javna forma | Ne |
| 1.9 "Zatvori termin" ekran u admin panelu | Ne |
| 1.10 Email potvrde i podsjetnici | Ne |

### Faza 2 — usvajanje i otpornost
| Zadatak | Kritičan? |
|---|---|
| 2.1 Viber bot — webhook + verifikacija potpisa | Da |
| 2.2 Tailscale postavka za mobilni pristup | Ne |
| 2.3 Dnevni email sa rasporedom, uptime monitoring | Ne |
| 2.4 Lista "za zakazati sledeći termin" | Ne |

### M0–M1 — materijal
| Zadatak | Kritičan? |
|---|---|
| M0.1 Katalog materijala i zalihe | Ne |
| M1.1 `material_usage` tabela, poseban `.db` fajl, SQLCipher enkripcija | Da |
| M1.2 Posebna lozinka za taj tab u aplikaciji | Da |
| M1.3 Agregatni izvještaji (bez imena pacijenta) | Da |
