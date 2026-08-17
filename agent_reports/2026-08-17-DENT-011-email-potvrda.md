---
task_id: DENT-011
risk: MEDIUM
implementer: pi
reviewers: [claude]
verdict: PASS
commits: []
created_at: 2026-08-17
---

# DENT-011 — Email potvrda pacijentu pri slanju javnog zahtjeva

## Task Contract

Pun tekst u `agent_reports/DENT-011-task-contract.md`. Suština: best-effort
email potvrda preko `smtplib`, sadržaj ograničen na ime ordinacije + traženi
datum + poruka o naknadnom kontaktu (minimizacija), SMTP kredencijali
isključivo iz env varijabli, greška pri slanju NE ruši booking zahtjev.

## Šta je urađeno

Iz implementer izvještaja (`agent_reports/DENT-011-implementer-report.md`),
provjereno protiv koda:

- `backend/notifications.py` (novi) — `send_booking_confirmation()` javna
  funkcija hvata `Exception` na najvišem nivou i loguje (best-effort),
  `_send()` preskače bez greške ako email prazan ili `DENTALAND_SMTP_HOST`
  nije postavljen, `_compose_message()` sadrži SAMO ime ordinacije + datum
  + poruku o kontaktu — nema `service`/`doctor` parametra u signaturi (pa
  curenje tih podataka nije ni moguće kroz ovu funkciju, ne samo
  "trenutno se ne šalju").
- `backend/main.py` — jedan poziv `send_booking_confirmation(...)` odmah
  poslije `create_request(...)`, uz komentar da je best-effort.
- Testovi: 6 u `test_notifications.py` (preskakanje bez emaila/SMTP-a,
  uspješno slanje sa mock `smtplib.SMTP`, sadržaj poruke, SMTP
  konekcija/`send_message` greška ne propagira), 1 u `test_backend.py`
  (POST sa emailom i pukim SMTP-om i dalje vraća 201).

## Verifikacija

Nezavisno ponovljeno (ne samo implementerova tvrdnja):

```
pytest tests/ -q
77 passed, 6 warnings in 3.23s

ruff check backend tests
All checks passed!

mypy src/dentaland desktop backend
Found 8 errors in 3 files (checked 16 source files)
— identično baseline-u, nula novih grešaka iz ove izmjene.
```

Ručna provjera loga: `grep -n "SMTP_PASSWORD\|logger\." backend/notifications.py`
— `logger.*` pozivi ne referenciraju `password`/`user`/`from_addr`
promjenljive, samo statične poruke + `exc` (SMTP biblioteka greške
tipično ne uključuju lozinku u tekstu, npr. `SMTPAuthenticationError`
vraća server-ov (kod, poruka) par).

## Review

```yaml
verdict: PASS
scope: PASS
acceptance: PASS
architecture: PASS
security: PASS
blocking_findings: []
```

Minimizacija je osigurana na nivou funkcije potpisa (`_compose_message`
ne prima `service`/`doctor`), ne samo konvencijom — jača garancija nego
"trenutno se ne koristi". Best-effort princip ispravno implementiran:
top-level `try/except Exception` u javnoj funkciji, `backend/main.py`
poziva NAKON uspješnog upisa u bazu, tako da booking zahtjev ostaje
primljen bez obzira na SMTP ishod. Kredencijali isključivo iz env
varijabli, bez hardkodovanih vrijednosti u kodu ili testovima (testovi
koriste `unittest.mock` na `smtplib.SMTP`, ne pravi SMTP nalog).

Non-blocking napomena (ne blokira merge): slanje emaila je sinhrono u
request handleru (`smtplib` SMTP konekcija, timeout 10s) — dodaje
latenciju POST odgovoru kad je SMTP konfigurisan i spor. Za obim jedne
ordinacije uz `slowapi` rate limit 10/min ovo je prihvatljivo
(CLAUDE.md — proporcionalna jednostavnost), ali vrijedi zapamtiti ako se
ikad doda drugi kanal (Viber, Faza 2) da async/queue pristup postane
razmatran, ne prije stvarne potrebe.

## Integration status

NOT_MERGED — čeka human approval (Radovan) prije merge-a u `main`.
