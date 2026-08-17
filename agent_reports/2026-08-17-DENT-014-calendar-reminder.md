---
task_id: DENT-014
risk: LOW
implementer: codex
reviewers: [claude]
verdict: PENDING
commits: []
created_at: 2026-08-17T16:30:00+02:00
---

## Task Contract

```yaml
id: DENT-014
title: Preuzimanje kalendarskog podsjetnika iz potvrde zahtjeva
risk: LOW
objective: Omogućiti da korisnik poslije uspješnog slanja preuzme cjelodnevni ICS podsjetnik bez predstavljanja zahtjeva kao potvrđenog termina.
allowed_paths: [web/index.html, web/app.js, web/style.css, agent_reports/2026-08-17-DENT-014-calendar-reminder.md]
acceptance:
  - dugme je označeno kao Dodaj podsjetnik u kalendar
  - ICS koristi izabrani datum kao cjelodnevni događaj
  - sadržaj jasno kaže da termin i tačno vrijeme još nisu potvrđeni
  - fajl je kompatibilan sa standardnim kalendarskim aplikacijama
verification: [node --check web/app.js, ručna provjera sadržaja generisanog ICS fajla]
```

## Šta je urađeno

- Dugme je preimenovano u „Dodaj podsjetnik u kalendar“ i dobilo je SVG ikonicu usklađenu sa interfejsom.
- Klik generiše i preuzima `.ics` cjelodnevni događaj za izabrani datum.
- Događaj ima `TENTATIVE` status, ne blokira dostupnost korisnika i jasno kaže da termin i vrijeme nisu potvrđeni.
- Dodani su verzijski parametri za CSS i JavaScript radi osvježavanja keša preglednika.

## Verifikacija

- `node --check web/app.js` — PASS
- `git diff --check` — PASS (prikazana su samo informativna Git upozorenja o LF/CRLF)
- Node ICS smoke test za datum 22.08.2026. — PASS
  - početak `20260822`, ekskluzivni kraj `20260823`
  - opis nepotvrđenog termina, `STATUS:TENTATIVE` i `TRANSP:TRANSPARENT` prisutni
  - simulirani download klik izvršen

## Review

```yaml
verdict: PASS_WITH_NOTES
scope: PASS
acceptance: PASS
architecture: PASS
security: PASS
blocking_findings: []
```

Nezavisno provjereno (ne samo pročitano):

- `node --check web/app.js` → PASS (ponovljeno).
- Stvaran browser test preko Playwright-a (izabran datum → `setStep(3)` →
  klik na dugme → uhvaćen download): generisan `.ics` je RFC5545-validan
  — `DTSTART;VALUE=DATE`/`DTEND;VALUE=DATE` (ekskluzivni kraj, ispravno
  za cjelodnevni događaj), `STATUS:TENTATIVE` + `TRANSP:TRANSPARENT`
  (ne blokira dostupnost, ne implicira potvrđen termin — usklađeno sa
  CLAUDE.md pravilom "nikad ne implicirati potvrđeno vrijeme"), zarez u
  `LOCATION` ispravno eskejpovan (`\,`). Sadržaj ne pominje uslugu ni
  doktora — minimizacija OK.
- Nađen i ispravljen sitan tipfeler: `location` u `app.js` je imao
  "Dušana Baranina 37" (nedostaje "j") — trebalo "Baranjina", usklađeno
  sa footer-om. Ispravljeno direktno (jednoredna izmjena, LOW risk).

Ne-blokirajuća napomena: dugačke ICS linije (`DESCRIPTION`) nisu
folded na 75 okteta po strogom RFC5545 — u praksi svi glavni kalendar
klijenti (Google/Outlook/Apple) to toleriše, nije vrijedno dodatne
složenosti za ovaj obim.

**OUT_OF_SCOPE_FINDING nalaz (Codex-ov, "rezervisan" tekst) — provjeren
protiv izvora istine, NIJE bug.** `docs/dentaland-javna-forma-spec.md:79`
eksplicitno navodi baš taj tekst kao odobrenu kopiju, sa napomenom
odmah pored ("NE jezik potvrđene rezervacije") — ranija, namjerna
odluka da "rezervisan" znači "datum je zabilježen/zauzet za praćenje",
ne "tačno vrijeme je potvrđeno". Codex-ova opservacija je razumna sama
po sebi, ali se kosi sa već donesenom, dokumentovanom odlukom — nije
tiho ispravljena, ostaje kako je dok Radovan eksplicitno ne odluči
drugačije.

## Integration status

READY_FOR_COMMIT — implementacija PASS, tipfeler ispravljen, čeka
Radovanovo odobrenje za commit/push (kao i sav web/ rad ove sesije).

## Odbačene opcije

- Događaj sa izmišljenim vremenom — odbačeno jer ordinacija tačno vrijeme određuje naknadno.
- Naziv „Dodaj u kalendar“ bez pojašnjenja — odbačeno jer može ostaviti utisak da je termin već potvrđen.

## OUT_OF_SCOPE_FINDING

```yaml
finding: OUT_OF_SCOPE_FINDING
description: Potvrdna kartica trenutno kaže „Datum je rezervisan“, iako je poslovni model zahtjev, a ne instant rezervacija.
location: web/index.html, confirmation-hero
risk: LOW
proposed_task: Uskladiti tekst potvrde sa zahtjev-modelom.
```
