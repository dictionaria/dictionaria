# coding: utf8
from __future__ import unicode_literals

from dictionaria.lib.dictionaria_sfm import Entry
from dictionaria.scripts.util import default_value_converter


MARKER_MAP = dict(
    ue=('usage', default_value_converter),
    et=('et', default_value_converter),
    es=('es', default_value_converter),
    ee=('ee', default_value_converter),
)


if __name__ == '__main__':
    e = Entry.from_string(r"""
\lx ap
\ps n
\sd fauna
\sd fish
\dn blak krab
\de shore crab
\ge shore.crab
\dr
\dt 29/Mar/2010
""")
    words = list(e.get_words())
    assert len(words) == 1
    word = words[0]
    assert word.ps == 'n'
    assert word.meanings
    assert word.meanings[0].de and word.meanings[0].ge
    assert len(word.meanings[0].sd) == 2

    e = Entry.from_string(r"""
\lx a
\ps conj
\sn 1
\dn be
\ge but
\dr
\sn 2
\dn mo
\de and
\ge and
\dt 13/Nov/2009
""")
    words = list(e.get_words())
    assert len(words) == 1
    word = words[0]
    assert len(word.meanings) == 2
    assert word.meanings[0].ge == 'but' and word.meanings[1].ge == 'and'

    e = Entry.from_string(r"""
\lx aa
\ps n
\sd plants
\dn nanggalat
\de nettle
\ge nettle
\dr
\sc

\se aa ne tes
\dn nanggalat blong solwota
\de jellyfish (lit. "nettle of the sea")
\dr

\se laa
\dn stampa blong nanggalat
\de nettle tree
\dr

\dt 29/Mar/2010
""")
    words = list(e.get_words())
    assert len(words) == 3
    assert words[1].ps == words[0].ps

    e = Entry.from_string(r"""
\lx bweang
\ps n
\sn 1
\sd plants
\dn hea blong wan plan
\de hairy parts of a plant
\ge treefern.hair
\dr
\xv bweang ane leevy'o
\xn hea blong blak palm
\xe fiber of the tree fern
\xr

\sn 2
\sd kastom
\dn fes rang, rang blong kapenta
\de the first rank, the rank of the carpenter
\ge carpenter.rank
\dr

\dt 14/Jul/2010""")
    words = list(e.get_words())
    assert len(words) == 1
    word = words[0]
    m1, m2 = word.meanings
    assert m1.x and m1.sd == ['plants']
    assert not m2.x
    assert m2.sd == ['kastom']

    e = Entry.from_string(r"""
\lx bwee
\ps n.rel
\pd 2
\dn olgeta samting we yu save fulum ap samting insaed, olsem plet, sospen, baket
\de container, vessel
\ge container
\dr

\xv bwee matyis
\xn bokis blong majis
\xe match box
\xr

\xv bwee tin
\xn tin
\xe a can containing fish or meat
\xr

\se bwee vini 'o
\dn skin blong kokonas
\de the fibrous husk of a coconut
\dr

\se bwee ne s'o'os'o'oan
\dn sospen, marmit
\de pot
\dr
\nt suggestion by Domatien

\se bwee ne enan
\dn pelet
\de plate
\dr

\se bwee bek
\dn grin snel
\de green snail
\dr

\dt 08/Sep/2011""")
    words = list(e.get_words())
    assert len(words) == 5
