# coding: utf8
from __future__ import unicode_literals, print_function
from io import open
from collections import OrderedDict

from clld.scripts.util import parsed_args

from dictionaria.lib.sfm import FIELD_SPLITTER_PATTERN, marker_split, read
from dictionaria.lib.dictionaria_sfm import Example
from dictionaria.scripts.util import Submission


def yield_examples(submission):
    example = None
    lx = None
    marker_map = submission.md.get('marker_map', {})
    example_props = 'xv xvm xeg xe'.split()

    for marker, content in marker_split(
            read(submission.db, submission.md.get('encoding', 'utf8'))):
        mmarker = marker_map.get(marker, marker)

        if marker == 'lx' or mmarker == 'lx':
            lx = content

        if (marker in example_props or mmarker in example_props):
            if not content:
                continue

            marker = mmarker

            if marker == 'xv':
                if example:
                    print('incomplete example in lx: %s' % lx)
                example = Example(content)
            elif marker in ['xvm', 'xeg']:
                assert example
                setattr(example, marker, content)
            else:  # elif marker == 'xe':
                if example:
                    example.xe = content
                    yield example
                    example = None
                else:
                    print('incomplete example in lx: %s' % lx)
        else:
            yield marker, content


def extract_examples(submission):
    outdir = submission.dir.joinpath('processed')
    outdir.mkdir_p()
    normalized = outdir.joinpath('db.txt')
    examples = OrderedDict()
    with open(normalized, 'w', encoding='utf8') as n:
        for res in yield_examples(submission):
            if isinstance(res, Example):
                if res.id in examples:
                    examples[res.id].merge(res)
                    #assert examples[res.id] == res
                    if not res == examples[res.id]:
                        print(res.xvm)
                        print(examples[res.id].xvm)
                        print(res.xeg)
                        print(examples[res.id].xeg)
                        print()
                examples[res.id] = res
                res = ('xref', res.id)
            n.write('\\{0} {1}\n'.format(*res))

    ex = outdir.joinpath('examples.txt')
    with open(ex, 'w', encoding='utf8') as x:
        for example in examples.values():
            x.write(example.text)

    print(normalized)
    print(ex)


def main():
    add_args = [
        (("command",), dict(help="stats")),
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
    elif args.command == 'normalize':
        extract_examples(Submission(args.dict))
