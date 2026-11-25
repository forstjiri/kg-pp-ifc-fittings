# Revize geometrie před plnou implementací

## Závěr

Metoda C zůstává vhodná jako **IFC reprezentace meshů**, ale `agent_C/generate.py`
není přijatelný zdroj výrobkových tvarů. Je to demonstrační konstruktor z
odhadnutých portů a rozměrů; `tessellation.ifc` se nemá použít jako geometrický
základ knihovny.

Plná implementace má nejdřív použít výrobní STEP/BIM geometrii, převést ji na
`IfcTriangulatedFaceSet` a připojit k ní ověřené porty. Parametrický mesh má být
záložní cesta jen pro kusy bez použitelného zdrojového modelu.

## Ověřené důkazy

- Náhled `agent_C/tessellation.ifc` ukazuje hrdla s ostrými přechody, umělé
  zaslepení odboček a poškozené okraje otvorů. `trim_faces()` odstraňuje celé
  trojúhelníky podle vzdálenosti jejich rohů, nikoli podle průsečnice válců;
  výsledek proto nemůže vytvořit přesný kruhový otvor.
- Specifikace spike přidělila všem kolenům i rozdvojkám zkušební polohy portů,
  nikoli katalogové rozměry. Například koleno 45° bylo zadáno jako výstup
  `(160, 0, 90)`, zatímco výrobní STEP `220220z.stp` má vlastní geometrii a
  katalogové rozměry Ostendorf `z1=25`, `z2=29`, `l1=85` mm.
- V `/tmp/opencode/barak-fitting-data/` jsou odpovídající STEP a triangulované
  JSON zdroje: mimo jiné `220200z`, `220210z`, `220220z`, `220300z`, `220400z`,
  `175600z`. V JSON jsou dvojice vrcholů/trojúhelníků připravené pro stejný typ
  mesh reprezentace jako v barak pilotu.
- `python/kanalizace-knihovna.py:add_catalogue_fitting` už v barak projektu
  řeší transformaci výrobního meshe, vkládací kotvu i porty. `kanalizace-pilot-
  kuchyn.py` používá `220220` a nastavuje porty mimo jiné z katalogového
  vrcholu/osy; tento zavedený postup je lepší výchozí bod než znovu modelovat
  koleno odhadnutou Bézierovou křivkou.
- `5.ifc` není sám o sobě univerzální katalog zdrojových tvarů: jeho 40
  tvarovek jsou jednotlivé pilotní výskyty a používají směs `CSG`,
  `AdvancedSweptSolid` a `SweptSolid`. Výrobní STEP/mesh zdroje jsou přesnější
  základ pro knihovnu než kopírování těchto kontextových výskytů.

## Opravený plán geometrie

1. Zachovat metodu C jako výstupní tessellaci IFC, ne jako příkaz konstruovat
   každý tvar z několika generických trubních pásů.
2. Pro KG importovat ověřené Ostendorf STEP/mesh zdroje a jejich katalogové
   rozměry; pro PP určit dostupné zdroje z katalogu Master 3 Plus.
3. Porty umístit na skutečné spojovací roviny výrobku, ověřit jejich osy,
   průměry a kotevní body proti STEP/katalogu.
4. Syntetickou geometrii C ponechat pouze pro typy bez zdrojového modelu;
   každý takový typ musí mít samostatný geometrický test/náhled.

Před importem zdrojových souborů do repozitáře ověřit licenci a vybrat
reprodukovatelný způsob jejich dodání. Zatím jsou zdroje v `/tmp`, takže nejde
na nich bezpečně stavět finální CLI.

## První výrobkový průchod

`definice.py`, `geometrie.py` a `generator.py` nyní tvoří ověřený průchod pro
Ostendorf `220220` (KG 45°, OD110): načtou dodaný triangulovaný STEP JSON,
použijí kotvu/orientaci a porty stávajícího barak pilotu, a vygenerují IFC4
Project Library s typem, mapovaným meshem, vzorovým výskytem a dvěma porty.

Ověření na zdroji `/tmp/opencode/barak-fitting-data/220220z.json`:

- IFC EXPRESS: 0 chyb; 1 typ, 1 výskyt, 2 porty.
- Výstupní mesh shoduje vrcholy i trojúhelníky transformovaného zdroje:
  5 230 vrcholů / 10 460 trojúhelníků.
- Obě portové roviny protínají zdrojový mesh: 43 bodů v poloměru 55.35 mm a
  84 bodů v poloměru 51.90–53.49 mm. Druhý průřez zahrnuje koncové zkosení;
  porty a osy zatím vycházejí ze zavedené transformace/pilotních metadat.
- `.venv/bin/pytest -q`: 3 passed.

Generátor zatím vytváří jeden výrobek na spuštění; negeneruje dávku typů ani
druhou normu.

## Druhá rodina: odbočka

Doplněna KGEA 45° OD160/110, čl. `222320`, z katalogového STEP mesh zdroje.
Zdrojové JSON mesh soubory pro obě ověřené tvarovky jsou nyní v
`data/ostendorf/` a SHA-256 shoduje s původními pracovními soubory.
Ostendorf katalogový řádek čl. 222320 uvádí `z1=2`, `z2=168`, `z3=159`,
`L=242` mm; definice obsahuje tři porty (průběžný OD160 + odbočka OD110).

Spuštění:

```
.venv/bin/python generator.py 222320 tmp/agent_C/ostendorf-222320.ifc
```

Výsledek: IFC4, 0 EXPRESS chyb, 3 porty; geometry-kernel shape 10 450
vrcholů / 20 904 trojúhelníků oproti zdroji 10 451 / 20 906. Dva velmi malé
trojúhelníky jsou odfiltrovány geometry kernelem; typ v IFC zachovává přesnou
topologii a souřadnice zdroje, obálka se shoduje v toleranci 0.05 mm.
Integrační testy pro koleno i odbočku procházejí.
