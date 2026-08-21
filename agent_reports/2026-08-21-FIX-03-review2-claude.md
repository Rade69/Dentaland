---
task_id: FIX-03
reviewer: claude
risk: MEDIUM
verdict: REJECT
date: 2026-08-21
---

# Review #2 — FIX-03 (popravka nakon prvog REJECT-a)

```yaml
verdict: REJECT
scope: PASS
acceptance: PASS (vizuelna popravka je stvarna i ispravna)
architecture: PASS
blocking_findings:
  - "Novi regresioni test test_status_legend_nema_horizontalni_overflow_na_punom_setu daje LAŽAN PASS na necommitovanom, prije-popravke (buggy) kodu — nije pouzdana zastita, mora se popraviti/zamijeniti prije merge-a."
```

## Dobra vijest prvo — sama popravka RADI

Nezavisno sam izmjerio `status_legend` širinu na 1536×760 nakon Pi-jeve
font/spacing izmjene (10px font, `&nbsp;` umjesto `&nbsp;&nbsp;&nbsp;&nbsp;`):

```text
status_legend.width()            = 973px
status_legend.sizeHint().width() = 934px  (39px margine, staje)
```

Ovo se poklapa sa Pi-jevim izvještajem. Vizuelno (offscreen screenshot,
1536×760, pun set od 6 statusa) legenda se sada zaista uklapa unutar
svog reda, bez odsijecanja koje sam vidio u prvom review-u. `no_show`/
`cancelled` nisu spojeni nazad. Ovaj dio je **stvarno riješen**.

## ⚠ BLOCKING — novi regresioni test je nepouzdan (lažan PASS na buggy kodu)

Adversarna provjera (tačno onako kako bi trebalo): privremeno vratio
STARI (buggy, prije-REJECT) `_update_status_legend()` HTML
(`font-size:14px`, `&nbsp;&nbsp;&nbsp;&nbsp;` separator — identičan
kod koji je izazvao prvi REJECT) i pokrenuo BAŠ test koji je Pi dodao
da uhvati tu regresiju:

```text
pytest tests/test_gui/test_main_window.py::test_status_legend_nema_horizontalni_overflow_na_punom_setu -v
→ PASSED  (na buggy kodu!)
```

Ponovio tri puta (izolovano, sa drugim testovima u istom fajlu, sa
`-s` da vidim stvarne brojeve) — **dosljedno lažan PASS**. Debug ispis
je pokazao da u pytest-qt/offscreen kontekstu `legend.width()` i
`legend.sizeHint().width()` u ovom specifičnom test-scenariju
KONVERGIRAJU na istu vrijednost (1358 = 1358) umjesto da `width()`
ostane ograničen na stvarno dodijeljeni prostor (973, kako sam ručno
izmjerio u plain PySide6 skripti bez qtbot-a, van pytest okruženja, sa
identičnim podacima). Tačan uzrok je Qt layout-timing specifičnost
ovog offscreen+pytest-qt okruženja (nisam uspio izolovati preciznu
liniju uzroka unutar razumnog vremena — probao `qtbot.addWidget` sa/bez,
`app.processEvents()` više puta, drugačiji redoslijed — ništa od toga
nije mijenjalo ishod na način koji bi objasnio razliku), ALI **činjenica
da test prolazi na kodu za koji znamo da je buggy je sama po sebi
dovoljan razlog da se test ne može vjerovati**, bez obzira na uzrok.

Vratio kod na Pi-jevu popravku (iz backup kopije, ne `git checkout --`,
diff identičan `713257f`), ponovo pokrenuo punu verifikaciju — vidi
ispod.

**Zašto ovo blokira, ne samo napomena**: cijeli smisao prve REJECT
runde bio je da se OVAJ TAČNO defekt spriječi da se ponovi. Test koji
daje lažnu sigurnost je gori od odsustva testa — budući reviewer/agent
bi mu vjerovao. MEDIUM risk zahtijeva pouzdanu regresionu pokrivenost
za tačno ono što je bio predmet REJECT-a.

**Preporuka za popravku (nisam implementirao, ovo je smjer za
implementera):** izbjeći oslanjanje na `.width()` vs `sizeHint().width()`
poređenje u trenutku koji zavisi od Qt layout-stabilizacije unutar
pytest-qt/offscreen okruženja (pokazano da je nepouzdano). Robusnija
alternativa: provjeriti deterministička svojstva generisanog HTML-a
direktno (npr. `assert "font-size:10px" in legend_html`), ili izmjeriti
tekst preko `QFontMetrics`/`QLabel.fontMetrics()` naspram POZNATE
budžetirane širine za ciljnu rezoluciju (fiksna konstanta, ne
`self.width()` u trenutku koji zavisi od show()/layout timinga), ili
`qtbot.waitUntil(...)` koji polluje dok se geometrija stvarno ne
stabilizuje PRIJE poređenja (provjeriti da li to uopšte pomaže — nisam
stigao to testirati).

## Ostatak — nepromijenjeno od prvog review-a, i dalje PASS

- `week_view.py` STATUS_META/STATUS_ORDER/_status_key razdvajanje —
  PASS (nepromijenjeno od runde 1).
- `appointment_details.py` `_STATUS_BG["no_show"]` — PASS, adversarno
  potvrđeno u rundi 1 (KeyError bez fixa), nije ponovo mijenjano.
- `test_week_view.py`, `test_appointment_details_dialog.py` — novi
  testovi tačni i ciljani, nema primjedbi.

## Verifikacija (na finalnom stanju, nakon vraćanja Pi-jeve popravke)

```text
pytest tests/ -q                              → 269 passed, 11 warnings
ruff check src/dentaland desktop backend tests → All checks passed!
mypy src/dentaland desktop backend             → Success: no issues found in 35 source files
```

## Zaključak

Vizuelna popravka je stvarna i ispravna (nezavisno izmjereno). Jedini
razlog za REJECT je što test koji treba da je štiti u budućnosti ne
radi svoj posao — daje lažan PASS na kodu koji smo dokazano poznajemo
kao buggy. Ovo bi trebalo biti brza popravka (jedan test, ne cijela
implementacija).

## Handoff

```text
CILJ: NO_SHOW/CANCELLED razdvojeni u UI-ju BEZ vizuelnog overflow-a
      legende, sa pouzdanom regresionom zaštitom protiv budućeg
      ponavljanja overflow-a.
URAĐENO: REJECT (runda 2) — sama popravka (font/spacing) je ispravna i
      nezavisno potvrđena, ALI dodati regresioni test daje lažan PASS
      na buggy kodu (dosljedno reprodukovano 3x) — ne pruža stvarnu
      zaštitu.
NE DIRATI: week_view.py, appointment_details.py, ostali testovi — svi
      i dalje PASS od runde 1, ne diraj ih ponovo.
SLJEDEĆE: Pi popravlja/zamjenjuje SAMO
      test_status_legend_nema_horizontalni_overflow_na_punom_setu da
      stvarno hvata overflow (vidi preporuku gore — deterministička
      provjera HTML-a ili font-metrike, ne fragilna width() vs
      sizeHint() geometrija koja zavisi od pytest-qt layout timinga).
      Dokazati popravku istom adversarnom metodom koju sam ja koristio
      (privremeno vratiti buggy font/spacing, potvrditi da test SADA
      pada, pa vratiti fix). Zatim ponovo pytest/ruff/mypy, pa treći
      Claude review.
```
