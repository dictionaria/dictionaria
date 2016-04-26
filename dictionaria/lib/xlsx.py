# coding: utf8
from __future__ import unicode_literals, print_function

import xlrd

from clldutils.path import as_posix
from clldutils.dsv import UnicodeWriter

from dictionaria.lib.ingest import Example, Examples, BaseDictionary


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


class Dictionary(BaseDictionary):
    required_sheets = ['lemmas', 'senses', 'examples']

    def __init__(self, filename, **kw):
        BaseDictionary.__init__(self, filename, **kw)
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

    def process(self, outfile, submission):
        """extract examples, etc."""
        BaseDictionary.process(self, outfile, submission)

        examples = Examples(list(self.yield_examples()))
        examples.write(outfile.parent.joinpath('examples.sfm'))

        for sheet in self.sheets:
            if sheet.name != 'examples':
                sheet.write_csv(outfile.parent)
