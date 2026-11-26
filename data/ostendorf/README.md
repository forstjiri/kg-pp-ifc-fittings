# Ostendorf KG referenční mesh

Triangulované mesh ze STEP výrobce, použité **jen** pro měření a IoU testy; knihovny jsou čisté SweptSolid. Každý JSON je `[vrcholy_mm, trojúhelníky_0_bázované]`.

| článek | výrobek | článek | výrobek |
|---|---|---|---|
| 220000z | trubka DN110 | 222000z | trubka DN160 |
| 220200z / 220210z / 220220z | koleno 15/30/45° DN110 | 222200z / 222210z | koleno 15/30° DN160 |
| 220300z / 220400z | odbočka 45/87° 110/110 | 222320z / 222420z | odbočka 45/87° 160/110 |
| 222700z | excentrická redukce 160/110 | 175600z | čistící kus DN110 |

Rozměry katalogu jsou v `data/kg_ostendorf.json`; chybějící reference (mimo jiné čistící kusy 220600/221600/222600, DN200–500) jsou parametrické a označené `GeometryStatus`. IFC deklaruje milimetry, souřadnice i placementy jsou v nativních mm. Zdrojové STEP a extrakce zůstávají v lokálním `/tmp/opencode/barak-fitting-data/`; podmínky redistribuce nebyly ověřeny.
