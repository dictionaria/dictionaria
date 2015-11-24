# coding: utf8
"""
Parsing functionality for the SFM variant understood for Dictionaria submissions.
"""
from __future__ import unicode_literals, print_function
from collections import defaultdict, Counter, OrderedDict
import re

from clldutils.misc import slug
from clldutils.path import Path
from clldutils import sfm

from dictionaria.lib.ingest import Corpus, Example


class Rearrange(object):
    #
    # Teop preprocess: \rf comes *after* the example, when the value is in square
    # brackets! So when \rf [xxx] is encountered immediately after \xe, it must be moved
    # before the corresponding \xv!
    #
    in_brackets = re.compile('\[+\s*(?P<text>[^\]]+)\s*\]+$')

    def __call__(self, entry):
        reorder_map = []
        last_rf = 0

        for index, (marker, content) in enumerate(entry):
            if marker == 'rf':
                content = content.strip()
                match = self.in_brackets.match(content)
                if match:
                    if entry[index - 1][0] == 'xe':
                        # search for the preceding xv marker, but make sure we do not go
                        # back before the last rf marker.
                        for i in range(index - 2, last_rf, -1):
                            if entry[i][0] == 'xv':
                                reorder_map.append((i, match.group('text'), index))
                                break
                    else:
                        entry[index] = ('rf', match.group('text'))
                last_rf = index

        for insert, content, delete in reorder_map:
            del entry[delete]
            entry.insert(insert, ('rf', content))


class ExampleExtractor(object):
    def __init__(self, corpus, log):
        self.example_props = {
            'rf': 'rf',
            'xv': 'tx',
            'xvm': 'mb',
            'xeg': 'gl',
            'xo': 'ot',
            'xe': 'ft',
        }
        self.examples = OrderedDict()
        self.corpus = corpus
        self.log = log

    def __call__(self, entry):
        example = None
        lx = None
        rf = None
        items = []

        for marker, content in entry:
            if marker == 'lx':
                lx = content

            if marker in self.example_props:
                if marker == 'rf':
                    rf = content
                elif marker == 'xv':
                    # new example starts
                    if example:
                        # but last one is unfinished
                        self.log.write(
                            '# incomplete example in lx: %s - missing xe:\n%s\n\n'
                            % (lx, example))
                    example = Example([('tx', content)])
                elif marker == 'xe':
                    # example ends
                    if example:
                        if rf:
                            example.insert(0, ('rf', rf))
                        example.append(('ft', content))
                        items.append(('xref', self.xref(example)))
                        rf = None
                        example = None
                    else:
                        self.log.write(
                            '# incomplete example in lx: %s - missing xv\n' % lx)
                else:
                    if not example:
                        self.log.write('incomplete example in lx: %s - missing xv\n' % lx)
                    else:
                        example.append((self.example_props[marker], content))
            else:
                items.append((marker, content))
        return entry.__class__(items)

    def merge(self, ex1, ex2):
        for prop in 'rf tx mb gl ft'.split():
            p1 = ex1.get(prop)
            p2 = ex2.get(prop)
            if p1:
                if p2:
                    try:
                        assert slug(p1) == slug(p2)
                    except AssertionError:
                        self.log.write(
                            '# cannot merge \\%s:\n%s\n# and\n%s\n\n' % (prop, ex1, ex2))
                        raise
            else:
                if p2:
                    ex1.set(prop, p2)

    def xref(self, example):
        if example.corpus_ref:
            from_corpus = self.corpus.get(example.corpus_ref)
            if from_corpus:
                try:
                    self.merge(example, from_corpus)
                except AssertionError:
                    pass
        if example.id in self.examples:
            try:
                self.merge(self.examples[example.id], example)
            except AssertionError:
                orig = example.id
                count = 0
                while example.id in self.examples:
                    count += 1
                    example.set('ref', '%s---%s' % (orig, count))
        self.examples[example.id] = example
        return example.id

    def write_examples(self, fname):
        examples = sfm.SFM(self.examples.values())
        examples.write(fname)


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
        kw['marker_map'] = kw.get('marker_map') or {}
        lexeme_marker = 'lx'
        reverse_marker_map = {v: k for k, v in kw['marker_map'].items()}
        if lexeme_marker in reverse_marker_map:
            lexeme_marker = reverse_marker_map[lexeme_marker]
            kw.setdefault('entry_prefix', '\\lx ')
        kw.setdefault('entry_sep', '\\%s ' % lexeme_marker)
        self.sfm = sfm.SFM.from_file(filename, **kw)
        self.dir = Path(filename).parent

    #def validated(self, entry):
    #    entry = sfm.Dictionary.validated(self, entry)
    #    return entry.preprocessed()

    def stats(self):
        stats = Stats()
        self.sfm.visit(stats)
        print(stats.count)
        print(stats._mult_markers)
        print(stats._implicit_mult_markers)

    def process(self, outfile):
        """extract examples, etc."""
        assert self.dir.name != 'processed'

        self.sfm.visit(Rearrange())

        with self.dir.joinpath('examples.log').open('w', encoding='utf8') as log:
            extractor = ExampleExtractor(Corpus(self.dir), log)
            self.sfm.visit(extractor)

        self.sfm.write(outfile)
        extractor.write_examples(outfile.parent.joinpath('examples.sfm'))
