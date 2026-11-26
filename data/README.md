# Catalogue data

- `kg_ostendorf.json` — Ostendorf KG (EN 1401-1), catalogue dimensions plus `sockets` (`t`, Dmax, wall).
- `pipelife_master3plus.json` — Pipelife Master 3 Plus (EN 1451-1), 2026 handbook; older articles 3496… only in `legacy_article_examples`.

Sources: [Master 3 Plus brochure](https://www.pipelife.cz/content/dam/pipelife/czech-republic/ke-stazen%C3%AD/english/PIPELIFE_MASTER_3_PLUS_BROCHURE_EN_ATI.pdf), [technical handbook](https://www.pipelife.at/content/dam/pipelife/austria/marketing/building/soil-waste/documents/Technisches%20Handbuch%20MASTER%203%20PLUS.pdf).

The catalogue gives `L1/L2/L3`, `Z1/Z2/Z3`, Dmax and the insertion depth `t`, but not the full socket section or the bend radius — these are approximated in the geometry and marked as `GeometryStatus` in IFC. Using `t` as the fitting socket depth is an explicit approximation. Cleanout cap dimensions are in the JSON (`service_diameter_mm`, `service_reach_mm`). The library is intended for coordination of placement and connections, not for manufacturing.
