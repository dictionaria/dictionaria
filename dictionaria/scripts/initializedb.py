from __future__ import unicode_literals
from datetime import date
from itertools import groupby, chain
from collections import OrderedDict
import re

import transaction
from nameparser import HumanName
from sqlalchemy.orm import joinedload_all, joinedload
from clldutils.misc import slug, nfilter
from clld.util import LGR_ABBRS
from clld.scripts.util import Data, initializedb
from clld.db.meta import DBSession
from clld.db.models import common
from clld.db import fts
from clld_glottologfamily_plugin.util import load_families
from pyconcepticon.api import Concepticon

import dictionaria
from dictionaria.models import ComparisonMeaning, Dictionary, Word, Variety
from dictionaria.lib.submission import REPOS, Submission
from dictionaria.util import join


def main(args):
    fts.index('fts_index', Word.fts, DBSession.bind)
    DBSession.execute("CREATE EXTENSION IF NOT EXISTS unaccent WITH SCHEMA public;")

    data = Data()

    dataset = common.Dataset(
        id=dictionaria.__name__,
        name="Dictionaria",
        description="The Dictionary Journal",
        published=date(2017, 3, 30),
        contact='dictionary.journal@uni-leipzig.de',
        domain='dictionaria.clld.org',
        publisher_name="Max Planck Institute for the Science of Human History",
        publisher_place="Jena",
        publisher_url="https://shh.mpg.de",
        license="http://creativecommons.org/licenses/by/4.0/",
        jsondata={
            'license_icon': 'cc-by.png',
            'license_name': 'Creative Commons Attribution 4.0 International License'})

    for i, (id_, name) in enumerate([
        ('haspelmathmartin', 'Martin Haspelmath'),
        ('moselulrike', 'Ulrike Mosel'),
        ('stiebelsbarbara', 'Barbara Stiebels')
    ]):
        ed = data.add(common.Contributor, id_, id=id_, name=name)
        common.Editor(dataset=dataset, contributor=ed, ord=i + 1)
    DBSession.add(dataset)

    for id_, name in LGR_ABBRS.items():
        DBSession.add(common.GlossAbbreviation(id=id_, name=name))

    comparison_meanings = {}

    print('loading concepts ...')

    concepticon = Concepticon(
        REPOS.joinpath('..', '..', 'concepticon', 'concepticon-data'))
    if not args.no_concepts:
        for conceptset in concepticon.conceptsets.values():
            cm = data.add(
                ComparisonMeaning,
                conceptset.id,
                id=conceptset.id,
                name=conceptset.gloss.lower(),
                description=conceptset.definition,
                concepticon_url='http://concepticon.clld.org/parameters/%s' % conceptset.id)
            comparison_meanings[cm.id] = cm

    DBSession.flush()

    print('... done')

    comparison_meanings = {k: v.pk for k, v in comparison_meanings.items()}
    submissions = []

    for submission in REPOS.joinpath(
            'submissions-internal' if args.internal else 'submissions').glob('*'):
        if not submission.is_dir():
            continue

        try:
            submission = Submission(submission)
        except ValueError:
            continue

        md = submission.md
        if md is None:
            continue

        if not args.internal and not md['date_published']:
            continue

        id_ = submission.id
        if args.dict and args.dict != id_ and args.dict != 'all':
            continue
        lmd = md['language']
        props = md.get('properties', {})
        props.setdefault('custom_fields', [])
        props['metalanguage_styles'] = {}
        for v, s in zip(props.get('metalanguages', {}).values(),
                        ['success', 'info', 'warning', 'important']):
            props['metalanguage_styles'][v] = s
        props['custom_fields'] = ['lang-' + f if f in props['metalanguage_styles'] else f
                                  for f in props['custom_fields']]

        language = data['Variety'].get(lmd['glottocode'])
        if not language:
            language = data.add(
                Variety, lmd['glottocode'], id=lmd['glottocode'], name=lmd['name'])

        md['date_published'] = md['date_published'] or date.today().isoformat()
        if '-' not in md['date_published']:
            md['date_published'] = md['date_published'] + '-01-01'
        dictionary = data.add(
            Dictionary,
            id_,
            id=id_,
            number=md.get('number'),
            name=props.get('title', lmd['name'] + ' dictionary'),
            description=submission.description,
            language=language,
            published=date(*map(int, md['date_published'].split('-'))),
            jsondata=props)

        for i, spec in enumerate(md['authors']):
            if not isinstance(spec, dict):
                cname, address = spec, None
                spec = {}
            else:
                cname, address = spec['name'], spec.get('affiliation')
            name = HumanName(cname)
            cid = slug('%s%s' % (name.last, name.first))
            contrib = data['Contributor'].get(cid)
            if not contrib:
                contrib = data.add(
                    common.Contributor,
                    cid,
                    id=cid,
                    name=cname,
                    address=address,
                    url=spec.get('url'),
                    email=spec.get('email'))
            DBSession.add(common.ContributionContributor(
                ord=i + 1,
                primary=True,
                contributor=contrib,
                contribution=dictionary))

        submissions.append((dictionary.id, language.id, submission))
    transaction.commit()

    for did, lid, submission in submissions:
        transaction.begin()
        print('loading %s ...' % submission.id)
        dictdata = Data()
        lang = Variety.get(lid)
        submission.load_examples(Dictionary.get(did), dictdata, lang)
        submission.dictionary.load(
            submission,
            dictdata,
            Dictionary.get(did),
            lang,
            comparison_meanings,
            OrderedDict(submission.md.get('properties', {}).get('labels', [])))
        transaction.commit()
        print('... done')

    transaction.begin()
    load_families(
        Data(),
        [v for v in DBSession.query(Variety) if re.match('[a-z]{4}[0-9]{4}', v.id)],
        glottolog_repos='../../glottolog3/glottolog')


def prime_cache(cfg):
    """If data needs to be denormalized for lookup, do that here.
    This procedure should be separate from the db initialization, because
    it will have to be run periodically whenever data has been updated.
    """
    for meaning in DBSession.query(ComparisonMeaning).options(
        joinedload_all(common.Parameter.valuesets, common.ValueSet.values)
    ):
        meaning.representation = sum([len(vs.values) for vs in meaning.valuesets])
        if meaning.representation == 0:
            meaning.active = False

    q = DBSession.query(Word)\
        .order_by(Word.dictionary_pk, common.Unit.name, common.Unit.pk)\
        .options(joinedload(Word.meanings), joinedload(Word.dictionary))
    for _, words in groupby(q, lambda u: u.name):
        words = list(words)
        for i, word in enumerate(words):
            word.description = ' / '.join(m.name for m in word.meanings)
            word.comparison_meanings = ' / '.join(nfilter(m.reverse for m in word.meanings))
            word.semantic_domain = ' / '.join(nfilter(m.semantic_domain for m in word.meanings))
            word.number = i + 1 if len(words) > 1 else 0

            for suffix in ['1', '2']:
                alt_t, alt_l = [], []
                for m in word.meanings:
                    if getattr(m, 'alt_translation' + suffix):
                        alt_l.append(getattr(m, 'alt_translation_language' + suffix))
                        alt_t.append(getattr(m, 'alt_translation' + suffix))
                if alt_t and len(set(alt_l)) == 1:
                    DBSession.add(common.Unit_data(
                        object_pk=word.pk, key='lang-' + alt_l.pop(), value=join(alt_t)))

    def count_unit_media_files(contrib, mtype):
        return DBSession.query(common.Unit_files)\
            .join(Word, common.Unit_files.object_pk == Word.pk)\
            .filter(Word.dictionary_pk == contrib.pk)\
            .filter(common.Unit_files.mime_type.ilike(mtype + '/%'))\
            .count()

    for d in DBSession.query(Dictionary).options(joinedload(Dictionary.words)):
        d.count_words = len(d.words)
        sds = set(chain(*[w.semantic_domain_list for w in d.words]))
        d.semantic_domains = join(sorted(sds))
        d.count_audio = count_unit_media_files(d, 'audio')
        d.count_image = count_unit_media_files(d, 'image')


if __name__ == '__main__':
    initializedb(
        (("--internal",), dict(action='store_true')),
        (("--no-concepts",), dict(action='store_true')),
        (("--dict",), dict()),
        create=main, prime_cache=prime_cache)
