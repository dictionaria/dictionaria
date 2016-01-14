# coding: utf8
from __future__ import unicode_literals, print_function

import xlrd

from clldutils.path import Path, as_posix
from clldutils.dsv import UnicodeWriter, reader
from clld.scripts.util import Data
from clld.db.meta import DBSession
from clld.db.models.common import Unit_data

from dictionaria.lib.ingest import Example, Examples, load_examples
from dictionaria import models


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
            marker_map):
        data = Data()
        rel = []

        vocab = models.Dictionary.get(did)
        lang = models.Variety.get(lid)
        load_examples(submission, data, lang)

        def id_(obj):
            return '%s-%s' % (submission.id, obj['ID'])

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
            except:
                print(submission.id)
                print(lemma)
                raise

        DBSession.flush()
        for lemma in reader(self.dir.joinpath('lemmas.csv'), dicts=True):
            #
            # FIXME: handle relations between words!
            #
            word = data['Word'][lemma['ID']]
            for key in lemma:
                if key not in ['ID', 'Lemma', 'PoS']:
                    value = lemma[key]
                    if value:
                        DBSession.add(Unit_data(key=key, value=value, object_pk=word.pk))

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
