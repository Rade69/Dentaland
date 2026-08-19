# Context Loading Rules

## Default

Ne čitaj repo široko. Ne pokreći `find`/`grep`/`tree` preko cijelog repoa
da bi otkrio strukturu — za to postoji `.agent/PROJECT_MAP.md`.

## Start

1. `AGENTS.md`
2. `.agent/PROJECT_MAP.md`
3. `.agent/CURRENT_STATE.md` — samo ako je relevantno za task (dostupnost
   agenata, poznati baseline problemi, aktivan veći rad na istoj domeni)
4. Task Contract za konkretan zadatak

## Then

Učitaj samo routing paket za taj tip taska — vidi `.agent/TASK_ROUTING.md`.

## Do not load by default

- cijeli `docs/`
- cijeli `agent_reports/`
- cijeli test suite source (samo relevantne test fajlove)
- cijelu git istoriju
- nepovezane domene (npr. `web/` kad se dira samo desktop GUI)
- dokumentaciju svih dostupnih MCP/tool servera

## Expand context only when evidence requires it

Ako impact analiza ili čitanje pozivalaca pokaže dodatni modul koji je
stvarno pogođen — učitaj ga, i zabilježi ZAŠTO (u Task Contract ili
report), ne tiho.

## Stop rule

Ako se kontekst počinje širiti zato što task nije dovoljno jasan — STOP,
ne nagađaj. Traži razjašnjenje ili redefiniši Task Contract prije nego što
nastaviš čitati sve više fajlova u nadi da će nešto postati jasnije.
