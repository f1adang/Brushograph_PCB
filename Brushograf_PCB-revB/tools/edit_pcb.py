#!/usr/bin/env python3
"""Rev-B PCB edits: place the power-protection parts, re-net from the schematic."""
import sys, os, uuid as _uuid, copy
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from kisexp import parse, dump, find, first, prop, propval, Str, f

PRJ = '/Users/gandalf/Documents/fun/Brushograph_PCB/Brushograf_PCB-revB/'
PCB = PRJ + 'Brushograf_PCB-revB.kicad_pcb'
SCH = PRJ + 'Brushograf_PCB-revB.kicad_sch'
NET = '/private/tmp/claude-502/-Users-gandalf-Documents-fun-Brushograph-PCB/7394b9a7-8b20-41b6-944a-8157dbeae41d/scratchpad/revB.net'
FP_DIR = '/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints/'

_ns = _uuid.UUID('6f1c4a2e-1111-4000-8000-000000000000'); _n = [0]
def uid(tag=''):
    _n[0] += 1
    return Str(str(_uuid.uuid5(_ns, f'{tag}:{_n[0]}')))

def fmt(v):
    return f'{round(float(v), 6):g}'

# ---------------------------------------------------------------- inputs
sch = parse(open(SCH).read())
sym_uuid = {}
for s in find(sch, 'symbol'):
    r = propval(s, 'Reference')
    if r and not r.startswith(('#PWR', '#FLG')):
        sym_uuid[r] = str(first(s, 'uuid')[1])

netlist = parse(open(NET).read())
pad_net = {}
for n in find(first(netlist, 'nets'), 'net'):
    name = str(first(n, 'name')[1])
    for nd in find(n, 'node'):
        pad_net[(str(first(nd, 'ref')[1]), str(first(nd, 'pin')[1]))] = name

pcb = parse(open(PCB).read())


# ------------------------------------------------- grow the board upward
# The RJ-12 needs ~19mm of depth behind the top edge and the existing strip
# only has ~11mm before the back-side SPI tracks, so the outline gains 25mm
# at the top. Everything already placed keeps its coordinates.
GROW_UP = 25.0
MID_Y = 109.85
for it in pcb:
    if isinstance(it, list) and it[0] == 'gr_line':
        ly = first(it, 'layer')
        if ly and str(ly[1]) == 'Edge.Cuts':
            for key in ('start', 'end'):
                q = first(it, key)
                if q and float(q[2]) < MID_Y:
                    q[2] = fmt(float(q[2]) - GROW_UP)
for fp in find(pcb, 'footprint'):
    if str(fp[1]).endswith('brushograf_edgeCut'):
        for p in find(fp, 'pad'):          # the two top mounting holes move too
            a = first(p, 'at')
            if float(a[2]) < 0:
                a[2] = fmt(float(a[2]) - GROW_UP)
# The GND pours were drawn overhanging the old edge and clipped by it, so they
# get the same stretch - otherwise they would stop partway up the new strip.
for z in find(pcb, 'zone'):
    if first(z, 'keepout'):
        continue
    poly = first(z, 'polygon')
    if not poly:
        continue
    for pt in first(poly, 'pts')[1:]:
        if pt[0] == 'xy' and float(pt[2]) < MID_Y:
            pt[2] = fmt(float(pt[2]) - GROW_UP)
    for filled in find(z, 'filled_polygon'):   # stale fill, pcbnew refills it
        z.remove(filled)
print(f'board grown {GROW_UP:g}mm upward')

# ------------------------------------------------- drop parts that left the schematic
sch_refs = set(sym_uuid)
import re as _re
def _is_designator(r):
    return bool(_re.fullmatch(r'[A-Z]{1,3}\d+', r or ''))
# only real designators: the logo and edge-cut footprints are "Ref**" and stay put
gone = [fp for fp in find(pcb, 'footprint')
        if _is_designator((propval(fp, 'Reference') or '').strip())
        and (propval(fp, 'Reference') or '').strip() not in sch_refs]
for fp in gone:
    pcb.remove(fp)
print('removed footprints no longer in the schematic:',
      [propval(fp, 'Reference') for fp in gone] or 'none')

# ------------------------------------------------- drop the invalidated tracks
ids = {int(x[1]): str(x[2]) for x in find(pcb, 'net')}
STALE = {'5V-EXT', 'Net-(J7-Pin_1)'}
dead = [s for s in find(pcb, 'segment') if ids[int(first(s, 'net')[1])] in STALE]
for s in dead:
    pcb.remove(s)
print(f'removed {len(dead)} track segments on the restructured power nets')

# ---------------------------------------------------------------- flip helper
def swap_layer(name):
    if name.startswith('F.'):
        return 'B.' + name[2:]
    if name.startswith('B.'):
        return 'F.' + name[2:]
    return name

def flip(node):
    """Mirror a footprint's contents to the back, as KiCad stores them."""
    for it in node:
        if not isinstance(it, list):
            continue
        tag = it[0]
        if tag in ('at', 'start', 'end', 'center', 'mid', 'xy') and len(it) >= 3:
            it[2] = fmt(-float(it[2]))
            if tag == 'at' and len(it) >= 4:
                it[3] = fmt(-float(it[3]) % 360)
        elif tag == 'layer' and len(it) >= 2:
            it[1] = Str(swap_layer(str(it[1])))
        elif tag == 'layers':
            for i in range(1, len(it)):
                it[i] = Str(swap_layer(str(it[i])))
        elif tag == 'effects':
            j = first(it, 'justify')
            if j:
                if 'mirror' not in [str(x) for x in j[1:]]:
                    j.append('mirror')
            else:
                it.append(['justify', 'mirror'])
        if tag not in ('at', 'start', 'end', 'center', 'mid', 'xy', 'layer', 'layers'):
            flip(it)

def make_fp(libmod, ref, value, x, y, ang, layer, thru):
    lib, mod = libmod.split(':')
    fp = parse(open(f'{FP_DIR}{lib}.pretty/{mod}.kicad_mod').read())
    fp[0] = 'footprint'
    fp[1] = Str(libmod)
    # strip library bookkeeping we re-supply ourselves
    lib_attr = None
    for tag in ('version', 'generator', 'generator_version', 'layer', 'attr', 'embedded_fonts'):
        for it in find(fp, tag):
            if tag == 'attr':
                lib_attr = list(it)
            fp.remove(it)
    for p in find(fp, 'property'):
        if str(p[1]) in ('Reference', 'Value'):
            p[2] = Str(ref if str(p[1]) == 'Reference' else value)
    if layer == 'B.Cu':
        flip(fp)
    body = [x for x in fp[2:]]
    out = ['footprint', Str(libmod),
           ['layer', Str(layer)],
           ['uuid', uid('fp' + ref)],
           ['at', fmt(x), fmt(y)] + ([fmt(ang)] if ang else [])]
    out += body
    out += [['path', Str('/' + sym_uuid[ref])],
            ['sheetname', Str('/')],
            ['sheetfile', Str('Brushograf_PCB-revB.kicad_sch')],
            lib_attr if lib_attr else ['attr', 'through_hole' if thru else 'smd']]
    # fine-pitch connectors have sub-0.25mm mask webs between contacts by
    # design; tell DRC those bridges are intentional
    if ref in ('J12',):
        at = first(out, 'attr')
        if at is not None and 'allow_soldermask_bridges' not in [str(x) for x in at[1:]]:
            at.append('allow_soldermask_bridges')
    # fresh uuids everywhere
    def reuid(n):
        for it in n:
            if isinstance(it, list):
                if it[0] == 'uuid':
                    it[1] = uid('x')
                else:
                    reuid(it)
    reuid(out[5:])
    # pad rotation follows the footprint
    for p in find(out, 'pad'):
        pa = first(p, 'at')
        if ang and len(pa) >= 4:
            pa[3] = fmt((float(pa[3]) + (ang if layer == 'F.Cu' else -ang)) % 360)
    return out

# ---------------------------------------------------------------- placements
R06   = 'Resistor_SMD:R_0603_1608Metric_Pad0.98x0.95mm_HandSolder'
R12   = 'Resistor_SMD:R_1206_3216Metric_Pad1.30x1.75mm_HandSolder'
C06   = 'Capacitor_SMD:C_0603_1608Metric_Pad1.08x0.95mm_HandSolder'
C12   = 'Capacitor_SMD:C_1206_3216Metric_Pad1.33x1.80mm_HandSolder'
C1210 = 'Capacitor_SMD:C_1210_3225Metric_Pad1.33x2.70mm_HandSolder'
FUSE18= 'Fuse:Fuse_1812_4532Metric_Pad1.30x3.40mm_HandSolder'
FUSE12= 'Fuse:Fuse_1206_3216Metric_Pad1.42x1.75mm_HandSolder'
SOT6  = 'Package_TO_SOT_SMD:SOT-23-6'
SOD323= 'Diode_SMD:D_SOD-323'
SMA   = 'Diode_SMD:D_SMA_Handsoldering'
LFP   = 'Inductor_SMD:L_7.3x7.3_H4.5'
SSOP10= 'Package_SO:SSOP-10-1EP_3.9x4.9mm_P1mm_EP2.1x3.3mm'
USBC  = 'Connector_USB:USB_C_Receptacle_GCT_USB4105-xx-A_16P_TopMnt_Horizontal'
RJ12FP= 'Connector_RJ:RJ12_Amphenol_54601-x06_Horizontal'
LEVER = 'Button_Switch_THT:SW_Lever_1P2T_NKK_GW12LxH'
TRIM  = 'Potentiometer_THT:Potentiometer_Bourns_3296W_Vertical'

# ref, footprint, value, x, y, rot, layer, through-hole, may overhang the edge
WANT = [
    # edge-mounted connectors and the panel switch
    # rot 270 points both actuator and receptacle opening off the left edge
    ('SW1', LEVER, 'ESP POWER',    56.0,  66.0, 270, 'F.Cu', True,  True),
    ('J12', USBC,  'USB-C PD in',  49.5,  79.0, 270, 'F.Cu', True,  True),
    ('J13', RJ12FP,'Pendant',     150.0,  63.0,   0, 'F.Cu', True,  True),
    # USB-C input: fuse and bulk, on the back behind the receptacle
    ('F1',  FUSE18,'1.5A',         64.0,  66.0,   0, 'B.Cu', False, False),
    ('C7',  C12,   '10uF/35V',     72.0,  66.0,   0, 'B.Cu', False, False),
    ('C10', C1210, '22uF/35V',     80.0,  66.0,   0, 'B.Cu', False, False),
    # PD sink
    ('U6',  SSOP10,'CH224K',       70.0,  78.0,   0, 'B.Cu', False, False),
    ('R22', R06,   '5.1k',         62.0,  73.0,   0, 'B.Cu', False, False),
    ('R23', R06,   '5.1k',         62.0,  76.0,   0, 'B.Cu', False, False),
    ('C9',  C06,   '1uF',          62.0,  79.0,   0, 'B.Cu', False, False),
    ('R24', R06,   '6.8k',         62.0,  82.0,   0, 'B.Cu', False, False),
    ('D17', 'LED_SMD:LED_0805_2012Metric_Pad1.15x1.40mm_HandSolder',
                   'PD OK',        80.0,  78.0,   0, 'B.Cu', False, False),
    ('R25', R06,   '1k',           86.0,  78.0,   0, 'B.Cu', False, False),
    ('D14', SMA,   'SS14',         70.0,  83.0,   0, 'B.Cu', False, False),
    # motor buck
    ('U7',  SOT6,  'TPS54202',    108.0,  68.0,   0, 'B.Cu', False, False),
    ('C11', C1210, '10uF/35V',     99.0,  68.0,   0, 'B.Cu', False, False),
    ('C12', C06,   '100nF',       108.0,  73.0,   0, 'B.Cu', False, False),
    ('L1',  LFP,   '10uH 3.5A',   118.0,  68.0,   0, 'B.Cu', False, False),
    ('C13', C1210, '22uF/25V',    128.0,  68.0,   0, 'B.Cu', False, False),
    ('C14', C1210, '22uF/25V',    136.0,  68.0,   0, 'B.Cu', False, False),
    ('R26', R06,   '100k',        128.0,  74.0,   0, 'B.Cu', False, False),
    ('R27', R06,   '7.5k',        134.0,  74.0,   0, 'B.Cu', False, False),
    ('RV1', TRIM,  '10k',         128.0,  80.0,   0, 'F.Cu', True,  False),
    # logic buck
    ('U8',  SOT6,  'TPS54202',    172.0,  68.0,   0, 'B.Cu', False, False),
    ('C15', C1210, '10uF/35V',    164.0,  68.0,   0, 'B.Cu', False, False),
    ('C16', C06,   '100nF',       172.0,  73.0,   0, 'B.Cu', False, False),
    ('L2',  LFP,   '15uH 2A',     182.0,  68.0,   0, 'B.Cu', False, False),
    ('C17', C1210, '22uF/25V',    192.0,  68.0,   0, 'B.Cu', False, False),
    ('R28', R06,   '75k',         192.0,  74.0,   0, 'B.Cu', False, False),
    ('R29', R06,   '10k',         198.0,  74.0,   0, 'B.Cu', False, False),
    # pendant protection, near J13
    ('F2',  FUSE12,'0.5A',        168.0,  80.0,   0, 'B.Cu', False, False),
    ('R30', R06,   '330',         176.0,  80.0,   0, 'B.Cu', False, False),
    ('R31', R06,   '330',         182.0,  80.0,   0, 'B.Cu', False, False),
    ('D18', SOD323,'PESD5V0S1BA', 176.0,  83.5,   0, 'B.Cu', False, False),
    ('D19', SOD323,'PESD5V0S1BA', 182.0,  83.5,   0, 'B.Cu', False, False),
    # motor-rail bulk, back side by the driver sockets
    ('C8',  C1210, '22uF/25V',     54.5, 128.0,   0, 'B.Cu', False, False),
]

import pcbgeom, math
BOARD = pcbgeom.Board(pcb, skip_refs={r for r, *_ in WANT},
                      limits=(45.7, 241.6, 61.85 + 1.0, 132.85))
PLACE = []
for ref, fpname, val, x, y, ang, layer, thru, over in WANT:
    best = None
    for radius in (0, 1, 2, 3, 4, 6, 8, 11, 14):
        cands = [(x, y)] if radius == 0 else [
            (x + radius * math.cos(t * math.pi / 8), y + radius * math.sin(t * math.pi / 8))
            for t in range(16)]
        for cx, cy in cands:
            cx, cy = round(cx, 2), round(cy, 2)
            if not BOARD.check(fpname, cx, cy, ang, layer, overhang=over):
                best = (cx, cy)
                break
        if best:
            break
    if best is None:
        raise SystemExit(f'ERROR: no clear spot found for {ref}')
    if (best[0], best[1]) != (x, y):
        print(f'  nudged {ref}: ({x},{y}) -> {best}')
    BOARD.occupy(fpname, best[0], best[1], ang, 'BOTH' if thru else layer)
    PLACE.append((ref, fpname, val, best[0], best[1], ang, layer, thru))

anchor = pcb.index(find(pcb, 'footprint')[-1]) + 1
new = [make_fp(lm, ref, val, x, y, a, lay, thru)
       for ref, lm, val, x, y, a, lay, thru in PLACE]
pcb[anchor:anchor] = new
print(f'placed {len(new)} new footprints')

# ------------------------------------------------- re-net every pad from the schematic
name2id = {str(x[2]): int(x[1]) for x in find(pcb, 'net')}
nxt = max(name2id.values()) + 1
used = set()
missing = []
for fp in find(pcb, 'footprint'):
    ref = propval(fp, 'Reference')
    for p in find(fp, 'pad'):
        num = str(p[1])
        nm = pad_net.get((ref, num))
        if nm is None:
            if num != '""' and ref and not str(fp[1]).endswith(('Logo', 'Logo2', 'edgeCut', 'logos')):
                missing.append(f'{ref}.{num}')
            continue
        if nm not in name2id:
            name2id[nm] = nxt; nxt += 1
        used.add(nm)
        nd = first(p, 'net')
        if nd:
            nd[1] = str(name2id[nm]); nd[2] = Str(nm)
        else:
            idx = len(p) - 1
            for k, it in enumerate(p):
                if isinstance(it, list) and it[0] in ('roundrect_rratio', 'layers', 'drill'):
                    idx = k
            p.insert(idx + 1, ['net', str(name2id[nm]), Str(nm)])
if missing:
    print('  pads with no schematic net:', ', '.join(sorted(set(missing))[:12]))

# rebuild the net table, keeping every id that tracks/zones already reference
for x in list(find(pcb, 'net')):
    pcb.remove(x)
ins = pcb.index(first(pcb, 'setup')) + 1
for nm, i in sorted(name2id.items(), key=lambda kv: kv[1]):
    pcb.insert(ins, ['net', str(i), Str(nm)])
    ins += 1
print(f'net table: {len(name2id)} nets')

open(PCB, 'w').write(dump(pcb) + '\n')
print('wrote', PCB)
