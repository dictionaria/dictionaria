# coding: utf8
from __future__ import unicode_literals, print_function
from collections import defaultdict
import re

from clldutils.path import Path
from clldutils.dsv import UnicodeWriter

from dictionaria.lib.ingest import Example, Examples, BaseDictionary


FORMAT_MAP = {
    'entries': (
        'lemmas.csv',
        {
            'entry_ID': 'ID',
            'headword': 'Lemma',
        }),
    'senses': (
        'senses.csv',
        {
            'sense_ID': 'ID',
            'sense': 'meaning description',
            'entry_ID': 'belongs to lemma',
        }),
}


class Dictionary(BaseDictionary):
    def __init__(self, filename, **kw):
        BaseDictionary.__init__(self, filename, **kw)
        self.workbook = None
        self.sheets = []

    def stats(self):
        print(self.filename)

    def readlines(self, name, suffix='csv', sep='\n'):
        fname = self.dir.joinpath('{0}.{1}'.format(name, suffix))
        with fname.open(encoding='macroman') as fp:
            c = fp.read()
        for line in c.split(sep):
            yield line.replace('\n', '\t')

    def yield_headers(self):
        fname = None
        for line in self.readlines('FIELDS', suffix='txt', sep='\n\n'):
            if line.endswith(':'):
                fname = line[:-1]
            elif line:
                assert fname
                yield fname, line.split('\t')

    @staticmethod
    def normalize_col(s):
        if s.startswith('"'):
            s = s[1:]
        if s.endswith('"'):
            s = s[:-1]
        return re.sub('\s+', ' ', s.replace('\x00', ' ')).strip()

    def readrows(self, name):
        for line in self.readlines(name):
            row = [self.normalize_col(c) for c in line.split('","')]
            if any(row):
                yield row

    def yield_examples(self):
        for row in self.readrows('examples'):
            id_, text, translation, sense = row
            ex = Example()
            ex.set('id', id_)
            ex.set('text', text)
            ex.set('translation', translation)
            yield ex

    def process(self, outfile):
        """extract examples, etc."""
        assert self.dir.name != 'processed'
        #
        # TODO:
        # - convert examples.csv into sfm
        # - inline assoc table data
        # - include associations.csv as col "associated lemma" in lemmas.csv!
        #
        associations = defaultdict(list)
        for s, t in self.readrows('associations'):
            associations[s].append(t)

        examples = defaultdict(list)
        for s, t in self.readrows('senses_examples'):
            examples[s].append(t)

        for fname, header in self.yield_headers():
            if fname in FORMAT_MAP:
                name, col_map = FORMAT_MAP[fname]
                header = [col_map.get(col, col) for col in header]
                with UnicodeWriter(outfile.parent.joinpath(name)) as fp:
                    if name == 'lemmas.csv':
                        header.append('associated lemma')
                    elif name == 'senses.csv':
                        header.append('example ID')
                    assert header[0] == 'ID'
                    fp.writerow(header)
                    for row in self.readrows(fname):
                        if name == 'lemmas.csv':
                            row.append('; '.join(associations.get(row[0], [])))
                        elif name == 'senses.csv':
                            row.append('; '.join(examples.get(row[0], [])))
                        fp.writerow(row)

        examples = Examples(list(self.yield_examples()))
        examples.write(outfile.parent.joinpath('examples.sfm'))
