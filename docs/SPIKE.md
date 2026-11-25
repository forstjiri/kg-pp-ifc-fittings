# SPIKE: srovnání metod generování tvarovek do IFC

**Cíl:** Vygenerovat jeden IFC4 soubor knihovny se 6 zkušebními tvarovkami (3 kolena OD110, 3 rozdvojky), aby se porovnaly 3 metody modelování těla. Pracuj VÝHRADNĚ ve své složce `tmp/agent_X/`. Spouštěj přes `/home/jirka/Projekty/tvarovky/.venv/bin/python` (ifcopenshell 0.9.0.post1, numpy).

## Povinná struktura IFC4 (stejná pro všechny)

- Jednotky SI (metry). Schéma **IFC4** (ne 4x3).
- `IfcProject` (Name `Tvarovky Spike — Agent X`), `IfcProjectLibrary` (Name `Spike Agent X | <metoda>`).
- **6× `IfcPipeFittingType`** (3 kolena PredefinedType=BEND, 3 rozdvojky PredefinedType=JUNCTION), každý s `RepresentationMaps` (IfcRepresentationMap s Body reprezentací) a Psetem `Pset_TvarovkaSpike` (Method, Norma, pozice+osa+směr+OD každého portu jako řetězce).
- **6× výskyt `IfcPipeFitting`** na mřížce (x = index × 1.2 m, y = 0), `PredefinedType` dle typu, napojený na typ.
- Na každém výskytu **`IfcDistributionPort`** pro každý konec: `PredefinedType='PIPE'`, `FlowDirection` dle zadání, `Pset_DistributionPortTypePipe.OuterDiameter` (v m), Name `SINK OD 110` / `SOURCE OD 50`, ObjectPlacement relativní k výskytu, lokální Z osy = vektor portu (outward ze těla), pozice = bod portu (v m).
- Materiál `IfcMaterial('PVC-U (KG)')` na typech (IfcRelAssociatesMaterial). Porty nikam nepřipojuj (knihovna, žádná síť).

## Společné rozměry (mm; do IFC převeď na m)

- OD110: vnější Ø 110, stěna 3.2, hrdlo: vnitřní Ø 110.4, vnější Ø 127, hloubka hrdla 66. Hrdlo na každém koncovém portu.
- OD50: vnější Ø 50, stěna 2.0, hrdlo: vnitřní Ø 50.4, vnější Ø 63, hloubka 45.
- Středový poloměr ohybu kolena OD110: R = 300.

### Kolena (vstupní port vždy (0,0,0), osa (−1,0,0), FlowDirection=SINK)

| kus | výstupní port pozice (mm) | osa (mm, jednotkový) | Flow |
|---|---|---|---|
| koleno 15° | (200, 0, 54) | (0.9659, 0, 0.2588) | SOURCE |
| koleno 45° | (160, 0, 90) | (0.7071, 0, 0.7071) | SOURCE |
| koleno 87.5° | (50, 0, 210) | (0.0436, 0, 0.9990) | SOURCE |

### Rozdvojky (vstup (0,0,0), osa (−1,0,0), SINK; hlavní výstup (260,0,0), osa (1,0,0), SOURCE, OD110)

| kus | odbočka | port pozice (mm) | osa | Flow |
|---|---|---|---|---|
| odbočka 45° nahoře | OD50 | (20, 0, 92) | (0.7071, 0, 0.7071) | SOURCE |
| odbočka 87.5° nahoře | OD50 | (60, 0, 45) | (0.0436, 0, 0.9990) | SOURCE |
| rohová 87.5° | OD110 UP | (65, 0, 65) | (0.0436, 0, 0.9990) | SOURCE |
| rohová 87.5° | OD110 VPRAVO | (65, −65, 0) | (0.0436, −0.9990, 0) | SOURCE |

Rohová = jeden kus se dvěma odbočkami (UP + VPRAVO). Hlavní tok všech kusů je rovný (vstup + hlavní výstup u rozdvojek). Barva/těsnění se nemodelují.

## Metody (každý agent jedna)

- **A — složené BRep bez boolean:** prstencové profily (IfcArbitraryClosedProfileDef / obdélníkový prstenec) extrudované (IfcExtrudedAreaSolid) a protáčené (IfcRevolvedAreaSolid) kolem středového poloměru; hrdla jako extrudované prstence. Tělo = více solid items v jedné reprezentaci, překryvy povoleny. Dokumentuj, kde se těla překrývají (např. hrdlo odbočky vs. stěna hlavního toku) a co z toho je vidět.
- **B — boolean BRep:** správný vodotěsný strom: UNION vnějších těles (válec + torusovéSegmenty + hrdlové věnce) MINUS UNION vnitřních dutin (vrty všech hrdel a toků). IfcBooleanResult/IfcBooleanClippingResult; otestuj, že ifcopenshell.geom tělo postaví bez chyby. Dokumentuj složitost a velikost.
- **C — parametrická tessellace:** IfcTriangulatedFaceSet generovaný numpy: trubní pásy, torusové segmenty (kruhový výřez sledující oblouk), hrdla s vnitřním vrtáním a upínací plochou. Svary po kapitolkách slučuj (weld), normálová konzistence není nutná. Dokumentuj počty trojúhelníků.

## Výstupy (ve své složce)

1. `generate.py` — celý generátor samostatně spustitelný (`python generate.py` vytvoří IFC vedle sebe).
2. `<metoda>.ifc` — výsledný soubor.
3. `README.md` — metoda, počet řádků kódu, úskalí, výhody/nevýhody, doporučení pro plnou knihovnu (kolena 4 úhly × 7 DN, rozdvojky ~30 permutací × 2 normy).
4. **Validace spuštěnou v generate.py a vytisknutou do stdout:**
   - soubor se načte, `ifcopenshell.validate` bez fatálních chyb,
   - `ifcopenshell.geom` postaví shape všech 6 výskytů (vypiš čas celkem), počet trojúhelníků per kus,
   - tabulka portů (kus, port, pozice, osa, flow, OD) a kontrola, že odpovídají zadání výše (tolerance 0.5 mm / 0.5°),
   - velikost souboru v kB.

## Pravidla

- Nesahej mimo `tmp/agent_X/` (ani na jiné agent_ složky, SPIKE.md, repo root).
- Nekommituj nic.
- Žádné závislosti navíc k ifcopenshell/numpy ze standardní knihovny.
- Před koncem vypiš do stdout shrnutí validace (body z kap. 4).
