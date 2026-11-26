# Katalogová data

- `kg_ostendorf.json` — Ostendorf KG (EN 1401-1), katalogové rozměry + `sockets` (t, Dmax, stěna).
- `pipelife_master3plus.json` — Pipelife Master 3 Plus (EN 1451-1), příručka 2026; staré články 3496… jen v `legacy_article_examples`.

Zdroje: [Master 3 Plus brochure](https://www.pipelife.cz/content/dam/pipelife/czech-republic/ke-stazen%C3%AD/english/PIPELIFE_MASTER_3_PLUS_BROCHURE_EN_ATI.pdf), [technical handbook](https://www.pipelife.at/content/dam/pipelife/austria/marketing/building/soil-waste/documents/Technisches%20Handbuch%20MASTER%203%20PLUS.pdf).

Katalog udává `L1/L2/L3`, `Z1/Z2/Z3`, Dmax a hloubku `t`, nikoli úplný řez hnízda ani poloměr ohybu — ty jsou v geometrii aproximovány a v IFC označeny `GeometryStatus`. Použití `t` jako hloubky hnízda tvarovky je explicitní aproximace. Čistící kusy mají rozměry víčka v JSON (`service_diameter_mm`, `service_reach_mm`). Knihovna slouží pro koordinaci umístění a spojení, ne pro výrobu.
