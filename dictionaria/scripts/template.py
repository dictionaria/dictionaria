# coding: utf8
from __future__ import unicode_literals

from sqlalchemy import Column, Integer, Unicode, ForeignKey, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base, declared_attr
from sqlalchemy.orm import relationship
from sqlalchemy import event


class Base(declarative_base()):
    __abstract__ = True

    @declared_attr
    def __tablename__(cls):
        return cls.__name__.lower()

    id = Column(Integer, primary_key=True)


class Lemma(Base):
    form = Column(Unicode, nullable=False)
    pos = Column(Unicode)


class Sense(Base):
    descriptors = Column(Unicode, nullable=False)
    lemma_id = Column(Integer, ForeignKey('lemma.id'), nullable=False)
    lemma = relationship(Lemma, backref='senses')


class Example(Base):
    text = Column(Unicode, nullable=False)
    gloss = Column(Unicode)
    translation = Column(Unicode)


class Reference(Base):
    author = Column(Unicode)
    year = Column(Unicode)
    title = Column(Unicode)
    glottolog_id = Column(Integer)


class ExampleSense(Base):
    __table_args__ = (UniqueConstraint('sense_id', 'example_id'),)

    example_id = Column(Integer, ForeignKey('example.id'), nullable=False)
    sense_id = Column(Integer, ForeignKey('sense.id'), nullable=False)


def enable_fk(conn, _):
    conn.execute("PRAGMA foreign_keys = ON")


if __name__ == '__main__':
    from sqlalchemy import create_engine

    db = create_engine('sqlite:////home/robert/dictionaria.sqlite')
    event.listen(db, 'connect', enable_fk)

    Base.metadata.create_all(db)
    db.execute("""
    create view dictionary as
    select l.form, l.pos, group_concat(s.descriptors) as senses
    from lemma as l, sense as s
    where l.id = s.lemma_id
    group by l.form, l.pos
    order by l.form
""")
    db.execute("""
    create view examples as
    select l.form as lemma, s.id as sense_id, e.id as example_id, e.text as example
    from example as e, examplesense as es, sense as s, lemma as l
    where e.id = es.example_id and es.sense_id = s.id and s.lemma_id = l.id
    order by l.form
""")

    for statement in [
        "lemma (id, form, pos) values (1, 'b form', 'v')",
        "lemma (id, form, pos) values (2, 'a form', 'n')",
        "sense (id, descriptors, lemma_id) values (1, 'a sense; b sense', 1)",
        "sense (id, descriptors, lemma_id) values (2, 'c sense', 1)",
        "sense (id, descriptors, lemma_id) values (3, 'a sense', 2)",
        "example (id, text) values (1, 'an example for b form and a form')",
        "example (id, text) values (2, 'an example for b form only')",
        "examplesense (id, example_id, sense_id) values (1, 1, 1)",
        "examplesense (id, example_id, sense_id) values (2, 1, 3)",
        "examplesense (id, example_id, sense_id) values (3, 2, 2)",
    ]:
        db.execute("insert into " + statement)
