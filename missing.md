# Missing — odložené kusy a otevřené body

Checklist věcí, které knihovna zatím **neřeší**. Odškrtnuté = doplněno.

## Rodiny kusů (dohodnuto odložit)

- [ ] Objímky a dvojobjímky, posuvná/prodloužená hrdla (Master 3 Plus: „dvojité/přesuvné hrdlo", „prodloužené hrdlo")
- [ ] Větrací odbočka (ventilation branch)
- [ ] UV větrací hlavice
- [ ] Sifonové adaptéry / připojovací sifonové kusy
- [ ] Revizní kus 87.5° v ose toku s odnímatelným víčkem (inline)
- [ ] Čistící kus 45° varianta
- [ ] Akustická objímka
- [ ] Rovné trubky (řeší samostatný barak generátor, ne knihovna)

## Normy a průměry k ověření

- [x] EN 1401-1 (PVC-U KG): Ostendorf katalog potvrzuje DN/OD **125**; pole `KG_OD` je `110, 125, 160`
- [x] EN 1401-1: katalogová kolena 15°/30°/45°/67°/87° pro OD110/125/160 a odbočky 45°/87° s hlavním i bočním OD do 160 jsou zahrnuty; část geometrie je aproximovaná a označená v IFC
- [x] KG OD200–500 se v Ostendorf katalogu prodává, ale je mimo explicitní rozsah plánu EN1401-1 (`110, 160`, ověřit `125`); rozšíření vyžaduje změnu rozsahu
- [ ] EN 1329-1 (PVC-U HT) pro malé průměry PVC-U 32–75 — případný třetí soubor, zatím vynecháno
- [x] KG (EN 1401-1) čistící kus — Ostendorf KGRE články 220600/221600/222600; katalogové délky zahrnuty. Tělo a víčko jsou jen přibližná koordinační geometrie.

## Detaily napojení

- [ ] Ověřit hloubky zasunutí a rozměry hrdel pro EN 1401-1 z Ostendorf tabulek (PP Master 3 Plus máme: Lesp)
- [ ] Těsnění (prstenec) — zda modelovat jako součást těla hrdla
- [ ] Záslepky: varianta se závitem vs. hladká (dle katalogů)

## Geometrie a porty (review 2026-11)

- [ ] **PP kolena: katalogové kóty l1/l2/z1/z2 nemají v repozitáři legendu a čísla jsou navzájem nekonzistentní** (M3-B100/45: l1+l2=119,6 ≠ length 92). Porty kol proto berou take-outy z měřeného KG receptu, nikoli z PP tabulky. Nelze z kót jednoznačně odvodit R ohybu — totéž odůvodnění, proč KG kolena zůstávají aproximovaná.
- [ ] **KG aproximovaná kolena** zůstávají síťová (Bezier), katalogové L/z nejsou jednoznačné.
- [ ] IoU verifikace měří tessellaci OCCT kernelu (display mesh). Případný budoucí přechod na vlastní analytický sampler (swept_bounds emitující quads) + invarianty `geometry.edges == []` a objem vs. Σ Pappus (θ·A·ρ̄) ± 3 %.
- [ ] Reference IoU je "see-through" síť (bez vnitřních stěn) — Y-pohled stagnuje kolem 0,92; neladit proti ní.
- [ ] Validovat porty odboček/redukcí proti katalogovým bodům odběru (nyní převzaty 1:1 z mesh verze).
- [ ] Podrobný rozsah: PP katalog obsahuje i průměry 63/90 mimo LIBRARY_SIZES — zahrnout, jen pokud plán rozšíříme.
- [x] SweptSolid rozšířen na všechny PP rodiny: kolena, odbočky (překryv těles na křižovatce, bez booleanů), redukce, spojky, čistící kusy. KG zátka/odbočky/redukce zůstávají síťové (approx).
- [x] SOURCE port KG excentrické redukce OD160/110 ověřen: leží v rovině kompletního prstence vrcholů, soustředý.
