# Razvojni plan — sistem zakazivanja za Dentaland

**Status:** radni dokument, originalna verzija. **Za tehnička preciziranja vidi `dentaland-razvojni-plan-v2.md`** — ovaj dokument ostaje kao izvor originalnih premisa i konteksta razgovora.
**Klijent:** Ljubo (suvlasnik ordinacije, prijatelj) — **ne** cijela ordinacija
**Ekonomski okvir:** neformalno, moguća naplata tek ako se pokaže vrijednost

---

## Polazne premise (iz razgovora)

- Ordinacija trenutno nema zajednički kalendar — svaki doktor (Zorka, Ljubo, Ana) vodi termine u vlastitoj svesci.
- Ljubo je taj koji traži promjenu; razlog nije precizno definisan (opšti "trend digitalizacije"), pa se to mora provjeriti prije nego što Faza 0 postane obavezujuća.
- Postojeći sajt (dentaland.org) nije rađen od tebe — sistem se gradi kao odvojena cjelina, ne dirajući postojeći kod.
- Gradi se **samo za Ljubu**. Zorka i Ana ulaze u priču tek ako same zatraže, nakon što vide da sistem radi.
- Minimalni podaci o pacijentu: ime i prezime, telefon, email — bez medicinske istorije, bez kartona.
- Model zakazivanja: **zahtjev, ne instant rezervacija** (pacijent šalje zahtjev, osoblje potvrđuje).

---

## Faza 0 — Digitalna sveska (lokalna, bez interneta)

**Cilj:** zamijeniti Ljubinu svesku, i ništa više. Bez javnog zakazivanja, bez servera, bez pacijenata koji bilo šta šalju spolja.

**Kriterijum uspjeha:** poslije mjesec dana stvarne upotrebe, Ljubo više ne otvara svesku. Ako je otvara — stani i preispitaj prije nego što ideš dalje.

### Stek
- PySide6 (desktop GUI)
- SQLite, lokalno na njegovom računaru
- Nema mrežnih poziva, nema servera

### Šema baze (namjerno ista forma kao buduća serverska baza, radi lakše migracije)
```
doctors        (id, ime, aktivan)
services       (id, naziv, trajanje_min, buffer_min)
working_hours  (id, doctor_id, dan_u_sedmici, od, do)
time_off       (id, doctor_id, od_datetime, do_datetime, razlog)
appointments   (id, doctor_id, service_id, ime, telefon, email, napomena,
                start_time, end_time, status, no_show, created_at)
```
(Samo jedan red u `doctors` za sada — Ljubo. Ostalo ostaje generičko.)

### Funkcionalnosti
- Sedmični pregled kao početni ekran (ne dnevni — sveska se otvara na cijelu sedmicu)
- Klik na prazno mjesto u kalendaru — odmah unos termina, bez više ekrana
- Prevlačenje termina mišem za pomjeranje
- Slobodno tekstualno polje za napomenu, bez validacije koja smeta
- Dugme "Štampaj raspored za dan / sedmicu"
- Automatski backup `.db` fajla u Google Drive / Dropbox folder pri zatvaranju aplikacije

### Preduslov prije puštanja u rad
Prepisati sve postojeće buduće termine iz sveske u aplikaciju — jedan trenutak, ne postepeni prelaz sa dva izvora istine.

### Prije nego počneš
Razgovor sa Ljubom: šta ga konkretno nervira kod sveske. Ako nema konkretan odgovor, cilj Faze 0 se mijenja — ne "zamijeni svesku", nego "dodaj uvid u raspored sa telefona van ordinacije" (vidi Tailscale u Fazi 2).

---

## Faza 1 — Javno online zakazivanje

(16.8.2026: preduslov "Faza 0 stvarno zaživjela kod Ljube" uklonjen — eksplicitna odluka, faze se više ne blokiraju međusobno tim kriterijumom.)

### Migracija
SQLite → PostgreSQL, ista šema (proširena poljima ispod). Jednokratan izvoz/uvoz, ne prepravka.

### Server
- FastAPI + PostgreSQL, na malom VPS-u (Hetzner / DigitalOcean, ~3–5 €/mjesec)
- Nginx + Uvicorn/Gunicorn, SSL sertifikat (Let's Encrypt)
- `EXCLUDE` constraint u PostgreSQL-u za fizičku zabranu preklapanja termina
- Sve vrijeme kao `timestamptz`, prikaz u `Europe/Sarajevo` (pazi na DST)

### Javna strana
- Poddomen (npr. `zakazivanje.dentaland.org`), stilizovan u boje ordinacije (`#3fbbc0`)
- Jedina izmjena na postojećem sajtu: `href` na dugmetu "Zakaži termin" → novi URL
- Forma (pojednostavljeno 16.8.2026 — usluga i doktor se biraju u ordinaciji/telefonom, ne online): kalendar sa slobodnim terminima → datum → vrijeme → ime, telefon (obavezno), email (opciono), kvačica pristanka → "Zahtjev poslat, javićemo se"
- Link za otkazivanje sa nasumičnim tokenom (`secrets.token_urlsafe(32)`), ne sekvencijalni ID
- Email potvrda pacijentu (SMTP / SendGrid) — SMS se za sada izostavlja (trošak, vidi Fazu 2 za Viber alternativu)

### Admin strana (Ljubo)
- Desktop aplikacija iz Faze 0 se proširuje da komunicira sa serverom (`httpx` / `QNetworkAccessManager`), umjesto čisto lokalne baze
- Lista dolaznih zahtjeva — Potvrdi / Odbij
- Ostale funkcije iz Faze 0 ostaju (ručni unos, pomjeranje, štampa)

### Pravno i podaci
- Kvačica pristanka na formi + kratka stranica o obradi podataka
- SMS/email podsjetnici nikad ne sadrže naziv usluge, samo vrijeme termina
- Automatsko anonimiziranje ličnih podataka nakon dogovorenog perioda (npr. 12 mjeseci) — ime/email/telefon se brišu, datum/usluga ostaju za statistiku
- Jednostranični ugovor sa Ljubom: ko je vlasnik podataka, ko odgovara, gdje se hostuje, šta se dešava ako prestaneš održavati, zadržano pravo da rješenje koristiš i za druge klijente

### Otpornost
- Dnevni `pg_dump` backup + **testiran** restore (ne samo napravljen)
- Rate limiting na javnom API-ju

---

## Faza 2 — Usvajanje i otpornost na prekide

Ide tek kad Faza 1 stabilno radi.

- **Tailscale** između Ljubinog računara/servera i telefona — uvid u raspored van ordinacije, bez otvaranja javnog porta
- Dnevni email sa rasporedom u 7:00, automatski — ako sistem padne u 9:00, raspored za taj dan je već isporučen
- Jednostavan uptime monitoring (npr. UptimeRobot) da ti javi prije nego što klijent primijeti pad
- **Viber bot** (Public Account + Bot API, besplatno) — pacijent klikne deep link na stranici potvrde da započne razgovor (opt-in), bot šalje potvrde/podsjetnike i odgovara na upit "kad mi je termin"; zahtijeva webhook na već postojećem serveru
- No-show praćenje: polje na terminu + upozorenje osoblju kod ponovljenog zakazivanja istog broja
- Jasna napomena na formi da online zakazivanje nije za hitne slučajeve + broj telefona za hitne pozive
- Mogućnost da Ljubo/sestra ubaci termin mimo svih pravila (radno vrijeme, preklapanje) za stvarne hitne slučajeve

---

## Faza 3 — Samo ako se pokaže potreba (ne planirati unaprijed)

- Drugi doktori (Zorka, Ana) — isključivo ako sami zatraže, nakon što vide da sistem radi kod Ljube
- Lista čekanja za otkazane termine
- Ponavljajući termini / kontrole (relevantno za Aninu ortodonciju)
- Multi-tenancy i konfigurabilnost za druge ordinacije, ako ovo postane proizvod — tek kad postoji drugi stvaran klijent, na osnovu stvarne razlike koju vidiš, ne unaprijed nagađane

---

## Eksplicitno NE raditi (i zašto)

- **Plugin sistem / arhitektura za proširenje** — nema drugog klijenta na osnovu kojeg bi se dizajnirale tačke proširenja; obična konfiguracija (baza + settings) pokriva potrebu za sada
- **Twilio SMS** — preskup za obim jedne ordinacije; Viber (Faza 2) je jeftinija i prirodnija alternativa u BiH
- **Instant rezervacija (Model B)** — oduzima kontrolu osoblju prerano; razmotriti tek kad sistem stekne povjerenje
- **Javni server na Ljubinom ličnom računaru** — poništava tačno onu sigurnosnu prednost zbog koje je izabran desktop pristup; za javnu dostupnost koristi se VPS
- **Rad za sva tri doktora odjednom** — najveći rizik neuspjeha cijelog projekta; jedan motivisan korisnik prvo, ostali kad sami zatraže

---

## Napomena o statusu pitanja za Ljubu

Originalna lista "Pitanja za Ljubu prije početka razvoja" je zamijenjena stvarnim razgovorom — odgovori i njihove posljedice po plan su obrađeni direktno kroz analizu u `dentaland-razvojni-plan-v2.md` i `CLAUDE.md` ("Otvorena pitanja"). Ova sekcija se ne održava odvojeno.
