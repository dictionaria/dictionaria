from __future__ import unicode_literals
import re
from datetime import date

import transaction
from path import path
from nameparser import HumanName
from sqlalchemy.orm import joinedload_all, joinedload
from clld.util import slug, LGR_ABBRS, jsonload
from clld.scripts.util import Data, initializedb
from clld.db.meta import DBSession
from clld.db.models import common
from clldclient.concepticon import Concepticon
from clld_glottologfamily_plugin.util import load_families

import dictionaria
from dictionaria.models import ComparisonMeaning, Dictionary, Word, Variety
from dictionaria.scripts.util import load_sfm


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

    ed = data.add(
        common.Contributor, 'hartmanniren', id='hartmanniren', name='Iren Hartmann')
    common.Editor(dataset=dataset, contributor=ed)
    DBSession.add(dataset)

    for id_, name in LGR_ABBRS.items():
        DBSession.add(common.GlossAbbreviation(id=id_, name=name))

    comparison_meanings = {}
    comparison_meanings_alt_labels = {}

    concepticon = Concepticon()
    for i, concept_set in enumerate(concepticon.resources('parameter').members):
        concept_set = concepticon.resource(concept_set)
        cm = ComparisonMeaning(
            id=concept_set.id,
            name=concept_set.name.lower(),
            description=concept_set.description,
            concepticon_url='%s' % concept_set.uriref)
        DBSession.add(cm)
        comparison_meanings[cm.name] = cm
        for label in concept_set.alt_labels:
            comparison_meanings_alt_labels.setdefault(label.lower(), cm)

    DBSession.flush()
    comparison_meanings = {k: v.pk for k, v in comparison_meanings.items()}
    comparison_meanings_alt_labels = {
        k: v.pk for k, v in comparison_meanings_alt_labels.items()}

    submissions = []

    for submission in datadir.dirs():
        sfm = submission.files('*.txt')
        md = submission.files('*.json')
        if sfm and md:
            assert len(sfm) == 1 and len(md) == 1
            id_ = submission.namebase
            md = jsonload(md[0])
            lmd = md['language']

            language = data['Variety'].get(lmd['glottocode'])
            if not language:
                language = data.add(
                    Variety, lmd['glottocode'], id=lmd['glottocode'], name=lmd['name'])

            dictionary = data.add(
                Dictionary,
                id_,
                id=id_,
                name=lmd['name'] + ' Dictionary',
                language=language,
                published=date(*map(int, md['published'].split('-'))))

            for i, cname in enumerate(md['authors']):
                name = HumanName(cname)
                cid = slug('%s%s' % (name.last, name.first))
                contrib = data['Contributor'].get(cid)
                if not contrib:
                    contrib = data.add(common.Contributor, cid, id=cid, name=cname)
                DBSession.add(common.ContributionContributor(
                    ord=i + 1,
                    primary=True,
                    contributor=contrib,
                    contribution=dictionary))

            submissions.append((id_, dictionary.id, language.id, sfm[0], md))
    transaction.commit()

    for id_, did, lid, sfm, md in submissions:
        try:
            mod = __import__('dictionaria.loader.' + id_, fromlist=['MARKER_MAP'])
            marker_map = mod.MARKER_MAP
        except ImportError:
            marker_map = {}

        transaction.begin()
        print('loading %s ...' % id_)
        load_sfm(
            id_,
            did,
            lid,
            sfm,
            comparison_meanings,
            comparison_meanings_alt_labels,
            marker_map,
            **md)
        transaction.commit()
        print('... done')

        #('hoocak', 'Hooca\u0328k', 43.5, -88.5, [('hartmanniren', 'Iren Hartmann')]),
        #('yakkha', 'Yakkha', 27.37, 87.93, [('schackowdiana', 'Diana Schackow')]),
        #('palula', 'Palula', 35.51, 71.84, [('liljegrenhenrik', 'Henrik Liljegren')], {}),
        #('daakaka', 'Daakaka', -16.27, 168.01, [('vonprincekilu', 'Kilu von Prince')],
        # {'published': date(2015, 9, 30), 'iso': 'bpa', 'glottocode': 'daka1243'}),
        #('teop', 'Teop', -5.67, 154.97, [('moselulrike', 'Ulrike Mosel')],
        # {'published': date(2015, 9, 30), 'iso': 'tio', 'glottocode': 'teop1238', 'encoding': 'latin1'}),

    transaction.begin()
    load_families(Data(), DBSession.query(Variety))


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

    for d in DBSession.query(Dictionary).options(joinedload(Dictionary.words)):
        d.count_words = len(d.words)


if __name__ == '__main__':
    initializedb(create=main, prime_cache=prime_cache)
