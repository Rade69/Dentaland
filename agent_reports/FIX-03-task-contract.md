---
task_id: FIX-03
risk: MEDIUM
implementer: pi
reviewers: [claude]
status: "MERGED → INTEGRATION_VERIFIED → DONE (merge 53db57c). Human approval: Radovan. Post-merge gate na main: pytest 269 passed, ruff clean, mypy clean (0 issues, 35 fajlova)."
created_at: 2026-08-21
---

# FIX-03 — Razdvojiti NO_SHOW i CANCELLED u UI statusima

## ⚠ Koordinacijska blokada — RIJEŠENA (21.8.2026)

`DENT-021` (panel doktora sa fotografijama) je MERGED (`9f08a7e`) i
claim je oslobođen. FIX-03 je spreman za dodjelu.

Napomena za implementera: `main_window.py`/`test_main_window.py` su se
promijenili kroz DENT-021 (dodat `_update_doctor_panel_counts()`,
brojčane znake pored doktora — nevezano za status semantiku). Provjereno
da referenca ispod (`tests/test_gui/test_main_window.py:72`, tvrdnja
`"Otkazan / Nije došao" in window.status_legend.text()`) i dalje stoji
na istoj liniji — DENT-021 je dodao testove na KRAJ fajla, nije mijenjao
postojeće linije. `week_view.py`-ov `STATUS_META`/`_status_key` (root
cause ispod) DENT-021 uopšte nije dirao — analiza ostaje potpuno
validna. Ipak, provjeri `coordination.py status` prije `claim`-a kao i
uvijek (mogao je u međuvremenu krenuti neki drugi paralelan task).

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

## Allowed paths (proširen 21.8.2026, poslije Claude review-a — vidi ⚠ REJECT ispod)

```text
desktop/views/week_view.py
desktop/views/main_window.py
tests/test_gui/test_week_view.py
tests/test_gui/test_day_view.py
tests/test_gui/test_appointment_details_dialog.py
tests/test_gui/test_main_window.py
```

`desktop/views/main_window.py` je DODAT u allowed_paths (uklonjen iz
forbidden) — DENT-021 je odavno mergovan (`9f08a7e`), originalni razlog
zabrane više ne važi. Dozvoljena izmjena je USKO ograničena na
`_update_status_legend()` (font-size/spacing u HTML-u, ili wrap u 2
reda) radi popravke potvrđenog vizuelnog overflow-a — vidi
`agent_reports/2026-08-21-FIX-03-review-claude.md`. Ne širiti izmjenu
van te jedne metode.

`desktop/views/dialogs/appointment_details.py` je već bio formalno u
forbidden_paths, ALI Pi je ispravno prijavio i primijenio nužan
1-linijski dodatak (`_STATUS_BG["no_show"]`) — bez njega Details dialog
puca `KeyError` na NO_SHOW terminu, nezavisno adversarno potvrđeno u
review-u. Ta izmjena OSTAJE, tretirati kao dio prihvaćenog scope-a, ne
ponovo uklanjati.

## Forbidden paths

```text
src/dentaland/models.py
migrations/
src/dentaland/services/booking.py
desktop/views/day_view.py
desktop/views/dialogs/**
```

(`appointment_details.py` uklonjen iz forbidden liste retroaktivno —
vidi napomenu iznad, već sadrži prihvaćenu izmjenu.)

## ⚠ REJECT (21.8.2026) — status legenda vizuelno pretiče kontejner

Claude review: `agent_reports/2026-08-21-FIX-03-review-claude.md`.
Izmjereno na 1536×760: `status_legend.sizeHint().width()` = 1358px,
`status_legend.width()` = 973px (dodijeljeno) → **385px teksta se
odsijeca** (`wordWrap=False`, bez elide-a). Logika razdvajanja statusa
(week_view.py) je PASS — problem je isključivo prezentacioni, u
`main_window.py::_update_status_legend()`.

**Popravka (dozvoljena po ovom kontraktu, sad i po allowed_paths):**
smanjiti `font-size`/spacing u HTML-u koji `_update_status_legend()`
generiše DOK `sizeHint().width()` ne stane u `status_legend.width()` na
1536×760, ILI dozvoliti wrap u 2 reda (`setWordWrap(True)` + provjeriti
da `setFixedHeight(48)` i dalje ima smisla ili treba blago povećati).
**NE spajati `no_show`/`cancelled` nazad zbog prostora** — to poražava
cilj cijelog taska.

Dodati regresioni test koji ovo hvata (test suite je trenutno slijep za
horizontalni overflow — postojeći `test_footer_ostaje_vidljiv_na_laptop_visini`
provjerava samo vertikalnu poziciju), npr. provjera da
`status_legend.sizeHint().width() <= status_legend.width()` nakon
punog seta statusa na fiksnoj test-širini.

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
