# Srovnání spike metod (6 kusů, shodné zadání)

| metrika | A složené BRep | B boolean | C tessellace |
|---|---|---|---|
| validace IFC4 (express) | 0 chyb | 0 chyb (po 5 opravách) | 0 chyb |
| porty dle zadání | 16/16 | 16/16 | 16/16 (0.00 mm/0.00°) |
| bbox vs porty | sedí (218/205 mm) | **přestřeluje** (340/374 mm) | sedí (216/205 mm) |
| trojúhelníky / kus | 1040–1456 | 1362–2753 | 832–2400 |
| velikost 6 kusů | 30.7 kB | 50.8 kB | 299.3 kB |
| shapes 6 kusů | 0.06 s | 2.73 s | 1.17 s (warm-up) |
| generace modelu | 0.02 s | 0.75 s | 0.01 s mesh + 0.15 s zápis |
| řádků kódu | 731 | ~700 | 593 |
| vodotěsné tělo | ne (překryvy) | ano | ne (trim otvoru) |
| úskalí | lom 26° u 87.5° (tětiva), překryv 58 mm u rohové | biarc přestřeluje, WHERE pravidla, radiány | hrubší hrana trimu, větší soubor |

## Závěr

- **B (boolean)** zamítnut: nejvyšší složitost, nejpomalejší, geometrický solver
  přestřeluje porty; vodotěsnost knihovna nevyužije.
- **A (složené BRep)** funkční a nejmenší soubor, ale na těsných úhlech nutí
  tětivové lomy (26°) a u rohové odbočky 58 mm přesah — pro knihovnu viditelné
  artefakty.
- **C (tessellace)** vybrán jako základ: přesné porty, deterministická generace
  bez geometrického kernelu, trim otvoru odbočky parametricky, konzistence
  s dnešními tessellovanými katalogovými tvarovkami v barak pilotu a data
  (vertices/faces) jdou přímo použít i pro `add_catalogue_fitting`.
  Nevýhoda: ~50 kB/kus (při ~100 kusech řádově jednotky MB) a otevřená síť.

## Korekce po vizuální kontrole

Výběr C platí pro **výstupní IFC tessellaci**, ne pro použití geometrie
z `agent_C/generate.py`. Jeho tvary vznikly ze spike portů a zjednodušených
rozměrů, ne z katalogových dat; náhled odhalil nepřesné napojení a hrubé,
uměle trimované otvory. Plná knihovna proto převezme skutečné výrobní STEP/mesh
modely, kde jsou dostupné, a převede je na `IfcTriangulatedFaceSet`. Parametrický
mesh zůstane jen fallback pro typy bez výrobního modelu. Podrobnosti a důkazy:
`tmp/MODEL_REVIEW.md`.

Sdílený IFC rámec (typy + mapované reprezentace + výskyty s porty +
IfcProjectLibrary) je u všech tří stejný — případná změna metody se dotkne jen
`geometrie.py`.
