---
task_id: DENT-011
risk: MEDIUM
implementer: pi
reviewer: claude
status: ASSIGNED
created_at: 2026-08-17
---

# Task Contract — DENT-011

Porijeklo: `docs/dentaland-razvojni-plan.md` v1 plan, sekcija "Javna
strana" — "Email potvrda pacijentu (SMTP / SendGrid)".

```yaml
id: DENT-011
title: Email potvrda pacijentu pri slanju javnog zahtjeva
risk: MEDIUM
objective: >
  Kad pacijent pošalje zahtjev preko javne forme (DENT-005/007) I unio je
  email (opciono polje), poslati kratku potvrdu da je zahtjev primljen.
  Sadržaj emaila SMIJE sadržati samo: ime ordinacije, traženi datum
  (requested_date), i tekst da će ih ordinacija kontaktirati sa tačnim
  vremenom — NIKAD naziv usluge ili doktora (oboje su u ovom trenutku i
  dalje nepoznati, PENDING zahtjev ih nema — ali pravilo važi i za buduće
  slično kod potvrde termina: minimizacija podataka u porukama je
  arhitekturno pravilo iz CLAUDE.md, ne samo trenutna nužnost).

  Implementacija: nova funkcija koja komponuje i šalje email preko SMTP-a
  (`smtplib`, stdlib — ne dodavati eksternu zavisnost za ovo dok se ne
  pokaže potreba). SMTP host/port/korisnik/lozinka/from-adresa dolaze iz
  env varijabli (npr. `DENTALAND_SMTP_HOST` itd.) — NEMA pravih kredencijala
  u kodu niti u testovima. Ako env varijable nisu postavljene (lokalni
  razvoj/testiranje bez pravog SMTP naloga), funkcija preskače slanje i
  loguje razlog — NE baca grešku koja bi srušila cio booking zahtjev.

  Ako pacijent NIJE unio email (polje je opciono), preskoči slanje bez
  greške — nema šta da se pošalje, ovo nije bug.

  Pozvati ovu funkciju iz `backend/main.py` (`submit_booking_request`)
  POSLIJE uspješnog upisa zahtjeva u bazu — slanje emaila je "best effort":
  ako slanje ne uspije (loš SMTP, mrežna greška), zahtjev OSTAJE uspješno
  primljen (već je u bazi), endpoint i dalje vraća 201, samo se greška
  loguje. Booking tok se nikad ne smije srušiti zbog email problema.
allowed_paths: [backend/main.py, backend/notifications.py, tests/test_backend.py, tests/test_notifications.py, agent_reports/**]
forbidden_paths: [desktop/**, src/dentaland/services/booking.py, src/dentaland/services/requests.py, src/dentaland/models.py, migrations/**, web/**, CLAUDE.md, AGENTS.md, docs/**]
acceptance:
  - Email se šalje samo ako je pacijent unio email adresu.
  - Sadržaj emaila ne pominje uslugu ni doktora — samo naziv ordinacije, traženi datum, i poruku o naknadnom kontaktu.
  - SMTP kredencijali dolaze isključivo iz env varijabli, nikad hardkodovani.
  - Nedostatak SMTP konfiguracije (lokalni razvoj) ne baca grešku — samo se ne šalje, sa jasnim log zapisom.
  - Neuspješno slanje emaila (SMTP greška) NE ruši booking zahtjev — POST /api/booking-requests i dalje vraća 201.
  - Testovi koriste mock/fake SMTP (npr. patch na smtplib.SMTP) — nema pravih kredencijala niti pravog slanja u testovima.
verification:
  - pytest tests/test_notifications.py tests/test_backend.py -v
  - pytest tests/ -q
  - ruff check backend tests
review:
  reviewers: 1
  required: [security, scope]
```

## Napomena

`security` je u obaveznim review fokusima jer ovo rukuje email adresama
(lični podaci) i SMTP kredencijalima (čak i ako dolaze iz env varijabli,
provjeriti da se nigdje ne loguju u plain textu, npr. u error porukama).
