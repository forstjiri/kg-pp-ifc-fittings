# Missing — odložené kusy a otevřené body

Checklist věcí, které knihovna zatím **neřeší**. Odškrtnuté = doplněno.

## Rodiny kusů (odloženo)

- [ ] Objímky a dvojobjímky, posuvná/prodloužená hrdla
- [ ] Větrací odbočka a UV větrací hlavice
- [ ] Sifonové adaptéry
- [ ] Revizní kus 87,5° v ose toku (inline) a 45° varianta čistícího kusu
- [ ] Akustická objímka
- [ ] Rovné trubky (řeší barak generátor, ne tato knihovna)
- [ ] EN 1329-1 (PVC-U HT, 32–75) — případný třetí soubor

## Vyřešené v poslední iteraci

- [x] KG i PP knihovny jsou čistě SweptSolid; síťové výrobní meshe slouží jen jako testovací reference
- [x] KG 15 kolen, 12 odboček, 3 excentrické redukce, 3 zátky, 3 čistící kusy; PP kóty z příručky 2026 včetně zátek a aktuálních článků M3-…
- [x] Staré články 3496… jsou v Psetu jako `LegacyArticle`, ne jako samostatné typy
- [x] Porty mají `EndType`, `InsertionDepth` (t), `TakeOut`; natočení hnízda KGB je „measured" ze STEP, „estimated" u zbylých článků
- [x] IoU 5 kolenních referencí ≥ 0,85 ve X/Y/Z po opravě kanonického rámu (dřívější nižší skóre byla chyba registrace, ne tvaru)

## Stále otevřené

- [ ] KG odbočky: katalogní `L` nesedí na STEP (např. 160/110: 242 vs 317,5 mm); 4 články jsou `measured`, 8 `estimated` škálováním
- [ ] Těsnicí prstenec/drážka hnízda není součástí těla; jen aproximovaný profil
- [ ] KG DN125 hnízdo (límec, zóna) je jen katalogové, bez STEP měření
- [ ] Barak pilot počítá u DN160 povytažení 81 − 10 = 71 mm, katalogový `t` = 84; funkční rozdíl ověřit při spojení v projektu
- [ ] Booleany na křižovatkách odboček: tělě se překrývají, bez vnitřního vyříznutí
- [ ] IoU odboček/redukce/čistícího kusu má rodinové prahy (min 0,55/0,45/0,25), ne 0,85; je to hrubá kontrola, ne přesnost výrobku
- [ ] Funkční zkouška v Bonsai: odbočka KG 160/110 — trubka OD110 — koleno 45° OD110, porty po importu a zasunutí
- [ ] PP stará řada (2021) má „oblouk 87,5°" bez hnízda — ponecháno mimo knihovnu

## Nástroje a validace

- [ ] Pset_FittingBend / Pset_FittingJunction / Pset_FittingTransition — ověřit použitelnost v cílovém IFC4 a případně doplnit standardní vlastnosti (podnět z OSArch)
