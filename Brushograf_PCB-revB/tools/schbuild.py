"""Helpers for placing symbols and wiring them by pin name on a KiCad schematic."""
import sys, os, uuid as _uuid
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from kisexp import Str, find, first
import symlib

_ns = _uuid.UUID('6f1c4a2e-2222-4000-8000-000000000000'); _n = [0]
def uid(tag=''):
    _n[0] += 1
    return Str(str(_uuid.uuid5(_ns, f'{tag}:{_n[0]}')))

def fmt(v):
    return f'{round(float(v), 4):g}'

def snap(v, g=1.27):
    return round(round(v / g) * g, 4)

def R(px, py, rot):
    x, y = px, -py
    for _ in range((int(rot) // 90) % 4):
        x, y = y, -x
    return x, y

class Sheet:
    def __init__(self, sheet_uuid):
        self.uuid = sheet_uuid
        self.items = []
        self.libs = {}
        self.pwr_n = 0
        self.flg_n = 0

    # -------------------------------------------------------------- primitives
    def wire(self, x1, y1, x2, y2):
        x1, y1, x2, y2 = snap(x1), snap(y1), snap(x2), snap(y2)
        if (x1, y1) == (x2, y2):
            return
        self.items.append(['wire',
            ['pts', ['xy', fmt(x1), fmt(y1)], ['xy', fmt(x2), fmt(y2)]],
            ['stroke', ['width', '0'], ['type', 'default']],
            ['uuid', uid('w')]])

    def route(self, a, b, horiz_first=True):
        """L-shaped route between two points."""
        (x1, y1), (x2, y2) = (snap(a[0]), snap(a[1])), (snap(b[0]), snap(b[1]))
        if abs(x1 - x2) < 1e-6 or abs(y1 - y2) < 1e-6:
            self.wire(x1, y1, x2, y2); return
        if horiz_first:
            self.wire(x1, y1, x2, y1); self.wire(x2, y1, x2, y2)
        else:
            self.wire(x1, y1, x1, y2); self.wire(x1, y2, x2, y2)

    def junction(self, x, y):
        x, y = snap(x), snap(y)
        self.items.append(['junction', ['at', fmt(x), fmt(y)], ['diameter', '0'],
                           ['color', '0', '0', '0', '0'], ['uuid', uid('j')]])

    def label(self, name, x, y, rot=0, shape='input'):
        x, y = snap(x), snap(y)
        just = 'right' if rot == 180 else 'left'
        self.items.append(['global_label', Str(name), ['shape', shape],
            ['at', fmt(x), fmt(y), str(int(rot))], ['fields_autoplaced', 'yes'],
            ['effects', ['font', ['size', '1.27', '1.27']], ['justify', just]],
            ['uuid', uid('gl')],
            ['property', Str('Intersheetrefs'), Str('${INTERSHEET_REFS}'),
             ['at', fmt(x), fmt(y), '0'],
             ['effects', ['font', ['size', '1.27', '1.27']], ['justify', just],
              ['hide', 'yes']]]])

    def _prop(self, name, value, x, y, hide=False, italic=False, justify=None):
        eff = ['effects', ['font', ['size', '1.27', '1.27']] +
               ([['italic', 'yes']] if italic else [])]
        if justify:
            eff.append(['justify', justify])
        if hide:
            eff.append(['hide', 'yes'])
        return ['property', Str(name), Str(value), ['at', fmt(x), fmt(y), '0'], eff]

    def gnd(self, x, y, rot=0, net='GND'):
        x, y = snap(x), snap(y)
        self.pwr_n += 1
        ref = f'#PWRX{self.pwr_n}'
        libid = 'power:' + net
        self.libs[libid] = symlib.load('power', net)
        self.items.append(['symbol', ['lib_id', Str(libid)],
            ['at', fmt(x), fmt(y), str(int(rot))], ['unit', '1'],
            ['exclude_from_sim', 'no'], ['in_bom', 'yes'], ['on_board', 'yes'],
            ['dnp', 'no'], ['fields_autoplaced', 'yes'], ['uuid', uid('g')],
            self._prop('Reference', ref, x, y + 6.35, hide=True),
            self._prop('Value', net, x, y + 5.08),
            self._prop('Footprint', '', x, y, hide=True),
            self._prop('Datasheet', '', x, y, hide=True),
            self._prop('Description', '', x, y, hide=True),
            ['pin', Str('1'), ['uuid', uid('p')]],
            ['instances', ['project', Str('Brusograf_PCB'),
             ['path', Str('/' + self.uuid), ['reference', Str(ref)], ['unit', '1']]]]])

    def pwrflag(self, x, y, rot=0):
        x, y = snap(x), snap(y)
        self.flg_n += 1
        ref = f'#FLGX{self.flg_n}'
        self.libs['power:PWR_FLAG'] = symlib.load('power', 'PWR_FLAG')
        self.items.append(['symbol', ['lib_id', Str('power:PWR_FLAG')],
            ['at', fmt(x), fmt(y), str(int(rot))], ['unit', '1'],
            ['exclude_from_sim', 'no'], ['in_bom', 'yes'], ['on_board', 'yes'],
            ['dnp', 'no'], ['fields_autoplaced', 'yes'], ['uuid', uid('f')],
            self._prop('Reference', ref, x, y - 3.81, hide=True),
            self._prop('Value', 'PWR_FLAG', x, y - 2.54),
            self._prop('Footprint', '', x, y, hide=True),
            self._prop('Datasheet', '', x, y, hide=True),
            self._prop('Description', '', x, y, hide=True),
            ['pin', Str('1'), ['uuid', uid('p')]],
            ['instances', ['project', Str('Brusograf_PCB'),
             ['path', Str('/' + self.uuid), ['reference', Str(ref)], ['unit', '1']]]]])

    # ----------------------------------------------------------------- symbols
    def place(self, lib, name, ref, value, footprint, x, y, rot=0,
              ref_at=None, val_at=None, hide_value=False):
        x, y = snap(x), snap(y)          # keep every pin on the 1.27mm grid
        key = f'{lib}:{name}'
        sym = symlib.load(lib, name)
        self.libs[key] = sym
        pins = symlib.pins(sym)
        if ref_at is None or val_at is None:
            if int(rot) % 180 == 90:
                ar, av = (x, y - 3.81, None), (x, y + 3.81, None)
            else:
                ar, av = (x + 2.54, y - 1.27, 'left'), (x + 2.54, y + 1.27, 'left')
            ref_at = ref_at or ar
            val_at = val_at or av
        node = ['symbol', ['lib_id', Str(key)],
                ['at', fmt(x), fmt(y), str(int(rot))], ['unit', '1'],
                ['exclude_from_sim', 'no'], ['in_bom', 'yes'], ['on_board', 'yes'],
                ['dnp', 'no'], ['uuid', uid('s' + ref)],
                self._prop('Reference', ref, ref_at[0], ref_at[1], justify=ref_at[2]),
                self._prop('Value', value, val_at[0], val_at[1],
                           hide=hide_value, justify=val_at[2]),
                self._prop('Footprint', footprint, x, y, hide=True, italic=True),
                self._prop('Datasheet', '~', x, y, hide=True),
                self._prop('Description', '', x, y, hide=True)]
        for pn, _, _, _ in pins:
            node.append(['pin', Str(pn), ['uuid', uid('p')]])
        node.append(['instances', ['project', Str(''),
                     ['path', Str('/' + self.uuid), ['reference', Str(ref)],
                      ['unit', '1']]]])
        self.items.append(node)
        return Part(ref, pins, x, y, rot)

class Part:
    def __init__(self, ref, pins, x, y, rot):
        self.ref = ref
        self.x, self.y, self.rot = x, y, rot
        self._by_num = {}
        self._by_name = {}
        for num, nm, px, py in pins:
            dx, dy = R(px, py, rot)
            pt = (round(x + dx, 4), round(y + dy, 4))
            self._by_num[num] = pt
            self._by_name.setdefault(nm, pt)

    def p(self, key):
        """Pin position by number or by name."""
        k = str(key)
        if k in self._by_num:
            return self._by_num[k]
        if k in self._by_name:
            return self._by_name[k]
        raise KeyError(f'{self.ref}: no pin {key!r} '
                       f'(numbers {sorted(self._by_num)}, names {sorted(self._by_name)})')
