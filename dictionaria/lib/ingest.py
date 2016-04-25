# coding: utf8
from __future__ import unicode_literals
from hashlib import md5
from collections import OrderedDict
from mimetypes import guess_type
import re

from clld.db.models import common
from clld.db.meta import DBSession
from clld.scripts.util import Data
from clldutils.dsv import reader
from clldutils.sfm import SFM, Entry
from clldutils.misc import cached_property, slug, UnicodeMixin
from clldutils.path import Path
from clldutils.jsonlib import load

import dictionaria
from dictionaria import models


def split(s, sep=';'):
    for p in s.split(sep):
        p = p.strip()
        if p:
            yield p


_concepticon = None


def get_concept(s):
    global _concepticon
    if _concepticon is None:
        _concepticon = load(Path(dictionaria.__file__).parent.joinpath(
            'static', 'concepticon-1.0-labels.json'))
    s = s.lower()
    if s in _concepticon['conceptset_labels']:
        return _concepticon['conceptset_labels'][s]
    return _concepticon['alternative_labels'].get(s)


class ComparisonMeaning(UnicodeMixin):
    def __init__(self, s):
        self.id = None
        self.label = None
        cid = get_concept(s)
        if cid:
            self.id, self.label = cid

    def __unicode__(self):
        if self.id:
            return '[%s](http://concepticon.clld.org/parameters/%s)' % (
                self.label, self.id)
        return ''


class MeaningDescription(object):
    # split s at ;
    # lookup concepticon match
    def __init__(self, s):
        self._meanings = []
        self._comparison_meanings = []
        for m in split(s):
            self._meanings.append(m)
            cm = ComparisonMeaning(m)
            self._comparison_meanings.append(cm if cm.id else '')

    @property
    def has_comparison_meaning(self):
        return any(self._comparison_meanings)

    @property
    def meanings(self):
        return '; '.join(self._meanings)

    @property
    def comparison_meanings(self):
        return '; '.join('%s' % cm for cm in self._comparison_meanings)


class Example(Entry):
    markers = OrderedDict()
    for k, v in [
        ('ref', 'id'),
        ('lemma', None),
        ('rf', 'corpus_ref'),
        ('tx', 'text'),
        ('mb', 'morphemes'),
        ('gl', 'gloss'),
        ('ft', 'translation'),
        ('ot', 'alt_translation'),
        ('sf', 'soundfile'),
    ]:
        markers[k] = v
    name_to_marker = {v: k for k, v in markers.items()}

    @staticmethod
    def normalize(morphemes_or_gloss):
        """
        Normalize aligned words by replacing whitespace with single tab, and removing
        ELAN comments.
        """
        if morphemes_or_gloss:
            return '\t'.join(
                [p for p in morphemes_or_gloss.split() if not p.startswith('#')])

    @property
    def id(self):
        res = self.get('ref')
        if not res:
            res = md5(slug(self.text or '' + self.translation or '').encode('utf')).hexdigest()
            self.insert(0, ('ref', res))
        return res

    def set(self, key, value):
        assert (key in self.markers) or (key in self.name_to_marker)
        key = self.name_to_marker.get(key, key)
        for i, (k, v) in enumerate(self):
            if k == key:
                if key == 'lemma':
                    value = ' ; '.join([v, value])
                self[i] = (key, value)
                break
        else:
            self.append((key, value))

    @property
    def lemmas(self):
        return [l.strip() for l in self.get('lemma', '').split(';') if l.strip()]

    @property
    def corpus_ref(self):
        return self.get('rf')

    @property
    def text(self):
        return self.get('tx')

    @property
    def translation(self):
        return self.get('ft')

    @property
    def alt_translation(self):
        return self.get('ot')

    @property
    def soundfile(self):
        return self.get('sf')

    @property
    def morphemes(self):
        return self.normalize(self.get('mb'))

    @property
    def gloss(self):
        return self.normalize(self.get('gl'))

    def __unicode__(self):
        lines = []
        for key in self.markers:
            value = self.get(key) or ''
            if key in ['mb', 'gl']:
                value = self.normalize(value) or ''
            else:
                value = ' '.join(value.split())
            lines.append('%s %s' % (key, value))
        return '\n'.join('\\' + l for l in lines)


class Examples(SFM):
    def read(self, filename, **kw):
        return SFM.read(self, filename, entry_impl=Example, **kw)

    @cached_property()
    def _map(self):
        return {entry.get('ref'): entry for entry in self}

    def get(self, item):
        return self._map.get(item)


def load_examples(args, submission, data, lang, xrefs=None):
    for ex in Examples.from_file(submission.dir.joinpath('processed', 'examples.sfm')):
        if xrefs is None or ex.id in xrefs:
            obj = data.add(
                models.Example,
                ex.id,
                id='%s-%s' % (submission.id, ex.id.replace('.', '_')),
                name=ex.text,
                language=lang,
                analyzed=ex.morphemes,
                gloss=ex.gloss,
                description=ex.translation,
                alt_translation=ex.alt_translation,
                alt_translation_language=submission.md.get('metalanguages', {}).get('gxx'))
            DBSession.flush()

            if ex.soundfile:
                name = ex.soundfile.replace('.wav', '.mp3').encode('utf8')
                sf = submission.dir.joinpath('audio', name)
                if sf.exists():
                    mimetype = guess_type(sf.name)[0]
                    if not mimetype:
                        print('missing soundfile:', sf.name)
                    else:
                        assert mimetype.startswith('audio/')
                        f = common.Sentence_files(
                            id='%s-%s' % (submission.id, obj.id),
                            name=sf.name.decode('utf8'),
                            object_pk=obj.pk,
                            mime_type=mimetype,
                            jsondata=submission.md.get('audio', {}))
                        DBSession.add(f)
                        DBSession.flush()
                        DBSession.refresh(f)
                        with open(sf.as_posix(), 'rb') as fp:
                            f.create(args.data_file('files'), fp.read())


class Corpus(object):
    """
    ELAN corpus exported using the Toolbox exporter

    http://www.mpi.nl/corpus/html/elan/ch04s03s02.html#Sec_Exporting_a_document_to_Toolbox
    """
    def __init__(self, dir_):
        self.examples = Examples()
        marker_map = {
            'utterance_id': 'ref',
            'utterance': 'tx',
            'gramm_units': 'mb',
            'rp_gloss': 'gl',
        }
        for path in dir_.glob('*.eaf.sfm'):
            self.examples.read(path, marker_map=marker_map, entry_sep='\\utterance_id')

    def get(self, key):
        res = self.examples.get(key)
        if not res:
            # We try to correct the lookup key. If a key like 'Abc.34' is used and not
            # found, we try 'Abc.034' as well.
            try:
                prefix, number = key.split('.', 1)
                res = self.examples.get('%s.%03d' % (prefix, int(number)))
            except ValueError:
                pass
        return res


ASSOC_PATTERN = re.compile('associated\s+[a-z]+\s*(\((?P<rel>[^\)]+)\))?')


class BaseDictionary(object):
    """
    A dictionary that knows how to load data from a `processed` directory.
    """
    def __init__(self, filename, **kw):
        self.filename = filename
        self.dir = Path(filename).parent

    def stats(self):
        print(self.filename)

    def process(self, outfile):
        """extract examples, etc."""
        assert self.dir.name != 'processed'
        raise NotImplementedError()

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

        vocab = models.Dictionary.get(did)
        lang = models.Variety.get(lid)
        load_examples(args, submission, data, lang)

        def id_(obj):
            return '%s-%s' % (submission.id, obj['ID'])

        img_map = {
            'nan-ke-öm.jpg': 'nan_ke-öm.jpg',
            'nan-ki-geigei.jpg': 'nan_ki-geigei.jpg',
            'nan_ki-nde': 'nan_ki-nde.jpg',
        }
        images = {}
        image_dir = self.dir.parent.joinpath('images')
        if image_dir.exists():
            for p in image_dir.iterdir():
                if p.is_file():
                    images[p.name.decode('utf8')] = p

        for lemma in reader(self.dir.joinpath('lemmas.csv'), dicts=True):
            try:
                word = data.add(
                    models.Word,
                    lemma['ID'],
                    id=id_(lemma),
                    name=lemma['Lemma'],
                    pos=lemma['PoS'],
                    dictionary=vocab,
                    language=lang)
                DBSession.flush()
                img = lemma.get('picture')
                if img:
                    img = img_map.get(img, img)
                    if img not in images:
                        print(img, self.dir)
                        raise ValueError
                    else:
                        mimetype = guess_type(img)[0]
                        assert mimetype.startswith('image/')
                        f = common.Unit_files(
                            id=id_(lemma),
                            name=img,
                            object_pk=word.pk,
                            mime_type=mimetype)
                        DBSession.add(f)
                        DBSession.flush()
                        DBSession.refresh(f)
                        with open(images[img].as_posix(), 'rb') as fp:
                            f.create(args.data_file('files'), fp.read())
                for index, (key, value) in enumerate(lemma.items()):
                    if key in marker_map:
                        DBSession.add(common.Unit_data(
                            object_pk=word.pk,
                            key=marker_map[key],
                            value=value,
                            ord=index))
            except:
                print(submission.id)
                print(lemma)
                raise

        DBSession.flush()

        for lemma in reader(self.dir.joinpath('lemmas.csv'), dicts=True):
            word = data['Word'][lemma['ID']]
            for key in lemma:
                if key in ['ID', 'Lemma', 'PoS', 'picture']:
                    continue
                assoc = ASSOC_PATTERN.match(key)
                if not assoc:
                    value = lemma[key]
                    if value and not marker_map:
                        DBSession.add(common.Unit_data(key=key, value=value, object_pk=word.pk))
                else:
                    for lid in split(lemma.get(key, '')):
                        # Note: we correct invalid references, e.g. "lx 13" and "Lx13".
                        lid = lid.replace(' ', '').lower()
                        DBSession.add(models.SeeAlso(
                            source_pk=word.pk,
                            target_pk=data['Word'][lid].pk,
                            description=assoc.group('rel')))

        for sense in reader(self.dir.joinpath('senses.csv'), dicts=True):
            w = data['Word'][sense['belongs to lemma']]
            try:
                m = models.Meaning(
                    id=id_(sense), name=sense['meaning description'], word=w)
            except:
                print(submission.id)
                print(sense)
                raise

            for exid in split(sense.get('example ID', '')):
                s = data['Example'].get(exid)
                if not s:
                    print(submission.id)
                    print(sense)
                    raise ValueError
                models.MeaningSentence(meaning=m, sentence=s)

            for i, md in enumerate(split(sense['meaning description'])):
                key = md.lower()
                if key in comparison_meanings:
                    concept = comparison_meanings[key]
                elif key in comparison_meanings_alt_labels:
                    concept = comparison_meanings_alt_labels[key]
                else:
                    continue

                vsid = '%s-%s' % (m.id, i)
                vs = data['ValueSet'].get(vsid)
                if not vs:
                    vs = data.add(
                        common.ValueSet, vsid,
                        id=vsid,
                        language=lang,
                        contribution=vocab,
                        parameter_pk=concept)

                DBSession.add(models.Counterpart(
                    id=vsid, name=w.name, valueset=vs, word=w))
