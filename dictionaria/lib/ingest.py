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
from clldutils.misc import cached_property, slug
from clldutils.path import Path

from dictionaria import models


def split(s, sep=';'):
    for p in s.split(sep):
        p = p.strip()
        if p:
            yield p


class Example(Entry):
    markers = OrderedDict()
    for k, v in [
        ('ref', 'id'),
        ('lemma', None),
        ('rf', 'corpus_ref'),
        ('tx', 'text'),
        ('mb', 'morphemes'),
        ('gl', 'gloss'),
        ('ft', 'translation')
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


def load_examples(submission, data, lang):
    for ex in Examples.from_file(submission.dir.joinpath('processed', 'examples.sfm')):
        data.add(
            common.Sentence,
            ex.id,
            id='%s-%s' % (submission.id, ex.id.replace('.', '_')),
            name=ex.text,
            language=lang,
            analyzed=ex.morphemes,
            gloss=ex.gloss,
            description=ex.translation)


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
        load_examples(submission, data, lang)

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
            try:
                m = models.Meaning(
                    id=id_(sense),
                    name=sense['meaning description'],
                    word=data['Word'][sense['belongs to lemma']])
            except:
                print(submission.id)
                print(sense)
                raise

            for exid in split(sense.get('example ID', '')):
                s = data['Sentence'].get(exid)
                if not s:
                    print(submission.id)
                    print(sense)
                    raise ValueError
                models.MeaningSentence(meaning=m, sentence=s)
