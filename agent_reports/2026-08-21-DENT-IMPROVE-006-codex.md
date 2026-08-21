---
task_id: DENT-IMPROVE-006
risk: LOW/MEDIUM
implementer: codex
reviewer: claude
status: "IMPLEMENTATION_COMPLETE / VERIFICATION_PENDING"
created_at: 2026-08-21
---

# DENT-IMPROVE-006 — Dedicated „Novi zahtjevi“ ekran

## Probni signal prije prve izmjene koda

- Pročitano prije prve code izmjene: **18 jedinstvenih fajlova** — 17
  projektnih fajlova i globalni `prime-feature/SKILL.md`.
- Korišten `.agent/PROJECT_MAP.md`: **DA** — sekcija „Public requests“ je
  odmah pokazala `requests_panel.py`, servisni kontekst i relevantne testove;
  „Desktop scheduler“ je pokazao `main_window.py`, sidebar i dialog putanju.
- Korišten `.agent/TASK_ROUTING.md`: **DA** — Desktop GUI paket je ograničio
  čitanje na relevantne view/dialog/test fajlove; nije bilo repo-wide
  `ls`/`find` istraživanja niti učitavanja backend/web/docs sadržaja.
- Traženo dodatno pojašnjenje strukture: **NE**.
- Allowed paths/scope: Task Contract nema eksplicitan `allowed_paths` YAML
  ključ. Operativni scope izveden je iz cilja i acceptancea te ograničen
  coordination claimom na requests/main-window/sidebar GUI, najbliže testove
  i ovaj izvještaj. Prije prve code izmjene nema scope prekršaja.

Otvoreni projektni fajlovi: `AGENTS.md`, `CLAUDE.md`, tri `.agent/` router
fajla, Task Contract, validaciona istorija, četiri ciljna GUI fajla, tri
najbliža GUI testa, `booking.py`, `requests.py` i GUI `conftest.py`.

## Planirani scope

- Dedicated requests page sa pending countom, imenom, kontaktom po potrebi,
  traženim datumom, vremenom kreiranja i dugmetom „Obradi“.
- Jedan zajednički helper za postojeći `ProcessRequestDialog` tok, koji
  koriste i `DashboardPanels` i nova stranica — bez dupliranja business
  logike.
- MainWindow ruta `zahtjevi` vodi na stvarnu stranicu; refresh nakon obrade
  osvježava i dashboard/sidebar/schedule postojeći tok.
- Testovi za prikaz, rutu, confirm/reject refresh i regresiju dashboarda.

Van scope-a: istorija zahtjeva, CRM, patient profile, analytics, schema,
backend/web i servisna poslovna pravila.

## Implementacija

- Dodan `desktop/views/requests_page.py` sa dedicated listom pending
  zahtjeva: count, ime, telefon/email samo kad postoje, traženi datum,
  lokalizovano vrijeme kreiranja i dugme „Obradi“.
- Ruta `zahtjevi` u `MainWindow` više nije `StubPage`; vodi na
  `RequestsPage` i osvježava je pri otvaranju i globalnom dashboard refreshu.
- Postojeći dialog/business tok iz `DashboardPanels._confirm` nije
  kopiran. Izdvojen je u jedan `process_pending_request()` helper koji i
  dashboard i dedicated page koriste za doctor/service izbor,
  confirm/reject, overlap grešku i ponavljanje dijaloga.
- Nakon uspješne potvrde ili odbijanja dedicated lista se osvježava i emituje
  `changed`, pa se osvježe dashboard panel, sidebar badge i schedule prikazi.
- Sačuvano je staro ponašanje dashboarda kada nema doktora/usluga i kada
  korisnik zatvori dijalog bez akcije.

## Testovi

- Novi `test_requests_page.py` provjerava count i sva tražena polja te da
  „Obradi“ koristi zajednički helper i uklanja obrađeni red nakon refresh-a.
- `test_main_window.py` potvrđuje da sidebar ruta vodi na stvarni
  `RequestsPage`.
- Postojeći dashboard/process-dialog testovi ostaju neizmijenjeni i prolaze,
  uključujući realni overlap → inline greška → reject tok.

## Verifikacija

```text
Headless Qt MainWindow smoke (ruta zahtjevi + stvarni page widget)
→ GUI_SMOKE_PASS, exit 0

pytest tests/ -q
→ 254 passed, 11 warnings, exit 0

ruff check src/dentaland desktop backend tests
→ All checks passed, exit 0

mypy src/dentaland desktop backend
→ Success: no issues found in 35 source files, exit 0

git diff --check
→ PASS, exit 0
```

Prvi standalone smoke pokušaj nije imao projektni `PYTHONPATH`, a drugi je
prošao assertions pa pao samo pri cp1252 ispisu slova `đ`; konačni smoke je
pokrenut sa projektnim `PYTHONPATH=src;.` i ASCII-only rezultatom te završio
exit 0. To su harness korekcije, ne skrivene aplikacijske greške.

## Scope rezultat

Izmijenjeni/dodani su samo claimovani GUI, GUI test i agent-report fajlovi:
`main_window.py`, `requests_panel.py`, novi `requests_page.py`,
`test_main_window.py`, novi `test_requests_page.py` i ovaj report.
`sidebar.py` i `ProcessRequestDialog` nisu morali biti mijenjani. Nijedan
backend/web/schema/service-business fajl nije dirnut.

## Review i integration

- Implementer review: nije rađen kao nezavisan review; urađen je samo
  implementacioni self-check/diff pregled.
- Nezavisna verifikacija: `PENDING` — korisnik radi review.
- Commit/merge: nisu urađeni.
- Integration status: `NOT_MERGED`.

## Handoff

CILJ: Zamijeniti sidebar stub stvarnim ekranom za pending online zahtjeve.

URAĐENO: Dedicated page koristi isti processing tok kao DashboardPanels,
prikazuje tražene podatke i osvježava cijeli relevantni UI nakon obrade;
automatska i headless GUI verifikacija prolaze.

NE DIRATI: Istoriju zahtjeva, CRM/profile/analytics i servisnu business
logiku bez novog Task Contracta.

SLJEDEĆE: Nezavisan korisnički/Claude review; tek nakon verdicta i human
approval-a slijede commit/merge/integration gate.
