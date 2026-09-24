"""Minimal S-expression reader/writer for KiCad files."""
import re

def parse(text):
    """Return nested lists; atoms are str (quoted strings keep a marker)."""
    i, n = 0, len(text)
    stack, cur = [], []
    while i < n:
        c = text[i]
        if c == '(':
            new = []
            cur.append(new); stack.append(cur); cur = new; i += 1
        elif c == ')':
            cur = stack.pop(); i += 1
        elif c == '"':
            j = i + 1; buf = []
            while j < n:
                if text[j] == '\\':
                    buf.append(text[j:j+2]); j += 2
                elif text[j] == '"':
                    break
                else:
                    buf.append(text[j]); j += 1
            cur.append(Str(''.join(buf))); i = j + 1
        elif c in ' \t\r\n':
            i += 1
        else:
            j = i
            while j < n and text[j] not in ' \t\r\n()"':
                j += 1
            cur.append(text[i:j]); i = j
    return cur[0]

class Str(str):
    """A string that was quoted in the source."""
    __slots__ = ()

def dump(node, indent=0, tab='\t'):
    if not isinstance(node, list):
        return '"%s"' % node if isinstance(node, Str) else str(node)
    head = node[0] if node else ''
    inline = not any(isinstance(x, list) for x in node[1:])
    if inline:
        return '(' + ' '.join(dump(x) for x in node) + ')'
    pad = tab * (indent + 1)
    parts = ['(' + dump(head)]
    # keep leading scalar args on the head line
    k = 1
    while k < len(node) and not isinstance(node[k], list):
        parts[0] += ' ' + dump(node[k]); k += 1
    for x in node[k:]:
        parts.append(pad + dump(x, indent + 1, tab))
    return '\n'.join(parts) + '\n' + tab * indent + ')'

def find(node, tag):
    return [x for x in node if isinstance(x, list) and x and x[0] == tag]

def first(node, tag):
    for x in node:
        if isinstance(x, list) and x and x[0] == tag:
            return x
    return None

def prop(sym, name):
    for p in find(sym, 'property'):
        if len(p) > 1 and p[1] == name:
            return p
    return None

def propval(sym, name):
    p = prop(sym, name)
    return str(p[2]) if p and len(p) > 2 else None

def f(x):
    return float(x)
