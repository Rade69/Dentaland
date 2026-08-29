# Dentaland — retention politika (DENT-IMPROVE-016)

Formalizuje koliko dugo Dentaland sistem čuva koju vrstu podataka.
Izvor istine za ono što je stvarno objavljeno pacijentima je
`web/privacy.html` (napisao Radovan, u produkciji od 17.8.2026) — ovaj
dokument je interna, tehnička formalizacija istog pravila, ne novo
pravilo.

## Booking podaci (ime, telefon, email, datum/vrijeme termina, usluga)

**Pet (5) godina od posljednjeg unosa.**

Potvrđeno kao poslovna odluka (Radovan, 29.8.2026), usklađeno sa
`web/privacy.html` sekcija 7 ("Koliko dugo čuvamo podatke?"). Odnosi se
na:

- neprihvaćene zahtjeve (brišu se/anonimiziraju kad više nisu potrebni
  za komunikaciju — vidi `privacy.html` sekcija 7, prvi pasus, kraći rok
  primjenjiv i prije 5 godina za ovu podkategoriju),
- prihvaćene termine koji postanu dio evidencije zakazivanja — pet
  godina od posljednjeg unosa (`privacy.html`, drugi pasus).

**Napomena o ispravci (bitno za kontinuitet):** raniji navod u CLAUDE.md
("automatska anonimizacija nakon 12 mjeseci") je bio netačan/zastario —
nikad usklađen sa `web/privacy.html`, koji je od 17.8.2026 u produkciji
sa petogodišnjim rokom. CLAUDE.md je ispravljen 29.8.2026 (commit
`0c83433`). Bilo koji stariji `agent_reports/` dokument koji pominje "12
mjeseci" u ovom kontekstu je zastario — ne oslanjati se na njega.

## Medicinska dokumentacija (istorija bolesti, planovi liječenja, anamneza)

**Nije primjenjivo na Dentaland sistem.**

Prava medicinska dokumentacija ostaje isključivo u papirnoj formi kod
ordinacije i **nikad ne ulazi u Dentaland bazu** — potvrđeno kao
arhitektonska/poslovna odluka (Radovan, 29.8.2026). Rok čuvanja te
dokumentacije je propisan zdravstvenim propisima Republike Srpske i
odgovornost je ordinacije kao fizičkog čuvara papirne dokumentacije, ne
Dentaland softvera.

`web/privacy.html` sekcija 2 eksplicitno upozorava korisnike da putem
javne forme NE unose JMBG, broj zdravstvene knjižice, dijagnozu,
anamnezu ili opis zdravstvenog stanja — ovo je dosljedno sa ovom
politikom, ne slučajno poklapanje.

## Tehnički zapisi (audit log, error log)

`audit_events` tabela (DENT-IMPROVE-014) je append-only — nema
ugrađenog mehanizma automatskog brisanja. Rok čuvanja audit zapisa nije
formalno definisan ovim dokumentom (van obima `DENT-IMPROVE-016`) — za
sada se čuvaju neograničeno, jer služe kao dokaz "ko/šta/kada" za
privilegovane radnje. Ako obim baze postane problem, ovo treba posebnu
odluku (ne default brisanje bez razmatranja compliance posljedica).

## Šta NIJE implementirano u kodu (poznato ograničenje)

**Automatska anonimizacija/brisanje nakon isteka roka trenutno NE
postoji u kodu** — potvrđeno `grep` pretragom (`anonymiz`/`retention` u
`src/` ne vraća ništa prije ovog taska). Ovaj dokument formalizuje
PRAVILO; mehanizam koji ga automatski primjenjuje (scheduled job koji
anonimizira/briše booking podatke starije od 5 godina) je budući,
poseban implementacioni task — van obima ovog release gate-a (koji je
compliance/dokumentacioni, ne implementacioni po ovoj stavci). Do tada,
primjena roka je ručna/proceduralna odgovornost ordinacije.

## Pravni osnov (kratak podsjetnik)

Pravni osnov obrade booking podataka je obavještenje/pristanak na javnoj
formi za zakazivanje (potvrđeno Radovan, 29.8.2026 — vidi CLAUDE.md
"Otvorena pitanja"). Ovo NIJE zamjena za nezavisnu pravnu provjeru —
poslovna je odluka, važi dok se ne pokaže suprotno.
