from __future__ import unicode_literals


def test_Example():
    from dictionaria.lib.ingest import Example

    e = Example([('tx', 'a'), ('ft', 'b')])
    id_ = e.id
    e.set('ref', 'x')
    assert id_ != e.id
