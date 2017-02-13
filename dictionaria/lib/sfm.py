# coding: utf8
"""
Parsing functionality for the SFM variant understood for Dictionaria submissions.
"""
from __future__ import unicode_literals, print_function
from collections import defaultdict
import re
from copy import copy

from clld.db.models import common
from clld.db.meta import DBSession

from clldutils import sfm
from clldutils.misc import cached_property

from dictionaria.lib.ingest import MeaningDescription, split, BaseDictionary
from dictionaria import models

sfm.MARKER_PATTERN = re.compile('\\\\(?P<marker>([A-Za-z1-3][A-Za-z_]*|zcom2))(\s+|$)')


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


class Meaning(object):
    """
    A word can have several meanings, described by meaning description and gloss.

    Semantic domain and examples are also meaning specific.
    """
    def __init__(self):
        self.de = None
        self.ge = None
        self.gxx = None
        self.gxy = None
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


RELATION_MAP = {
    'cf': 'see also',
    'mn': 'main entry',
    'an': 'antonym',
    'sy': 'synonym',
}


class Entry(sfm.Entry):
    """
    A dictionary entry.
    """
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
        for marker, mtype in [('sf', 'audio'), ('pc', 'image')]:
            for n in self.getall(marker):
                for nn in split(n):
                    res.append((nn, mtype))
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
            elif k in ['de', 'ge', 're', 'gxx', 'gxy']:
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
            elif k in RELATION_MAP:
                word.rel.extend([(RELATION_MAP[k], vv.strip()) for vv in split(v, ',')])
            else:
                word.data[k].append(v)
        if word and word.form:
            yield self.checked_word(word, meaning, pos)


class Dictionary(BaseDictionary):
    @cached_property()
    def sfm(self):
        return sfm.SFM.from_file(
            self.dir.joinpath('db.sfm'),
            entry_sep='\\lx ',
            entry_prefix='\\lx ',
            entry_impl=Entry)

    def concepticon(self, db):
        visitor = Concepticon()
        self.sfm.visit(visitor)
        print('Found comparison meanings for %s of %s entries' % (
            visitor.count, len(self.sfm)))
        self.sfm.write(db)

    def load(
            self,
            submission,
            data,
            vocab,
            lang,
            comparison_meanings,
            labels):
        rel = []
        skipped = []
        words_by_lemma = defaultdict(list)

        def meaning_descriptions(s):
            return split((s or '').replace('.', ' ').lower())

        for i, entry in enumerate(self.sfm):
            words = list(entry.get_words())
            headword = None

            for j, word in enumerate(words):
                if word.form.startswith('\\_'):
                    continue
                if not word.meanings:
                    skipped.append(word)
                    continue

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

                if not headword:
                    headword = word.id
                else:
                    rel.append((w, 'main entry', headword))

                for tw in word.rel:
                    rel.append((w, tw[0], tw[1]))

                words_by_lemma[word.form].append(w)
                if word.hm:
                    words_by_lemma['{0} {1}'.format(word.form, word.hm)].append(w)
                DBSession.flush()

                for md5, type_ in set(entry.files):
                    submission.add_file(type_, md5, common.Unit_files, w)

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
                        alt_translation1=meaning.gxx,
                        alt_translation_language1=submission.props.get('metalanguages', {}).get('gxx'),
                        alt_translation2=meaning.gxy,
                        alt_translation_language2=submission.props.get('metalanguages', {}).get('gxy'),
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
                for m in re.finditer('\[(?P<id>[0-9]+)\]', entry.get('zcom2', '')):
                    cid = m.group('id')
                    vsid = '%s-%s' % (submission.id, cid)
                    if vsid in data['ValueSet']:
                        vs = data['ValueSet'][vsid]
                    else:
                        vs = data.add(
                            common.ValueSet,
                            vsid,
                            id=vsid,
                            language=lang,
                            contribution=vocab,
                            parameter_pk=comparison_meanings[cid])

                    vid = '%s-%s' % (vsid, w.id)
                    if vid not in data['Counterpart']:
                        data.add(
                            models.Counterpart,
                            vid,
                            id=vid,
                            name=w.name,
                            valueset=vs,
                            word=w)

                for index, (key, values) in enumerate(word.data.items()):
                    if key in labels:
                        for value in values:
                            DBSession.add(common.Unit_data(
                                object_pk=w.pk, key=labels[key], value=value, ord=index))

        # FIXME: vgroup words by description and add synonym relationships!
        for word in data['Word'].keys()[:]:
            if '-' in word:
                alt = word.replace('-', '')
                if alt not in data['Word']:
                    data['Word'][alt] = data['Word'][word]

        for i, (w, d, target) in enumerate(rel):
            for t in words_by_lemma.get(target, []):
                DBSession.add(models.SeeAlso(
                    source_pk=w.pk, target_pk=t.pk, description=d, ord=i))

        if skipped:
            print('{0} entries with no meaning skipped'.format(len(skipped)))
