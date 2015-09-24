# coding: utf8
"""
 lx             Palula lexeme (lexical representation) = main entry
 +-  hm         Homonym number
 +-  va         Variant form, usually (but not exclusively) a phonological variant form
 |   |          used within the target dialect or in the other main dialect
 |   +-  ve     The domain of the form in  va, usually the name of the geographical
 |              location, e.g. Biori
 +-  se         Used liberally for multi-word constructions in which the lexeme occurs
     +-  ph     Phonetic form (surface representation)
     +-  gv     Vernacular form
     +-  mn     Reference to a main entry, especially in cases where a variant form or an
     |          irregular form needs a separate listing
     +-  mr     Morphemic form (underlying representation, if different from lexical)
     +-  xv     Example phrase or sentence
     |   +-  xe Translation of above  xv
     |   +-  xvm Morphemes of IGT
     |   +-  xeg Gloss of IGT
     +-  bw     Indicating that it is a borrowed word, but by using the label Comp I
     |          don’t make any specific claims as to the route of borrowing, instead just
     |          mentioning the language that has a similar form and citing the source form
     |          itself
     +-  ps     Part of speech label
         +-  pd Paradigm label (e.g. i-decl)
         |   +-  pdl    Specifying the form category of the following pdv
         |       +-  pdv    The word form
         +-  sn Sense number (for a lexeme having clearly different senses). I use this
             |  very sparingly, trying to avoid too much of an English or Western bias
             +-  re Word(s) used in English (reversed) index.
             +-  de Gloss(es) or multi-word definition
             +-  oe Restrictions, mainly grammatical (e.g. With plural reference)
             +-  ue Usage (semantic or grammatical)
             +-  cf Cross-reference, linking it to another main entry
             +-  et Old Indo-Aryan proto-form (I’m restricting this to Turner 1966)
                 +-  eg The published gloss of  et
                 +-  es The reference to Turner, always in the form T: (referring to the
                        entry number in Turner, not the page number)

"""
from __future__ import unicode_literals

from dictionaria.scripts.util import default_value_converter


def et(v, d):
    res = d['et'][0]
    if d.get('eg'):
        res += " '%s'" % d['eg'][0]
    if d.get('es'):
        res += " (%s)" % d['es'][0]
    return res


MARKER_MAP = dict(
    va=('variant form', lambda v, d: d['va'][0] + (' (%s)' % d['ve'][0] if d.get('ve') else '')),
    gv=('vernacular form', default_value_converter),
    mr=('morphemic form', default_value_converter),
    bw=('borrowed', default_value_converter),
    oe=('restrictions', default_value_converter),
    ue=('usage', default_value_converter),
    et=('old Indo-Aryan proto-form', et),
)
