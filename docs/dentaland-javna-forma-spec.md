---
datum: 2026-08-16
tip: UI/UX spec — Faza 1 javna forma
status: spremno za implementaciju mokapa (Codex), backend nije u obimu ovog fajla
---

# Javna forma zakazivanja — potpuna specifikacija

Ovo je jedini izvor istine za izgled i tekst javne stranice za zakazivanje (Faza 1). Zamjenjuje sve prethodne usmene/chat instrukcije date Codexu — ako se nešto ovdje razlikuje od ranije poruke, ovaj fajl važi.

Kontekst modela: **zahtjev, ne instant rezervacija** — pacijent šalje zahtjev, osoblje potvrđuje (vidi `CLAUDE.md`). Sva tri doktora (Ljubo, Zorka, Ana) dijele istu formu — doktor i usluga se NE biraju online, rješava ih osoblje.

## Struktura — tačno tri koraka

```
1. Odaberite datum → 2. Vaši podaci → 3. Potvrda
```

Nema koraka za uslugu, nema koraka za doktora, nema izbora tačnog vremena (samo datum).

---

## Korak 1 — Odaberite datum

**Naslov koraka:** "Odaberite datum"
**Podnaslov:** "Izaberite dan za svoj termin"

- Mjesečni kalendar (strelice lijevo/desno za promjenu mjeseca), pun mjesečni grid (6 sedmica × 7 dana, uključujući sive datume iz susjednih mjeseci kao popunu).
- **Radni dani: ponedjeljak–subota.** Nedjelja je neradni dan. **Prikaz (17.8.2026, konačna odluka — treća iteracija, zamjenjuje i 16.8. petodnevnu i 17.8. šestodnevnu-bez-nedjelje verziju): kalendar prikazuje SVIH SEDAM kolona (PO–NE), nedjeljni datumi su vidljivi ali onemogućeni (sivi, neklikabilni)** — obrnuto od ranije odluke "nedjelja se ne prikazuje uopšte". Razlog promjene: implementacija punog mjesečnog grid-a (sa danima iz susjednih mjeseci kao kontekst) prirodnije radi sa punih 7 kolona; Radovan je potvrdio da ne mijenja ovo rješenje. Legenda ispod kalendara: "Dostupno" (puna teal tačka) / "Onemogućeno" (siva tačka) — nedjelja i prošli datumi dijele "Onemogućeno" stanje.
- **Samo DVA vizuelna stanja datuma — dostupno i onemogućeno.** Ne tri (ranija verzija mokapa je imala legendu Dostupno/Ograničeno/Nedostupno — to više nema smisla jer se ne bira tačno vrijeme, samo dan, pa "ograničeno" nema jasno značenje za prikazati). Dostupan dan: normalna boja teksta, klikabilan. Onemogućen dan (prošlost, unutar prikazanih Pon–Pet kolona): vizuelno bljeđi, neklikabilan. Ne uvoditi treću nijansu.
- Klik na DOSTUPAN dan: (a) bira datum (vizuelno istaknut, puni krug u brend boji) I (b) **odmah prebacuje na Korak 2** — nema posebnog "Nastavi" dugmeta na Koraku 1 (za razliku od Koraka 2, koji ima svoje dugme jer forma treba validaciju prije nastavka).
- Info okvir ispod kalendara, uvijek vidljiv:
  > "Tačno vrijeme termina biće određeno od strane naše ordinacije.
  > Kontaktiraćemo vas dan ranije kako bismo potvrdili vrijeme."

**Nema:** grid termina/sati, nema izbora usluge, nema izbora doktora.

---

## Korak 2 — Vaši podaci

**Naslov koraka:** "Vaši podaci"
**Podnaslov:** "Unesite svoje podatke"
**Naslov panela:** "Molimo unesite tražene podatke."

Polja tačno ovim redoslijedom:

1. **Ime i prezime** — obavezno (`*`), placeholder "Unesite ime i prezime".
2. **Telefon** — obavezno (`*`), sa selektorom pozivnog broja (BiH zastava, `+387` default), placeholder "Unesite broj telefona".
3. **Email** — opciono, jasno označeno "(opcionalno)", placeholder "Unesite email adresu".

**Nema polje za napomenu (16.8.2026, izmjena).** Slobodno tekstualno polje na anonimnoj javnoj formi je poziv pacijentu da napiše zdravstveni podatak (simptom, razlog posjete, "bolan zub" i sl.) — to je tačno ono što `docs/dentaland-razvojni-plan-v3.1.md` već zabranjuje ("Ne prikupljati u javnoj booking formi: ... dijagnozu, anamnezu, lijekove, detaljne simptome"). Bilo šta relevantno se kaže osoblju telefonom kad zovu da potvrde vrijeme, ne upisuje se trajno u bazu preko neautentifikovane forme. (Napomena polje i dalje postoji u `appointments` šemi — to je za Fazu 0 desktop unos gdje osoblje samo direktno piše, ne za javnu formu.)

Ispod polja, kutija sa štitom/ikonom povjerenja:
> **Vaši podaci su sigurni**
> Koristimo vaše podatke isključivo za rezervaciju termina i komunikaciju u vezi s istim. Ne dijelimo ih sa trećim stranama.
> [Obavještenje o obradi ličnih podataka] (link, otvara u novom tabu)

Ispod toga, **obavezna kvačica pristanka** (checkbox, ne pre-čekiran):
> "Upoznat/a sam sa Obavještenjem o obradi ličnih podataka."

Dugme "Nastavi" — **neaktivno dok kvačica nije čekirana ILI ime/telefon nisu popunjeni.**

Na dnu: "* Obavezna polja"

**Nema:** polje za uslugu, polje za doktora, polje za JMBG/adresu/zdravstvenu knjižicu (nikad — vidi `docs/dentaland-razvojni-plan-v3.1.md` "Ne prikupljati u javnoj booking formi").

---

## Korak 3 — Potvrda

**Naslov koraka:** "Potvrda"
**Podnaslov koraka (gore, mala oznaka uz broj 3):** "Zahtjev je poslat" — NE "Termin je zakazan".

**Glavni naslov (veliki, sa zelenom kvačicom/ikonom):**
> "ZAHTJEV PRIMLJEN!"

**Podnaslov ispod:**
> "Datum je rezervisan, javićemo vam se dan ranije sa tačnim vremenom."

⚠️ **Bitno — ovo je izmjena u odnosu na prethodni mokap:** prethodna verzija je imala "TERMIN JE ZAKAZAN!" / "vaša rezervacija je potvrđena" — to jezik prejako obećava izvjesnost koju sistem namjerno ne daje (model je zahtjev, ne rezervacija). Naslov i podnaslov MORAJU biti tekst iznad, ne prethodni.

Kartica sa detaljima zahtjeva (ostaje kao u prethodnom mokapu, ovaj dio je bio ispravan):
- 📅 Datum: `12.06.2026. (četvrtak)`
- 🕐 Vrijeme: "Biće određeno od strane ordinacije"
- 🏥 Ordinacija: "Dentaland — Stomatološka ordinacija"

Sekcija "Šta dalje?":
> 📞 "Kontaktiraćemo vas dan ranije kako bismo potvrdili vrijeme vašeg termina."

Dva dugmeta (ostaju kao u mokapu):
- "📅 Dodaj u kalendar" (ICS export sa privremenim datumom, bez tačnog vremena — ili bez ovog dugmeta ako vrijeme nije poznato; po nahođenju Codexa koje je tehnički jednostavnije, nije blokirajuće)
- "✏️ Otkaži ili promijeni termin" — vodi na link sa tokenom (backend, van obima ovog mokapa; sam link/URL format nije poznat još, dovoljno je da dugme postoji)

Na dnu: "Imate pitanja? Nazovite nas: [broj telefona ordinacije]"

---

## Globalno (svi koraci)

- **Brend:** teal `#3fbbc0` kao primarna boja, bijela pozadina — u skladu sa postojećim dentaland.org sajtom.
- **Header (16.8.2026, ispravljena odluka — ranija verzija ovog reda je pogrešno tvrdila "finalno" bez stvarne potvrde):** puniji header je odobren. Desktop: logo lijevo, pun meni (Početna/Usluge/Ordinacija/Za pacijente/Kontakt), telefon ordinacije + radno vrijeme, "Zakaži termin" dugme desno. Mobilni: logo, telefon ordinacije, bez punog menija (prostorno se ne uklapa). **Nigdje u headeru (desktop ni mobilni) NE smije biti "Login" dugme ili bilo šta što implicira nalog/prijavu pacijenta** — to je eksplicitno van obima (vidi "Šta NIJE u obimu" ispod), prikazivanje UI-ja za nepostojeću funkciju zbunjuje pacijenta.
- **Step indicator** (1-2-3) na vrhu, uvijek vidljiv, trenutni korak istaknut bojom.
- **Mobilni prikaz (16.8.2026, precizirano):** na širinama ispod ~768px, tri kolone (koraci) se NE prikazuju jedna pored druge — prikazuje se SAMO panel trenutnog koraka, preko cijele širine, ostali koraci su sakriveni dok se ne dođe do njih. Step indicator (1-2-3) ostaje vidljiv na vrhu kao orijentir. Desktop prikaz (sve tri kolone vidljive uporedo) ostaje kao u mokapu za širokе ekrane.
- **Ikonice** su SVG (linijske, u stilu mokapa), ne emoji — radi vizuelne konzistentnosti sa dentaland.org.
- **Ton teksta:** direktan, ljudski, bez žargona — "Zahtjev je poslat", ne "Vaš zahtjev je uspješno procesiran".
- **Nikad ne implicirati potvrđeno vrijeme termina** ni na jednom koraku dok ga osoblje stvarno ne potvrdi telefonom — ovo pravilo važi za SVAKI tekst na stranici, ne samo korak 3.
- **Kvačica pristanka je jedina obavezna saglasnost** — nema drugih checkboxova (newsletter, marketing i sl.) osim ako se posebno zatraži.

## Šta NIJE u obimu ovog mokapa (ne graditi, ne pretpostavljati)

- Izbor doktora ili usluge — rješava se u ordinaciji.
- Grid slobodnih termina / izbor tačnog vremena.
- Login/nalog pacijenta.
- Instant potvrda vremena termina.
- Bilo koji zdravstveni podatak (dijagnoza, simptomi, JMBG, broj zdravstvene knjižice).
- Stvaran backend (slanje zahtjeva, email potvrda, token generisanje) — ovo je samo vizuelni mokap/frontend, backend je poseban budući zadatak (Faza 1, HIGH risk — token generisanje ide kroz Claude prema CLAUDE.md ulogama).

## Provjera prije nego se mokap smatra gotovim

- [ ] Tri koraka: Datum → Vaši podaci → Potvrda (ne četiri, ne pet)
- [ ] Nema koraka/polja za uslugu ni doktora
- [ ] Nema grida termina, samo kalendar datuma
- [ ] Ime i telefon obavezni (`*`), email jasno opciono
- [ ] Nema polja za napomenu/slobodan tekst nigdje na formi
- [ ] Kvačica pristanka postoji, nije pre-čekirana, link na privacy obavještenje radi
- [ ] Korak 3 naslov/podnaslov je "ZAHTJEV PRIMLJEN!" / "Datum je rezervisan, javićemo vam se..." — NE jezik potvrđene rezervacije
- [ ] Nigdje na stranici ne piše da je tačno vrijeme potvrđeno
- [ ] Kalendar prikazuje svih 7 kolona (Pon–Ned), nedjelja vidljiva ali onemogućena, samo dva vizuelna stanja (dostupno/onemogućeno) sa legendom
- [ ] Klik na dostupan datum odmah prebacuje na Korak 2 (nema "Nastavi" dugmeta na Koraku 1)
- [ ] Header: pun meni + telefon na desktopu, telefon na mobilnom — ALI nigdje "Login" dugme ili bilo šta što implicira nalog pacijenta
- [ ] Mobilni prikaz (< ~768px) pokazuje samo trenutni korak, ne sve tri kolone uporedo
