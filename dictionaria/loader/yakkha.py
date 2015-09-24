"""
"""
from __future__ import unicode_literals

from dictionaria.lib.dictionaria_sfm import Entry


MARKER_MAP = {
    'intstr': 'internal structure',
    'gn': 'Nepali gloss',
    'eth': 'ethnographic notes',
    'bzn': 'botanical or zoological name',
    'sem': 'semantic categories',
}


if __name__ == '__main__':
    e = Entry.from_string("""
\lx a
\ge a; b; c
    """)
    for p in e.preprocessed():
        print(p)

    for w in e.get_words():
        for m in w.meanings:
            print(m.ge)
