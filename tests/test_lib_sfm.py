# coding: utf8
from __future__ import unicode_literals, print_function, division

from dictionaria.lib.sfm import Entry


def test_Entry():
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


def test_EntryMultipleSenses():
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


def test_EntryWithSubentry():
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


def test_EntryWithExample():
    e = Entry.from_string(r"""
\lx bweang
\ps n
\sn 1
\sd plants
\dn hea blong wan plan
\de hairy parts of a plant
\ge treefern.hair
\dr
\xref 1234

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
    assert m1.xref
    assert m1.sd == ['plants']
    assert not m2.xref
    assert m2.sd == ['kastom']


def test_EntryWithMultipleSensesAsSubentries():
    e = Entry.from_string(r"""
\lx abdal
\lxc абдал
\lc
\lcc
\mr

\sf abdal.wav

\pl abdalte

\sn 1
\ps n
\pr сущ
\ge fool
\gr глупец
\nt

\xv Het durħu abdalde.
\xc Гьет дурх1у абдалде.
\xe That boy was a fool.
\xr Тот мальчик был дурной.
\sfx abdal_1.wav

\sn 2
\ps adj
\pr прил
\ge stupid; foolish
\gr дурной; глупый; безумный
\nt

\dt 08/Sep/2011""")
    words = list(e.get_words())
    assert len(words) == 2


def test_Daakaka():
    e = Entry.from_string(r"""
\lx abwilyep
\sn
\sn 1
\ps n
\dn poson man
\de (black) magician, sorcerer
\dr
\xref 123

\sn 2
\ps adj2
\dn poson
\ge poisonous
\xref 2345
\dt 08/Sep/2011
""")
    words = list(e.get_words())
    assert len(words) == 2


def test_EntryWithMultipleSensesAndSubentry():
    e = Entry.from_string(r"""
\lx yaangme
\ps v.intr
\sn 1
\ge come_down
\gn turun_datang
\de come down to the bottom taverse
across a slope
\gxx datang turun dari sebelah ke bawah
\cf wehe
\sn 2
\ge exit
\gn keluar
\xref 47d85a28df71ac0647ca29dc6a6807e3
\se -yaangme
\ps v.tr.gen
\de release, unleash, let out
\gxx mengeluarkan
\xref 0d870c72d91c64f32c0d60b65126dc6b---2
\dt 05/Aug/2011
""")
    words = list(e.get_words())
    assert len(words) == 2
    assert words[0].ps == 'v.intr'
    assert words[1].ps == 'v.tr.gen'
    assert len(words[0].meanings) == 2
    assert len(words[1].meanings) == 1
