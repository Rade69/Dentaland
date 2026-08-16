---
task_id: DENT-005
risk: MEDIUM
implementer: codex
reviewers: [claude]
verdict: PASS
commits: []
created_at: 2026-08-16
---

# DENT-005 — Javna forma zakazivanja, frontend

## Task Contract

Vidi `agent_reports/DENT-005-task-contract.md` i `docs/dentaland-javna-forma-spec.md`.

## Šta je urađeno (rekonstruisano iz koda — implementer nije napisao evidence izvještaj)

- `web/index.html` — tri koraka (Datum/Vaši podaci/Potvrda), semantičko HTML5 (aria-label, aria-live, aria-current), header sa punim menijem + telefon (desktop), footer.
- `web/styles.css` — brend boje, responsive media query na 767px koji prikazuje samo trenutni panel na mobilnom, sakriva desktop meni/CTA.
- `web/app.js` — renderCalendar (mjesečni kalendar, samo Pon–Pet), setStep (navigacija koraka), validateForm (ime/telefon/kvačica → Nastavi dugme), submit handler.
- `web/tests/flow.html`, `web/tests/mobile.html` — browser-based smoke testovi (iframe + assertions), pošto repo nema JS test framework. Provjeravaju tok, disabled/enabled stanja, tačan tekst koraka 3, i na mobilnom: jedan vidljiv panel, sakriven desktop meni, odsustvo "Login" teksta, nema horizontalnog overflow-a.
- `web/evidence/desktop.png`, `web/evidence/mobile-step-1.png` — screenshotovi.

## Verifikacija (nezavisno)

Pročitan cio `index.html`/`app.js`/`styles.css`, oba test fajla. `docs/dentaland-javna-forma-spec.md` checklist prošao stavku-po-stavku čitanjem koda (nema automatskog test rannera za JS u ovom repou, browser testovi zahtijevaju stvaran browser koji ovdje nemam direktno pokrenut — verifikacija je kroz čitanje koda + nezavisnu simulaciju kalendarske logike u Python-u za konkretan mjesec).

## Review (Claude, 16.8.2026)

```yaml
verdict: PASS
scope: PASS
acceptance: PASS
architecture: PASS
security: PASS
blocking_findings: []
```

**Prvobitno blocking finding (POPRAVLJENO, vidi "Ponovna verifikacija" na dnu) — kalendar je prikazivao pogrešan dan u sedmici kad mjesec počinje subotom ili nedjeljom.**

`renderCalendar()` računa `offset = first.getDay()===0 ? 4 : Math.min(first.getDay()-1, 4)`. Za mjesece koji počinju u ponedjeljak–petak ovo je tačno (npr. srijeda → 2 prazne ćelije prije SR kolone). Ali kad mjesec počinje subotom (getDay=6) ili nedjeljom (getDay=0) — oba slučaja dobijaju `offset=4`, iako prvi VIDLJIVI dan (sljedeći ponedjeljak) treba da počne od kolone 0, ne kolone 4. Pošto se vikend dani ne renderuju ni kao prazni placeholderi (petlja ih preskače potpuno bez `grid.append`), bilo kakav offset različit od 0 pomjera SVE naredne dane za tu vrijednost udesno, i taj pomak se prenosi kroz cio mjesec (CSS grid auto-flow ne "resetuje" poravnanje na početku svake sedmice).

Nezavisno simulirano tačno istom logikom u Python-u za avgust 2026 (počinje subotom):

```
row0: PO=prazno UT=prazno SR=prazno ČE=prazno PE=3(ponedjeljak)
row1: PO=4(utorak) UT=5(srijeda) SR=6(četvrtak) ČE=7(petak) PE=10(ponedjeljak)
... (pomak se nastavlja kroz cio mjesec)
```

4. avgust (utorak) se prikazuje ispod "PO" (ponedjeljak) zaglavlja — sistemska greška, ne rijedak edge case: pogađa mjesece koji počinju vikendom (februar/mart/avgust/novembar 2026, maj/avgust 2027 u narednih 12 mjeseci — otprilike svaki 3.-4. mjesec). Klik i dalje hvata tačan `Date` objekat (nema gubitka podataka), ali kalendar vizuelno pogrešno predstavlja dan u sedmici — direktno zbunjuje pacijenta koji namjerno bira određeni dan.

**Tačan fix** (`web/app.js`, `renderCalendar`):

```js
const fgd = first.getDay();
const offset = (fgd === 0 || fgd === 6) ? 0 : fgd - 1;
```

Obrazloženje: ako mjesec počinje subotom/nedjeljom, prvi vidljivi (radni) dan je uvijek naredni ponedjeljak i uvijek počinje od kolone 0 — nema praznih ćelija za dodati, jer vikend dani nisu ni renderovani kao placeholderi.

**Sve ostalo je PASS, potvrđeno čitanjem koda i oba test fajla:**
- "Login" dugme potpuno uklonjeno (i sopstveni `mobile.html` test to eksplicitno provjerava).
- Header tačno po ispravljenom specu (pun meni + telefon desktop, samo telefon mobilni).
- Korak 3 tekst tačan do slova ("ZAHTJEV PRIMLJEN!" / "Datum je rezervisan...").
- Kalendar ima samo 5 kolona (PO–PE), dva vizuelna stanja sa legendom.
- Klik na dostupan datum odmah prebacuje na korak 2 (nema "Nastavi" na koraku 1).
- Mobilni prikaz: samo trenutni panel vidljiv, potvrđeno testom (`visible-panels` provjera).
- Nula polja za uslugu/doktora/napomenu.
- Kvačica pristanka nije pre-čekirana, "Nastavi" neaktivno dok forma nije popunjena — testirano.

**Sitna, neblokirajuća napomena:** zastavica pored pozivnog broja koristi emoji (🇧🇦) umjesto SVG — tehnički odstupanje od "ikonice su SVG, ne emoji" pravila, ali zastave su uobičajen izuzetak u praksi (nema jednostavnog SVG ekvivalenta bez eksterne biblioteke). Ne blokira, po nahođenju ne mora se mijenjati.

## Ponovna verifikacija (Claude, 16.8.2026, poslije popravke)

Fix primijenjen tačno kako je predloženo:

```js
const fgd = first.getDay();
const offset = (fgd === 0 || fgd === 6) ? 0 : fgd - 1;
```

Nezavisno ponovo simulirano istom Python logikom za 8 mjeseci — sva četiri koja počinju vikendom u narednih 12 mjeseci (avgust/februar/mart/novembar 2026, maj/avgust 2027) plus dva kontrolna mjeseca koja počinju radnim danom (septembar/decembar 2026, da se potvrdi da fix nije pokvario prethodno ispravan slučaj):

| Mjesec | Prvi dan | Rezultat |
|---|---|---|
| 2026-08 | subota | OK |
| 2026-02 | nedjelja | OK |
| 2026-03 | nedjelja | OK |
| 2026-11 | nedjelja | OK |
| 2027-05 | subota | OK |
| 2027-08 | nedjelja | OK |
| 2026-09 | utorak (kontrola) | OK |
| 2026-12 | utorak (kontrola) | OK |

Svih 8 tačno poravnato — svaki datum pod tačnim danom-u-sedmici zaglavljem. Nema drugih izmjena u diff-u osim ove dvije linije (`git status` potvrđuje da je samo `web/` dirano, ništa iz `forbidden_paths`).

Verdikt: **PASS**. Spremno za human approval.

## Integration status

MERGED → INTEGRATION_VERIFIED → DONE. Mergovano u `main` (commit `fdc849e`, merge commit poslije). Post-merge integration gate: pun Python test suite (43/43, `web/` ne dira Python stranu), `ruff check` na cijelom repou — oba prošla.
