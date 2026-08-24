---
task_id: DENT-023
risk: LOW
implementer: pi
reviewers: [claude]
status: "DONE — MERGED u main (merge commit, 2026-08-24), post-merge integration gate PASS."
created_at: 2026-08-23
merged_at: 2026-08-24
---

# DENT-023 — SMTP env var dokumentacija (.env.example + README)

## Task Contract

**Cilj:** `src/dentaland/services/notifications.py` čita SMTP postavke
iz env varijabli (`DENTALAND_SMTP_HOST/PORT/USER/PASSWORD/FROM`), ali
nigdje u repou ne postoji dokumentacija tih varijabli — ko god postavlja
lokalno testiranje ili produkciju mora čitati izvorni kod da ih otkrije.
Ovo je otkriveno tokom audita email funkcionalnosti (22.8.2026,
Radovanov zahtjev), potvrđeno uživo Gmail SMTP testom istog dana.

**Risk:** LOW (čista dokumentacija, nema izmjene logike).

## Šta uraditi

1. **Novi fajl `.env.example`** u korijenu repoa — dokumentuje SVE pet
   varijabli sa objašnjenjem i primjer (NE stvarnim) vrijednostima:
   ```
   # SMTP postavke za email obavještenja (src/dentaland/services/notifications.py)
   # Bez DENTALAND_SMTP_HOST slanje se tiho preskače (best-effort, aplikacija ne puca).
   DENTALAND_SMTP_HOST=smtp.gmail.com
   DENTALAND_SMTP_PORT=587
   DENTALAND_SMTP_USER=tvoja.adresa@gmail.com
   # Gmail zahtijeva "App Password" (16 znakova, generisan na
   # myaccount.google.com/apppasswords uz uključenu 2-Step Verification),
   # NE običnu Gmail lozinku.
   DENTALAND_SMTP_PASSWORD=
   DENTALAND_SMTP_FROM=tvoja.adresa@gmail.com
   ```
   (implementer može prilagoditi tačan tekst komentara, sadržaj/suština
   mora ostati — objasniti Gmail App Password specifičnost, pošto je to
   uzrokovalo stvarnu grešku 22.8.2026 uživo — `534 5.7.9
   Application-specific password required`).
2. **Novi odjeljak u `README.md`**, "## Email obavještenja (SMTP)",
   ubaciti PRIJE "## Testovi i provjera koda" (trenutno oko linije 66),
   NAKON odjeljka "Lokalno testiranje". Sadržaj: kratko objasniti da su
   ove varijable opcione (aplikacija radi i bez njih, samo ne šalje
   email), uputiti na `.env.example`, i navesti TAČNO kako se postavljaju
   u PowerShell-u prije `python scripts/dev_local.py` (env varijable
   moraju biti postavljene u ISTOM terminalu/procesu koji pokreće
   `dev_local.py` — `_build_env()` u toj skripti kopira `os.environ` u
   trenutku poziva, ne čita `.env` fajl automatski — NE tvrditi da
   `.env` fajl radi sam od sebe, to trenutno nije implementirano, samo
   `.env.example` kao referenca za ručno kucanje).
3. **NE implementirati automatsko učitavanje `.env` fajla** (npr.
   `python-dotenv`) — to je nova zavisnost/mehanizam, van obima ovog
   LOW dokumentacionog taska. Ako se pokaže vrijedno, to je poseban
   budući task, prijaviti kao `OUT_OF_SCOPE_FINDING` ako se čini
   vrijednim pomena, ne implementirati sada.

## Allowed paths

```text
.env.example
README.md
agent_reports/**
```

## Forbidden paths

```text
src/dentaland/services/notifications.py
backend/
desktop/
scripts/dev_local.py
```

## Acceptance criteria

- [ ] `.env.example` postoji, dokumentuje svih 5 `DENTALAND_SMTP_*`
      varijabli, objašnjava Gmail App Password specifičnost.
- [ ] `.env.example` NE sadrži stvarne kredencijale (samo primjeri/prazno).
- [ ] README ima novi odjeljak koji upućuje na `.env.example` i
      objašnjava da varijable moraju biti postavljene u istom terminalu
      prije `dev_local.py`.
- [ ] Nema izmjena u `notifications.py` ili bilo kojem kodu — čista
      dokumentacija.

## Verification

```bash
ruff check src/dentaland desktop backend tests   # mora ostati čisto (dokumentacija ne dira kod)
pytest tests/ -q                                  # mora ostati na baseline broju
```

Baseline (23.8.2026, `main`): pytest 287 passed. Napomena: `DENT-022`
(HIGH, zaštita od dupliranog slanja podsjetnika) je paralelno u toku,
u worktree-u/reviewu, još nije mergovan u `main` — ne čekati na njega,
ovaj task je nezavisan (dira samo dokumentaciju). Provjeriti tačan
trenutni broj testova na svom worktree-u prije početka, ne pretpostaviti.

## Review

Claude, nezavisan od implementera. LOW risk — human approval nije
obavezan, Radovan odlučuje.

## Koordinacija — obavezno prije početka

Provjeri `python scripts/coordination.py status` prije `claim`. Radi u
zasebnom git worktree (`Dentaland-worktrees/DENT-023-<slug>`, grana
`task/DENT-023-<slug>`).
