# coding: utf8
from __future__ import unicode_literals

from clld.scripts.util import parsed_args

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
