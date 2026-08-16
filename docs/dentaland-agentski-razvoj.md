# Agentski razvojni plan — Dentaland zakazivanje

**Svrha ovog dokumenta:** kako se zadaci iz `dentaland-razvojni-plan.md` dijele na AI agente koji pišu kod, i kako se taj kod kontroliše prije nego uđe u glavnu granu. Ne mijenja arhitekturu ni faze — samo definiše proces rada.

**Napomena (vidi `CLAUDE.md`):** ovaj dokument je originalna verzija procesnog plana. `CLAUDE.md` u korijenu projekta ga operacionalizuje i proširuje (risk-tier eskalacija, Task Contract sa `allowed_paths`/`forbidden_paths`, strukturiran verdikt, Reviewer Context Pack, ownership manifest, Post-merge Integration Gate, `OUT_OF_SCOPE_FINDING`, hijerarhija autoriteta) — gdje se razlikuju, `CLAUDE.md` je operativni izvor.

---

## Osnovni princip

**Agent koji piše kod nikad ne pregleda sopstveni rad.** Pregled uvijek radi neko drugi — drugi agent, drugi model, ili čovjek. Ovo nije formalnost; agent koji je nešto upravo napisao ima sistemsku slijepu tačku za sopstvene greške, isto kao i čovjek. Nezavisan par očiju to hvata.

**Automatska (execution-based) provjera ide prije bilo kakvog pregleda, ne poslije.** Testovi, provjera šeme, linter — objektivni su i ne mogu se "ubijediti" da nešto prođe. LLM pregled dolazi tek pošto to prođe, kao dodatni sloj za ono što testovi ne hvataju (čitljivost, uklapanje u arhitekturu, kršenje pravila iz AGENTS.md) — ne kao zamjena za testove.

**Svaki zadatak je mali, izolovan i ima jasan kriterijum "gotovo".** Veliki, nejasno definisani zadaci su nemogući za pouzdan pregled — recenzent ne može reći "ovo je tačno" ako ni sam ne zna šta je zadatak tražio.

---

## Uloge

| Uloga | Ko | Posao |
|---|---|---|
| **Implementer** | Worker agent (jeftiniji model — nastavak postojećeg cost-routing pristupa) | Piše kod i testove za jedan dodijeljeni zadatak, u svom izolovanom git worktree-u |
| **Verifikacija** | Automatski (pytest, linter, schema provjera) | Blokira dalje kretanje zadatka ako ne prođe — prije nego ijedan reviewer i pogleda kod |
| **Reviewer 1** | Claude | Nezavisan pregled diff-a nasuprot kriterijuma zadatka i bezbjednosne liste za tu fazu |
| **Reviewer 2** | Codex | Drugi nezavisan pregled — posebno za zadatke označene kao kritični (vidi ispod) |
| **Finalna kontrola** | Radovan | Zadnja riječ prije merge-a; rješava neslaganje između reviewera 1 i 2 ako se ne slažu |

Implementer nikad nije isti agent kao Reviewer 1 ili 2 za taj zadatak.

---

## Kad treba jedan reviewer, kad dva

Dvostruki nezavisni pregled za svaki sitan zadatak je pretjeran — trošak vremena bez proporcionalne koristi. Podjela po riziku:

**Dva reviewer-a (Claude + Codex), obavezno:**
- Šema baze i migracije
- Bilo šta vezano za `EXCLUDE` constraint, token generisanje, autentifikaciju
- Bilo šta što dodiruje razdvajanje osjetljivih podataka (materijal-po-pacijentu, M1)
- Javni API endpointi (Faza 1)

**Jedan reviewer (Claude ili Codex, svejedno koji), dovoljno:**
- UI/prikaz (view sloj), formatiranje štampe
- Sitne izmjene teksta, labela, stilova
- Interni admin ekrani bez osjetljivih podataka

---

## Tok rada po zadatku

1. **Definicija zadatka** — opis, tačan obim, kriterijum prihvatanja, da li je kritičan
2. **Implementer** kreira izolovan git worktree/branch (`task/<naziv>`), piše kod + testove
3. **Automatska verifikacija** — pytest, linter, schema provjera. Ne prolazi — vraća se implementeru, reviewer se ne uključuje
4. **Reviewer(i)** nezavisno pregledaju diff
5. **Odbijeno** — vraća se implementeru sa konkretnim, tačno navedenim razlogom
6. **Prihvaćeno** — Radovan radi finalni pregled, odobrava merge
7. **Merge u main, zadatak zatvoren**

---

## Git izolacija

- Svaki zadatak = svoj git worktree, imenovan po zadatku
- **Ownership manifest** — mala tabela/fajl koji kaže koji zadatak smije dirati koje fajlove/tabele
- Merge u main samo poslije verifikacije i reviewa, nikad direktno

---

## Agent konfiguracija (CLAUDE.md / AGENTS.md)

- **Tanak root fajl** — mapa projekta, osnovna pravila koja važe svuda
- **Poseban fajl po modulu** — pravila specifična za taj dio
- **`# DOC:` komentari** na kritičnim mjestima — podsjećaju agenta *zašto* je nešto urađeno na određen način

---

## Podjela zadataka po fazama

### Faza 0 — lokalna desktop aplikacija
| Zadatak | Kritičan? |
|---|---|
| 0.1 SQLAlchemy modeli + Alembic za šemu (doctors, services, working_hours, time_off, appointments) | Da |
| 0.2 Servisni sloj — provjera preklapanja termina u kodu, generisanje slobodnih slotova | Da |
| 0.3 Views/controllers — sedmični prikaz, klik-unos, prevlačenje termina | Ne |
| 0.4 Štampa dnevnog/sedmičnog rasporeda | Ne |
| 0.5 Backup mehanizam (export `.db` u cloud folder) | Ne — **napomena CLAUDE.md: preporučena MEDIUM zbog SQLite backup API zahtjeva** |

### Faza 1 — server i javno zakazivanje
| Zadatak | Kritičan? |
|---|---|
| 1.1 FastAPI skelet — routers/services/repositories/models/schemas | Da |
| 1.2 Migracija SQLite → PostgreSQL, `EXCLUDE` constraint | Da |
| 1.3 Javni endpoint — slobodni slotovi + zahtjev za termin | Da |
| 1.4 Token generisanje za cancel link | Da |
| 1.5 Admin autentifikacija (heš lozinki) | Da |
| 1.6 Rate limiting na javnom API-ju | Da |
| 1.7 Desktop klijent — `api_client/` sloj | Ne — **napomena CLAUDE.md: blago sklon MEDIUM-u s obzirom na FlowOS iskustvo sa auth-propagacijom u sličnom sloju** |
| 1.8 Javna forma — dvokoračni kalendar (dan → vrijeme) | Ne |
| 1.9 "Zatvori termin" ekran u admin panelu | Ne |
| 1.10 Email potvrde i podsjetnici | Ne |

### Faza 2 — usvajanje i otpornost
| Zadatak | Kritičan? |
|---|---|
| 2.1 Viber bot — webhook + verifikacija potpisa | Da |
| 2.2 Tailscale postavka za mobilni pristup | Ne |
| 2.3 Dnevni email sa rasporedom, uptime monitoring | Ne |
| 2.4 Lista "za zakazati sledeći termin" | Ne |

### M0–M1 — materijal (kad god se gradi)
| Zadatak | Kritičan? |
|---|---|
| M0.1 Katalog materijala i zalihe (nezavisno od pacijenata) | Ne |
| M1.1 `material_usage` tabela, poseban `.db` fajl, SQLCipher enkripcija | Da |
| M1.2 Posebna lozinka za taj tab u aplikaciji | Da |
| M1.3 Agregatni izvještaji (bez imena pacijenta) | Da |

---

## Kriterijum "gotovo"

- [ ] Testovi napisani i prolaze
- [ ] Reviewer(i) potvrdili da kod odgovara tačno definisanom zadatku
- [ ] Ownership manifest provjeren
- [ ] Relevantna bezbjednosna stavka provjerena
- [ ] Radovan pregledao i odobrio merge

---

## Impact analiza (MEDIUM/HIGH)

Prije implementacije: koji moduli zavise od koda koji se mijenja, koje testove izmjena pogađa, postoje li paralelni taskovi nad istim kodom, mijenja li se contract/API. Ako impact analiza otkrije veći uticaj nego što je zadatak prvobitno definisao — zadatak se ne širi tiho, vraća se na redefinisanje obima.

## Reviewer Context Pack i strukturirani verdikt

Reviewer ne dobija samo `git diff` — dobija Task Contract, diff, listu dirnutih fajlova, relevantne dijelove CLAUDE.md, rezultat verifikacije, i (za MEDIUM/HIGH) rezultat impact analize.

```yaml
verdict: PASS  # ili PASS_WITH_NOTES, REJECT
scope: PASS
acceptance: PASS
architecture: PASS
security: PASS
blocking_findings: []
```

## Konflikt između reviewera

Ne rješava se glasanjem. Execution evidence ima prednost nad mišljenjem modela. Radovan odlučuje samo kad problem nije moguće razriješiti objektivnom provjerom.

## Scope expansion pravilo

Agent ne proširuje zadatak sam. Prijavljuje kao `OUT_OF_SCOPE_FINDING` i nastavlja originalni zadatak — osim ako nalaz direktno blokira bezbjednu implementaciju.

## Post-merge Integration Gate

Poslije merge-a: pun test suite na čistom `main`, schema/migration provjera, smoke test. Status `MERGED → INTEGRATION_VERIFIED → DONE`, ili `MERGED → INTEGRATION_FAILED` (dobija prioritet nad novim taskovima).

## Šta ne graditi odmah

Ne pravi se poseban orkestrator samo da bi se ovaj proces sproveo. Prvih 5–10 stvarnih Dentaland zadataka ide ručno/poluautomatski, sa postojećim alatima. Automatizuje se tek ono što se pokaže repetitivnim i stabilnim.

## Hijerarhija autoriteta

1. Execution evidence (rezultat testa)
2. Task Contract
3. Projektna arhitektura i bezbjednosna pravila
4. AGENTS.md / CLAUDE.md
5. Reviewer zaključak
6. Implementer tvrdnja
7. **Radovan** — konačna riječ kad gornje ne razriješi neslaganje
