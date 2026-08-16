---
datum: 2026-08-16
tip: setup-sažetak
status: skela postavljena, nijedan red aplikacijskog koda nije napisan
---

# Sažetak — postavljanje Dentaland projekta

Kratak zapis šta je urađeno prije nego se počne pisati stvaran kod, da se ne mora ponovo rekonstruisati iz razgovora.

## Šta je urađeno

1. **Analiza dva izvorna dokumenta** (`dentaland-agentski-razvoj.md` — proces, `dentaland-razvojni-plan.md` — v1 tehnički plan) i unakrsna provjera da li se risk-tier oznake u procesnom dokumentu slažu sa stvarnim tehničkim sadržajem.
2. **Istraživanje** (WebSearch/WebFetch) tehničkih i pravnih nepoznanica: PostgreSQL `EXCLUDE` constraint pattern, Viber Bot API signature/subscribe mehanika, `sqlcipher3`, DST zamke u zakazivanju, `pgloader`, i — najvažnije — **nov Zakon o zaštiti ličnih podataka BiH** (Sl. glasnik 12/25, na snazi od 4.10.2025).
3. **Postavljena projektna skela** na `C:\Users\38765\Desktop\Dentaland`: `CLAUDE.md`, `docs/`, `agent_reports/README.md`, `.gitignore`, `pyproject.toml` (bez zavisnosti — Faza 0 kod još nije pisan), `git init` (bez commit-a).
4. **`CLAUDE.md` spaja** FlowOS-stil radnog toka (risk tier LOW/MEDIUM/HIGH, Task Contract sa `allowed_paths`/`forbidden_paths`, strukturiran verdict blok, eksplicitno pravilo Implementer≠Reviewer, Reviewer Context Pack, ownership manifest, Post-merge Integration Gate, `OUT_OF_SCOPE_FINDING`, hijerarhija autoriteta) sa Dentaland-specifičnim sadržajem. Strukturni ključevi (YAML polja, enumi) su na engleskom, proza na srpskom/bosanskom — svjesna odluka radi dosljednosti sa CI/review obrascima.
5. **Tri iteracije plana svedene na jednu** — v1 (originalne premise) ostaje, v2 i v3 (tehnički + privacy/compliance dopune) su spojene i zamijenjene sa `docs/dentaland-razvojni-plan-v3.1.md`, koji je sada **jedini tehnički/pravni izvor istine**.

## Ključne odluke i ispravke urađene usput

- `EXCLUDE` constraint: `WHERE (status IN ('PENDING', 'SCHEDULED'))`, ne `!= 'CANCELLED'` — moja prvobitna verzija je pogrešno dozvoljavala da `REJECTED` zahtjevi trajno blokiraju slot.
- Cancel/reschedule token: u bazi se čuva **SHA-256 hash**, ne plaintext — curenje baze ne smije davati odmah upotrebljive javne linkove.
- Backup: SQLite backup API (ne file copy) **i** enkripcija prije cloud sync-a — dva odvojena rizika (korupcija i povjerljivost) na istom fajlu.
- Evidencija aktivnosti obrade **jest** obavezna za Dentaland (booking je kontinuirana, ne povremena obrada) — moja ranija tvrdnja da je izuzet zbog malog broja zaposlenih je bila pogrešna.
- DPIA **vjerovatno nije obavezna** za trenutan obim — ovo je nezavisno provjereno (ne pretpostavljeno) protiv Sl. glasnika BiH 70/25, koji nabraja 11 kategorija obrada za koje DPIA jest obavezna; obično zakazivanje bez profiliranja ne pogađa nijednu.
- **Proporcionalnost Faza 0 / Faza 1**: teška privacy dokumentacija (data inventory, evidencija obrade, pravni osnov po svrsi) je namjerno pomjerena sa Faze 0 na Faza 0→1 tranziciju (dio Produkcijskog release gate-a) — Faza 0 je privatna, offline, jednokorisnička aplikacija i ne zaslužuje isti regulatorni teret kao javni sistem. Faza 0 zadržava samo jeftine stavke (BitLocker, enkriptovan backup, politika o test podacima).

## Šta NIJE urađeno (namjerno)

- Nijedan red Faza 0 aplikacijskog koda (modeli, servisni sloj, GUI).
- Nijedan git commit — sve stoji kao untracked, čeka pregled.
- Razgovor sa Ljubom o "šta ga konkretno nervira kod sveske" — obrađen i zaključen kao ne-blokirajući (odgovor je bio generički "trend digitalizacije"); ne otvarati ponovo osim ako Ljubo sam pokrene temu.
- Konačna pravna potvrda (advokat/knjigovođa) za: tačan pravni osnov po svrsi, rokove čuvanja medicinske dokumentacije (propisi RS), kontrolor/obrađivač ugovor.

## Sljedeći korak kad se počne graditi

Prvi stvaran Task Contract — vjerovatno `DENT-001`, Faza 0 šema (`doctors/services/working_hours/time_off/appointments`) + Alembic, `risk: HIGH` po tabeli iz `dentaland-agentski-razvoj.md`. Šema je već precizno definisana u `docs/dentaland-razvojni-plan-v3.1.md` (sekcija "Faza 0 — Šema baze") — implementacija je prepisivanje te definicije u SQLAlchemy modele, ne novo projektovanje.

Prije prvog Task Contracta, pogledati `CLAUDE.md` sekciju "Otvorena pitanja" — provjeriti da li je nešto od toga u međuvremenu razriješeno.
