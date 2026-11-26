# Missing dimensions and ranges

## PP (EN 1451-1) — DN20 and DN25

The source catalogue `data/pipelife_master3plus.json` (Technisches Handbuch MASTER 3 PLUS, 2026)
starts at DN32 (`dn_od` 32, actual OD 33.0 mm). DN20 and DN25 dimensions are absent from it:
pipe OD and wall thickness, socket OD, insertion depth `t`, lengths `L`, `l1`, `l2`,
dimensions `z1`/`z2`/`z3` and article numbers are all missing. The PP grid therefore starts
at DN32 and the DN20/DN25 columns are left empty rather than filled with estimates.

Adding DN20/DN25 requires a documented source (a drawing or technical catalogue) with the
following values for each diameter:

- pipe OD, wall thickness, socket OD, socket insertion depth `t`;
- catalogue lengths and dimensions `L`, `l1`, `l2`, `z1`, `z2`, `z3` for bends, branches,
  reducers, cleanouts and caps;
- article designations and the status/source/series of each dimension.

## Other open items

- The KG DN125 socket has no STEP reference; its profile is derived from measurements on DN110 and DN160.
- The sealing ring in the socket groove is only approximated.
- DN160 pull-out in the barak pilot (81−10 mm) does not match the catalogue `t` of 84 mm.
- Standard `Pset_FittingBend/Junction/Transition` still needs verification in the target IFC4.
- Collars, vent branch/UV cap, siphon adapters, acoustic collar, 87.5° cleanout in the flow axis
  and 45° cleanout have no documented dimensions in the catalogue.
- Straight pipes outside the grid ranges and EN 1329-1 (32–75) are not included.
