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
    for tag in ('version', 'generator', 'generator_version', 'layer', 'attr', 'embedded_fonts'):
        for it in find(fp, tag):
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
            ['attr', 'through_hole' if thru else 'smd']]
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
R12  = 'Resistor_SMD:R_1206_3216Metric_Pad1.30x1.75mm_HandSolder'
C12  = 'Capacitor_SMD:C_1206_3216Metric_Pad1.33x1.80mm_HandSolder'
FUSE = 'Fuse:Fuse_1812_4532Metric_Pad1.30x3.40mm_HandSolder'
SOT  = 'Package_TO_SOT_SMD:SOT-23'
SOD  = 'Diode_SMD:D_SOD-123'
SMA  = 'Diode_SMD:D_SMA_Handsoldering'
C1210= 'Capacitor_SMD:C_1210_3225Metric_Pad1.33x2.70mm_HandSolder'

PLACE = [
    # input protection, on the back by the barrel jack
    ('F1',  FUSE, '1.5A',      52,   124,     0, 'B.Cu', False),
    ('Q1',  SOT,  'AO3401A',   60,   124,     0, 'B.Cu', False),
    ('D13', SOD,  'BZX84C10',  60,   128,     0, 'B.Cu', False),
    ('C7',  C12,  '10uF/50V',  63.5, 124,    90, 'B.Cu', False),
    ('R21', R12,  '100k',      66.5, 128.5,   0, 'B.Cu', False),
    ('D14', SMA,  'SS14',      77,   124,    90, 'B.Cu', False),
    ('C8',  C1210,'22uF/25V',  54.5, 128,     0, 'B.Cu', False),
]
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
