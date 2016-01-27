# coding: utf8
from __future__ import unicode_literals, print_function
from mimetypes import guess_type
import re

import xlrd

from clldutils.path import Path, as_posix
from clldutils.dsv import UnicodeWriter, reader
from clld.scripts.util import Data
from clld.db.meta import DBSession
from clld.db.models.common import Unit_data, Unit_files

from dictionaria.lib.ingest import Example, Examples, load_examples
from dictionaria import models


ASSOC_PATTERN = re.compile('associated\s+[a-z]+\s*(\((?P<rel>[^\)]+)\))?')


def split(s, sep=';'):
    for p in s.split(sep):
        p = p.strip()
        if p:
            yield p


class Sheet(object):
    def __init__(self, sheet):
        self.name = sheet.name.lower()
        self._sheet = sheet
        self.header = []
        self.rows = []
        for i in range(sheet.nrows):
            row = [cell.value for cell in sheet.row(i)]
            if i == 0:
                self.header = row
                assert 'ID' in self.header[0].split()
                self.header[0] = 'ID'
            else:
                if self.header[0] == 'ID' and set(row[1:]) == {''}:
                    continue
                self.rows.append(row)
        ids = [r[0] for r in self.rows]
        assert len(ids) == len(set(ids))

    def yield_dicts(self):
        for row in self.rows:
            yield dict(zip(self.header, row))

    def write_csv(self, outdir):
        with UnicodeWriter(outdir.joinpath('%s.csv' % self.name)) as writer:
            writer.writerow(self.header)
            writer.writerows(self.rows)


class Dictionary(object):
    required_sheets = ['lemmas', 'senses', 'examples']

    def __init__(self, filename, **kw):
        self.filename = filename
        self.dir = Path(filename).parent
        self.workbook = None
        self.sheets = []
        if self.dir.name != 'processed':
            self.workbook = xlrd.open_workbook(as_posix(filename))
            self.sheets = [Sheet(sheet) for sheet in self.workbook.sheets()]

            for name in self.required_sheets:
                assert name in [s.name for s in self.sheets]

    def stats(self):
        print(self.filename)
        for sheet in self.sheets:
            print(sheet.name, len(sheet.rows))

    def __getitem__(self, item):
        for sheet in self.sheets:
            if sheet.name == item:
                return sheet

    def yield_examples(self):
        for d in self['examples'].yield_dicts():
            ex = Example()
            ex.set('id', d['ID'])
            ex.set('text', d['vernacular'])
            ex.set('morphemes', d['morphemes'])
            ex.set('gloss', d['gloss'])
            ex.set('translation', d['translation'])
            yield ex

    def process(self, outfile):
        """extract examples, etc."""
        assert self.dir.name != 'processed'

        examples = Examples(list(self.yield_examples()))
        examples.write(outfile.parent.joinpath('examples.sfm'))

        for sheet in self.sheets:
            if sheet.name != 'examples':
                sheet.write_csv(outfile.parent)

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
                        f = Unit_files(
                            id=id_(lemma),
                            name=img,
                            object_pk=word.pk,
                            mime_type=mimetype)
                        DBSession.add(f)
                        DBSession.flush()
                        DBSession.refresh(f)
                        with open(images[img].as_posix(), 'rb') as fp:
                            f.create(args.data_file('files'), fp.read())
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
                    if value:
                        DBSession.add(Unit_data(key=key, value=value, object_pk=word.pk))
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
