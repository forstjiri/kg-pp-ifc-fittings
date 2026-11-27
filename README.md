# Parametric IFC fittings

> **Status: draft / nástřel.** This is an experimental collection of parametric
> IFC4 libraries of KG and PP fittings and pipe profiles. The API, data structure
> and geometry may change without backward compatibility. It is intended for
> coordination, experiments and validation, not for manufacturing. Catalogue
> dimensions and STEP references come from manufacturer publications (Ostendorf,
> Pipelife); their redistribution terms have not been verified. Source code is
> licensed under the [MIT license](LICENSE); the data files are not relicensed.

```sh
python -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python generate_all.py            # both libraries
.venv/bin/python generate_all.py --preview   # + sample grid
.venv/bin/python -m pytest tests -q
```

Outputs (IFC4 Project Library, `IfcPipeFittingType` + occurrences with ports): `out/tvarovky-EN1401-1.ifc` (KG: 15 bends, 12 branches, 3 reducers, 3 caps, 3 cleanouts = 36 types) and `out/tvarovky-EN1451-1.ifc` (PP Master 3 Plus: 33 bends, 35 branches, 10 reducers, 5 cleanouts, 6 caps = 90 types).

Bodies are exact `IfcRevolvedAreaSolid` (SweptSolid); the eccentric KG reducer uses `IfcExtrudedAreaSolidTapered` in `SolidModel` (IFC4 does not allow tapered solids in `SweptSolid`). The libraries contain no booleans or manufacturer meshes — STEP is used only as a reference for IoU tests. Bodies overlap at junctions. Dimensions live in `data/*.json`, separate from geometry; each value carries `status` (`catalogue`/`measured`/`estimated`), `source` and `series`, and missing dimensions are marked in IFC as `GeometryStatus`. Ports have `EndType` (`SOCKET`/`SPIGOT`), `InsertionDepth` (catalogue `t`) and `TakeOut`; the socket is at the mouth, the spigot tip lies `t` inside the body, and the axes point outwards.

## Modules and tools

- `swept_geometrie.py` — meridian profiles and revolutions (`Lathe`, `Taper`, `SweptBody`, `lathes_to_ifc`, `swept_bounds`)
- `ifc_util.py` — shared IFC4 helpers; `generator.py` — library writing and validation
- `kg_generator.py`, `pp_generator.py` — recipes per standard; `definice.py` — `Port`, `Fitting`, STEP measurement
- `generate_all.py --preview` — `out/preview-*.ifc` (sample grid for Blender)
- `generate_all.py --grid` — `out/grid-kg.ifc` (columns 110/125/160) and `out/grid-pp.ifc` (32/40/50/75/90/110); every article has its own type with ports on both the type and the occurrence, plus an `IfcPipeSegmentType` with a hollow profile for pulling networks in Bonsai. The grids use the IFC unit **METRE** (catalogue libraries stay in mm) so that Bonsai 5.3 inserts from types at the correct scale.
- `grid.py` — layout and validation of the catalogue grids; see `missing.md` for missing ranges
- `tools/` has been removed; STEP measurement and canonicalisation live in `tests/silhouette.py`

## Verification

IoU tests compare SweptSolid bodies with manufacturer STEP meshes from orthogonal views. The reference is canonicalised deterministically via the mouths (`align_by_mouths`, `canonical_two_mouths`, `align_cleanout`), without PCA or caching. Thresholds: bends ≥ 0.85; branches X ≥ 0.90, Z ≥ 0.85 (220300z ≥ 0.70), Y ≥ 0.55; reducers 0.78/0.82; cleanouts 0.45/0.85.

## Open items

- Collars, vent branch/UV cap, siphon adapters, acoustic collar, 87.5° cleanout in the flow axis, 45° cleanout
- Straight pipes (barak generator), EN 1329-1 (32–75), older PP series 2021; Ostendorf HT only branch 113410 is included (see `missing.md`)
- Socket groove sealing ring only approximated; KG DN125 socket without STEP measurement
- DN160 pull-out in the barak pilot (81−10) vs catalogue `t` = 84 — verify when connecting
- Standard `Pset_FittingBend`/`Junction`/`Transition` — verify in the target IFC4

History: a spike compared A (BRep), B (booleans) and C (tessellation); fittings are now modelled as exact revolutions from catalogue dimensions, and the STEP/mesh data in `data/ostendorf/` is only a reference. The Master 3 Plus catalogue (2026) is in `data/pipelife_master3plus.json`, with older articles 3496… stored as `LegacyArticle`.

## KG type codes (DE vs CZ)

German and Czech catalogues use the same Ostendorf type codes; only the descriptive names differ. The `Article` stored in `Pset_Tvarovka.CatalogArticle` is the manufacturer article number (e.g. `220300`), identical in both languages. Resellers use their own codes — DEK KGEA 110/110 45° is `4410050076` (catalogue code `44F22`) — which are not article numbers.

| Code  | German (Ostendorf catalogue) | Czech                | This library                                |
|-------|------------------------------|----------------------|---------------------------------------------|
| KGB   | Bogen                        | koleno               | `IfcPipeFittingType/BEND`                   |
| KGEA  | Abzweig                      | odbočka              | `IfcPipeFittingType/JUNCTION`               |
| KGR   | Reduktion                    | redukce              | `IfcPipeFittingType/TRANSITION`             |
| KGM   | Muffenstopfen                | hrdlová zátka        | `IfcPipeFittingType/USERDEFINED` (cap)      |
| KGK   | Kappe                        | víčko                | `IfcPipeFittingType/USERDEFINED` (cap)      |
| KGRE  | Reinigungsrohr               | čisticí kus          | `IfcPipeFittingType/USERDEFINED` (cleanout) |
| KGUG  | Anschluss an Guss            | přechodka litina/PVC | not included                                |

Caps and cleanouts share `USERDEFINED` as the IFC `PredefinedType`; the distinction is kept in `Name` and `CatalogArticle`. The library covers DN110/125/160; larger sizes are listed in `missing.md`.

Sources: [Ostendorf KG catalogue (DE, 07/2019)](https://ostendorf-osma.de/uploads/page/translation/de/catalog_pdf/90/DE_KG_KATALOG_OSMA_7_2019.pdf), [Ostendorf price list 2026](https://www.emax-haustechnik.de/shop/images/products/media/hersteller/kgrohr-katalog.pdf).
