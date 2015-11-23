# coding: utf8
from __future__ import unicode_literals, print_function
from collections import OrderedDict
import re

from clldutils.sfm import SFM, FIELD_SPLITTER_PATTERN
from clld.scripts.util import parsed_args

from dictionaria.lib.sfm import Example
from dictionaria.scripts.util import Submission, Corpus


#
# Teop preprocess: \rf comes *after* the example, when the value is in square brackets!
# so when \rf [xxx] is encountered immediately after \xe, it must be moved before the
# corresponding \xv!
#
def rearrange(submission, outdir):
    d = SFM.from_file(
        submission.raw,
        encoding=submission.md.get('encoding', 'utf8'),
        marker_map=submission.md.get('marker_map'))

    in_brackets = re.compile('\[+\s*(?P<text>[^\]]+)\s*\]+$')

    def visitor(entry):
        reorder_map = []
        last_rf = 0

        for index, (marker, content) in enumerate(entry):
            if marker == 'rf':
                content = content.strip()
                match = in_brackets.match(content)
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

    d.visit(visitor)
    d.write(outdir.joinpath('db-rearranged.txt'))


class ExampleExtractor(object):
    def __init__(self, corpus):
        self.example_props = 'rf xv xvm xeg xo xe'.split()
        self.examples = OrderedDict()
        self.corpus = corpus

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
                    if example:
                        print('incomplete example in lx: %s - missing xe' % lx)
                    example = Example(content)
                elif marker == 'xe':
                    if example:
                        example.rf = rf
                        example.xe = content
                        if not example.xe:
                            print('incomplete example in lx: %s - empty xe' % lx)
                        else:
                            items.append(('xref', self.xref(example)))
                        rf = None
                        example = None
                    else:
                        print('incomplete example in lx: %s - missing xv' % lx)
                else:
                    if not example:
                        print('incomplete example in lx: %s - missing xv' % lx)
                    else:
                        setattr(example, marker, content)
            else:
                items.append((marker, content))
        return entry.__class__(items)

    def xref(self, example):
        if example.rf:
            from_corpus = self.corpus.get(example.rf)
            if from_corpus:
                example.merge(from_corpus, force_sameid=False)
        if example.id in self.examples:
            self.examples[example.id].merge(example)
            #assert examples[example.id] == example
            if not example == self.examples[example.id]:
                for prop in 'xvm xeg rf'.split():
                    if getattr(example, prop) != getattr(self.examples[example.id], prop):
                        print(prop)
                        print(getattr(example, prop).encode('utf8'))
                        print(getattr(self.examples[example.id], prop).encode('utf8'))
                        print()
        self.examples[example.id] = example
        return example.id

    def write_examples(self, fname):
        with fname.open('w', encoding='utf8') as x:
            for example in self.examples.values():
                x.write(example.text)


def extract_examples(submission, outdir):
    kw = {}
    fname = outdir.joinpath('db-rearranged.txt')
    if not outdir.joinpath('db-rearranged.txt').exists():
        fname = submission.raw
        kw['encoding'] = submission.md.get('encoding')
        kw['marker_map'] = submission.md.get('marker_map')
    db = SFM.from_file(fname, **kw)
    extractor = ExampleExtractor(Corpus(submission.dir))
    db.visit(extractor)
    db.write(outdir.joinpath('db.txt'))
    extractor.write_examples(outdir.joinpath('examples.txt'))


def main():
    add_args = [
        (("command",), dict(help="stats|process")),
        (("dict",), dict(help="dictionary ID")),
    ]

    args = parsed_args(*add_args)
    if args.command == 'stats':
        submission = Submission(args.dict)
        submission.dict.stats()

        if 0:  # args.dict == 'yakkha':
            same, d1, d2 = 0, 0, 0
            for e in submission.dict:
                for w in e.get_words():
                    ne = len(w.meanings)
                    nn = len(FIELD_SPLITTER_PATTERN.split(w.data.get('gn', [''])[0]))
                    if ne < nn:
                        d1 += 1
                    elif nn < ne:
                        d2 += 1
                    else:
                        same += 1
            print(same, d1, d2)

        if args.dict == 'palula':
            for e in submission.dict:
                if len(e.getall('ps')) > len(e.getall('se')) + len(e.getall('lx')):
                    print(e.get('lx'))
    elif args.command == 'process':
        submission = Submission(args.dict)
        outdir = submission.dir.joinpath('processed')
        outdir.mkdir(parents=True, exist_ok=True)
        if args.dict == 'teop':
            rearrange(submission, outdir)
        extract_examples(submission, outdir)
