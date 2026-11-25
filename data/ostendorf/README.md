# Ostendorf KG meshes

Triangulated sources used by the KG library generator:

| File | Catalogue article | Product |
|---|---:|---|
| `220220z.json` | 220220 | KGB 45°, OD110 |
| `220200z.json` | 220200 | KGB 15°, OD110 |
| `220210z.json` | 220210 | KGB 30°, OD110 |
| `222320z.json` | 222320 | KGEA 45°, OD160/110 |
| `222700z.json` | 222700 | KGR eccentric reducer, OD160/110 |

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
the corresponding Ostendorf STEP model. Catalogue dimensions and port data are
in `definice.py`; port placements follow the existing barak pilot transform.
The IFC files declare millimetres as their length unit, so representation
coordinates and placements are written in native millimetres (not metres).

Source STEP files and the mesh extraction process remain in the local
`/tmp/opencode/barak-fitting-data/` workspace. Redistribution/licence terms
for the manufacturer geometry have not been checked; these derived meshes are
kept in this working repository for reproducible local generation.
