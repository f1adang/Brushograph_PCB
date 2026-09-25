#!/usr/bin/env python3
"""Rev-B schematic edits: sheet size, motor-rail bulk cap, 5V system rail."""
import sys, os, uuid as _uuid
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from kisexp import parse, dump, find, first, prop, propval, Str
import symlib

SCH = '/Users/gandalf/Documents/fun/Brushograph_PCB/Brushograf_PCB-revB/Brushograf_PCB-revB.kicad_sch'
doc = parse(open(SCH).read())
SHEET_UUID = str(first(doc, 'uuid')[1])

# deterministic UUIDs so re-running the script is reproducible
_ns = _uuid.UUID('6f1c4a2e-0000-4000-8000-000000000000')
_n = [0]
def uid(tag=''):
    _n[0] += 1
    return Str(str(_uuid.uuid5(_ns, f'{tag}:{_n[0]}')))

def R(px, py, rot):
    """library pin coords -> sheet offset for a symbol rotated `rot` degrees"""
    x, y = px, -py
    for _ in range((int(rot) // 90) % 4):
        x, y = y, -x
    return x, y

# ---------------------------------------------------------------- primitives
def wire(x1, y1, x2, y2):
    return ['wire',
            ['pts', ['xy', fmt(x1), fmt(y1)], ['xy', fmt(x2), fmt(y2)]],
            ['stroke', ['width', '0'], ['type', 'default']],
            ['uuid', uid('w')]]

def junction(x, y):
    return ['junction', ['at', fmt(x), fmt(y)], ['diameter', '0'],
            ['color', '0', '0', '0', '0'], ['uuid', uid('j')]]

def glabel(name, x, y, rot, shape='input'):
    just = 'right' if rot == 180 else 'left'
    return ['global_label', Str(name), ['shape', shape],
            ['at', fmt(x), fmt(y), str(int(rot))],
            ['fields_autoplaced', 'yes'],
            ['effects', ['font', ['size', '1.27', '1.27']], ['justify', just]],
            ['uuid', uid('gl')],
            ['property', Str('Intersheetrefs'), Str('${INTERSHEET_REFS}'),
             ['at', fmt(x), fmt(y), '0'],
             ['effects', ['font', ['size', '1.27', '1.27']], ['justify', just], ['hide', 'yes']]]]

def fmt(v):
    s = f'{round(float(v), 4):g}'
    return s

def mkprop(name, value, x, y, rot=0, hide=False, italic=False, justify=None):
    eff = ['effects', ['font', ['size', '1.27', '1.27']] + ([['italic', 'yes']] if italic else [])]
    if justify:
        eff.append(['justify', justify])
    if hide:
        eff.append(['hide', 'yes'])
    return ['property', Str(name), Str(value), ['at', fmt(x), fmt(y), str(int(rot))], eff]

used_libs = {}
def symbol(lib, name, ref, value, footprint, x, y, rot=0, ref_dy=None, val_dy=None,
           hide_value=False, dnp=False, ref_at=None, val_at=None):
    # default text placement: above/below for horizontal parts, to the right for
    # vertical ones, so the reference and the value never land on each other
    if ref_at is None or val_at is None:
        if int(rot) % 180 == 90:
            auto_ref, auto_val = (x, y - 3.81, None), (x, y + 3.81, None)
        else:
            auto_ref, auto_val = (x + 2.54, y - 1.27, 'left'), (x + 2.54, y + 1.27, 'left')
        ref_at = ref_at or auto_ref
        val_at = val_at or auto_val
    key = f'{lib}:{name}'
    if key not in used_libs:
        used_libs[key] = symlib.load(lib, name)
    s = symlib.load(lib, name)
    pinnums = [p[0] for p in symlib.pins(s)]
    node = ['symbol',
            ['lib_id', Str(key)],
            ['at', fmt(x), fmt(y), str(int(rot))],
            ['unit', '1'],
            ['exclude_from_sim', 'no'], ['in_bom', 'yes'], ['on_board', 'yes'],
            ['dnp', 'yes' if dnp else 'no'],
            ['uuid', uid('s' + ref)],
            mkprop('Reference', ref, ref_at[0], ref_at[1], 0, justify=ref_at[2]),
            mkprop('Value', value, val_at[0], val_at[1], 0, hide=hide_value,
                   justify=val_at[2]),
            mkprop('Footprint', footprint, x, y, 0, hide=True, italic=True),
            mkprop('Datasheet', '~', x, y, 0, hide=True),
            mkprop('Description', '', x, y, 0, hide=True)]
    for pn in pinnums:
        node.append(['pin', Str(pn), ['uuid', uid('p')]])
    node.append(['instances', ['project', Str(''),
                 ['path', Str('/' + SHEET_UUID), ['reference', Str(ref)], ['unit', '1']]]])
    return node

pwr_n = [max(int(propval(s, 'Reference')[4:])
             for s in find(doc, 'symbol')
             if (propval(s, 'Reference') or '').startswith('#PWR'))]
def gnd(x, y, rot=0):
    pwr_n[0] += 1
    ref = f'#PWR{pwr_n[0]}'
    node = ['symbol', ['lib_id', Str('power:GND')],
            ['at', fmt(x), fmt(y), str(int(rot))], ['unit', '1'],
            ['exclude_from_sim', 'no'], ['in_bom', 'yes'], ['on_board', 'yes'],
            ['dnp', 'no'], ['fields_autoplaced', 'yes'], ['uuid', uid('g')],
            mkprop('Reference', ref, x, y + 6.35, 0, hide=True),
            mkprop('Value', 'GND', x, y + 5.08, 0),
            mkprop('Footprint', '', x, y, 0, hide=True),
            mkprop('Datasheet', '', x, y, 0, hide=True),
            mkprop('Description', '', x, y, 0, hide=True),
            ['pin', Str('1'), ['uuid', uid('p')]],
            ['instances', ['project', Str('Brusograf_PCB'),
             ['path', Str('/' + SHEET_UUID), ['reference', Str(ref)], ['unit', '1']]]]]
    return node

flg_n = [0]
def pwrflag(x, y, rot=0):
    flg_n[0] += 1
    ref = f'#FLG{flg_n[0]}'
    used_libs['power:PWR_FLAG'] = symlib.load('power', 'PWR_FLAG')
    return ['symbol', ['lib_id', Str('power:PWR_FLAG')],
            ['at', fmt(x), fmt(y), str(int(rot))], ['unit', '1'],
            ['exclude_from_sim', 'no'], ['in_bom', 'yes'], ['on_board', 'yes'],
            ['dnp', 'no'], ['fields_autoplaced', 'yes'], ['uuid', uid('f')],
            mkprop('Reference', ref, x, y - 3.81, 0, hide=True),
            mkprop('Value', 'PWR_FLAG', x, y - 2.54, 0),
            mkprop('Footprint', '', x, y, 0, hide=True),
            mkprop('Datasheet', '', x, y, 0, hide=True),
            mkprop('Description', '', x, y, 0, hide=True),
            ['pin', Str('1'), ['uuid', uid('p')]],
            ['instances', ['project', Str('Brusograf_PCB'),
             ['path', Str('/' + SHEET_UUID), ['reference', Str(ref)], ['unit', '1']]]]]

add = []

# ===================================================================== A3 sheet
paper = first(doc, 'paper')
paper[1] = Str('A2')

# footprints shared by the blocks below
RSMD  = 'Resistor_SMD:R_1206_3216Metric_Pad1.30x1.75mm_HandSolder'
CSMD  = 'Capacitor_SMD:C_1206_3216Metric_Pad1.33x1.80mm_HandSolder'

# ======================================================= motor-rail bulk cap
add += [
    glabel('5V', 375.92, 160.02, 90),
    wire(375.92, 160.02, 375.92, 166.37),
    # bulk on the motor rail; a 1210 ceramic keeps it on the crowded back side
    symbol('Device', 'C', 'C8', '22uF/25V',
           'Capacitor_SMD:C_1210_3225Metric_Pad1.33x2.70mm_HandSolder',
           375.92, 170.18, 0),
    gnd(375.92, 173.99),
]

# --- D14: blocking Schottky between the regulator output and the 5V system rail,
#     so USB 5V on the DevKitC cannot back-feed the converter.
cut = None
for w in find(doc, 'wire'):
    pts = [(float(p[1]), float(p[2])) for p in first(w, 'pts')[1:]]
    if sorted(pts) == [(143.51, 30.48), (185.42, 30.48)]:
        cut = w
        break
if cut is None:
    raise SystemExit('ERROR: regulator output wire not found')
doc.remove(cut)
add += [
    symbol('Device', 'D_Schottky', 'D14', 'SS14', 'Diode_SMD:D_SMA_Handsoldering',
           147.32, 30.48, 180),
    wire(151.13, 30.48, 156.21, 30.48),
    junction(156.21, 30.48),
    wire(156.21, 30.48, 185.42, 30.48),
    wire(156.21, 30.48, 156.21, 34.29),
    pwrflag(156.21, 34.29, 180),
]

# ---------------------------------------------------------------- merge & save
libsec = first(doc, 'lib_symbols')
have = {str(s[1]) for s in find(libsec, 'symbol')}
for key, s in sorted(used_libs.items()):
    if key not in have:
        libsec.append(s)

anchor = doc.index(first(doc, 'sheet_instances'))
doc[anchor:anchor] = add

open(SCH, 'w').write(dump(doc) + '\n')
print(f'wrote {SCH}')
print(f'  +{len([a for a in add if a[0]=="symbol"])} symbols, '
      f'{len([a for a in add if a[0]=="wire"])} wires, '
      f'{len([a for a in add if a[0]=="global_label"])} labels')
print('  lib_symbols added:', [k for k in used_libs if k not in have])
