"""Load symbols from the global KiCad libraries, flattening `extends`."""
import os, sys, copy
sys.path.insert(0, os.path.dirname(__file__))
from kisexp import parse, find, first, prop, Str, dump

SYMDIR = '/Applications/KiCad/KiCad.app/Contents/SharedSupport/symbols/'
_cache = {}

def _lib(libname):
    if libname not in _cache:
        _cache[libname] = parse(open(SYMDIR + libname + '.kicad_sym').read())
    return _cache[libname]

def _raw(libname, symname):
    for s in find(_lib(libname), 'symbol'):
        if str(s[1]) == symname:
            return copy.deepcopy(s)
    raise KeyError(f'{libname}:{symname}')

def load(libname, symname):
    """Return a lib_symbols entry named 'Lib:Sym', with extends resolved."""
    s = _raw(libname, symname)
    ext = first(s, 'extends')
    if ext:
        parent = load(libname, str(ext[1]))
        merged = [x for x in parent if not (isinstance(x, list) and x and x[0] == 'property')]
        # parent properties, overridden by the child's
        props = {str(p[1]): p for p in find(parent, 'property')}
        for p in find(s, 'property'):
            props[str(p[1])] = p
        child_units = [x for x in s if isinstance(x, list) and x and x[0] == 'symbol']
        if child_units:  # child overrides graphics
            merged = [x for x in merged if not (isinstance(x, list) and x and x[0] == 'symbol')]
            merged += child_units
        out = [merged[0], merged[1]] + list(props.values()) + merged[2:]
        s = out
        # rename unit sub-symbols to the child's name
        for u in [x for x in s if isinstance(x, list) and x and x[0] == 'symbol']:
            u[1] = Str(symname + '_' + str(u[1]).rsplit('_', 2)[-2] + '_' + str(u[1]).rsplit('_', 1)[-1])
    s[1] = Str(f'{libname}:{symname}')
    return s

def pins(sym):
    """[(number, name, x, y)] in library coordinates."""
    out = []
    def walk(n):
        for x in n:
            if isinstance(x, list):
                if x and x[0] == 'pin' and first(x, 'number'):
                    at = first(x, 'at')
                    out.append((str(first(x, 'number')[1]), str(first(x, 'name')[1]),
                                float(at[1]), float(at[2])))
                else:
                    walk(x)
    walk(sym)
    return out
