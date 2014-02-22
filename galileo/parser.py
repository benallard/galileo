"""\
This is a custom implementation of the yaml parser in order to prevent an
extra dependency in the PyYAML module. This implementation will be used when
the PyYAML module will not be found.

The configurability of galileo should not be based on the possibility of this
parser. This parser should be adapted to allow the correct configuration.

Known limitations:
- Only spaces, no tabs
- The returned dictionnaly supports only one level
"""

import json

class ParserError(Exception): pass

def _stripcomment(line):
    s = []
    for c in line:
        if c == '#':
            break
        s.append(c)
    # And we strip the trailing spaces
    return ''.join(s).rstrip()

def _getident(line):
    i = 0
    for c in line:
        if c != ' ':
            break
        i += 1
    return i

def _addKey(d, key):
    if d is None and key:
        d = {key: None}
    d[key] = None
    return d


def unJSONize(s):
    """ json is not enough ...
    "'a'" doesn't get decoded,
    even worst, "a" neither """
    try:
        return json.loads(s)
    except ValueError:
        s = s.strip()
        if s[0] == "'" and s[-1] == "'":
            return s[1:-1]
        return s


def loads(s):
    res = None
    current_key = None
    prev_ident = ''
    for line in s.split('\n'):
       line = _stripcomment(line)
       if not line: continue
       if _getident(line) == 0:
           current_key = None
           k, v = line.split(':')
           res = _addKey(res, k)
           if not v:
               current_key = k
           else:
               res[k] = unJSONize(v)
       else:
           assert current_key is not None
           # value indented
           line = line.lstrip()
           if not line.startswith('- '):
               res[current_key] = unJSONize(line)
           else:
               if res[current_key] is None:
                   res[current_key] = []
               res[current_key].append(unJSONize(line[2:]))
    return res


def load(f):
    return loads(f.read())

if __name__ == "__main__":
    import sys
    # For fun and quick test
    with open(sys.argv[1], 'rt') as f:
        print load(f.read())
