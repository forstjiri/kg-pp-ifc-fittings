# Ostendorf KG reference meshes

Triangulated meshes extracted from the manufacturer's STEP files, used **only** for measurement and IoU tests; the libraries are pure SweptSolid. Each JSON file contains `[vertices_mm, zero_based_triangles]`.

| article | product | article | product |
|---|---|---|---|
| 220000z | DN110 pipe | 222000z | DN160 pipe |
| 220200z / 220210z / 220220z | 15/30/45° DN110 bend | 222200z / 222210z | 15/30° DN160 bend |
| 220300z / 220400z | 45/87° 110/110 branch | 222320z / 222420z | 45/87° 160/110 branch |
| 222700z | eccentric 160/110 reducer | 175600z | DN110 cleanout |

Catalogue dimensions are in `data/kg_ostendorf.json`; missing references (among others cleanouts 220600/221600/222600 and DN200–500) are parametric and marked with `GeometryStatus`. IFC declares millimetres, and both coordinates and placements are in native mm. The source STEP files and the extraction remain in local `/tmp/opencode/barak-fitting-data/`; redistribution terms have not been verified.
