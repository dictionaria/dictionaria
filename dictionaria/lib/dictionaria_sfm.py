# coding: utf8
"""
Parsing functionality for the SFM variant understood for Dictionaria submissions.
"""
from __future__ import unicode_literals
from collections import defaultdict
from hashlib import md5

from dictionaria.lib import sfm


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


class Example(object):
    def __init__(self, xv):
        self.xv = xv
        self.xvm = None
        self.xeg = None
        self.xe = None

    def merge(self, other):
        assert self.id == other.id
        for a, b in [(self, other), (other, self)]:
            for prop in ['xvm', 'xeg']:
                if getattr(a, prop) is None and getattr(b, prop) is not None:
                    setattr(a, prop, getattr(b, prop))

    def __setattr__(self, key, value):
        object.__setattr__(self, key, (value.strip() or None) if value else None)

    @property
    def id(self):
        return self.__hash__()

    def __hash__(self):
        return md5(self.xv.encode('utf8') + self.xe.encode('utf')).hexdigest()

    def __eq__(self, other):
        return self.id == other.id and self.xvm == other.xvm and self.xeg == other.xeg

    @property
    def text(self):
        return "\\ref {0}\n\\tx {1}\n\\mb {2}\n\\gl {3}\n\\ft {4}\n\n".format(
            self.id, self.xv, self.xvm or '', self.xeg or '', self.xe)


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


class Dictionary(sfm.Dictionary):
    def __init__(self, filename, **kw):
        kw.setdefault('entry_impl', Entry)
        lexeme_marker = 'lx'
        reverse_marker_map = {v: k for k, v in kw['marker_map'].items()}
        if lexeme_marker in reverse_marker_map:
            lexeme_marker = reverse_marker_map[lexeme_marker]
            kw.setdefault('entry_prefix', '\\lx ')
        kw.setdefault('entry_sep', '\\%s ' % lexeme_marker)
        sfm.Dictionary.__init__(self, filename, **kw)
        self.entries = filter(lambda r: r.get('lx'), self.entries)

    def validated(self, entry):
        entry = sfm.Dictionary.validated(self, entry)
        return entry.preprocessed()

    def stats(self):
        words = 0
        meanings = 0
        for entry in self:
            for word in entry.get_words():
                words += 1
                meanings += len(word.meanings)
        sfm.Dictionary.stats(self)
        print('%s words' % words)
        print('%s meanings' % meanings)
