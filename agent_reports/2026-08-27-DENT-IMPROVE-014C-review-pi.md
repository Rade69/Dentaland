---
task_id: DENT-IMPROVE-014C
risk: HIGH
reviewer: pi
role: Reviewer 2 (arhitektura/scope + nezavisna reprodukcija)
verdict: PASS_WITH_NOTES
date: 2026-08-27
---

# DENT-IMPROVE-014C — Pi nezavisan review (audit: CRUD termina)

Nezavisan pregled, izveden od nule — nisam čitao Codex rezonovanje prije
sopstvene provjere. Svi ključni nalazi **reprodukovani uživo**, ne preuzeti
iz izvještaja. (Napomena o atribuciji: potvrđeno — kod je zadržan i
nezavisno verifikovan, ali moj review je neutralan prema tome ko ga je
pisao; ocjenjujem sam kod.)

## Obim / scope — PROLAZI

- **Jedine izmjene: `src/dentaland/services/appointments.py` (4 funkcije)
  + novi `tests/test_audit_appointments.py`.** Potvrđeno `git status`.
- **Sve 4 operacije instrumentisane** na jedinoj zajedničkoj tački
  (servisni sloj `appointments.py`), ne u `booking.py` fasadi niti u
  desktop kontrolerima — ispravno, pokriva sav stvaran saobraćaj.

## Forbidden paths — PROLAZI

`git diff HEAD` za sve zaštitne putanje → **prazan**:

- `src/dentaland/models.py`, `src/dentaland/services/audit.py` (jezgro),
  `src/dentaland/services/auth.py` — netaknuti
- `backend/main.py` — netaknut
- `desktop/**`, `web/**` — netaknuti
- `migrations/**` — netaknuti

**Zaključak:** jezgro iz DENT-IMPROVE-014 je SAMO pozivano (preko
`write_audit_event`), nikad izmijenjeno. Forbidden paths strogo ispoštovani.

## Atomski `session=session` — NEZAVISNO REPRODUKOVAN ZA SVE 4 (ključno)

Ovo je najvažnija tačka. Trajni test pokriva samo `create_appointment`,
pa sam **nezavisno replicirao fault-injekciju (`write_audit_event` puca
NAKON realnog upisa) za svaku od 4 operacije** u svojoj probi:

```
create:  RuntimeError paco (ispravno)
update:  RuntimeError paco (ispravno)
cancel:  RuntimeError paco (ispravno)
delete:  RuntimeError paco (ispravno)
Appointments na kraju: 1 (treba 1)   <- originalni termin ostaje
AuditEvent na kraju:  1 (treba 1)   <- samo originalni CREATE audit
```

**Zaključak:** `write_audit_event(..., session=session)` STVARNO dijeli
transakciju sa poslovnom izmjenom u sve 4 funkcije — rollback povlači i
termin i audit red, bez izuzetka. **Dokazano za cijeli set, ne samo za
create.** Posebno važno za `delete` (objekat već `session.delete()`-ovan)
— potvrđeno da i tamo radi atomski.

## Pojedinačne provjere (tražene)

- **`create_appointment` `session.flush()` — NECEPHODAN i ispravan.**
  Bez njega `appt.id` bi bio `None` pre audit poziva (SQLAlchemy dodeljuje
  PK pri flush/insert, ne pri `session.add`), pa bi `resource_id=None`
  upisao u audit. Flush je stavljen NAKON `session.add(appt)`, u istoj
  transakciji. Ispravno.
- **`delete_appointment` koristi ulazni `appt_id` — ispravno.** Objekat je
  već `session.delete(appt)`-ovan (temp pending state), pa za audit
  treba **izdvojeni ulazni `appt_id`**, ne `appt.id`. Korišten
  `resource_id=appt_id`. Ispravno — i potvrđeno da radi atomski.
- **`UPDATE_APPOINTMENT` `metadata=None` — ispravno + potvrđeno da ne
  mijenja status.** Pročitao sam punu `update_appointment`: postavlja
  `ime/telefon/email/doctor_id/service_id/napomena/start/end`, **nikad
  `status`** (funkcija zahtijeva `status == SCHEDULED` i ne postavlja
  novi). Zato bi `old_status`/`new_status` bili konstantni
  (`SCHEDULED`/`SCHEDULED`) — nula vrijednosti. Odluka tačna i dobro
  obrazložena.
- **`metadata_minimal` bez PII — potvrđeno.** Grep diff-a:
  `metadata=` nigdje nije proslijeđen (default `None`), a PII polja
  (`patient_name`/`.ime`/`telefon`/`email`/`napomena`) se NE prosljeđuju
  u audit poziv. Jedini grep pogodak `appt.napomena = note` je poslovna
  izmjena polja, ne audit prosleđivanje. Potvrđeno testom
  (`test_metadata_minimal_ne_sadrzi_licne_podatke`).

## Standardni gateovi (reprodukovano)

- `pytest tests/ -q` → **419 passed, 2 skipped** (potvrđeno, ne preuzeto)
- `ruff check src/dentaland desktop backend tests scripts/agent_sensors.py` → **All checks passed**
- `mypy src/dentaland desktop backend` → **54 fajla, 0 grešaka**
- `python scripts/agent_sensors.py --all` → **0 blocking findings**

## Nalazi

- **N1 (non-blocking, sugestija — slažem se sa Codexom, ne insistiram):**
  Trajni failure-path test pokriva samo `create_appointment`. Ja sam
  nezavisno potvrdio da je kod atomski u sve 4, ali **trajni test ne štiti
  od buduće lokalne greške samo u UPDATE/CANCEL/DELETE pozivu** (npr. ako
  neko slučajno izbaci `session=session` iz jednog od njih). Preporuka:
  **jedan parametrizovan/spy test** koji za sva 4 pozivna mjesta potvrđuje
  da je proslijeđen isti ORM `session` — jeftin, štiti sva četiri bez
  dupliranja četiri failure-path testa. Slažem se da 4 duplirana
  failure-path testa nisu potrebna sada; ovo je čisto inkrementalna
  zaštita, ne blokira.
- **N2 (informativno):** `actor_user_id=NULL` u sve 4 (desktop nema login)
  — prihvaćeno ograničenje, ispoštovano bez izmišljanja lažnog actor-a.
  Usklađeno sa Radovanovom odlukom i 014B/014C kontraktima.

## Verdict: PASS_WITH_NOTES

Kod je arhitektonski čist i minimalan — 4 ciljana poziva `write_audit_event`
u servisnom sloju, atomski sa poslovnom izmjenom (nezavisno dokazano za sve
4), bez izmjene jezgra (samo poziv), svi forbidden paths netaknuti,
`metadata=None` bez PII, `actor_user_id=NULL` ispravan. Sve 4 pozivne tačke
su na jedinom zajedničkom mjestu i rade ispravno. Nema blokirajućih nalaza.

Jedina sugestija (N1) — jedan parametrizovan `session`-spy test za sve 4
umjesto samo create — je inkrementalna zaštita, ne pošto je implementacija
dokazano ispravna. Nije blokirajuća ni za mene ni za approval.
