# Master 3 Plus katalog — reference pro definice.py

Zdroj: `/tmp/opencode/barak-fitting-data/pipelife-master3plus-cz.pdf` (PP, EN 1451-1).
Layout verze: `/tmp/opencode/pipelife-master3plus-layout.txt` (pdftotext -layout).
Surový extract řádků: `/tmp/opencode/tvarovky-katalog-rows.txt` (regex, 93 řádků, kotva = kód 349610xxxx).

## Sekce (řádky layout txt)

| řádek | rodina | podvarianty |
|---|---|---|
| 663 | koleno | 15°, 30°, 45°, oblouk 87.5°, LONG BENDS (prodloužené) |
| 763 | odbočka | 45°, 67.5°, 87.5°, 87.5° s prodlouženým hrdlem |
| 837 | dvojitá odbočka 87.5°, dvojitá rohová odbočka 87.5° | |
| 894 | zátka do hrdla (záslepka) | |
| 925–1014 | redukce, krátká redukce, vnitřní redukce, připojovací sifonový kus | |
| 1015 | čistící kus (access/inspection pipe) | DN 50–160 |
| 1050 | ventilační odbočka, UV větrací hlavice (odloženo, viz missing.md) | |

## Sloupce

- `DN/OD` = jmenovitý/vnější Ø; `d` = skutečný vnější Ø (110 → 111.3), `Dmax` = vnější Ø hrdla (127)
- `L1` `L2` `L3` = délky portů/úseků; `Lesp` = hloubka zasunutí; `Z1` `Z2` `Z3` = ofsety portu
- `Kg/ks` hmotnost; `Kód` = číslo článku (349610xxxx) — kotva pro přiřazení do podtabulky

## Parser (implementační plán)

1. Regex nad layout txt: `(\d+) (d) (Dmax) (L1) (L2) (Lesp) (Z1) (Z2) (hmotnost) (kód)` — hotový (viz extract).
2. Přiřazení do podtabulky (úhel/varianta) podle x-pozice kódu vs. x-pozice nejbližší hlavičky nad ním (`α = 45°`, `87,5º BRANCHES` atd.).
3. Test proti známým řádkům: `3496103039` = koleno 15° DN110: d=111.3, Dmax=127, L1=66, L2=60.6, Lesp=76, Z1=10, Z2=15; `3496102512` = odbočka 87.5° 110/50: Z1=−16, Z2=92, Z3=103.
4. Do `definice.py` jako dict kód → rozměry + rodina + úhel + DN kombinace; permutace se řídí existujícími kódy (jen prodávané kusy).

## Poznámky

- PVC-U KG (EN 1401-1, Ostendorf): rozměry řešit zvlášť z `/tmp/opencode/barak-fitting-data/ostendorf-osma-kg.txt` (1750 ř., anglická verze) + stažené STEP/JSON; hloubky zasunutí ověřit (viz missing.md).
- Master 3 Plus zátka: řádek 894 — jediná „záslepka" v PP katalogu (do hrdla).
