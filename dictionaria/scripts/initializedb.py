from __future__ import unicode_literals
import re
from datetime import date

from path import path
from sqlalchemy.orm import joinedload_all, joinedload
from clld.util import slug, LGR_ABBRS
from clld.scripts.util import Data, initializedb, add_language_codes
from clld.db.meta import DBSession
from clld.db.models import common
from clldclient.concepticon import Concepticon

import dictionaria
from dictionaria.models import ComparisonMeaning, Dictionary, Word


DB = 'postgresql://robert@/wold'
LOADER_PATTERN = re.compile('(?P<id>[a-z]+)\.py$')


def main(args):
    datadir = path('/home/robert/venvs/dictionaria/dictionaria-intern/submissions')
    data = Data()

    dataset = common.Dataset(
        id=dictionaria.__name__,
        name="Dictionaria",
        description="The Dictionary Journal",
        published=date(2015, 10, 1),
        contact='dictionaria@eva.mpg.de',
        domain='dictionaria.clld.org',
        license="http://creativecommons.org/licenses/by/4.0/",
        jsondata={
            'license_icon': 'cc-by.png',
            'license_name': 'Creative Commons Attribution 4.0 International License'})

    ed = data.add(common.Contributor, 'hartmanniren', id='hartmanniren', name='Iren Hartmann')
    common.Editor(dataset=dataset, contributor=ed)
    DBSession.add(dataset)

    for id_, name in LGR_ABBRS.items():
        DBSession.add(common.GlossAbbreviation(id=id_, name=name))

    comparison_meanings = {}
    concepticon = Concepticon()
    for concept_set in concepticon.resources('parameter').members:
        concept_set = concepticon.resource(concept_set)
        cm = ComparisonMeaning(
            id=concept_set.id,
            name=concept_set.name.lower(),
            description=concept_set.description,
            concepticon_url='%s' % concept_set.uriref)
        DBSession.add(cm)
        comparison_meanings[cm.name] = cm
        for label in concept_set.alt_labels:
            comparison_meanings.setdefault(label.lower(), cm)

    for id_, name, lat, lon, contribs, props in [
        #('hoocak', 'Hooca\u0328k', 43.5, -88.5, [('hartmanniren', 'Iren Hartmann')]),
        #('yakkha', 'Yakkha', 27.37, 87.93, [('schackowdiana', 'Diana Schackow')]),
        #('palula', 'Palula', 35.51, 71.84, [('liljegrenhenrik', 'Henrik Liljegren')], {}),
        ('daakaka', 'Daakaka', -16.27, 168.01, [('vonprincekilu', 'Kilu von Prince')],
         {'published': date(2015, 9, 30), 'iso': 'bpa', 'glottocode': 'daka1243'}),
        ('teop', 'Teop', -5.67, 154.97, [('moselulrike', 'Ulrike Mosel')],
         {'published': date(2015, 9, 30), 'iso': 'tio', 'glottocode': 'teop1238', 'encoding': 'latin1'}),
    ]:
        language = data.add(
            common.Language, id_, id=id_, name=name, latitude=lat, longitude=lon)
        if 'iso' in props:
            add_language_codes(
                data, language, props['iso'], glottocode=props.get('glottocode'))
        dictionary = data.add(
            Dictionary, id_,
            id=id_,
            name=name + ' Dictionary',
            language=language,
            published=props.get('published', date(2014, 2, 12)))
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
            mod.load(id_, data, args.data_file('files'), datadir, comparison_meanings, **props)


def prime_cache(cfg):
    """If data needs to be denormalized for lookup, do that here.
    This procedure should be separate from the db initialization, because
    it will have to be run periodiucally whenever data has been updated.
    """
    for meaning in DBSession.query(ComparisonMeaning).options(
        joinedload_all(common.Parameter.valuesets, common.ValueSet.values)
    ):
        meaning.representation = sum([len(vs.values) for vs in meaning.valuesets])
        if meaning.representation == 0:
            meaning.active = False

    for word in DBSession.query(Word).options(joinedload(Word.meanings)):
        word.description = ' / '.join(m.name for m in word.meanings)


if __name__ == '__main__':
    initializedb(create=main, prime_cache=prime_cache)
