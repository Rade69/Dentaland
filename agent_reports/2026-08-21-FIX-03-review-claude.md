---
task_id: FIX-03
reviewer: claude
risk: MEDIUM
verdict: REJECT
date: 2026-08-21
---

# Review — FIX-03 (status semantika NO_SHOW/CANCELLED, MEDIUM)

```yaml
verdict: REJECT
scope: PASS
acceptance: FAIL (status legenda vizuelno pretiče kontejner)
architecture: PASS
blocking_findings:
  - "status_legend sizeHint width 1358px > actual width 973px na 1536x760 — 385px teksta se odsijeca (wordWrap=False, bez elide-a)"
```

## Scope — PASS

`git diff --stat`: `week_view.py` (produkcijska izmjena, +9/-3),
`desktop/views/dialogs/appointment_details.py` (+1, obrazložen izuzetak
od `forbidden_paths` — vidi ispod), 3 test fajla. `day_view.py`,
`main_window.py` produkcijski kod, `booking.py`, modeli/migracije —
netaknuto. Sve unutar duha kontrakta.

## Root cause fix (week_view.py) — PASS

`STATUS_META`/`STATUS_ORDER`/`_status_key` razdvajanje je tačno prema
kontraktu: `"no_show": ("!", "#c2410c", "Nije došao")`, `"cancelled"`
labela skraćena na `"Otkazan"`, `_status_key` dvije odvojene grane.
Boja `#c2410c` je vizuelno razlučiva od `#ff8a00` (waiting) i `#ef334f`
(cancelled) — provjereno okom na renderu.

## `appointment_details.py` izuzetak od forbidden_paths — PASS, dobar nalaz

Pi je prijavio da `_STATUS_BG` (lokalni dict u `appointment_details.py`,
formalno u `forbidden_paths`) ima samo 5 ključeva i da bi bez izmjene
Details dialog pucao na NO_SHOW terminu. **Nezavisno adversarno
provjereno**: privremeno uklonio `"no_show"` red iz `_STATUS_BG`,
kreirao pravi termin, pozvao `svc.mark_no_show(...)`, konstruisao
`AppointmentDetailsDialog(appt)` → **`KeyError: 'no_show'`, potvrđeno**.
Vratio fix (iz backup kopije fajla, ne `git checkout --`), diff nakon
vraćanja identičan originalnom (`b7e0e39`). Ovo je bio stvaran, tačan
propust u mojoj originalnoj kontraktnoj analizi (previdio sam ovaj
dict) — Pi je ispravno postupio po kontraktovom uputstvu ("prijaviti
kao dio agent_report-a, ne kao OUT_OF_SCOPE_FINDING") umjesto da
zaobiđe ili ignoriše. Dobra praksa, ne nalaz protiv Pi-ja.

## ⚠ BLOCKING — status legenda vizuelno pretiče kontejner na ciljnoj rezoluciji

Pi je ovo sam prijavio kao "unresolved risk" i tražio da review
odluči — nezavisno sam izmjerio i **potvrđujem da je stvaran problem,
ne teoretski**:

```text
status_legend.width()              = 973px  (stvarno dodijeljeno)
status_legend.sizeHint().width()   = 1358px (potrebno za 6 stavki)
overflow                            = 385px
wordWrap                            = False
```

Vizuelno (offscreen render 1536×760, screenshot sačuvan) — tekst
legende se vidljivo nastavlja van desne ivice svog kontejnera i
odsijeca se. Ovo NIJE isto što i `test_footer_ostaje_vidljiv_na_laptop_visini`
koji prolazi — taj test provjerava samo VERTIKALNU poziciju
(`geometry().bottom() <= schedule_page.rect().bottom()`), ne
HORIZONTALNO uklapanje teksta unutar QLabel-a. Test suite je slijep za
ovaj konkretan defekt.

Kontrakt (`FIX-03-task-contract.md`, sekcija "Status summary širina")
je EKSPLICITNO predvidio ovaj scenario i dao jasno uputstvo: "smanjiti
spacing/font unutar HTML-a je u redu; NE spajati statuse nazad zbog
prostora." Pi nije primijenio nijednu od tih mjera — samo je prijavio
rizik i ostavio ga za review. Po projektnoj praksi (implementer
prijavljuje, ne odlučuje o kompromisu koji kontrakt već daje kao
dozvoljenu opciju), ovo je trebalo biti riješeno u implementaciji, ne
ostavljeno kao otvoreno pitanje — kontrakt je već dao odgovor.

**Zašto REJECT, ne PASS_WITH_NOTES**: ovo nije kozmetička sitnica koja
može čekati follow-up — legenda je JEDINI način na koji osoblje vidi
zbirne brojeve statusa, uključujući upravo NOVU "Nije došao" stavku
koja je razlog ovog taska. Ako se ona odsijeca, cilj taska
(razdvojiti NO_SHOW vizuelno) je djelimično poražen za bilo koga na
1536px ili užoj rezoluciji.

## Verifikacija (ponovljena nezavisno)

```text
pytest tests/ -q                              → 268 passed, 11 warnings
ruff check src/dentaland desktop backend tests → All checks passed!
mypy src/dentaland desktop backend             → Success: no issues found in 35 source files
```

Svi testovi prolaze, ali ne pokrivaju horizontalno uklapanje teksta —
vrijedno dodati regresioni test za ovo u ispravci (npr.
`assert status_legend.sizeHint().width() <= status_legend.width()`
nakon renderovanja sa punim setom statusa, na fiksnoj test-rezoluciji).

## Zaključak

Logika razdvajanja statusa je ispravna i temeljno testirana (uključujući
nalaz van originalnog scope-a koji je ispravno obrađen). Jedini razlog
za REJECT je vizuelni overflow legende koji kontrakt eksplicitno
predviđa i daje gotovo rješenje za — ostaje da se stvarno primijeni
(manji font/spacing u HTML-u ili dozvoljen wrap u 2 reda), ne da se
statusi ponovo spajaju.

## Handoff

```text
CILJ: NO_SHOW i CANCELLED odvojeni svuda u UI-ju (simbol/boja/labela/
      count), bez regresije ostalih statusa.
URAĐENO: REJECT — logika razdvajanja je ispravna i dobro testirana
      (uklj. ispravno obrađen appointment_details.py nalaz), ALI
      status legenda vizuelno pretiče kontejner za 385px na ciljnoj
      1536×760 rezoluciji (izmjereno, ne teoretski) — blokira merge.
NE DIRATI: booking.py, models.py/migrations, day_view.py/main_window.py
      produkcijski kod (već netaknuto).
SLJEDEĆE: Pi popravlja `_update_status_legend()` u main_window.py —
      smanjiti font-size/spacing u HTML-u DOK sizeHint().width() ne
      stane u status_legend.width() na 1536×760 (ili dozvoliti wrap u
      2 reda), NE spajati no_show/cancelled nazad. main_window.py
      NIJE u trenutnim allowed_paths FIX-03 kontrakta (samo
      week_view.py + testovi) — treba proširiti allowed_paths za ovaj
      jedan, već predviđeni slučaj prije nego Pi nastavi (Radovanova/
      moja odluka, ne Pi-jeva samoinicijativa). Zatim ponovo pytest/
      ruff/mypy + nov regresioni test za horizontalno uklapanje, pa
      ponovo Claude review.
```
