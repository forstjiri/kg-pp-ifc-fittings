# Ostendorf KG meshes

Triangulated reference meshes (from manufacturer STEP models), used only by
tests (IoU) and measurement — the shipped libraries are pure SweptSolid:

| File | Catalogue article | Product |
|---|---:|---|
| `220000z.json` | 220000 | KGEM pipe DN110 (socketed stub) |
| `220200z.json` | 220200 | KGB 15°, OD110 |
| `220210z.json` | 220210 | KGB 30°, OD110 |
| `220220z.json` | 220220 | KGB 45°, OD110 |
| `220300z.json` | 220300 | KGEA 45°, OD110/110 |
| `220400z.json` | 220400 | KGEA 87°, OD110/110 |
| `222000z.json` | 222000 | KGEM pipe DN160 |
| `222000z-socket.json` | 222000 | KGEM DN160 socket detail |
| `222200z.json` | 222200 | KGB 15°, OD160 |
| `222210z.json` | 222210 | KGB 30°, OD160 |
| `222320z.json` | 222320 | KGEA 45°, OD160/110 |
| `222420z.json` | 222420 | KGEA 87°, OD160/110 |
| `222700z.json` | 222700 | KGR eccentric reducer, OD160/110 |
| `175600z.json` | 175600 | KGRE cleanout, OD110 |

`katalog-p35-kgb-kolena.png`: catalogue page 35 (KGB elbow tables + drawing).


Ostendorf catalogue KGRE cleanout article numbers `220600`, `221600`, and
`222600` are included with catalogue overall lengths. Their coordination
geometry is parametric and explicitly approximate; no manufacturer mesh was
available locally.

The library covers the catalogue elbows (15°/30°/45°/67°/87°) and 45°/87°
branch combinations with main and branch OD up to 160 mm, plus reducers
125/110, 160/110 and 160/125. Entries without a matching local manufacturer
mesh use parametric coordination geometry and carry `GeometryStatus` in IFC;
catalogue dimensions and article numbers are retained.

Ostendorf also sells KG sizes OD200–500, as shown in the full catalogue tables.
They are intentionally excluded because the approved project scope in
`tvarovky-parametricka-knihovna-ifc.md` specifies KG `110, 160` and a check of
`125`; they are not missing combinations within that scope.

Each JSON file is `[vertices_mm, triangle_indices_zero_based]`, extracted from
the corresponding Ostendorf STEP model. Catalogue dimensions live in
`data/kg_ostendorf.json`; port placements follow the existing barak pilot
transform. The IFC files declare millimetres as their length unit, so
representation coordinates and placements are written in native millimetres
(not metres).

Source STEP files and the mesh extraction process remain in the local
`/tmp/opencode/barak-fitting-data/` workspace. Redistribution/licence terms
for the manufacturer geometry have not been checked; these derived meshes are
kept in this working repository for reproducible local generation.
