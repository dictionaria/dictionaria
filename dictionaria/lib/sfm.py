# coding: utf8
"""
Parsing functionality for the SFM variant understood for Dictionaria submissions.
"""
from __future__ import unicode_literals, print_function
from collections import defaultdict, Counter, OrderedDict
import re
from copy import copy
from mimetypes import guess_type

from transliterate import translit

from clld.scripts.util import Data
from clld.db.models import common
from clld.db.meta import DBSession

from clldutils.misc import slug
from clldutils.path import Path
from clldutils import sfm

from dictionaria.lib.ingest import Corpus, Example, MeaningDescription, split
from dictionaria import models


def move_marker(entry, m, before):
    reorder_map = []
    last_m = 0

    for index, (marker, content) in enumerate(entry):
        if marker == m:
            # search for the preceding 'before' marker, but make sure we do not go
            # back before the last 'm' marker.
            for i in range(index - 1, last_m, -1):
                if entry[i][0] == before:
                    reorder_map.append((i, content, index))
                    break
            else:
                entry[index] = (m, content)
            last_m = index

    for insert, content, delete in reorder_map:
        del entry[delete]
        entry.insert(insert, (m, content))


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

        move_marker(entry, 'xsf', 'xe')
        move_marker(entry, 'xo', 'xe')
        move_marker(entry, 'xr', 'xe')


class Files(object):
    def __init__(self, submission):
        self.submission = submission
        # we create a lookup for files
        self.files = {'audio': {}, 'image': {}}
        for type_ in self.files:
            _dir = submission.dir.joinpath(type_)
            if _dir.exists():
                for p in _dir.iterdir():
                    if p.is_file():
                        self.files[type_][p.name.decode('utf8')] = p
                        # and just in case, add transliterated variants of file names:
                        nname = translit(p.name.decode('utf8'), 'ru', reversed=True)
                        if nname not in self.files[type_]:
                            self.files[type_][nname] = p
                        self.files[type_][p.stem.decode('utf8') + p.suffix.lower()] = p
                        self.files[type_][p.stem.decode('utf8') + p.suffix.upper()] = p
        self.missingg = set()

    def process(self, type_, content):
        fp = self.files[type_].get(content)
        if fp:
            res = self.submission.process_file(type_, fp)
            return res.name.decode('utf8')
        self.missingg.add(content)
        print('missing {0} file: {1}'.format(type_, content))
        return ''

    def __call__(self, entry):
        items = []
        for marker, content in entry:
            if marker == 'pc':
                for fname in split(content):
                    content = self.process('image', fname)
                    if content:
                        items.append((marker, content))
                continue
            if marker in ['sf', 'sfx']:
                for fname in split(content):
                    maintype = 'audio'
                    mtype = guess_type(fname)[0]
                    if mtype and mtype.startswith('image/'):
                        maintype = 'image'
                    content = self.process(maintype, fname)
                    if content:
                        items.append((marker, content))
                continue
            if content:
                items.append((marker, content))
        return entry.__class__(items)


class Concepticon(object):
    def __init__(self):
        self.count = 0

    def __call__(self, entry):
        items = []
        for marker, content in entry:
            if marker == 'de':
                md = MeaningDescription(content)
                items.append((marker, md.meanings))
                if md.has_comparison_meaning:
                    self.count += 1
                items.append(('comparison_meanings', md.comparison_meanings))
            else:
                items.append((marker, content))
        return entry.__class__(items)


class ExampleExtractor(object):
    def __init__(self, corpus, log):
        self.example_props = {
            'rf': 'rf',
            'xv': 'tx',
            'xvm': 'mb',
            'xeg': 'gl',
            'xo': 'ot',
            'xn': 'ot',
            'xr': 'ota',
            'xe': 'ft',
            'sfx': 'sf',
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
                    assert example
                elif marker == 'xe':
                    # example ends
                    if example:
                        if rf:
                            example.insert(0, ('rf', rf))
                        example.append(('ft', content))
                        example.set('lemma', lx)
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
        for prop in 'rf tx mb gl ft ot'.split():
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
        if ex1.lemmas:
            ex2.set('lemma', ex1.get('lemma'))
        if ex2.lemmas:
            ex1.set('lemma', ex2.get('lemma'))

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
        self.re = None
        self.sd = []
        self.xref = []


class Word(object):
    """
    A word is the atomic language unit in dictionaria.

    A dictionary entry may contain multiple words via sub-entry markers.
    """
    def __init__(self, form):
        self.form = form
        self._hm = 0  # homonym marker
        self.ph = None  # phonetic representation of the word
        self._ps = None  # part-of-speech
        self.data = defaultdict(list)  # to store additional marker, value pairs
        self.rel = []
        self.meanings = []
        self.non_english_meanings = defaultdict(list)

    @property
    def ps(self):
        return self._ps

    @ps.setter
    def ps(self, value):
        if self._ps and self._ps != value:
            raise ValueError('Multiple assignments of different pos for %s: %s, %s' % (
                self.form, self._ps, value))
        self._ps = value

    @property
    def hm(self):
        return '{0}'.format(self._hm) if self._hm else ''

    @hm.setter
    def hm(self, value):
        m = re.search('(?P<number>[0-9]+)', value)
        self._hm = int(m.group('number')) if m else 0

    def copy(self):
        w = Word(self.form)
        w.ph = self.ph
        if not self.hm:
            self.hm = '1'
        w.hm = '{0}'.format(int(self.hm) + 1)
        w.data = copy(self.data)
        return w

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

    def checked_word(self, word, meaning, pos):
        if meaning:
            if meaning.de or meaning.ge:
                word.meanings.append(meaning)
            #else:
                #print('meaning without description for %s' % word.form)
        if word.ps is None:
            word.ps = pos
        return word

    @property
    def files(self):
        res = []
        for n in self.getall('sf'):
            for nn in n.split(' ;'):
                nn = nn.strip()
                if nn:
                    res.append((nn, 'audio'))
        res.extend([(n, 'image') for n in self.getall('pc')])
        return res

    def get_words(self):
        """
        :return: generator for the words contained within the entry.
        """
        word = None
        # if an entry has only one \ps marker but multiple words, the value of \ps is used
        # as part-of-speech for all words.
        pos = None

        meaning = None

        # flag signaling whether we are dealing with the first meaning of a word or
        # subsequent ones.
        first_meaning = True
        sn_is_se = False

        # now we loop over the (marker, value) pairs of the entry:
        for k, v in self:
            # individual words are identified by \lx or \se (sub-entry) markers.
            if k in ['lx', 'se']:
                if word:
                    yield self.checked_word(word, meaning, pos)
                word = Word(v)
                meaning = Meaning()
            elif k == 'sn':  # a new sense number: initialize a new Meaning.
                word.hm = word.hm or v
                if first_meaning:
                    # determine whether we are dealing with the case where \ps comes after
                    # \sn, thus, \sn has to be treated like \se:
                    sn_is_se = not bool(pos)
                    first_meaning = False
                else:
                    self.checked_word(word, meaning, pos)
                    if sn_is_se and word.form:
                        yield word
                        word = word.copy()
                    meaning = Meaning()
            # meaning-specific markers:
            elif k in ['de', 'ge', 're']:
                # FIXME: we must support multiple meanings expressed by
                # semicolon-separated \ge values, e.g. "jump ; jump at"
                setattr(meaning, k, v)
            elif k == 'sd':
                meaning.sd.append(v)
            elif k == 'xref':
                meaning.xref.append(v)
            # word-specific markers:
            elif k in ['hm', 'ph']:
                if getattr(word, k) is None:
                    # only record first occurrence of the marker!
                    setattr(word, k, v)
            elif k == 'ps':
                pos = v
                try:
                    word.ps = v
                except ValueError:
                    self.checked_word(word, meaning, pos)
                    if word.form:
                        yield word
                        word = word.copy()
                        word.ps = v
                    meaning = Meaning()
            elif k in ['cf', 'mn']:
                word.rel.extend([(k, vv) for vv in split(v, ',')])
            elif k in ['gxx', 'gxy']:  # support two meta/target languages
                word.non_english_meanings[k].extend(sfm.FIELD_SPLITTER_PATTERN.split(v))
            else:
                word.data[k].append(v)
        if word and word.form:
            yield self.checked_word(word, meaning, pos)


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


def default_value_converter(value, _):
    return value


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

    def stats(self):
        stats = Stats()
        self.sfm.visit(stats)
        print(stats.count)
        print(stats._mult_markers)
        print(stats._implicit_mult_markers)

    def concepticon(self, db):
        visitor = Concepticon()
        self.sfm.visit(visitor)
        print('Found comparison meanings for %s of %s entries' % (
            visitor.count, len(self.sfm)))
        self.sfm.write(db)

    def process(self, outfile, submission):
        """extract examples, etc."""
        assert self.dir.name != 'processed'

        self.sfm.visit(Rearrange())
        files = Files(submission)
        self.sfm.visit(files)
        print('{0} files missing'.format(len(files.missingg)))
        #for m in files.missingg:
        #    print(m)

        with self.dir.joinpath('examples.log').open('w', encoding='utf8') as log:
            extractor = ExampleExtractor(Corpus(self.dir), log)
            self.sfm.visit(extractor)

        self.sfm.write(outfile)
        extractor.write_examples(outfile.parent.joinpath('examples.sfm'))

    def load(
            self,
            submission,
            did,
            lid,
            comparison_meanings,
            comparison_meanings_alt_labels,
            marker_map,
            args):
        data = Data()
        rel = []

        vocab = models.Dictionary.get(did)
        lang = models.Variety.get(lid)
        xrefs = []
        for entry in self.sfm:
            xrefs.extend(entry.getall('xref'))
        submission.load_examples(args, data, lang, set(xrefs))

        def meaning_descriptions(s):
            return list(split((s or '').replace('.', ' ').lower()))

        for i, entry in enumerate(self.sfm):
            words = list(entry.get_words())
            headword = None

            for j, word in enumerate(words):
                #if not word.meanings:
                #    print('skip entry without meaning: %s' % word.form)
                #    continue

                if not headword:
                    headword = word.id
                else:
                    rel.append((word.id, 'sub', headword))

                for tw in word.rel:
                    rel.append((word.id, tw[0], tw[1]))

                w = data.add(
                    models.Word,
                    word.id,
                    id='%s-%s-%s' % (submission.id, i + 1, j + 1),
                    name=word.form,
                    number=int(word.hm) if word.hm and word.hm != '-' else 0,
                    phonetic=word.ph,
                    pos=word.ps,
                    #original='%s' % entry
                    dictionary=vocab,
                    language=lang)
                DBSession.flush()

                submission.add_file(
                    args, 'image', w.name + '.png', common.Unit_files, w, 1, log='found')

                for index, (fname, type_) in enumerate(entry.files):
                    submission.add_file(
                        args, type_, fname, common.Unit_files, w, index)

                concepts = []

                for k, meaning in enumerate(word.meanings):
                    if not (meaning.ge or meaning.de):
                        # FIXME: better logging!
                        #print('meaning without description for word %s' % w.name)
                        continue

                    if meaning.ge:
                        meaning.ge = meaning.ge.replace('.', ' ')

                    m = models.Meaning(
                        id='%s-%s' % (w.id, k + 1),
                        name=meaning.de or meaning.ge,
                        description=meaning.de,
                        gloss=meaning.ge,
                        reverse=meaning.re,
                        #ord=k + 1,
                        word=w,
                        semantic_domain=', '.join(meaning.sd))

                    for xref in meaning.xref:
                        s = data['Example'].get(xref)
                        if s is None:
                            print('missing example referenced: %s' % xref)
                        else:
                            models.MeaningSentence(meaning=m, sentence=s)

                    #
                    # Lookup comparison meanings.
                    #
                    concept, key = None, None
                    for key in meaning_descriptions(meaning.re) + \
                            meaning_descriptions(meaning.de) + \
                            meaning_descriptions(meaning.ge):
                        if key in comparison_meanings:
                            concept = comparison_meanings[key]
                        elif key in comparison_meanings_alt_labels:
                            concept = comparison_meanings_alt_labels[key]
                        if concept:
                            break

                    if concept and key and concept not in concepts:
                        concepts.append(concept)
                        vsid = '%s-%s' % (key, submission.id),
                        if vsid in data['ValueSet']:
                            vs = data['ValueSet'][vsid]
                        else:
                            vs = data.add(
                                common.ValueSet, vsid,
                                id='%s-%s' % (submission.id, m.id),
                                language=lang,
                                contribution=vocab,
                                parameter_pk=concept)

                        DBSession.add(models.Counterpart(
                            id='%s-%s' % (w.id, k + 1),
                            name=w.name,
                            valueset=vs,
                            word=w))

                for _lang, meanings in word.non_english_meanings.items():
                    assert _lang in submission.md['metalanguages']

                    #DBSession.add(common.Unit_data(
                    #    object_pk=w.pk,
                    #    key='lang-%s' % submission.md['metalanguages'][_lang],
                    #    value='; '.join(meanings),
                    #    ord=-1))

                    for meaning in meanings:
                        k += 1
                        models.Meaning(
                            id='%s-%s' % (w.id, k + 1),
                            name=meaning,
                            gloss=meaning,
                            language=submission.md['metalanguages'][_lang],
                            word=w)

                for index, (key, values) in enumerate(word.data.items()):
                    if key in marker_map:
                        label = marker_map[key]
                        converter = default_value_converter
                        if isinstance(label, (list, tuple)):
                            label, converter = label
                        for value in values:
                            DBSession.add(common.Unit_data(
                                object_pk=w.pk,
                                key=label,
                                value=converter(value, word.data),
                                ord=index))

        # FIXME: vgroup words by description and add synonym relationships!

        for s, d, t in rel:
            if s in data['Word'] and t in data['Word']:
                DBSession.add(models.SeeAlso(
                    source_pk=data['Word'][s].pk,
                    target_pk=data['Word'][t].pk,
                    description=d))
            else:
                pass
                # FIXME: better logging!
                #print('---m---', s if s not in data['Word'] else t)
