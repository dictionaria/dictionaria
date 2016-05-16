# coding: utf8
from __future__ import unicode_literals, print_function
import re

import xlrd

from clldutils.path import as_posix
from clldutils.dsv import UnicodeWriter

from dictionaria.lib.ingest import Example, Examples, BaseDictionary

"""
lemmas.csv - entries.csv
------------------------
Lemma - headword
PoS - part-of-speech

senses.csv
----------
belongs to lemma - entry ID
example ID - <missing>

examples.csv
------------
<missing> - sense ID
vernacular - example
morphemes - <missing>
gloss - <missing>
<missing> - source

questions
---------
- should we allow alternatives to relate examples and senses?
"""


class Sheet(object):
    def __init__(self, sheet):
        self.name = sheet.name.lower()
        self._sheet = sheet
        self.header = []
        self.rows = []
        for i in range(sheet.nrows):
            row = [cell.value for cell in sheet.row(i)]
            if i == 0:
                self.header = self.normalized_header(row, self.name)
            else:
                if self.header[0] == 'ID' and set(row[1:]) == {''}:
                    continue
                self.rows.append(self.normalized_row(row, self.name))
        ids = [r[0] for r in self.rows]
        assert len(ids) == len(set(ids))

    def normalized_header(self, row, name):
        for i, col in enumerate(row[:]):
            row[i] = re.sub(
                '(?P<c>[^\s])ID$', lambda m: m.group('c') + ' ID', col.strip())

        if 'ID' not in row:
            assert 'ID' in row[0]
            row[0] = 'ID'

        nrow = [''.join(r.lower().split()) for r in row]

        def repl(old, new):
            try:
                row[nrow.index(old)] = new
            except ValueError:
                pass

        if name == 'entries':
            repl('pos', 'part-of-speech')
            repl('lemma', 'headword')

        if name == 'senses':
            repl('meaningdescription', 'description')
            repl('belongstolemma', 'entry ID')

        print(self.name)
        print(row)
        return row

    def normalized_row(self, row, name):
        for i, head in enumerate(self.header):
            if 'ID' in head:
                val = row[i]
                if isinstance(val, (int, float)):
                    row[i] = '%s' % int(val)
        return row

    def yield_dicts(self):
        for row in self.rows:
            yield dict(zip(self.header, row))

    def write_csv(self, outdir, example_map=None):
        with UnicodeWriter(outdir.joinpath('%s.csv' % self.name)) as writer:
            if example_map:
                assert 'example ID' not in self.header
                self.header.append('example ID')
                for row in self.rows:
                    row.append(example_map.get(row[self.header.index('ID')], ''))

            writer.writerow(self.header)
            writer.writerows(self.rows)


class Dictionary(BaseDictionary):
    required_sheets = ['entries', 'senses', 'examples']

    def __init__(self, filename, **kw):
        BaseDictionary.__init__(self, filename, **kw)
        self.workbook = None
        self._example_map = {}
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
            if 'sense ID' in d:
                self._example_map[d['sense ID']] = d['ID']
            if 'example' not in d:
                d['example'] = d['vernacular']
            ex = Example()
            ex.set('id', d['ID'])
            ex.set('text', d['example'])
            ex.set('morphemes', d.get('morphemes'))
            ex.set('gloss', d.get('gloss'))
            ex.set('translation', d['translation'])
            yield ex

    def process(self, outfile, submission):
        """extract examples, etc."""
        BaseDictionary.process(self, outfile, submission)

        examples = Examples(list(self.yield_examples()))
        examples.write(outfile.parent.joinpath('examples.sfm'))

        for sheet in self.sheets:
            if sheet.name != 'examples':
                sheet.write_csv(outfile.parent, self._example_map)
