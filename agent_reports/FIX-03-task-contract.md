---
task_id: FIX-03
risk: MEDIUM
implementer: TBD (Crush/Pi/Codex — Radovan dodjeljuje)
reviewers: [claude]
status: OPEN — BLOKIRANO dok DENT-021 (Codex) ne oslobodi main_window.py/test_main_window.py
created_at: 2026-08-21
---

# FIX-03 — Razdvojiti NO_SHOW i CANCELLED u UI statusima

## ⚠ Koordinacijska blokada — pročitati PRIJE dodjele

`python scripts/coordination.py status` (21.8.2026) pokazuje aktivan
claim:

```text
DENT-021   codex   paths: desktop/views/main_window.py,
                          desktop/assets/doctors,
                          tests/test_gui/test_main_window.py, ...
```

Codex trenutno radi DIREKTNO u glavnom checkout-u (ne worktree),
necommitovano, na panelu doktora sa fotografijama u desnoj koloni
(vizuelno nevezano za ovaj task — vidi screenshot koji je Radovan
poslao). FIX-03 treba `tests/test_gui/test_main_window.py` (postojeći
test na liniji 72 tvrdi `"Otkazan / Nije došao" in
window.status_legend.text()`, što se mora promijeniti). **Ne
dodjeljivati FIX-03 dok DENT-021 nije commitovan/mergovan i claim
oslobođen** — inače garantovan konflikt na istom fajlu. Provjeriti
`coordination.py status` neposredno prije starta; ako je DENT-021 i
dalje aktivan, sačekati.

## Task Contract

**Cilj:** `CANCELLED` i `NO_SHOW` trenutno dijele isti UI status
("Otkazan / Nije došao") — isti simbol, ista boja, isti zbirni count.
Poslovno su različita stanja (pacijent je otkazao unaprijed vs. pacijent
se nije pojavio) i treba ih razdvojiti svuda u UI-ju.

**Risk:** MEDIUM

**Izvor:** `docs/dentaland-desktop-korektivni-plan.md`, sekcija 4
(PRIORITET 4). Pun kontekst korektivnog plana (FIX-01 do FIX-06) tamo —
ovaj task pokriva SAMO FIX-03, ne šire.

## Root cause (već lociran, ne treba ponovo istraživati) — jedan izvor istine

`desktop/views/week_view.py` linije 47–67 su JEDINO mjesto gdje se
status mapira na (simbol, boja, labela):

```python
STATUS_META: dict[str, tuple[str, str, str]] = {
    "confirmed": ("✓", "#149447", "Potvrđen"),
    "waiting": ("◷", "#ff8a00", "Čeka potvrdu"),
    "arrived": ("▲", "#1473e6", "Stigao"),
    "completed": ("★", "#7c3aed", "Završen"),
    "cancelled": ("✗", "#ef334f", "Otkazan / Nije došao"),
}
STATUS_ORDER = ["confirmed", "waiting", "arrived", "completed", "cancelled"]

def _status_key(appt: AppointmentDTO) -> str:
    status = getattr(getattr(appt, "status", None), "value", None)
    if status in {"CANCELLED", "NO_SHOW"}:
        return "cancelled"
    ...
```

**Bitan nalaz — svi potrošači su generički, ne treba ih mijenjati:**
`day_view.py`, `main_window.py` (`_update_status_legend`, linije
388–398) i `dialogs/appointment_details.py` SVI čitaju
`STATUS_META`/`STATUS_ORDER`/`_status_key`/`status_icon` iz
`week_view.py` — nijedan od njih ne zna za konkretne stringove statusa,
samo iteriraju generički. Znači: **produkcijska izmjena je gotovo u
potpunosti ograničena na `week_view.py`** (jedan dict + jedna grana u
jednoj funkciji); ostala tri fajla trebaju SAMO izmjene u njihovim
POSTOJEĆIM testovima (koji hardkodiraju stari kombinovani label/count),
ne izmjene produkcijskog koda. Ovo je provjereno `grep`-om za sve
pozivaoce (`STATUS_META`, `STATUS_ORDER`, `_status_key`, `status_icon`)
kroz `desktop/views/`.

## Šta uraditi

1. U `week_view.py`:
   - Dodati novi ključ `"no_show"` u `STATUS_META`, npr.
     `"no_show": ("!", "#c2410c", "Nije došao")` (predložen simbol/boja
     — jasno različiti od postojećeg `"waiting"` `#ff8a00` i
     `"cancelled"` `#ef334f`; implementer može odabrati drugu boju uz
     kratko obrazloženje u `agent_report`, ali mora ostati vizuelno
     razlučiva od te dvije).
   - Promijeniti `"cancelled"` labelu sa `"Otkazan / Nije došao"` na
     `"Otkazan"`.
   - U `STATUS_ORDER` dodati `"no_show"` PRIJE `"cancelled"` (redoslijed
     iz plana: Potvrđen, Čeka potvrdu, Stigao, Završen, Nije došao,
     Otkazan) → `["confirmed", "waiting", "arrived", "completed",
     "no_show", "cancelled"]`.
   - U `_status_key()`: razdvojiti `if status in {"CANCELLED",
     "NO_SHOW"}: return "cancelled"` na dvije grane —
     `if status == "NO_SHOW": return "no_show"` i
     `if status == "CANCELLED": return "cancelled"`.
2. `day_view.py`, `main_window.py`, `dialogs/appointment_details.py` —
   **ne mijenjati produkcijski kod** osim ako se tokom rada pokaže da
   negdje ipak postoji hardkodirana pretpostavka o samo 5 statusa (nije
   pronađena u ovoj analizi, ali provjeriti). Ako se nešto takvo nađe,
   prijaviti kao dio `agent_report`-a, ne kao `OUT_OF_SCOPE_FINDING`
   (to je i dalje unutar cilja ovog taska, samo šire od trenutne
   pretpostavke).
3. Ažurirati postojeće testove koji pretpostavljaju stari kombinovani
   status (vidi "Obavezni regression testovi").

## Status summary širina (ako zatreba)

Ako `status_legend` HTML sa 6 stavki umjesto 5 ne staje u postojeću
širinu/visinu (`setFixedHeight(48)`, `main_window.py:275`): smanjiti
spacing/font unutar HTML-a je u redu; NE spajati statuse nazad zbog
prostora (eksplicitno pravilo iz plana). Ako treba layout izmjenu u
`main_window.py` (npr. dozvoliti wrap u 2 reda), to je razlog VIŠE da se
sačeka da DENT-021 oslobodi taj fajl — ne raditi paralelno.

## Allowed paths

```text
desktop/views/week_view.py
tests/test_gui/test_week_view.py
tests/test_gui/test_day_view.py
tests/test_gui/test_appointment_details_dialog.py
tests/test_gui/test_main_window.py
```

`desktop/views/main_window.py` je dodano u forbidden (ispod) SAMO ako
se pokaže da produkcijska izmjena tamo nije potrebna (očekivano — vidi
root cause analizu). Ako se tokom rada pokaže da JE potrebna izmjena u
`main_window.py` (npr. layout za 6. stavku), to je
`OUT_OF_SCOPE_FINDING` — prijaviti, ne implementirati bez odobrenja,
JER je taj fajl trenutno pod tuđim claim-om (DENT-021).

## Forbidden paths

```text
src/dentaland/models.py
migrations/
src/dentaland/services/booking.py
desktop/views/day_view.py
desktop/views/main_window.py
desktop/views/dialogs/appointment_details.py
desktop/views/dialogs/**
```

## Obavezni regression testovi

1. `tests/test_gui/test_week_view.py:208-229`
   (`test_status_ikonice`, parametrizovan) — ažurirati red
   `("NO_SHOW", None, None, "✗")` na novi simbol za no_show (npr. `"!"`,
   šta god je izabrano u `STATUS_META`), i dodati novi red za
   `("CANCELLED", None, None, "✗")` da cancelled ostane eksplicitno
   pokriven.
2. `tests/test_gui/test_main_window.py:70-74` — zamijeniti
   `assert "Otkazan / Nije došao" in window.status_legend.text()` sa
   provjerom da su `"Otkazan"` i `"Nije došao"` sada ODVOJENE stavke
   (npr. dva odvojena termina, jedan CANCELLED jedan NO_SHOW, provjeriti
   oba counta u legendi zasebno).
3. Novi test: legenda ispravno broji NO_SHOW i CANCELLED odvojeno kad
   oba postoje istovremeno (npr. jedan termin `mark_no_show`, jedan
   `cancel`, `status_legend.text()` sadrži oba counta tačno).
4. `dialogs/appointment_details.py` prikazuje tačnu labelu/boju za
   NO_SHOW termin (novi test u `test_appointment_details_dialog.py`,
   po uzoru na postojeće testove tog fajla).
5. Regresija — svi ostali statusi (confirmed/waiting/arrived/completed)
   nepromijenjeni u simbolu/boji/labeli/redoslijedu.

## Acceptance criteria

- [ ] NO_SHOW i CANCELLED imaju odvojene countove u status legendi.
- [ ] Kartice termina (WeekView/DayView) imaju različitu oznaku za
      NO_SHOW vs CANCELLED.
- [ ] Details dialog pokazuje tačno stanje (NO_SHOW ≠ CANCELLED label).
- [ ] Postojeći status action workflow (`mark_no_show`/`cancel`/itd. u
      `booking.py`) nije promijenjen — ovo je čisto UI/prezentaciona
      izmjena.
- [ ] Nema izmjena van `allowed_paths`, posebno nema izmjena u
      `main_window.py` bez prethodnog `OUT_OF_SCOPE_FINDING`.

## Verification

```bash
pytest tests/ -q
ruff check src/dentaland desktop backend tests
mypy src/dentaland desktop backend
```

Baseline za poređenje (izmjereno 21.8.2026 na `main` nakon `FIX-01`):
pytest 258 passed, ruff clean, mypy clean (0 issues, 35 fajlova).

## Review

Claude, nezavisan od implementera. MEDIUM risk — po tabeli u
`docs/dentaland-agentski-razvoj.md` human approval (Radovan) JE
obavezan prije merge-a.

## Koordinacija — obavezno prije početka

1. **Provjeriti `python scripts/coordination.py status` — ako je
   `DENT-021` (Codex) i dalje aktivan na `main_window.py`/
   `test_main_window.py`, NE počinjati FIX-03 dok se ne oslobodi.**
2. Nakon toga, `claim` na `allowed_paths` iz ovog kontrakta.
3. Radi isključivo u zasebnom git worktree
   (`Dentaland-worktrees/FIX-03-<slug>`, grana `task/FIX-03-<slug>`).
