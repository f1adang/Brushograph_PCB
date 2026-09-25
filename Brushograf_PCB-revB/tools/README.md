# Rev-B generation scripts

One-shot scripts used to derive the rev-B schematic and PCB from the rev-A
project (`../../Brushograf_PCB-china/`). They are kept for reference and so the
revision can be regenerated or audited; ordinary further editing should happen
in KiCad, not here.

Run order, starting from a fresh copy of the rev-A `.kicad_sch` / `.kicad_pcb`:

1. `edit_sch.py`  - sheet -> A2, motor-rail bulk cap, 5V system rail
2. `edit_sch2.py` - USB-C PD input, both buck converters, ESP lever switch,
                    RJ-12 pendant port, and removal of the old linear regulator
                    and barrel jack
3. `edit_pcb.py`  - grows the outline 25mm upward, places all 36 new parts
                    (auto-nudging each clear of existing copper) and re-nets
                    every pad from the exported netlist
4. `fillzones.py` - refills the copper pours. Needs KiCad's bundled Python:
                    /Applications/KiCad/KiCad.app/Contents/Frameworks/\
                    Python.framework/Versions/3.9/bin/python3

Between steps 2 and 3, export the netlist:

    kicad-cli sch export netlist --format kicadsexpr -o revB.net Brushograf_PCB-revB.kicad_sch

Support modules: `kisexp.py` (S-expression reader/writer), `symlib.py` (loads
library symbols and flattens `extends`), `schbuild.py` (symbol placement and
wiring by pin name), `pcbgeom.py` (board occupancy model used to check that a
footprint placement clears existing copper).
