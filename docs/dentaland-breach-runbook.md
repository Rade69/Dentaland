# Dentaland — breach runbook (DENT-IMPROVE-016)

Šta raditi ako se posumnja ili potvrdi povreda ličnih podataka
(neovlašten pristup, curenje, gubitak, izmjena bez ovlaštenja) u
Dentaland sistemu. Ovaj dokument je operativan — koraci, rokovi,
kontakti — ne pravna analiza.

**Pravni osnov roka:** Zakon o zaštiti ličnih podataka BiH (Sl. glasnik
BiH 12/25, na snazi od 4.10.2025) — 72h rok prijave Agenciji je obavezan
za sve obrađivače, bez obzira na veličinu (vidi CLAUDE.md, "Sigurnost i
privatnost"). Ovaj rok se NE pregovara i NE čeka internu istragu do kraja
— prijava ide sa onim što se zna u tom trenutku, dopunjuje se kasnije.

## 1. Detekcija

Povreda može biti prijavljena/uočena kroz:

- neuobičajenu aktivnost u `audit_events` (npr. masovan pristup podacima
  van radnog vremena, ponovljeni neuspjeli login pokušaji —
  `LOGIN_FAILURE` zapisi, DENT-IMPROVE-014B),
- prijavu trećeg lica (pacijent, hosting provider, sigurnosni istraživač),
  ili
- sopstveno otkriće tokom rada/održavanja (npr. slučajno izloženi
  backup, kompromitovan kredencijal).

**Prvi korak čim se posumnja: zabilježi TAČNO vrijeme otkrića** — od
njega teče 72h rok, ne od trenutka kad je incident stvarno počeo.

## 2. Containment (zaustavi širenje)

Redoslijed prioriteta — zaustaviti aktivan pristup prije istrage detalja:

1. Ako je kompromitovan kredencijal (lozinka, token) — odmah ga
   poništi/rotiraj. Tokeni za javne linkove (cancel link) su
   jednokratni i imaju `expires_at` (CLAUDE.md) — ako je token curio,
   provjeri da li je već iskorišten/istekao.
2. Ako je kompromitovan pristup serveru/bazi — promijeni lozinke
   pogođenih naloga (`dentaland_app`, `postgres` superuser, SMTP
   kredencijali).
3. Ako je izvor aktivan API endpoint (npr. eksploatisana ranjivost) —
   po potrebi privremeno onemogući javnu formu dok se ne zakrpi.
4. NE brisati logove/audit zapise koji dokumentuju šta se desilo — to
   otežava i istragu i dokazivanje da je incident obrađen odgovorno.

## 3. Procjena — da li je ovo "povreda ličnih podataka"?

Povreda ličnih podataka = bezbjednosni incident koji dovodi do
slučajnog ili nezakonitog uništenja, gubitka, izmjene, neovlaštenog
otkrivanja ili pristupa ličnim podacima.

Pitanja za procjenu:

- Koji podaci su pogođeni? (ime/telefon/email iz booking zahtjeva —
  vidi `web/privacy.html` sekcija 2 za pun spisak onoga što sistem
  prikuplja; **medicinska dokumentacija nikad nije u sistemu** —
  ostaje na papiru kod ordinacije, van ovog rizika)
- Koliko lica je pogođeno?
- Da li je pristup stvarno ostvaren, ili je propust postojao ali bez
  dokaza pristupa? (i dalje se prijavljuje ako je rizik realan, ne samo
  ako je zloupotreba dokazana)
- Da li je rizik za prava i slobode lica visok? (relevantno za odluku o
  direktnom obavještavanju pacijenata — vidi korak 5)

Ako je odgovor "da, lični podaci su pogođeni" na bilo koje pitanje —
tretiraj kao povredu i idi na korak 4, čak i dok procjena obima traje.

## 4. Prijava Agenciji za zaštitu ličnih podataka BiH (rok: 72h)

Kontakt (isti kao u `web/privacy.html` sekcija 9):

- Agencija za zaštitu ličnih podataka u Bosni i Hercegovini
- Dubrovačka broj 6, 71000 Sarajevo
- [azlp.ba](https://azlp.ba/)

Prijava treba sadržavati (dopuni kasnije ako se ne zna sve odmah — rok
se ne čeka radi potpunosti):

- prirodu povrede (šta se desilo, koje kategorije podataka, približan
  broj pogođenih lica),
- kontakt osobu za dalja pitanja (ordinacija),
- vjerovatne posljedice,
- preduzete/planirane mjere za ublažavanje.

## 5. Obavještavanje pogođenih pacijenata (kad je rizik visok)

Ako povreda vjerovatno dovodi do visokog rizika za prava pacijenata
(npr. curenje kontakt podataka spojeno sa dodatnim kontekstom koji
otkriva da su nečiji pacijent stomatologa), obavijesti ih direktno —
jasnim jezikom, bez tehničkog žargona: šta se desilo, koji podaci,
preporučene mjere opreza (npr. oprez sa sumnjivim pozivima/porukama),
kontakt za pitanja.

Kontakt kanal: telefon/email iz `web/privacy.html` (`+387 66 615 326`,
`info@dentaland.org`), isti kanal koji pacijenti već poznaju sa forme za
zakazivanje.

## 6. Interna evidencija incidenta

Zakon zahtijeva evidenciju SVIH povreda, bez obzira da li su prijavljene
Agenciji (npr. i onih procijenjenih kao nizak rizik). Zapisati:

- datum/vrijeme otkrića i procijenjeno vrijeme same povrede,
- šta se desilo (kratak opis, tehnički uzrok kad je poznat),
- koji podaci/koliko lica pogođeno,
- preduzete mjere (containment, obavještavanje),
- da li je prijavljeno Agenciji i kada,
- da li su pacijenti obaviješteni i kada.

Čuvati ovu evidenciju odvojeno od `audit_events` (koji je operativan
audit log aplikacije, ne incident-evidencija) — npr. kao poseban
dokument/fajl van repozitorija (repo je javno vidljiv kroz git
istoriju, incident evidencija nije za to).

## 7. Post-incident pregled

Nakon što je incident zatvoren:

- Šta je omogućilo incident? (ranjivost, propust u procesu, ljudska
  greška)
- Da li postojeća arhitektura (rate limiting, RBAC, audit log, token
  sigurnost — vidi CLAUDE.md "Sigurnost i privatnost") pokriva ovaj
  scenario, ili treba dopuna?
- Ažurirati ovaj runbook ako je proces pokazao prazninu.

## Ko ovo koristi

Radovan (ownership/koordinacija) i osoblje ordinacije sa administrativnim
pristupom (Ljubo/Zorka/Ana ili recepcija, zavisno ko ima kredencijale).
Ne zahtijeva tehničko znanje za korake 3-6 — koraci 1-2 (containment)
najčešće zahtijevaju nekoga ko zna administrirati sistem.
