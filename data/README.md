# Catalogue data sources

`pipelife_master3plus.json` transcribes current elbow tables (handbook pp. 29–31)
and selected single-branch rows (pp. 32–33) from Pipelife's official 2026
technical handbook. The 2021 Czech catalogue examples are kept in a separate
`legacy_article_examples` section; legacy article numbers and dimensions must
not silently replace current rows.

The handbook drawings identify `L1/L2/L3`, `Z1/Z2/Z3`, socket maximum diameter
and insertion dimension `t`. They do not provide a complete dimensioned
cross-section of each fitting socket or bend centreline. Those mesh details
must be labelled approximate in any parametric geometry. The current JSON
records the socket OD and handbook pipe `t`; assigning `t` to fitting socket
depth is explicitly an approximation.

`pp_generator.py` consumes handbook elbow rows, selected 45°/87.5° single
branches, nine reducer pairs, and five vertical inspection-piece sizes at
library sizes 32, 40, 50, 75, 110, 125 and 160. It writes
`out/tvarovky-EN1451-1.ifc`. Elbow centreline curvature, branch intersections,
inspection covers, reducer tapers and socket bores/wall transitions are
approximated. The IFC types carry this status in
`Pset_Tvarovka.GeometryStatus`. These shapes support placement and connection
coordination, not manufacturing.

For the inspection pieces, the service-port centre uses the handbook `Z1`
datum. The sketch does not tabulate the cover diameter or its projection, so
both are explicit per-size approximations in the JSON (`service_diameter_mm`,
`service_projection_mm`), not hidden geometry-generator ratios.

Official sources:

- [MASTER 3 PLUS English brochure](https://www.pipelife.cz/content/dam/pipelife/czech-republic/ke-stazen%C3%AD/english/PIPELIFE_MASTER_3_PLUS_BROCHURE_EN_ATI.pdf)
- [MASTER 3 PLUS technical handbook](https://www.pipelife.at/content/dam/pipelife/austria/marketing/building/soil-waste/documents/Technisches%20Handbuch%20MASTER%203%20PLUS.pdf)
- [Pipelife Austria drainage systems](https://partner.pipelife.at/pipelifeAT/de/EUR/Geb%C3%A4udetechnik/Abfluss-Systeme/c/PLWGHT000035)
