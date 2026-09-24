"""Occupancy model of the board, used to sanity-check new footprint placements."""
import sys, os, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from kisexp import parse, find, first, propval, f

S = 0.25
FP_DIR = '/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints/'

def rot(p, a):
    a = math.radians(-a)
    return (p[0] * math.cos(a) - p[1] * math.sin(a), p[0] * math.sin(a) + p[1] * math.cos(a))

def load_mod(libmod):
    lib, mod = libmod.split(':')
    return parse(open(f'{FP_DIR}{lib}.pretty/{mod}.kicad_mod').read())

def mod_extents(libmod):
    """(pad bbox, courtyard bbox) in footprint-local coords."""
    d = load_mod(libmod)
    px = []; py = []; cx = []; cy = []
    for p in find(d, 'pad'):
        a = first(p, 'at'); s = first(p, 'size')
        px += [f(a[1]) - f(s[1]) / 2, f(a[1]) + f(s[1]) / 2]
        py += [f(a[2]) - f(s[2]) / 2, f(a[2]) + f(s[2]) / 2]
    for t in ('fp_line', 'fp_poly', 'fp_rect', 'fp_circle', 'fp_arc'):
        for it in find(d, t):
            ly = first(it, 'layer')
            if not ly or 'CrtYd' not in str(ly[1]):
                continue
            for k in ('start', 'end', 'center', 'mid'):
                q = first(it, k)
                if q:
                    cx.append(f(q[1])); cy.append(f(q[2]))
            pts = first(it, 'pts')
            if pts:
                for q in pts[1:]:
                    if q[0] == 'xy':
                        cx.append(f(q[1])); cy.append(f(q[2]))
    pad = (min(px), max(px), min(py), max(py))
    crt = (min(cx), max(cx), min(cy), max(cy)) if cx else pad
    return pad, crt

class Board:
    def __init__(self, pcb, skip_refs=()):
        self.d = parse(open(pcb).read()) if isinstance(pcb, str) else pcb
        self.skip = set(skip_refs)
        self.grid = {}
        self._build()

    def _mark(self, x, y, lay):
        self.grid[(int(round(x / S)), int(round(y / S)))] = \
            self.grid.get((int(round(x / S)), int(round(y / S))), 0) | lay

    def _rect(self, cx, cy, w, h, lay, clr=0.3):
        w += 2 * clr; h += 2 * clr
        nx = max(2, int(w / S)); ny = max(2, int(h / S))
        for i in range(nx + 1):
            for j in range(ny + 1):
                self._mark(cx - w / 2 + w * i / nx, cy - h / 2 + h * j / ny, lay)

    def _seg(self, x1, y1, x2, y2, lay, wdt):
        n = max(2, int(math.dist((x1, y1), (x2, y2)) / S) + 1)
        for i in range(n + 1):
            t = i / n
            self._rect(x1 + (x2 - x1) * t, y1 + (y2 - y1) * t, wdt, wdt, lay, 0.3)

    def _build(self):
        d = self.d
        for fp in find(d, 'footprint'):
            if propval(fp, 'Reference') in self.skip:
                continue
            at = first(fp, 'at'); fx, fy = f(at[1]), f(at[2])
            fa = f(at[3]) if len(at) > 3 else 0
            side = str(first(fp, 'layer')[1])
            for p in find(fp, 'pad'):
                pat = first(p, 'at'); sz = first(p, 'size')
                px, py = rot((f(pat[1]), f(pat[2])), fa)
                thru = str(p[2]) == 'thru_hole'
                self._rect(fx + px, fy + py, f(sz[1]), f(sz[2]),
                           3 if thru else (1 if side == 'F.Cu' else 2))
        for s in find(d, 'segment'):
            lay = 1 if str(first(s, 'layer')[1]) == 'F.Cu' else 2
            a = first(s, 'start'); b = first(s, 'end')
            self._seg(f(a[1]), f(a[2]), f(b[1]), f(b[2]), lay, f(first(s, 'width')[1]))
        for v in find(d, 'via'):
            a = first(v, 'at')
            self._rect(f(a[1]), f(a[2]), f(first(v, 'size')[1]), f(first(v, 'size')[1]), 3)

    def check(self, libmod, x, y, ang, layer):
        """Return a list of complaints for placing `libmod` at x,y,ang on `layer`."""
        d = load_mod(libmod)
        bad = []
        for p in find(d, 'pad'):
            pat = first(p, 'at'); sz = first(p, 'size')
            px, py = rot((f(pat[1]), f(pat[2])), ang)
            thru = str(p[2]) == 'thru_hole'
            want = 3 if thru else (1 if layer == 'F.Cu' else 2)
            cx, cy = x + px, y + py
            w, h = f(sz[1]) + 0.5, f(sz[2]) + 0.5
            nx = max(2, int(w / S)); ny = max(2, int(h / S))
            for i in range(nx + 1):
                for j in range(ny + 1):
                    gx = cx - w / 2 + w * i / nx; gy = cy - h / 2 + h * j / ny
                    occ = self.grid.get((int(round(gx / S)), int(round(gy / S))), 0)
                    if occ & want:
                        bad.append(f'pad {str(p[1])} at ({cx:.2f},{cy:.2f}) hits '
                                   f'{"front" if occ & want & 1 else ""}'
                                   f'{"back" if occ & want & 2 else ""} copper near ({gx:.2f},{gy:.2f})')
                        break
                else:
                    continue
                break
        # board outline
        pad, crt = mod_extents(libmod)
        for (lo_x, hi_x, lo_y, hi_y), what in ((pad, 'pads'), (crt, 'courtyard')):
            corners = [rot((cx_, cy_), ang) for cx_ in (lo_x, hi_x) for cy_ in (lo_y, hi_y)]
            xs = [x + c[0] for c in corners]; ys = [y + c[1] for c in corners]
            if min(xs) < 45.7 or max(xs) > 241.6 or min(ys) < 86.85 or max(ys) > 132.85:
                bad.append(f'{what} outside board: x {min(xs):.2f}..{max(xs):.2f} '
                           f'y {min(ys):.2f}..{max(ys):.2f}')
        return bad
