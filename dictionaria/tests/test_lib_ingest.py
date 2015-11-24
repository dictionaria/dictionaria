# coding: utf8
from __future__ import unicode_literals
from unittest import TestCase


class Tests(TestCase):
    def test_Example(self):
        from dictionaria.lib.ingest import Example

        e = Example([('tx', 'a'), ('ft', 'b')])
        id_ = e.id
        e.set('ref', 'x')
        self.assertNotEquals(id_, e.id)
