# Rev-B generation scripts

One-shot scripts used to derive the rev-B schematic and PCB from the rev-A
project (`../../Brushograf_PCB-china/`). They are kept for reference and so the
revision can be regenerated or audited; ordinary further editing should happen
in KiCad, not here.

Run order, starting from a fresh copy of the rev-A `.kicad_sch` / `.kicad_pcb`:

1. `edit_sch.py`  - barrel-jack input protection, sheet -> A2
2. `edit_sch2.py` - USB-C PD input, both buck converters, ESP power switch,
                    RJ-12 pendant port, and removal of the old linear regulator
3. `edit_pcb.py`  - places the input-protection parts on the board and re-nets
                    every pad from the exported netlist

Between steps 2 and 3, export the netlist:

    kicad-cli sch export netlist --format kicadsexpr -o revB.net Brushograf_PCB-revB.kicad_sch

Support modules: `kisexp.py` (S-expression reader/writer), `symlib.py` (loads
library symbols and flattens `extends`), `schbuild.py` (symbol placement and
wiring by pin name), `pcbgeom.py` (board occupancy model used to check that a
footprint placement clears existing copper).
