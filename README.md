# Parametrické IFC tvarovky

Generate both IFC4 Project Libraries with:

```sh
.venv/bin/python generate_all.py
```

Outputs:

- `out/tvarovky-EN1401-1.ifc` — current KG catalogue subset (Ostendorf STEP-derived fittings).
- `out/tvarovky-EN1451-1.ifc` — Pipelife MASTER 3 PLUS elbows, single branches,
  reducers and vertical inspection pieces.

PP dimensions are kept in `data/pipelife_master3plus.json`. Every PP fitting is
an exact IFC4 SweptSolid (`swept_geometrie.py`): `IfcRevolvedAreaSolid` lathes —
hollow-circle revolve for bends, overlapping straight lathes (tube + socket
cups) for runs, reducers, branches and cleanouts. No booleans, no tessellation;
bends match the measured Ostendorf reference at IoU ≥ 0.97 in all three axes.
KG approximate fittings (`geometrie.py`, `pp_geometrie.py` legacy meshes) remain
explicitly approximate, not manufacturing geometry.

Run checks with `.venv/bin/python -m pytest tests -q`. Bonsai Project Library UI
validation still requires an active Blender/Bonsai bridge.
