# coding: utf8
from __future__ import unicode_literals

from clld.scripts.util import parsed_args

from dictionaria.lib.sfm import FIELD_SPLITTER_PATTERN
from dictionaria.scripts.util import Submission


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

        #if args.dict == 'teop':
        #    for e in submission.dict:
        #        if len(e.getall('de')) > 40:
        #            print(e.get('lx'))
