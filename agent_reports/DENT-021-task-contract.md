---
task_id: DENT-021
risk: LOW
implementer: pi
reviewers: [claude]
verdict: "MERGED → INTEGRATION_VERIFIED → DONE (merge 9f08a7e). Fotografije zamijenjene Codex-ovim originalima tokom finalne provjere (Pi-jevi placeholderi bili premali/generisani, ne stvarne fotografije). Human approval: Radovan. Post-merge gate: pytest 264 passed, ruff clean, mypy clean (0 issues, 35 fajlova)."
commits: []
created_at: 2026-08-21
---

# Task Contract — panel doktora na rasporedu

## ⚠ Revizija (21.8.2026, nakon Claude review-a i Radovanove odluke)

Codex-ova prva verzija (necommitovana, još u glavnom checkout-u,
`git diff -- desktop/views/main_window.py tests/test_gui/test_main_window.py`)
je nezavisno pregledana — `verdict: PASS_WITH_NOTES` (vidi
`agent_reports/2026-08-21-DENT-021-review-claude.md`), ispunjava
originalni kontrakt, ALI ne odgovara Radovanovom referentnom
screenshot-u: fotografije su premale i indikator je prazan kružić boje
umjesto brojčane znake. Radovan je eksplicitno odlučio:

1. **Fotografije povećati** — ima prostora u desnoj koloni (širina
   panela je ograničena na 255–285px, vidi
   `requests_panel.py:66-67`, `doctor_legend` je poravnat sa tim
   panelom). Trenutno `DOCTOR_AVATAR_SIZE = 38` → povećati na **48px**
   (predlog, implementer može fino podesiti nakon vizuelne provjere ako
   38→48 ne izgleda dobro, ali ne vraćati na ~38 ili manje).
2. **Broj umjesto praznog kružića boje** — obojena kružna znaka
   (pozadina = ista `WeekView._DOCTOR_PALETTE` boja koja se već koristi)
   sa **bijelim podebljanim brojem** unutra. Broj = **broj termina tog
   doktora u trenutno prikazanom periodu (sedmica ILI dan, zavisno koji
   je aktivan)** — Radovanova eksplicitna odluka (ne "čeka potvrdu", ne
   "danas" fiksno). Mora se osvježavati pri navigaciji (strelice,
   "Danas", promjena Dan/Sedmica) — isti trenuci kad se već zove
   `_update_status_legend()`.

**VAŽNO — ne graditi na Codex-ovom necommitovanom diff-u u glavnom
checkout-u.** Taj diff ostaje netaknut dok se ne završi ova revizija
(Claude će ga očistiti tek NAKON što nova verzija bude commitovana i
mergovana, bezbjedno, ne prije). Implementiraj FRESH u zasebnom git
worktree, po specifikaciji ispod — Codex-ova verzija je referenca/dokaz
da je pristup (avatar pipeline, hide-when-empty logika) ispravan, ne
baza za nastavak.

### Root cause / gdje kopati (već locirano)

- `desktop/views/week_view.py`: `_filter_doctor_id`,
  `_fetch_appointments()` (RAW, bez filtera — filter se primjenjuje tek
  u `_visible_appointments()`), `_cell_span()` (grid-vidljivost),
  `visible_status_counts()` (postojeći obrazac za per-status count na
  trenutno vidljivim terminima — TAČNO taj obrazac treba kopirati za
  per-doktor count, ali BEZ primjene `_filter_doctor_id`, jer panel mora
  prikazivati SVE doktore bez obzira koji je tab aktivan).
- `desktop/views/day_view.py`: isti obrazac, `_fetch_appointments()` tu
  već nema doctor-filter uopšte (DayView nema filter tabova), pa je
  jednostavnije.
- `desktop/views/main_window.py:388-398` (`_update_status_legend`): isti
  `view = self.view_stack.currentWidget()` +
  `getattr(view, "<metoda>", None)` obrazac — dodati poziv novoj
  `_update_doctor_panel_counts()` metodi NA KRAJU
  `_update_status_legend()` tijela (jedno mjesto poziva, pokriva sve
  postojeće trigere umjesto da se dodaje 6 novih poziva).

### Novi metod — dodati u OBA `week_view.py` i `day_view.py`

```python
def visible_doctor_counts(self) -> dict[int, int]:
    """Broj vidljivih termina po doktoru u trenutnom periodu —
    NAMJERNO ignoriše self._filter_doctor_id (WeekView), panel doktora
    mora prikazivati sve doktore bez obzira na aktivni tab."""
    counts: dict[int, int] = {}
    for appt in self._fetch_appointments():
        if self._cell_span(appt) is None:
            continue
        doctor_id = getattr(appt, "doctor_id", None)
        if doctor_id is None:
            continue
        counts[doctor_id] = counts.get(doctor_id, 0) + 1
    return counts
```

(DayView nema `_filter_doctor_id` pa je razlika samo u odsustvu
komentara o njemu — ista implementacija.)

### `main_window.py` — spoj

- U `_build_schedule_page`, kad se pravi `indicator` QLabel po redu:
  zamijeniti plain `"●"` label obojenim kružnim brojem. Sačuvati
  referencu po doktoru (npr. `self._doctor_badge_labels: dict[int,
  QLabel] = {}`) da bi `_update_doctor_panel_counts()` mogla ažurirati
  tekst bez ponovnog građenja panela.
- Nova metoda:
  ```python
  def _update_doctor_panel_counts(self) -> None:
      view = self.view_stack.currentWidget()
      counts_fn = getattr(view, "visible_doctor_counts", None)
      counts = counts_fn() if callable(counts_fn) else {}
      for doctor_id, label in self._doctor_badge_labels.items():
          label.setText(str(counts.get(doctor_id, 0)))
  ```
- Pozvati je na kraju `_update_status_legend()` (jedno dodato mjesto,
  pokriva sve postojeće call sajtove).
- Stil znake: `border-radius: <pola širine>px`, `background-color:
  <doctor color>`, `color: #ffffff`, `font-weight: 700`, fiksna veličina
  (npr. 22–24px) — provjeriti vizuelno da broj ne prelijeva za
  dvocifrene vrijednosti (10+); ako prelijeva, malo povećati širinu
  znake ili font ne mora biti fiksno kvadratan (blago ovalan je u redu).

### Allowed paths (revizija — isto kao original + isti obim)

```text
desktop/views/week_view.py
desktop/views/day_view.py
desktop/views/main_window.py
desktop/assets/doctors/
tests/test_gui/test_week_view.py
tests/test_gui/test_day_view.py
tests/test_gui/test_main_window.py
```

### Obavezni testovi (dodatno na postojeće)

1. `visible_doctor_counts()` u WeekView vraća tačan broj po doktoru za
   trenutnu sedmicu, NEZAVISNO od `set_filter()` (test: postaviti
   filter na jednog doktora, provjeriti da `visible_doctor_counts()`
   ipak vraća count za SVE doktore).
2. Isto za DayView (bez filter dijela, samo tačan count za dan).
3. `main_window`: nakon `create()` termina, znaka odgovarajućeg doktora
   pokazuje ažuriran broj; nakon `_move_week`/`_go_today`/prebacivanja
   Dan↔Sedmica, broj se ažurira na tačan broj za NOVI period.
4. Avatar veličina — provjeriti da je `DOCTOR_AVATAR_SIZE` stvarno
   povećan (npr. `assert avatar.size().width() >= 48` ili tačna
   vrijednost).
5. Regresija — postojeći `test_panel_doktora_je_sakriven_kad_store_nema_doktore`
   i osnovni sadržaj/redoslijed testovi ne smiju se pokvariti.

### Acceptance (revizija)

- [ ] Fotografije vidljivo veće (≥48px) i i dalje čisto uklopljene u
      panel bez clippinga (ručni/offscreen smoke test na istoj
      rezoluciji koju je Codex koristio, 1536×760).
- [ ] Svaki red ima obojenu kružnu znaku sa BROJEM (ne prazan kružić).
- [ ] Broj = tačan count termina tog doktora za trenutno prikazan
      period (sedmica ili dan), NEZAVISNO od aktivnog doctor-filter
      taba.
- [ ] Broj se ispravno osvježava pri navigaciji (strelice, Danas,
      Dan/Sedmica prebacivanje) i nakon CRUD akcija (create/cancel/delete).
- [ ] Sve iz originalnog kontrakta ispod i dalje važi (skrivanje bez
      doktora, poravnanje sa DashboardPanels, itd.).

---

## Originalni kontrakt (Codex, PASS_WITH_NOTES protiv OVOG teksta —
revizija iznad ga proširuje, ne zamjenjuje)

```yaml
id: DENT-021
title: Panel doktora sa fotografijama na rasporedu
risk: LOW
objective: Zamijeniti jednorednu legendu doktora desnim panelom sa lokalnim kružnim fotografijama, imenima i indikatorima boje.
allowed_paths:
  - desktop/views/main_window.py
  - desktop/assets/doctors/
  - tests/test_gui/test_main_window.py
  - agent_reports/DENT-021-task-contract.md
  - agent_reports/2026-08-21-DENT-021-doctor-panel.md
forbidden_paths:
  - src/dentaland/models.py
  - src/dentaland/services/
  - migrations/
acceptance:
  - panel je u desnoj koloni iznad postojećih današnjih statusa
  - prikazuje tačno Dr Ljubo, Dr Zorka i Dr Ana sa odgovarajućim lokalnim fotografijama
  - svaki red ima mali kružni avatar i indikator u postojećoj boji doktora
  - panel se sakriva kada store nema doktore
  - raspored, filter tabovi i DashboardPanels ostaju funkcionalno nepromijenjeni
verification:
  - pytest tests/test_gui/test_main_window.py -q
  - ruff check desktop/views/main_window.py tests/test_gui/test_main_window.py
```

## Scope

Izolovana vizuelna izmjena postojećeg `doctorLegend` dijela i dodavanje tri
lokalna bitmap resursa.

## Out of scope

Promjene modela doktora, upload fotografija kroz Postavke, baza, servisni sloj
i promjene semantike brojčanih indikatora.

## Acceptance

Automatski GUI testovi potvrđuju sadržaj, lokalne pixmape, raspored redova i
skrivanje bez doktora; ručni smoke test potvrđuje da panel vizuelno staje u
desnu kolonu na laptop rezoluciji.
