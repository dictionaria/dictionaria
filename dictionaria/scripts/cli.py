# coding: utf8
from __future__ import unicode_literals, print_function

from clldutils.sfm import FIELD_SPLITTER_PATTERN
from clld.scripts.util import parsed_args

from dictionaria.lib.submission import Submission


def main():
    add_args = [
        (("command",), dict(help="stats|process")),
        (("dict",), dict(help="dictionary ID")),
        (("--internal",), dict(action='store_true', help='run on private repos')),
        (("--raw",), dict(action='store_true')),
    ]

    args = parsed_args(*add_args)
    submission = Submission(args.dict, internal=args.internal)

    if args.command == 'stats':
        submission.stats(processed=not args.raw)

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
        submission.process()
