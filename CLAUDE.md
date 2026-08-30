# CLAUDE.md — Dentaland

Ovaj fajl vodi Claude Code i druge agente kroz **projektne premise**
Dentaland projekta — sistema zakazivanja za stomatološku ordinaciju. Za
**proces rada** (Task Contract, risk nivoi, review, git izolacija) vidi
`docs/dentaland-agentski-razvoj.md` — taj dokument je sada kanonski za
proces, ovaj fajl ga ne duplira.

## Start here

1. Pročitaj `AGENTS.md`.
2. Pročitaj `.agent/PROJECT_MAP.md` — gdje se šta nalazi.
3. Pročitaj konkretan Task Contract za zadatak (ako postoji).
4. Koristi `.agent/TASK_ROUTING.md` da izabereš dodatni kontekst po tipu
   zadatka.
5. `.agent/CURRENT_STATE.md` — samo ako je relevantno (dostupnost agenata,
   trenutni fokus, poznati baseline problemi).

## Non-negotiable global rules

- Implementer nikad nije isti agent/sesija kao Reviewer za taj zadatak.
- Svaki netrivijalan zadatak = svoj git worktree.
- Task Contract prije koda, ne retroaktivno.
- Execution evidence prije review-a, review prije human approval-a.
- Agent ne širi obim zadatka sam — prijavljuje `OUT_OF_SCOPE_FINDING`.
- Prati risk-tier proces (LOW/MEDIUM/HIGH — vidi razvoj.md za tok po
  nivou).

Pun proces: `docs/dentaland-agentski-razvoj.md`. Koordinacija paralelnih
agenata: `scripts/coordination.py` (vidi `AGENTS.md`).

---

## Šta je Dentaland

Sistem zakazivanja termina za **sva tri doktora ordinacije** (Ljubo, Zorka, Ana) — promjena od 16.8.2026 od ranijeg "samo Ljubo, ostali tek ako zatraže". Ekonomski okvir je neformalan; naplata je moguća tek ako se pokaže vrijednost.

Poznat i prihvaćen rizik, ne novo otkriće: raniji plan je namjerno izbjegavao rad za sva tri doktora odjednom ("najveći rizik neuspjeha cijelog projekta" — ako se ne dopadne svima, sistem pada). Ta procjena nije povučena kao pogrešna, samo svjesno prevaziđena poslovnom odlukom — sporo usvajanje kod Zorke/Ane se ne tretira kao iznenađenje.

Desktop GUI se gradi **odmah punom funkcionalnošću**, ne postepenim čekaj-pa-validiraj MVP-om (17.8.2026 odluka) — koriste se provjereni UI/workflow obrasci iz zrelih dentalnih sistema (Open Dental, Curve Dental, NexHealth — vidi `docs/istrazivanje-dentalni-scheduler-gui.md` sekcija 14) umjesto čekanja na Ljubinu stvarnu upotrebu. Ovo NE mijenja risk-tier proces (šema/migracije i dalje isključivo HIGH kroz Claude) niti znači kopiranje cijelog EHR scope-a (treatment plans, insurance, recall, operatories ostaju van obima).

Iz istog razloga — sistem treba biti brzo konvertibilan za drugu ordinaciju — funkcionalna potpunost (npr. štampa) se gradi bez provjere "treba li mu ovo" prije svake stavke iz plana (18.8.2026 pojašnjenje). Odvojeno od "Šta se namjerno ne gradi unaprijed" niže: ne pitati Ljubu prije implementacije planirane funkcije ≠ ne graditi generičnost za klijenta koji ne postoji — oba pravila važe istovremeno.

Razvoj ide u fazama, svaka sa jasnim kriterijumom uspjeha prije prelaska na sljedeću:

```text
Faza 0 — digitalna sveska (lokalno, PySide6 + SQLite, bez interneta)
→ Faza 1 — javno online zakazivanje (FastAPI + PostgreSQL, VPS, EXCLUDE constraint)
→ Faza 2 — usvajanje i otpornost (Tailscale, Viber bot, monitoring)
→ Faza 3 — samo ako se pokaže potreba (drugi doktori, lista čekanja, multi-tenancy)
```

Model zakazivanja je **zahtjev, ne instant rezervacija** — pacijent šalje zahtjev, osoblje potvrđuje. (Instant rezervacija je kratko razmatrana i odbačena 16.8.2026 — odluka nije promijenjena, ne pretpostavljati suprotno bez eksplicitne potvrde.)

## Izvori istine

- [docs/dentaland-razvojni-plan.md](docs/dentaland-razvojni-plan.md) — originalni plan (v1): premise, faze, funkcionalnosti, kontekst razgovora sa Ljubom.
- [docs/dentaland-razvojni-plan-v3.1.md](docs/dentaland-razvojni-plan-v3.1.md) — objedinjen tehnički + privacy/compliance plan (spaja ranije v2 i v3 iteracije). **Za tehničke, sigurnosne i pravne detalje ovaj dokument ima prednost nad v1** kad se razlikuju — v1 ostaje za originalne premise i kontekst. Sadrži tačan `EXCLUDE` constraint pattern, token-storage šemu (hash, ne plaintext), backup/migracija proceduru, RBAC, audit log, i puni privacy/compliance okvir sa nezavisno provjerenim pravnim izvorima.
- [docs/dentaland-agentski-razvoj.md](docs/dentaland-agentski-razvoj.md) — **kanonski procesni dokument**: risk nivoi, uloge, Task Contract, ownership/koordinacija, Reviewer Context Pack, strukturiran verdikt, hijerarhija autoriteta, evidence paket. Ovaj `CLAUDE.md` sadrži samo projektne premise, ne proces.
- [.agent/PROJECT_MAP.md](.agent/PROJECT_MAP.md) — struktura repoa, gdje se šta nalazi. [.agent/CURRENT_STATE.md](.agent/CURRENT_STATE.md) — kratkotrajno stanje (fokus, dostupnost agenata, baseline).
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
- Instant rezervacija (Model B) — oduzima kontrolu osoblju prerano (vidi napomenu uz "Model zakazivanja" na vrhu fajla).
- Javni server na Ljubinom ličnom računaru — poništava sigurnosnu prednost desktop pristupa.
- Multi-tenancy — tek kad postoji drugi stvarni klijent, na osnovu stvarne razlike, ne unaprijed nagađane.
- Redis/message broker/mikroservisi — jedan VPS, jedna instanca aplikacije pokriva obim; `slowapi` in-memory rate limiting je dovoljan, ne treba distribuiran backend.
- `project_rooms/` folder — kreira se tek kad prva HIGH-risk izmjena stvarno zatreba plan fajl van agent_reporta, ne unaprijed.

## Sigurnost i privatnost

- `appointments` i `material_usage` (M1) nikad u istom fajlu/bazi; M1 dodatno ide kroz `sqlcipher3` enkripciju sa posebnom lozinkom za taj tab u aplikaciji.
- Token generisanje: `secrets.token_urlsafe(32)`, nikad izvedeno iz appointment ID-a ili drugog predvidljivog izvora. Poređenje: `hmac.compare_digest()`.
- SMS/email/Viber podsjetnici nikad ne sadrže naziv usluge, samo vrijeme termina (minimizacija — potvrđeno kao usklađeno sa "minimum necessary" principom).
- Podaci o zakazivanju (ime/email/telefon/datum/usluga) čuvaju se **pet godina** od posljednjeg unosa (potvrđeno Radovan, 29.8.2026 — usklađeno sa `web/privacy.html` sekcija 7, "Koliko dugo čuvamo podatke?", u produkciji od 17.8.2026). Raniji navod od 12 mjeseci automatske anonimizacije je zastario i NE važi — ne oslanjati se na njega u starijim `agent_reports/`.
- Usklađenost sa Zakonom o zaštiti ličnih podataka BiH (Sl. glasnik BiH 12/25, na snazi od 4.10.2025, GDPR-usklađen) — vidi `docs/dentaland-razvojni-plan-v3.1.md` za pun privacy/compliance okvir. Ukratko: formalni DPO vjerovatno nije obavezan (dokumentovana procjena, ne pretpostavka), DPIA vjerovatno nije obavezna za trenutni obim (nezavisno provjereno protiv Sl. glasnika BiH 70/25 — booking sistem bez profiliranja ne triggeruje nijednu od 11 nabrojanih kategorija), ALI evidencija aktivnosti obrade JEST obavezna (booking je kontinuirana, ne povremena obrada — izuzetak za <250 zaposlenih ne važi ovdje), i 72h rok prijave povrede podataka JE obavezan za sve, bez obzira na veličinu.
- Backup baze ide kroz `sqlite3.Connection.backup()` API, nikad sirovo kopiranje `.db` fajla dok je aplikacija otvorena — rizik korupcije (WAL nekonzistentnost).
- Rate limiting na svakom javnom API endpointu.
- Dnevni `pg_dump` backup (Faza 1+) + **testiran** restore, ne samo napravljen.
- Migracija SQLite→PostgreSQL prvo na kopiji podataka (test instanca), provjera integriteta, tek onda produkcija uz backup neposredno prije.
- Nikad ne commitovati tajne, `.env` fajlove sa stvarnim vrijednostima, stvarne pacijentske podatke, lokalne baze.
- Ne tvrditi sigurnost koju sistem nema — konkretne činjenice i rezultati testova, ne uvjeravanje.

## Otvorena pitanja (trenutno stanje)

Vidi kraj `docs/dentaland-razvojni-plan-v3.1.md` sekcije "Šta i dalje ostaje otvoreno" za pun kontekst.

**Djelimično razriješeno (Radovan, 29.8.2026, poslovna odluka — nije nezavisna pravna provjera):** pravni osnov obrade booking podataka = obavještenje/pristanak na javnoj formi za zakazivanje; medicinska dokumentacija (istorija bolesti, planovi liječenja) ostaje isključivo u papirnoj formi kod ordinacije i nikad ne ulazi u Dentaland bazu — pitanje rokova čuvanja MEDICINSKE dokumentacije time nije primjenjivo na ovaj sistem. Booking podaci (ime/telefon/vrijeme termina) i dalje idu na VPS po planiranoj Fazi 1 arhitekturi — ovo NIJE promjena arhitekture.

**I dalje otvoreno, blokira HIGH-risk `EXCLUDE` constraint rad:** kontrolor/obrađivač ugovor, izbor hosting/cloud procesora, da li `service_id` mora ostati uz identitet pacijenta u bazi. Token i RBAC rad se u međuvremenu odvijao (DENT-IMPROVE-013, DENT-IMPROVE-014B) jer nije direktno zavisio od preostalih otvorenih tačaka — samo `EXCLUDE` constraint (PostgreSQL concurrency protection) ostaje eksplicitno blokiran dok se hosting/procesor pitanje ne razriješi.

**Izbor hostinga — namjerno odgođen (Radovan, 29.8.2026):** trenutno nema pristup/informaciju gdje se hostuje zvanični sajt ordinacije, pa se ta odluka svjesno odgađa do kraja projekta, ne rješava sad. Ovo znači da HTTPS, processor evidencija i `EXCLUDE` constraint ostaju na čekanju do tada — nije propust, nego dogovoren redoslijed.

**Dopuna (Radovan, 29.8.2026):** dostupan je poseban, nekorišten Contabo VPS koji Radovan može posvetiti isključivo Dentalandu — nije isti server kao zvanični sajt ordinacije. Namjena za sada: **samo testiranje deploymenta** (HTTPS/Let's Encrypt, Viber webhook, `EXCLUDE` constraint mehanika), ne stvarna produkcijska odluka — ta ostaje odvojena i i dalje otvorena. Testiranje na ovom VPS-u ide isključivo sa sintetičkim podacima, nikad stvarnim pacijentskim (vidi `docs/dentaland-politika-produkcijski-podaci.md`).

**Status (Radovan + Claude, 29.8.2026, isti dan):** pristup uspostavljen i HTTPS stvarno testiran — vidi `.agent/CURRENT_STATE.md` sekciju "Test VPS (Contabo)" za pun tehnički trag (SSH pristup, firewall, izdat Let's Encrypt sertifikat). Server dijeli sa `ffplayout` servisom koji ostaje netaknut — Dentaland testiranje izbjegava njegove portove.
