# coding: utf8
"""
Parsing functionality for the SFM variant understood for Dictionaria submissions.
"""
from __future__ import unicode_literals
from collections import defaultdict, Counter
from hashlib import md5

from clldutils.misc import slug
from clldutils.path import Path
from clldutils import sfm


class Meaning(object):
    """
    A word can have several meanings, described by meaning description and gloss.

    Semantic domain and examples are also meaning specific.
    """
    def __init__(self):
        self.de = None
        self.ge = None
        self.sd = []
        self.x = []
        self.xref = []


class Example(object):
    def __init__(self, xv):
        self.xv = xv
        self.xvm = None
        self.xeg = None
        self.xo = None
        self.xe = None
        self.rf = None

    def merge(self, other, force_sameid=True):
        try:
            assert self.id == other.id
        except AssertionError:
            print self.xv.encode('utf8')
            print other.xv.encode('utf8')
            print self.xe.encode('utf8')
            print other.xe.encode('utf8')
            if force_sameid:
                raise
        for a, b in [(self, other), (other, self)]:
            for prop in ['xvm', 'xeg', 'rf']:
                if getattr(a, prop) is None and getattr(b, prop) is not None:
                    setattr(a, prop, getattr(b, prop))

    def __setattr__(self, key, value):
        object.__setattr__(self, key, (value.strip() or None) if value else None)

    @property
    def id(self):
        return self.__hash__()

    def __hash__(self):
        return md5(slug(self.xv).encode('utf8') + slug(self.xe).encode('utf')).hexdigest()

    def __eq__(self, other):
        return all(getattr(self, a) == getattr(other, a) for a in 'id xvm xeg rf'.split())

    @property
    def text(self):
        rf = '\\rf {0}\n'.format(self.rf) if self.rf else ''
        xo = '\\ot {0}\n'.format(self.xo) if self.xo else ''
        return "\\ref {0}\n{5}\\tx {1}\n\\mb {2}\n\\gl {3}\n\\ft {4}\n{6}\n".format(
            self.id, self.xv, self.xvm or '', self.xeg or '', self.xe, rf, xo)


class Word(object):
    """
    A word is the atomic language unit in dictionaria.

    A dictionary entry may contain multiple words via sub-entry markers.
    """
    def __init__(self, form):
        self.form = form
        self.hm = None  # homonym marker
        self.ph = None  # phonetic representation of the word
        self.ps = None  # part-of-speech
        self.data = defaultdict(list)  # to store additional marker, value pairs
        self.rel = []
        self.meanings = []
        self.non_english_meanings = defaultdict(list)

    @property
    def id(self):
        return self.form + (self.hm or '')


class Entry(sfm.Entry):
    """
    A dictionary entry.
    """
    def preprocessed(self):
        for i, (k, v) in enumerate(self[:]):
            if k == 'ge' and sfm.FIELD_SPLITTER_PATTERN.search(v):
                ges = sfm.FIELD_SPLITTER_PATTERN.split(v)
                self[i] = ('zzz', 'zzz')
                for ge in ges:
                    self.append(('sn', 'auto'))
                    self.append(('ge', ge))
        return self

    def checked_word(self, word, meaning):
        if meaning:
            if meaning.de or meaning.ge:
                word.meanings.append(meaning)
            else:
                print('meaning without description for %s' % word.form)
        return word

    def get_words(self):
        """
        :return: generator for the words contained within the entry.
        """
        word = None
        # if an entry has only one \ps marker but multiple words, the value of \ps is used
        # as part-of-speech for all words.
        pos = None

        example = None
        meaning = None

        # flag signaling whether we are dealing with the first meaning of a word or
        # subsequent ones.
        first_meaning = True

        # now we loop over the (marker, value) pairs of the entry:
        for k, v in self:
            # individual words are identified by \lx or \se (sub-entry) markers.
            if k in ['lx', 'se']:
                if word:
                    yield self.checked_word(word, meaning)
                word = Word(v)
                if pos:
                    word.ps = pos
                meaning = Meaning()
            elif k == 'sn':  # a new sense number: initialize a new Meaning.
                if not first_meaning:
                    self.checked_word(word, meaning)
                    meaning = Meaning()
                first_meaning = False
            # meaning-specific markers:
            elif k in ['de', 'ge']:
                # FIXME: we must support multiple meanings expressed by
                # semicolon-separated \ge values, e.g. "jump ; jump at"
                setattr(meaning, k, v)
            elif k == 'sd':
                meaning.sd.append(v)
            elif k == 'xv':
                if example:
                    example.xv += ' %s' % v
                else:
                    example = Example(v)
            elif k in ['xvm', 'xeg']:
                if getattr(example, k):
                    v = getattr(example, k) + ' ' + v
                setattr(example, k, v)
            elif k == 'xe':
                if example:
                    example.xe = v
                    try:
                        assert meaning
                        meaning.x.append(example)
                    except AssertionError:
                        print(
                            'no meanings for (sense or subentry of) word %s' % word.form)
                    example = None
                else:
                    print('xe without xv for word %s' % word.form)
            elif k == 'xref':
                meaning.xref.append(v)
            # word-specific markers:
            elif k in ['hm', 'ph']:
                if getattr(word, k) is None:
                    # only record first occurrence of the marker!
                    setattr(word, k, v)
            elif k == 'ps':
                pos = word.ps = v
            elif k in ['cf', 'mn']:
                for vv in v.split(','):
                    if vv.strip():
                        word.rel.append((k, vv.strip()))
            elif k == 'gxx':
                word.non_english_meanings[k].extend(sfm.FIELD_SPLITTER_PATTERN.split(v))
            else:
                word.data[k].append(v)
        if word:
            yield self.checked_word(word, meaning)


class Stats(object):
    def __init__(self):
        self.count = Counter()
        self._mult_markers = defaultdict(int)
        self._implicit_mult_markers = set()

    def __call__(self, entry):
        if not entry.get('lx'):
            return
        entry_markers = entry.markers()
        self.count.update(entry_markers)
        for k, v in entry_markers.items():
            if v > self._mult_markers[k]:
                self._mult_markers[k] = v
        for k, v in entry:
            if sfm.FIELD_SPLITTER_PATTERN.search(v):
                self._implicit_mult_markers.add(k)
        for word in entry.get_words():
            self.count.update(words=1)
            self.count.update(meanings=len(word.meanings))


class Dictionary(object):
    def __init__(self, filename, **kw):
        kw.setdefault('entry_impl', Entry)
        lexeme_marker = 'lx'
        reverse_marker_map = {v: k for k, v in kw['marker_map'].items()}
        if lexeme_marker in reverse_marker_map:
            lexeme_marker = reverse_marker_map[lexeme_marker]
            kw.setdefault('entry_prefix', '\\lx ')
        kw.setdefault('entry_sep', '\\%s ' % lexeme_marker)
        self.sfm = sfm.SFM.from_file(filename, **kw)
        self.dir = Path(filename).parent

    def validated(self, entry):
        entry = sfm.Dictionary.validated(self, entry)
        return entry.preprocessed()

    def stats(self):
        stats = Stats()
        self.sfm.visit(stats)
        print stats.count
        print stats._mult_markers
        print stats._implicit_mult_markers


class Examples(sfm.SFM):
    """
    \ref d48204ced7d012dd071d0ec402e58d20
    \tx A beiko.
    \mb
    \gl
    \ft The child.
    """
    def __init__(self, filename, **kw):
        sfm.Dictionary.__init__(self, filename, **kw)
        self._map = {entry.get('ref'): entry for entry in self.entries}

    @staticmethod
    def normalize(morphemes_or_gloss):
        if morphemes_or_gloss:
            return '\t'.join(
                [p for p in morphemes_or_gloss.split() if not p.startswith('#')])

    def get(self, item):
        try:
            return Examples.as_example(self._map[item])
        except KeyError:
            return None

    @staticmethod
    def as_example(r):
        ex = Example(r.get('tx'))
        ex.xe = r.get('ft')
        ex.xvm = Examples.normalize(r.get('mb'))
        ex.xeg = Examples.normalize(r.get('gl'))
        return ex


class ElanExamples(Examples):
    """
    \\utterance_id Iar_02RG.001
    \\ELANBegin 0.000
    \\ELANEnd 1.843
    \\ELANParticipant
    \\utterance Bara.
    \\gramm_units # Bara
    \\rp_gloss # alright
    \\GRAID #
    \\utterance_tokens Bara.
    \\ft Alright.
    """
    def __init__(self, filename, **kw):
        kw['marker_map'] = {
            'utterance_id': 'ref',
            'utterance': 'tx',
            'gramm_units': 'mb',
            'rp_gloss': 'gl',
        }
        kw['entry_sep'] = '\\utterance_id'
        Examples.__init__(self, filename, **kw)
        for k in list(self._map.keys()):
            # abc.069 may be looked up as abc.69!
            try:
                prefix, number = k.split('.', 1)
                self._map['%s.%s' % (prefix, int(number))] = self._map[k]
            except:
                pass
