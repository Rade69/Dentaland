# REF-14 — Claude nezavisan review (arhitektura, Reviewer 2)

```yaml
verdict: PASS_WITH_NOTES
scope: PASS
acceptance: PASS
architecture: PASS
blocking_findings: []
non_blocking_notes: 1
```

## CILJ

Codex je pokrio test kvalitet i provider semantiku temeljno (late-binding
dokaz, dead-field trostruka provjera) — ne ponavljam to. Fokus: da li ova
izmjena, koja dodaje tri nove lambda-closure na `MainWindow`-ovu instancu,
ima arhitektonsku posljedicu s obzirom na REF-10-ov nedavni weakref fix za
TAČNO istu klasu problema (referentni ciklus → PySide6/shiboken teardown
crash).

## URAĐENO

- Potvrdio diff, `day_view.py`/`week_view.py`/`requests_panel.py`
  netaknuti (`git diff --stat ce960d3` prema tim fajlovima prazan).
- Pokrenuo `tests/test_gui/test_main_window.py` samostalno — 32 passed.

## ARHITEKTONSKA ISTRAGA (razlog PASS_WITH_NOTES, ne blocking)

REF-14 dodaje tri nova provider callable-a za `MainWindow`-ovu instancu:
`doctors_provider=lambda: self._doctors` itd. — svaka lambda zatvara
(closure) `self` (MainWindow), i ta lambda se čuva UNUTAR
`AppointmentController` kao `self._doctors_provider`. To je STRUKTURNO
identičan obrazac referentnom ciklusu koji je REF-10 upravo popravio
weakref-om (`_parent_widget`): `MainWindow → _controller →
_doctors_provider(closure) → MainWindow`.

**Provjerio sam da li je ovo NOVI rizik ili postojeći, samo proširen:**
`refresh_callback` parametar (postoji od REF-04, prije REF-10) se za
`MainWindow`-ovu instancu prosljeđuje kao `self._refresh_dashboard` —
BOUND METHOD, koja isto tako strukturno zatvara `self` i strogo
referencira `MainWindow` iznutra `AppointmentController`-a
(`self._refresh_callback`). Isti obrazac postoji i za `DashboardPanels`
(REF-09, `self._on_appointment_changed`). Dakle **ovaj ciklus je već
postojao za dva od četiri potrošača PRIJE REF-14** — REF-14 ga ne uvodi,
samo dodaje tri dodatna zatvaranja istog tipa za `MainWindow`.

Zašto zaključujem da ovo NIJE praktičan regresijski rizik (za razliku od
REF-10-ovog slučaja): `tests/test_gui/test_main_window.py` konstruiše i
uništava `MainWindow` (kroz `window` fixture) u **32 odvojena testa**, i
to je bilo tako i prije REF-14 (`_refresh_dashboard` ciklus je već
postojao) — da je ovaj obrazac sam po sebi dovoljan da pokrene shiboken
teardown crash, vidjeli bismo ga već u postojećem test suite-u, mnogo
prije REF-14. REF-10-ov crash se specifično desio u scenariju gdje se
DVA view-a (`week_view` + `day_view`) konstruišu ZAJEDNO u istom testu
(`test_pravi_viewovi_ne_fetchuju_interno`) — moguće da je taj specifičan
dvostruki-konstrukcija obrazac (ne sama prisutnost ciklusa) trigerovao
problem, ne generička prisutnost strong-ref ciklusa.

## NON-BLOCKING NAPOMENA

### N1 — dokumentovati obrazac, ne čekati sljedeći crash da ga otkrijemo

Preporučujem da se ovo eksplicitno zapiše kao poznato arhitektonsko
svojstvo (npr. u `AppointmentController`-ovom docstringu ili
`.agent/CURRENT_STATE.md`): **"`refresh_callback` i provider callable-ovi
prosljeđeni ovoj klasi mogu strukturno zatvarati (closure) svoj
`parent_widget`, stvarajući referentni ciklus analogan onom koji je
riješen za `_parent_widget` (REF-10, weakref). Trenutno nema dokazanog
crash-a za ove puteve (opsežno testirano), ali ako se ikad doda test koji
konstruiše/uništava VIŠE `MainWindow`/`DashboardPanels` instanci ZAJEDNO u
istom testu (analogno REF-10-ovom trigeru), prvo provjeriti ovaj ciklus
prije nego što se traži drugi uzrok."**

Ovo nije razlog za REJECT — nema dokaza o stvarnom kvaru, i "popraviti"
bi značilo weakref-ovati i `refresh_callback`/providere što dodaje
kompleksnost bez dokazane potrebe (protivno CLAUDE.md principu — ne
graditi robusnost za problem koji nije pokazan). Samo dokumentovati da
budući debugging ne počinje od nule ako se ikad pojavi sličan simptom.

## ZAKLJUČAK

Dizajn je ispravan i dosljedan REF-04..13 obrascima. Jedina napomena je
preventivna dokumentacija poznatog (ali empirijski netriggerovanog)
strukturnog obrasca — ne blokira merge. `PASS_WITH_NOTES`. Spremno za
Radovanov human approval.
