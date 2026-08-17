# Implementer izveštaj — DENT-011

Task: DENT-011 | Risk: MEDIUM | Implementer: pi | Status: IMPLEMENTED (čeka review)

## Šta je urađeno

- `backend/notifications.py` (novi fajl) — `send_booking_confirmation(to_email, requested_date)`:
  - best-effort slanje preko `smtplib` (stdlib, bez nove zavisnosti);
  - SMTP postavke isključivo iz env varijabli (`DENTALAND_SMTP_HOST`, `_PORT`,
    `_USER`, `_PASSWORD`, `_FROM`); bez `DENTALAND_SMTP_HOST` → preskače i loguje;
  - javna funkcija hvata svaki `Exception` i loguje ga — nikad ne propagira;
  - sadržaj poruke: SAMO ime ordinacije (`Dentaland`), `requested_date`
    (ISO format) i poruka o naknadnom kontaktu. Nema usluge ni doktora.
- `backend/main.py` — poziv `send_booking_confirmation(payload.email, payload.requested_date)`
  u `submit_booking_request` POSLIJE `create_request` (zahtjev je već u bazi).
- `tests/test_notifications.py` (novi) — 6 testova: preskakanje bez emaila,
  preskakanje bez SMTP konfiguracije, uspješno slanje (mock `smtplib.SMTP`),
  sadržaj poruke (minimizacija), SMTP konekcija greška ne baca, send_message greška ne baca.
- `tests/test_backend.py` — 1 novi test: POST sa emailom ne pada kad SMTP pukne (i dalje 201).

## Verifikacija (execution-based)

- `pytest tests/test_notifications.py tests/test_backend.py -v` → **16 passed**
- `pytest tests/ -q` → **77 passed**
- `ruff check backend tests` → **All checks passed**

## Napomene za reviewera (security focus)

- Kredencijali se NIGDJE ne loguju: log zapisi sadrže samo razlog preskakanja
  ili poruku o neuspjehu, nikad `DENTALAND_SMTP_PASSWORD`/`_USER`/`_FROM`.
- Email adresa pacijenta se ne loguje (samo činjenica da je poruka poslata).
- Sadržaj emaila ne pominje uslugu ni doktora — `_compose_message` uopšte ne
  prima te podatke, pa je pravilo osigurano na nivou signature + test.
- Rate limiter u test procesu je globalan — novi submit-test je namjerno stavljen
  PRIJE `test_rate_limit_na_submit_endpointu` da ne poremeti brojanje.

## Dirnuti fajlovi (svi u allowed_paths)

- `backend/main.py` (mod)
- `backend/notifications.py` (nov)
- `tests/test_backend.py` (mod)
- `tests/test_notifications.py` (nov)
