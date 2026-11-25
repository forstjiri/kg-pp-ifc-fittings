# Parametrické IFC tvarovky

```sh
.venv/bin/python generate_all.py            # obě knihovny
.venv/bin/python generate_all.py --preview   # + mřížka vzorků do out/preview-*.ifc
.venv/bin/python -m pytest tests -q
```

Výstupy (IFC4 Project Library, `IfcPipeFittingType` + vzorové výskyty s porty):

- `out/tvarovky-EN1401-1.ifc` — Ostendorf KG: 15 kolen, 12 odboček, 3 redukce, 3 zátky, 3 čistící kusy (36 typů, 292 kB).
- `out/tvarovky-EN1451-1.ifc` — Pipelife Master 3 Plus: 33 kolen, 35 odboček, 10 redukcí, 5 čistících kusů, 6 zátek (90 typů, 755 kB).

Obě knihovny jsou čistě `IfcRevolvedAreaSolid` (SweptSolid) — žádné `IfcTriangulatedFaceSet`, žádné booleany. Rozměry žijí v `data/kg_ostendorf.json` a `data/pipelife_master3plus.json` Odděleně od geometrie; každá hodnota nese `status` (`catalogue`/`measured`/`estimated`), `source` a `series`. Chybějící rozměry jsou v IFC v `GeometryStatus`.

Porty mají `EndType` (`SOCKET`/`SPIGOT`), `InsertionDepth` (katalogové `t`) a `TakeOut`; hnízdo je v ústí, hrot o `t` uvnitř těla. U KGB je natočení hnízda (rovně/šikmo) vlastnost článku změřená ze STEP.

Nástroje:

- `tools/measure_reference.py <mesh.json>` — ústí, osy, OD/ID výrobního STEPu.
- `tools/build_comparison.py` — `out/compare-kgb.ifc`: STEP vlevo, SweptSolid vpravo, stejný rám (KGB 15°/30°/45° OD110).
- `tools/build_preview.py --standard kg|pp|all` — mřížka vzorků pro Blender.

IoU proti STEP referencím: kolena ≥ 0,85 ve všech třech pohledech; odbočky, excentrická redukce a čistící kus mají rodinové prahy, protože jejich hnízda a křižovatky jsou approximated (viz `missing.md`).
