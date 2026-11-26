# Parametrické IFC tvarovky

```sh
.venv/bin/python generate_all.py            # obě knihovny
.venv/bin/python generate_all.py --preview   # + mřížka vzorků
.venv/bin/python -m pytest tests -q
```
Výstupy (IFC4 Project Library, `IfcPipeFittingType` + výskyty s porty): `out/tvarovky-EN1401-1.ifc` (KG: 15 kolen, 12 odboček, 3 redukce, 3 zátky, 3 čistící kusy = 36 typů) a `out/tvarovky-EN1451-1.ifc` (PP Master 3 Plus: 33 kolen, 35 odboček, 10 redukcí, 5 čistících kusů, 6 zátek = 90 typů).

Těla jsou přesné `IfcRevolvedAreaSolid` (SweptSolid); excentrická KG redukce používá `IfcExtrudedAreaSolidTapered` v `SolidModel` (IFC4 nedovoluje tapered v `SweptSolid`). Žádné booleany ani výrobní meshe v knihovnách — STEP slouží jen jako reference pro IoU testy. Těla se na křižovatkách překrývají. Rozměry žijí v `data/*.json` odděleně od geometrie, každá hodnota nese `status` (`catalogue`/`measured`/`estimated`), `source` a `series`; chybějící rozměry jsou v IFC v `GeometryStatus`. Porty mají `EndType` (`SOCKET`/`SPIGOT`), `InsertionDepth` (katalogové `t`) a `TakeOut`; hnízdo je v ústí, hrot o `t` uvnitř těla, osy ven.

## Moduly a nástroje

- `swept_geometrie.py` — meridiánové profily a revoluce (`Lathe`, `Taper`, `SweptBody`, `lathes_to_ifc`, `swept_bounds`)
- `ifc_util.py` — sdílené IFC4 helpery; `generator.py` — zápis a validace knihovny
- `kg_generator.py`, `pp_generator.py` — recepty per norma; `definice.py` — `Port`, `Fitting`, STEP měření
- `generate_all.py --preview` — `out/preview-*.ifc` (mřížka vzorků pro Blender)
- `tools/` zrušen; měření a kanonizace STEP je v `tests/silhouette.py`

## Ověřování

IoU testy porovnávají SweptSolid s výrobními STEP meshi po ortogonálních pohledech. Reference se kanonizuje deterministicky přes ústí (`align_by_mouths`, `canonical_two_mouths`, `align_cleanout`), bez PCA/cache. Prahy: kolena ≥ 0,85; odbočky X ≥ 0,90, Z ≥ 0,85 (220300z ≥ 0,70), Y ≥ 0,55; redukce 0,78/0,82; čistící kus 0,45/0,85.

## Otevřené body

- Objímky, větrací odbočka/UV hlavice, sifonové adaptéry, akustická objímka, revizní kus 87,5° v ose toku, 45° čistící kus
- Rovné trubky (barak generátor), EN 1329-1 (32–75), PP stará řada 2021
- Těsnicí kroužek drážky hnízda jen aproximován; KG DN125 hnízdo bez STEP měření
- Povytažení DN160 v barak pilotu (81−10) vs katalogové `t` = 84 — ověřit při spojení
- Standardní Pset_FittingBend/Junction/Transition — ověřit v cílovém IFC4

Historie: spike porovnal A (BRep), B (boolean) a C (tessellace); dnes se tvarovky modelují jako přesné revoluce z katalogových rozměrů, STEP/mesh v `data/ostendorf/` je jen referencí. Katalog Master 3 Plus (2026) je v `data/pipelife_master3plus.json`, staré články 3496… jako `LegacyArticle`.
