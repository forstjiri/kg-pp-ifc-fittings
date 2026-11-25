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

- [x] KG odbočky: katalogní `L` nesedí na STEP (např. 110/110 45°: 215,7 vs 277,0 mm; 160/110: 242 vs 317,5 mm) — 4 články jsou `measured` ze STEP se správnými délkami hrot→hnízdo, 8 `estimated` škálováním
- [ ] Těsnicí prstenec/drážka hnízda není součástí těla; jen aproximovaný profil
- [ ] KG DN125 hnízdo (límec, zóna) je jen katalogové, bez STEP měření
- [ ] Barak pilot počítá u DN160 povytažení 81 − 10 = 71 mm, katalogový `t` = 84; funkční rozdíl ověřit při spojení v projektu
- [ ] Booleany na křižovatkách odboček: tělě se překrývají, bez vnitřního vyříznutí
- [x] IoU odboček: kóty opraveny ze STEP; prahy zvýšeny na X ≥ 0,90, Z ≥ 0,85 (výjimka 220300z ≥ 0,70, šikmé čelo bez zkosení), Y ≥ 0,55 (pohled podél osy brzdí aproximovaná hnízda). Redukce/čistící kus zůstávají na rodinových prazích
- [x] Vyšetřeno katalogové `z1` redukcí KG: neodpovídá STEP (34 vs 23,1 mm) ani logika rovných límců či dna → posun škálován `23,1 × DN/160`
- [x] Čistící kus: krk + víčko ze STEP 175600z (KG), PP z katalogu M3+RE (`Z1`, `Z2`, `a`); IoU 0,91/0,51/0,70
- [x] PP redukce: `Z1` od malého ústí do konce kuželu, rovný válec `L − Z1`
- [ ] Souosé kusy na jeden uzavřený profil: čistící kus ani redukce nejsou souosé (boční hrdlo, excentricita), jediný kandidát je zátka a tam je zisk jen čistota modelu — odloženo
- [x] Registrace IoU testů se počítá jednou a ukládá do `data/ostendorf/align.json` (`register_cached`); celá sada z ~10,5 min na ~4 min. Zastaralá registraci chytí prahy IoU
- [x] Funkční zkouška v Bonsai: odbočka KG 160/110 — trubka OD110 (`tools/check_connection.py` → `out/connection-check.ifc` načten v Blenderu/Bonsai), porty čtené zpět z IFC, osy opačné, hrot 66 mm uvnitř hnízda; PP mřížka zobrazena
- [ ] PP stará řada (2021) má „oblouk 87,5°" bez hnízda — ponecháno mimo knihovnu

## Nástroje a validace

- [ ] Pset_FittingBend / Pset_FittingJunction / Pset_FittingTransition — ověřit použitelnost v cílovém IFC4 a případně doplnit standardní vlastnosti (podnět z OSArch)
