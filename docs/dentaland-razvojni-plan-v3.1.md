# Razvojni plan v3.1 — sistem zakazivanja za Dentaland

**Status:** objedinjena, finalna tehnička+privacy verzija. Spaja v2 (tehnička preciziranja: EXCLUDE constraint, backup, migracija, token) i v3 (privacy-by-design, sigurnost, pravni okvir) u jedan dokument, sa dvije izmjene primijenjene u odnosu na v3: (a) proporcionalnost Faza 0 naspram Faza 1 za privacy zadatke, (b) nezavisno potvrđen pravni citat (vidi "Izvori" na kraju). Premise ostaju iste kao u originalnom planu (klijent Ljubo, "samo za Ljubu" prvo).

**Metod:** svaka izmjena u odnosu na originalni plan ima naveden razlog i, gdje je relevantno, izvor. Ništa nije dodano "jer je moderno" — samo tamo gdje je original imao konkretnu tehničku, pravnu ili sigurnosnu rupu.

**Odnos prema starijim verzijama:** ovaj dokument zamjenjuje i v2 i v3 kao tehničko-pravni izvor istine. Originalni `dentaland-razvojni-plan.md` (v1) ostaje kao izvor premisa i konteksta razgovora — nije obrisan.

---

## Šta se mijenja u odnosu na originalni plan (v1) — sažetak

| # | Oblast | v1 | v3.1 | Razlog |
|---|---|---|---|---|
| 1 | Backup (Faza 0) | Kopiranje `.db` fajla | SQLite backup API + enkripcija prije cloud sync-a | Sirovo kopiranje rizikuje korupciju; nekriptovan backup je isti privatnost-rizik kao produkcija |
| 2 | `appointments.status` | Nedefinisan enum | Definisan od Faze 0 | Faza 1 ne smije mijenjati semantiku kolone na živim podacima |
| 3 | `EXCLUDE` constraint | Pomenut, bez detalja | `WHERE (status IN ('PENDING', 'SCHEDULED'))` | Blokiraju samo statusi koji predstavljaju aktivnu rezervaciju — `REJECTED`/`CANCELLED` ne smiju trajno zauzimati slot |
| 4 | Emergency override | Dvosmisleno ("mimo svih pravila") | Eksplicitno: zaobilazi FORM validaciju, nikad fizičku nemogućnost dva termina istovremeno | `EXCLUDE` constraint tehnički ne dozvoljava selektivno zaobilaženje po flagu, samo po statusu |
| 5 | `working_hours` | Implicitno | Lokalno vrijeme + IANA zona (`Europe/Sarajevo`) | DST bi pomjerio rekurentne termine dva puta godišnje |
| 6 | Token | Nepomenuto | Hash u bazi (SHA-256), poređenje `hmac.compare_digest()`, rok, jednokratna semantika | Curenje baze ne smije davati odmah upotrebljive javne linkove; timing-attack zaštita |
| 7 | SQLite→Postgres migracija | "Jednokratan izvoz/uvoz" | `pgloader` ≥3.6.0, prvo na kopiji, provjera integriteta, tek onda produkcija | "Prvi put na produkcijskim podacima" antipattern |
| 8 | SQLCipher biblioteka | Nepominjano | `sqlcipher3` (ne `pysqlcipher3`, napušten) | Konkretan, održavan izbor |
| 9 | Rate limiting | Nepominjano | In-memory limiter (npr. `slowapi`) za jedan aplikacijski proces | Proporcionalno obimu; Redis tek ako se pređe na više instanci |
| 10 | Viber pretplata | "Klikne deep link, bot šalje potvrde" | Deep link daje samo JEDNU welcome poruku; treba eksplicitan opt-in | `conversation_started` nije subscribe event |
| 11 | Konkurentan booking | Nepokriveno | `409 Conflict` → forma se osvježi | `EXCLUDE` sprečava podatak, ne govori šta korisnik vidi |
| 12 | Pravni osnov obrade | Kvačica pristanka za sve | Pravni osnov po svrsi; zdravstvena obrada nije automatski saglasnost | Zakon predviđa poseban osnov za zdravstvenu zaštitu/tretman |
| 13 | Evidencija aktivnosti obrade | Nije pominjano | Vodi se — izuzetak za <250 zaposlenih ne važi ako obrada nije povremena ili uključuje posebne kategorije | Booking termina je kontinuirana, ne povremena aktivnost |
| 14 | Audit | Nema | Poseban append-only log, odvojen od `updated_at` | Timestamp reda ne govori ko je šta uradio |
| 15 | RBAC | Nema | `RECEPTION` / `DENTIST` / `ADMIN`, najmanje privilegije | Sestra već danas odgovara na telefon — uloga ima stvaran, ne hipotetičan, korisnika |
| 16 | Data minimization | Nedefinisano | Javna forma traži minimum; `napomena` polje eksplicitno upozorava da se ne unose medicinski podaci | Slobodno tekstualno polje je stvaran curenje-vektor |
| 17 | Breach workflow | 72h pomenuto uzgred | Formalan `privacy_incidents` registar + eskalacioni tok | Zakonska obaveza za sve, bez obzira na veličinu |
| 18 | DPIA/DPO | Nepominjano | Dokumentovana procjena (`dpo-assessment.md`), ne pretpostavka — **nezavisno potvrđeno da Dentaland vjerovatno ne triggeruje DPIA** (vidi Izvori) | Procedura umjesto nagađanja |

---

## Proporcionalnost — Faza 0 naspram Faze 1 (izmjena u odnosu na v3)

v3 je stavio veći dio privacy dokumentacije (`P0.1`-`P0.3`: data inventory, evidencija obrade, dokumentovan pravni osnov) kao HIGH-risk zahtjev VEĆ u Fazi 0 — dok je Faza 0 privatna, offline, jednokorisnička aplikacija koja digitalizuje nešto što Ljubo već radi u papirnoj svesci. To je pravno ispravno u apstraktnom smislu, ali **nesrazmjerno cijeni izvođenja u odnosu na stvaran rizik te faze** i kosi se sa osnovnim principom cijelog projekta ("stani i preispitaj prije nego što ideš dalje" — isporuči jednostavno, provjeri upotrebu, tek onda širi).

**Rješenje u v3.1:** privacy zadaci se dijele po CIJENI izvođenja, ne samo po pravnoj ispravnosti:

- **Faza 0 — odmah, jeftino, bez pogovora:** OS login + full-disk encryption (BitLocker), enkriptovan backup + restore test, politika o zabrani stvarnih podataka u razvoju. Ovo je minuti posla, radi se bez obzira na fazu.
- **Faza 0 → Faza 1 tranzicija (dio "Produkcijskog release gate-a" ispod):** data inventory, evidencija aktivnosti obrade, dokumentovan pravni osnov po svrsi, registar procesora, DPIA/DPO procjena. Ovo se radi JEDNOM, ozbiljno, kad stvarno postoji javna forma i eksterni procesori za popisati — ne dvaput (hipotetički za privatnu svesku, pa opet za stvaran javni sistem).

Detaljna tabela zadataka (ispod, "Privacy implementacioni zadaci po fazama") je izmijenjena u odnosu na v3 upravo po ovom principu.

---

## Arhitektonske odluke — kratko

1. **Baza je konačni autoritet za konflikt termina.** UI i service sloj mogu pre-validirati, ali race condition rješava DB constraint.
2. **Booking sistem nije medicinski karton.** Ne širiti ga u zdravstveni ERP bez nove faze i procjene rizika.
3. **Privacy-by-design je horizontalni zahtjev, ali proporcionalan fazi** (vidi sekciju iznad) — ne postoji jedna "GDPR faza" niti se sve radi odjednom prije bilo kakvog koda.
4. **Audit nije `updated_at`.** Potreban je odvojen zapis ko/šta/kada za osjetljive radnje.
5. **Backup nije kopija fajla nego dokaziv oporavak** — i ne smije biti čitljiv van ovlaštenog pristupa.
6. **Treće strane su dio arhitekture.** Hosting, email, Viber, backup i monitoring se tretiraju kao procesori, ne kao nevidljiva infrastruktura.
7. **Tehničke biblioteke nisu cilj.** Zaključava se ponašanje/invarijanta; konkretna biblioteka se provjerava u trenutku implementacije.

---

## Faza 0 — Digitalna sveska (lokalna, bez interneta)

Cilj i kriterijum uspjeha ostaju kao u v1.

### Šema baze

```sql
doctors        (id, ime, aktivan)
services       (id, naziv, trajanje_min, buffer_min)
working_hours  (id, doctor_id, dan_u_sedmici, od_local, do_local, timezone)
time_off       (id, doctor_id, od_datetime, do_datetime, razlog)
appointments   (
    id, doctor_id, service_id,
    ime, telefon, email, napomena,
    start_time, end_time,
    status,               -- SCHEDULED | CANCELLED | COMPLETED | NO_SHOW  (Faza 1 dodaje PENDING/REJECTED)
    is_manual_override,   -- bool, default false — zaobilazi business pravila, ne overlap constraint
    created_at, updated_at
)
```

- `working_hours.timezone` — eksplicitno polje, ne pretpostavka.
- `status` enum definisan od početka, da Faza 1 migracija bude čisto aditivna, ne semantička izmjena na živim podacima.
- `is_manual_override` — kolona postoji od Faze 0 (nekorišćena dok ne postoji forma koja je postavlja) da Faza 2 ne traži migraciju baš `appointments` tabele.
- `updated_at` — prati posljednju izmjenu reda, **nije audit log** (vidi Audit sekciju niže, dolazi u Fazi 1).

### Backup mehanizam

**Problem u v1:** sirovo kopiranje `.db` fajla dok je SQLite u WAL režimu (ili čak i bez njega, dok je fajl otvoren) može dati nekonzistentnu kopiju — greška se otkriva tek kad backup zatreba.

```python
import sqlite3

def backup_database(source_path: str, dest_path: str) -> None:
    src = sqlite3.connect(source_path)
    dst = sqlite3.connect(dest_path)
    with dst:
        src.backup(dst)
    dst.close()
    src.close()
```

**Backup više ne ide kao čitljiv `.db` direktno u cloud folder.** Backup se prvo lokalno kreira kroz SQLite backup API, zatim enkriptuje, pa se tek enkriptovana kopija stavlja u sync folder (Google Drive/Dropbox). Ključevi za dekripciju ne smiju biti u istom folderu kao backup.

Minimalni zahtjevi: dnevni automatski backup, enkripcija prije cloud sync-a, rotacija (npr. 30 dnevnih + nekoliko mjesečnih), evidencija zadnjeg uspješnog backupa, periodičan restore test, dokumentovana lokacija i pristup.

Za lokalni računar: OS-level full-disk encryption (BitLocker) i odvojeni korisnički nalozi. **Cloud backup bez enkripcije nije prihvatljiv.**

**Risk tier:** procesni dokument označava backup kao "Ne" (nekritično). Preporuka: **MEDIUM** — jedan reviewer je dovoljan, ali taj reviewer eksplicitno provjerava backup API (ne file copy) i enkripciju prije sync-a.

---

## Faza 1 — Javno online zakazivanje

### `EXCLUDE` constraint

```sql
CREATE EXTENSION IF NOT EXISTS btree_gist;

ALTER TABLE appointments
    ADD CONSTRAINT appointments_time_valid
    CHECK (end_time > start_time);

ALTER TABLE appointments
    ADD CONSTRAINT no_doctor_overlap
    EXCLUDE USING gist (
        doctor_id WITH =,
        tstzrange(start_time, end_time, '[)') WITH &&
    )
    WHERE (status IN ('PENDING', 'SCHEDULED'));
```

- Nema redundantne `period` kolone koja bi se mogla razići sa `start_time`/`end_time`.
- `[)` interval dozvoljava da termin B počne tačno kad termin A završi.
- Blokiraju SAMO statusi koji predstavljaju aktivnu buduću rezervaciju — `REJECTED`, `CANCELLED`, `COMPLETED`, `NO_SHOW` ne zauzimaju slot.
- Baza, ne UI, ostaje konačni autoritet za sprečavanje overlap-a.

**Emergency override:** `is_manual_override=true` smije zaobići business pravila (radno vrijeme, buffer, standardno trajanje), ali **ne smije zaobići fizički overlap kod istog doktora**. Pravi double-booking (npr. hitan slučaj pored zakazanog) nije "override" nego promjena domenskog modela (dodatni resurs — stolica/soba/asistent) i zahtijeva zaseban dizajn, ne flag na postojećoj tabeli.

### Konkurentan booking

`INSERT` koji padne na `EXCLUDE` constraint (`23P01 exclusion_violation`) → API vraća `409 Conflict`. Javna forma na `409` automatski osvježi listu slobodnih slotova i prikaže "Ovaj termin je upravo zauzet, izaberite drugi" — ne generička greška.

### Migracija SQLite → PostgreSQL

**Alat:** `pgloader` ≥3.6.0. Zahtijeva SQLite ≥3.8 (praktično uvijek zadovoljeno), PostgreSQL ≥12.

**Obavezan redoslijed:**
1. Kopija Ljubinog stvarnog `.db` fajla (kroz backup API, ne raw copy).
2. `pgloader` migracija NA KOPIJI, u test Postgres instanci.
3. Provjera: broj redova po tabeli, spot-check termina, `EXCLUDE` constraint se uspješno kreira bez konflikta na postojećim podacima.
4. Tek nakon uspješne probne migracije: backup produkcijskog `.db` fajla, pa stvarna migracija.

### Token cancel/reschedule link

Generisanje ostaje kriptografski slučajno (`secrets.token_urlsafe(32)`), ali čuvanje se mijenja:

1. server generiše token;
2. pacijentu se šalje samo originalni token kroz URL;
3. u bazi se čuva **SHA-256 digest tokena**, ne plaintext;
4. pri zahtjevu se hashira primljeni token i poredi sa `hmac.compare_digest()`;
5. token ima `expires_at`;
6. nakon uspješnog otkazivanja/reprogramiranja token se invalidira ili rotira;
7. token se ne loguje u application/access logovima.

```text
cancel_token_hash
cancel_token_expires_at
cancel_token_used_at
```

Curenje baze samo po sebi ne daje napadaču važeće cancel linkove.

### SQLCipher (M1)

`sqlcipher3` (PyPI) — trenutno održavan izbor, `pysqlcipher3`/`pysqlcipher` su napušteni. Od verzije 0.6.2 self-contained wheel, bez eksternih zavisnosti. SQLAlchemy dialect ga prepoznaje automatski.

### Rate limiting

Za jedan aplikacijski proces, in-memory limiter (`slowapi` ili ekvivalent trenutno kompatibilan sa FastAPI/Starlette verzijom) je dovoljan. Prelazak na više workera/instanci zahtijeva shared backend (Redis) ili reverse-proxy nivo — ne prije nego što deployment stvarno to zatreba.

Odvojeni limiti minimalno za: prikaz slobodnih slotova, kreiranje booking zahtjeva, login, cancel/reschedule token endpoint. Viber webhook je prvenstveno zaštićen signature verifikacijom, ne klasičnim rate limitom.

---

## Faza 2 — Usvajanje i otpornost

### Viber bot

Klik na deep link okida `conversation_started` event, koji **nije subscribe event** — dozvoljava samo JEDNU welcome poruku. Za kontinuirano slanje potvrda/podsjetnika, korisnik mora eksplicitno "pretplatiti" nalog (poslati poruku botu ili drugi opt-in korak koji Viber API prepoznaje kao subscribe).

**Posljedica za dizajn:** forma treba jasno uputstvo ("Kliknite link, PA pošaljite bilo koju poruku botu da primate podsjetnike").

**Signature verifikacija:** HMAC-SHA256, ključ = account token, poruka = sirov JSON body, potpis u `X-Viber-Content-Signature` header-u. Python SDK ima `verify_signature(body, signature)`. Webhook URL mora imati validan SSL sertifikat sa CA liste koju Viber priznaje — Let's Encrypt uobičajeno zadovoljava, provjeriti prije registracije webhook-a.

---

## Privacy & Compliance — horizontalna komponenta

### Pravna osnova

BiH Zakon o zaštiti ličnih podataka (`Sl. glasnik BiH 12/25`, na snazi od 4.10.2025, GDPR-usklađen) uvodi risk-based režim. Za Dentaland su posebno važne četiri stvari:

1. podaci o zdravlju su posebna kategorija ličnih podataka;
2. evidencija aktivnosti obrade **nije automatski izuzeta** samo zato što ordinacija ima manje od 250 zaposlenih — izuzetak pada ako obrada nije povremena ili obuhvata posebne kategorije podataka (booking termina je kontinuirana aktivnost, ne povremena);
3. zdravstvena obrada se ne mora automatski zasnivati na saglasnosti — zakon predviđa osnov kada je obrada neophodna za pružanje zdravstvene zaštite/tretmana;
4. kod povrede podataka postoji 72-satni režim prijave Agenciji kada je primjenjivo, svaka povreda mora biti dokumentovana.

### Klasifikacija podataka

- **LEVEL 0 — javni/konfiguracijski:** ime doktora (javno objavljeno), naziv usluge bez veze sa pacijentom, radno vrijeme, slobodni slotovi bez identiteta.
- **LEVEL 1 — lični podaci:** ime i prezime, telefon, email, IP/device podaci gdje se opravdano loguju, korisnički nalog zaposlenog.
- **LEVEL 2 — osjetljiv zdravstveni kontekst:** identitet pacijenta povezan sa konkretnom uslugom, medicinska napomena/simptom/dijagnoza/terapija, materijal vezan za pacijenta, bilo šta iz čega se zaključuje zdravstveno stanje.

**Pravilo za agente:** LEVEL 2 podaci se nikad ne šalju eksternom AI/LLM servisu iz produkcije bez posebne privacy procjene i eksplicitno odobrene arhitekture.

### Data minimization

Javna forma prikuplja samo: ime i prezime, telefon (obavezno), odabrani datum i vrijeme. Email opciono, samo ako pacijent sam želi da ga ostavi. Usluga i doktor se NE biraju na javnoj formi (16.8.2026) — to se rješava u ordinaciji/telefonom prilikom potvrde zahtjeva, što dodatno smanjuje LEVEL 2 izloženost (identitet pacijenta se ne povezuje sa konkretnom uslugom već na javnoj formi, samo interno kod potvrde).

**Ne prikupljati u javnoj booking formi:** JMBG, adresu stanovanja, broj zdravstvene knjižice, dijagnozu, anamnezu, lijekove, detaljne simptome.

Polje `napomena` je rizično jer korisnik spontano može unijeti zdravstveni podatak. Ograničiti na kratku logističku napomenu sa jasnim tekstom: **"Ne unosite medicinske podatke, dijagnoze ni detalje o zdravstvenom stanju."**

### Pravni osnov po svrsi

Ne koristiti "prihvatam obradu ličnih podataka" kao univerzalno opravdanje za sve. Svaka svrha (zakazivanje, komunikacija o terminu, pružanje usluge, evidencija materijala, sigurnosni logovi, marketing) dobija svoj pravni osnov, kategorije podataka, primaoce, rok čuvanja, tehničke mjere — vidi `processing_registry.md` (kreira se u Faza 0→1 tranziciji, ne u Fazi 0).

**Marketing mora biti odvojen** — nikad uslov za zakazivanje termina; ako se koristi saglasnost, mora biti dobrovoljna, dokaziva, jednako jednostavna za povlačenje kao za davanje.

Konačnu formulaciju pravnog osnova za zdravstvenu obradu treba potvrditi sa pravnikom koji poznaje i zakon BiH i zdravstvene propise Republike Srpske.

### Privacy notice

Booking forma mora imati dostupno obavještenje PRIJE slanja zahtjeva: kontrolor, svrhe obrade, kategorije podataka, pravni osnov, primaoci, transferi (ako postoje), rok čuvanja, prava nosioca podataka, kontakt za privacy pitanja, pravo prigovora Agenciji.

Tekst uz dugme je informativan ("Slanjem zahtjeva potvrđujete da ste pročitali Obavještenje o obradi ličnih podataka") — **ovo nije saglasnost** ako se obrada oslanja na drugi pravni osnov.

### Kontrolor, obrađivač, ugovor

Ordinacija/pravni subjekt = kontrolor (određuje svrhe i način obrade). Developer/održavalac = obrađivač samo ako stvarno obrađuje podatke u ime ordinacije (pristup produkciji, backupima, support dumpovima).

Ako si obrađivač, pisani ugovor treba definisati: predmet i trajanje obrade, prirodu i svrhu, vrste podataka, obradu samo po dokumentovanim uputstvima kontrolora, povjerljivost, sigurnosne mjere, sub-processore, pomoć kod zahtjeva pacijenata, incident notification, vraćanje/brisanje podataka po završetku usluge.

**Support pravilo:** produkcijska baza se ne kopira na developerski računar radi debugovanja osim ako je nužno, odobreno i adekvatno zaštićeno. Preferirati sanitizovan/anonimizovan test dataset.

### Registar eksternih procesora

Prije produkcije popisati svaki servis kojem podaci mogu otići: VPS/hosting, email provider, Viber, DNS/CDN/WAF (ako vidi relevantne podatke), backup/cloud storage, monitoring/error tracking. Za svaki: koji podatak prima, zašto, gdje se obrađuje/čuva, ugovorni status, sub-processori, retention, transfer u drugu državu.

**Default:** ne stavljati Google Analytics, Meta Pixel, session replay i slične trackere na booking flow bez konkretne poslovne potrebe.

### RBAC

- **`RECEPTION`** — vidi raspored, kreira/mijenja/otkazuje termin, vidi osnovne kontakt podatke, nema pristup detaljnoj medicinskoj dokumentaciji. (Sestra već danas odgovara na telefon — ovo je stvaran, ne hipotetičan korisnik.)
- **`DENTIST`** — vidi raspored, vidi podatke potrebne za pružanje usluge, pristupa medicinskim podacima gdje su implementirani i potrebni.
- **`ADMIN`** — administrira korisnike/konfiguraciju/sistem; **ne dobija automatski pravo da čita medicinski sadržaj samo zato što je administrator sistema**.

Permission check na nivou endpointa/servisa. UI skrivanje nije sigurnosna kontrola.

### Autentifikacija i sesije

Argon2id (ili trenutno preporučen ekvivalent) za password hash, HTTPS obavezno, secure/HttpOnly/SameSite cookie ako se koristi cookie session, CSRF zaštita gdje je relevantna, login rate limiting, session expiration, invalidacija sesija poslije promjene lozinke, bez zajedničkog `admin` naloga za više zaposlenih — svaki zaposleni svoj nalog (audit ima smisla samo tako).

2FA nije obavezan MVP uslov, ali treba biti spreman kao nadogradnja prije šireg izlaganja internetu.

### Audit log

Poseban od `updated_at` — append-only:

```text
audit_events
- id, actor_user_id, action, resource_type, resource_id,
  occurred_at, request_id, source_ip (uz retention), metadata_minimal
```

Akcije: `LOGIN_SUCCESS/FAILURE`, `VIEW_PATIENT`, `CREATE/UPDATE/CANCEL_APPOINTMENT`, `EXPORT_PERSONAL_DATA`, `DELETE_OR_ANONYMIZE_PERSONAL_DATA`, `CHANGE_ROLE`, `VIEW_MEDICAL_DATA`. Audit log ne kopira medicinski sadržaj u `metadata`.

### Zahtjevi pacijenata

Ne treba self-service portal za malu ordinaciju, ali treba operativan workflow sa rokom:

```text
data_subject_requests
- id, request_type, requester_identity_reference, received_at, due_at,
  status, assigned_to, resolved_at, outcome
```

Tipovi: ACCESS, RECTIFICATION, ERASURE, RESTRICTION, PORTABILITY (gdje primjenjivo), OBJECTION. Sistem računa rok od **30 dana** i upozorava prije isteka.

**Napomena:** "pravo na brisanje" nije "obriši sve na klik" — ako poseban zdravstveni propis nalaže čuvanje medicinske dokumentacije, zahtjev može biti ograničen. Booking podaci i medicinska dokumentacija imaju odvojene retention politike.

### Retention

```text
DATASET                     RETENTION        RAZLOG
appointments                TBD              operativna potreba + pravna potvrda
cancel/reschedule tokens    do isteka        tehnička potreba
audit logs                  TBD              sigurnost/odgovornost
security logs               kraće/TBD        sigurnost
backups                     rotacija/TBD     oporavak
marketing consent evidence  dok je potrebno  dokaz saglasnosti
medical records             TBD              zdravstveni propisi RS — ne izmišljati rok ovdje
```

Automatsko brisanje se uvodi tek kad su rokovi pravno potvrđeni.

### Breach/incident workflow

```text
privacy_incidents
- id, detected_at, description, affected_systems, data_categories,
  estimated_people_affected, containment_actions, risk_assessment,
  agency_notification_required, agency_notified_at,
  data_subject_notification_required, data_subjects_notified_at, closed_at
```

Tok: incident → da li je povreda? → containment + evidencija → procjena rizika → (bez rizika: dokumentuj odluku) / (rizik: prijava Agenciji ≤72h gdje moguće) → (visok rizik: obavijesti pogođene osobe bez odgađanja).

**Operativno pravilo:** timer počinje kad organizacija SAZNA za povredu, ne kad se završi istraga.

### DPIA i DPO

**DPO:** mala ordinacija vjerovatno neće ispuniti prag "opsežne obrade" posebnih kategorija niti sistemskog praćenja velikog broja lica — formalni DPO vjerovatno nije obavezan. Zahtijeva se kratak dokument `dpo-assessment.md` sa razlogom zaključka, ponovnu procjenu ako se značajno poveća obim ili uvede profiliranje/AI.

**DPIA — nezavisno potvrđeno (vidi Izvori):** Agencija za zaštitu ličnih podataka BiH je objavila (Sl. glasnik BiH 70/25) spisak od 11 kategorija obrada za koje je DPIA obavezna — profiliranje/automatizovano odlučivanje sa značajnim uticajem, podaci djece za profiliranje/marketing, posebne kategorije za profiliranje, obrada od trećih strana za odluke o ugovorima, posebne kategorije "u velikom obimu", sistemski nadzor javnih mjesta, nove tehnologije (IoT), biometrija zaposlenih, povezivanje podataka iz više izvora, biometrija sa dodatnim rizikom, genetski podaci. **Zdravstveni podaci nisu samostalna kategorija na listi** — jedina primjenjiva stavka (posebne kategorije za profiliranje) zahtijeva da se podaci KORISTE ZA PROFILIRANJE, što običan booking sistem ne radi. Zaključak: Dentaland kako je trenutno zamišljen (bez profiliranja, bez automatizovanog odlučivanja, bez velikog obima) **vjerovatno ne triggeruje formalnu DPIA obavezu** — ovo je sad potvrđena činjenica, ne pretpostavka.

Ako sistem kasnije uvede AI nad medicinskim podacima, profiliranje, automatizovano odlučivanje sa značajnim učinkom, biometriju ili znatno veći obim — DPIA se procjenjuje PRIJE implementacije te funkcije, ne poslije.

### Podsjetnici

**Dobro:** "Dentaland: imate zakazan termin 17.08. u 10:30. Za izmjenu termina koristite link…"
**Izbjegavati:** "Podsjećamo Vas na implantološki zahvat…"

Naziv zdravstvene procedure se ne šalje kroz treće kanale ako nije neophodan. Cancel/reschedule URL koristi random token i ne otkriva `appointment_id`, ime ili uslugu.

### Logovi i monitoring

Ne logovati: plaintext cancel token, lozinku, cijeli request body booking forme, medicinsku napomenu, email/Viber sadržaj sa osjetljivim podacima. Error tracking ima sanitizaciju/redakciju prije slanja trećoj strani. Produkcijski logovi imaju definisan retention i pristup.

### Granica booking sistema i medicinskog kartona

**Booking baza ne postaje medicinski karton.** Ako se jednog dana gradi medicinska dokumentacija: zaseban modul/baza/security boundary, stroži RBAC, detaljniji audit, posebna retention politika, posebna DPIA/DPO procjena, zabrana automatskog slanja produkcijskih podataka eksternim AI servisima.

M1 `material_usage` ostaje zasebna osjetljiva cjelina; SQLCipher je dodatni sloj, ne zamjena za RBAC/audit/backup zaštitu.

---

## Privacy implementacioni zadaci po fazama (izmijenjeno u odnosu na v3 — vidi proporcionalnost gore)

### Faza 0 — odmah, prije korištenja stvarnih podataka

| ID | Zadatak | Risk |
|---|---|---|
| P0.1 | Lokalni uređaj: OS login + full-disk encryption | MEDIUM |
| P0.2 | Enkriptovan backup + restore test | MEDIUM |
| P0.3 | Politika korištenja stvarnih podataka u developmentu (default: zabranjeno) | MEDIUM |

### Faza 0 → Faza 1 tranzicija (dio Produkcijskog release gate-a, ne prije)

| ID | Zadatak | Risk |
|---|---|---|
| P1.1 | Data inventory + klasifikacija LEVEL 0/1/2 | HIGH |
| P1.2 | Evidencija aktivnosti obrade | HIGH |
| P1.3 | Dokumentovana procjena pravnog osnova po svrsi | HIGH |
| P1.4 | Privacy notice za booking | HIGH |
| P1.5 | Data minimization javne forme; ograničiti `napomena` | HIGH |
| P1.6 | RBAC (`RECEPTION`, `DENTIST`, `ADMIN`) | HIGH |
| P1.7 | Individualni user nalozi + sigurne sesije | HIGH |
| P1.8 | Append-only audit events | HIGH |
| P1.9 | Token hash + expiry + invalidacija + log redaction | HIGH |
| P1.10 | Registar procesora/subprocesora + ugovorni status | HIGH |
| P1.11 | Data Subject Request evidencija + 30-dnevni rok | MEDIUM |
| P1.12 | Retention matrica za booking/audit/log/backup | HIGH |
| P1.13 | Breach register + 72h incident runbook | HIGH |
| P1.14 | Privacy Risk Assessment + DPO/DPIA odluka (dokumentovana, vidi DPIA sekciju) | HIGH |
| P1.15 | Produkcijski security/privacy review | HIGH |

### Faza 2 — otpornost

| ID | Zadatak | Risk |
|---|---|---|
| P2.1 | Incident drill: simulirani gubitak/curenje podataka | HIGH |
| P2.2 | Restore drill iz enkriptovanog backupa | HIGH |
| P2.3 | Periodični access review: ko ima koju ulogu | MEDIUM |
| P2.4 | Pregled retention pravila i purge mehanizma | HIGH |
| P2.5 | Viber/email sadržaj i procesori — privacy review | HIGH |

---

## Produkcijski release gate — javni booking ne ide live dok ovo ne prođe

- [ ] EXCLUDE/konkurentni booking testovi prolaze
- [ ] HTTPS i admin autentifikacija prolaze security provjeru
- [ ] javna forma prikuplja samo odobren minimum podataka
- [ ] privacy notice je dostupan prije slanja zahtjeva
- [ ] pravni osnov i svrhe su dokumentovani (P1.1-P1.3)
- [ ] evidencija aktivnosti obrade postoji
- [ ] kontrolor/obrađivač uloge su ugovorno razjašnjene
- [ ] registar eksternih procesora je popunjen
- [ ] RBAC radi server-side
- [ ] svaki zaposleni ima svoj nalog
- [ ] audit log radi i ne sadrži osjetljivi payload
- [ ] cancel/reschedule token se ne čuva plaintext
- [ ] backup je enkriptovan i restore je testiran
- [ ] breach runbook postoji
- [ ] data-subject-request workflow postoji
- [ ] retention matrica postoji makar za booking/logove/backupe
- [ ] DPO/DPIA procjena je dokumentovana (uz napomenu da formalna DPIA vjerovatno nije obavezna za trenutni obim — vidi DPIA sekciju)
- [ ] nema produkcionih podataka pacijenata u AI promptovima, test fixture-ima ili developerskim dumpovima

---

## Agent rules — dopuna za `CLAUDE.md`

```text
PRIVACY / SECURITY HARD RULES

1. Never send production patient data to external AI/LLM services.
2. Never log passwords, auth cookies, reset/cancel tokens, medical notes, or full booking request bodies.
3. Public booking collects the minimum data required for scheduling.
4. Medical data never belongs directly in views, logs, analytics, or generic support dumps.
5. All authorization is enforced server-side.
6. Every privileged user has an individual account; no shared admin account.
7. Changes to auth, RBAC, audit, token logic, retention, backups, patient data schema,
   processors, or public API are HIGH-risk tasks and require two independent reviewers.
8. Backup is not DONE until restore is proven.
9. A failed privacy/security gate blocks merge/release exactly like a failed test.
10. Any new external SaaS that receives personal data requires processor/privacy review before integration.
```

---

## Faza 3 — namjerno otvorena, sa obaveznim re-assessment triggerima

Funkcionalnosti se i dalje ne planiraju unaprijed bez stvarne potrebe. Prije svake veće nove funkcije obavezno ponovo procijeniti privacy/security ako se uvodi: medicinski karton, AI nad podacima pacijenata, profiliranje ili automatizovano odlučivanje, biometrija, novi komunikacioni kanal, novi hosting/cloud/analytics provider, mobilna aplikacija sa lokalnim cache-om, više ordinacija/tenant-a. Ovo su arhitektonski triggeri, ne samo nove UI funkcije — i tačno se poklapaju sa kategorijama koje Agencija (Sl. glasnik BiH 70/25) navodi kao DPIA-obavezne.

---

## Izvori i autoritativne reference (provjereno 16.8.2026)

### Pravni — primarni izvori, nezavisno provjereni
- [Službeni glasnik BiH 12/25 — Zakon o zaštiti ličnih podataka](https://advokat-prnjavorac.com/Zakon-o-zastiti-licnih-podataka-BiH.html)
- **[Službeni glasnik BiH 70/25 — Odluka o utvrđivanju i javnoj objavi spiska obrada za koje je potrebno provesti DPIA](https://www.zakoni.ba/page/akt/5Pj6Q6z7NKA%3D)** — direktno dohvaćen i provjeren sadržaj: 11 kategorija, izdato od Agencije za zaštitu ličnih podataka BiH (dir. Dr. Dragoljub Reljić), 10.11.2025. Zdravstveni podaci nisu samostalna kategorija; jedina primjenjiva stavka zahtijeva profiliranje.
- [Novi zakon — DPO i evidencija obaveze](https://www.rtvslon.ba/od-oktobra-na-snazi-novi-zakon-o-zastiti-licnih-podataka-sta-znaci-za-gradjane-i-firme/)

### Tehnički izvori — koristiti aktuelnu službenu dokumentaciju pri implementaciji
- PostgreSQL dokumentacija — range types i exclusion constraints
- Python dokumentacija — `sqlite3.Connection.backup`, `secrets`, `hmac`, `zoneinfo`
- FastAPI/Starlette i izabrani rate-limiter — aktuelna dokumentacija
- Viber Bot API — webhook/signature/deep-link dokumentacija
- SQLCipher / odabrani Python binding — aktuelna dokumentacija (`sqlcipher3` na PyPI)
- pgloader — aktuelna dokumentacija

**Pravilo:** verzije biblioteka u planu nisu trajno zaključane. Agent prije implementacije provjerava trenutno podržanu stabilnu verziju i kompatibilnost sa zaključanim stackom projekta.

---

## Šta i dalje ostaje otvoreno — odluke prije produkcije

1. **Tačan pravni osnov po svakoj svrsi obrade** — DJELIMIČNO RIJEŠENO (Radovan, 29.8.2026): pravni osnov za booking podatke (ime/telefon/vrijeme termina) je obavještenje/pristanak na javnoj formi za zakazivanje. **Nije potvrđeno sa pravnikom** — ovo je Radovanova poslovna odluka, ne nezavisna pravna provjera; ostaje na toj osnovi dok se ne pokaže suprotno.
2. **Rokovi čuvanja medicinske dokumentacije** — RIJEŠENO kao "nije primjenjivo na Dentaland sistem" (Radovan, 29.8.2026): prava medicinska dokumentacija (istorija bolesti, planovi liječenja) ostaje isključivo u papirnoj formi kod ordinacije, nikad ne ulazi u bazu. Sistem čuva samo booking podatke (ime/email/telefon/vrijeme termina), za koje rok čuvanja već postoji — 12 mjeseci, automatsko anonimiziranje (vidi CLAUDE.md "Sigurnost i privatnost").
3. **Kontrolor/obrađivač ugovor** — I DALJE OTVORENO — potvrditi pravni subjekt ordinacije i da li developer u praksi ima pristup produkcionim podacima.
4. **Cloud/hosting lokacija i procesori** — I DALJE OTVORENO — odabrati konkretne providere i provjeriti ugovorne/transfer uslove prije produkcije. Booking podaci (ime/telefon/vrijeme termina, ne medicinska dokumentacija) IDU na VPS po Fazi 1 arhitekturi (CLAUDE.md) — potvrđeno 29.8.2026, nije promjena arhitekture — pa procesor ugovor sa hosting providerom ostaje neophodan.
5. **Emergency override** — zaključano na "zaobiđi business pravila, ne overlap". Promjena toga zahtijeva novi resource model.
6. **Da li se `service_id` mora čuvati uz identitet u booking bazi** — ako ordinacija može poslovno raditi sa neutralnom kategorijom/trajanjem, dodatno smanjuje osjetljivost; ako ne može, tretirati kombinaciju pacijent+usluga kao LEVEL 2.
7. **2FA za zaposlene** — nije blokada za lokalni MVP, ali ponovo procijeniti prije javnog internet deploymenta.
8. **Viber** — uvesti tek nakon što osnovni booking/email tok radi stabilno.
