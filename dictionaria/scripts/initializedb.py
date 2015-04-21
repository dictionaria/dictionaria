from __future__ import unicode_literals
import os
import re
from datetime import date

from sqlalchemy import create_engine
from sqlalchemy.orm import joinedload_all
from path import path
from clld.util import slug, LGR_ABBRS
from clld.scripts.util import Data, initializedb
from clld.db.meta import DBSession
from clld.db.models import common

import dictionaria
from dictionaria.models import Meaning, Word, SemanticDomain, Dictionary


DB = 'postgresql://robert@/wold'
LOADER_PATTERN = re.compile('(?P<id>[a-z]+)\.py$')


def main(args):
    data = Data()

    dataset = common.Dataset(
        id=dictionaria.__name__,
        name="Dictionaria",
        description="The Dictionary Journal",
        #published=date(2009, 8, 15),
        license='http://creativecommons.org/licenses/by-nc-nd/2.0/de/deed.en',
        contact='dictionaria@eva.mpg.de',
        jsondata={
            'license_icon': 'http://i.creativecommons.org/l/by-nc-nd/2.0/de/88x31.png',
            'license_name':
                'Creative Commons Attribution-NonCommercial-NoDerivs 2.0 Germany License',
        },
        domain='dictionaria.clld.org')

    ed = data.add(common.Contributor, 'hartmanniren', id='hartmanniren', name='Iren Hartmann')
    common.Editor(dataset=dataset, contributor=ed)
    DBSession.add(dataset)

    for id_, name in LGR_ABBRS.items():
        DBSession.add(common.GlossAbbreviation(id=id_, name=name))

    ps = data.add(common.UnitParameter, 'pos', id='pos', name='part of speech')
    DBSession.flush()

    for name in [
        'noun',
        'affix',
        'verb',
        'transitive verb',
        'active verb',
        'inactive verb',
        'auxiliary verb',
        'adjective',
        'adverb',
        'function word',
        'pronoun',
        'numeral',
        'determiner',
        'conjunction',
        'intransitive verb',
        'particle',
        'adposition',
        'quantifier',
        'other',
    ]:
        p = data.add(common.UnitDomainElement, name, id='pos-%s' % slug(name), name=name)
        p.unitparameter_pk = ps.pk

    wold_db = create_engine(DB)
    for row in wold_db.execute("select * from semantic_field"):
        if row['id'] not in data['SemanticDomain']:
            kw = dict((key, row[key]) for key in ['name', 'description'])
            data.add(SemanticDomain, row['id'], id=str(row['id']), **kw)

    for row in wold_db.execute("select * from meaning"):
        if row['id'] not in data['Meaning']:
            kw = dict((key, row[key] or None) for key in [
                'ids_code', 'semantic_category'])
            data.add(
                Meaning, row['label'].lower(),
                id=row['id'].replace('.', '-'),
                name=row['label'],
                description=re.sub('^t(o|he)\s+', '', row['label']),
                semantic_domain=data['SemanticDomain'][row['semantic_field_id']],
                **kw)
            DBSession.flush()

    for id_, name, lat, lon, contribs in [
        ('hoocak', 'Hooca\u0328k', 43.5, -88.5, [('hartmanniren', 'Iren Hartmann')]),
        ('yakkha', 'Yakkha', 27.37, 87.93, [('schackowdiana', 'Diana Schackow')]),
        ('palula', 'Palula', 35.51, 71.84, [('liljegrenhenrik', 'Henrik Liljegren')]),
    ]:
        language = data.add(
            common.Language, id_, id=id_, name=name, latitude=lat, longitude=lon)
        dictionary = data.add(
            Dictionary, id_,
            id=id_,
            name=name + ' Dictionary',
            language=language,
            published=date(2014, 2, 12))
        for i, _data in enumerate(contribs):
            cid, cname = _data
            contrib = data['Contributor'].get(cid)
            if not contrib:
                contrib = data.add(common.Contributor, cid, id=cid, name=cname)
            DBSession.add(common.ContributionContributor(
                ord=1,
                primary=True,
                contributor=contrib,
                contribution=dictionary))

            mod = __import__('dictionaria.loader.' + id_, fromlist=['load'])
            mod.load(id_, data, args.data_file('files'))


def prime_cache(cfg):
    """If data needs to be denormalized for lookup, do that here.
    This procedure should be separate from the db initialization, because
    it will have to be run periodiucally whenever data has been updated.
    """
    for meaning in DBSession.query(Meaning).options(
        joinedload_all(common.Parameter.valuesets, common.ValueSet.values)
    ):
        meaning.representation = sum([len(vs.values) for vs in meaning.valuesets])

    for word in DBSession.query(Word).options(
        joinedload_all(common.Unit.unitvalues, common.UnitValue.unitparameter)
    ):
        word.pos = ', '.join([val.unitdomainelement.name for val in word.unitvalues if val.unitparameter.id == 'pos'])


if __name__ == '__main__':
    initializedb(create=main, prime_cache=prime_cache)
