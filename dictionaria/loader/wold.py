from __future__ import unicode_literals
from datetime import date

from sqlalchemy import create_engine
from clld.db.meta import DBSession
from clld.db.models import common

from dictionaria import models


DB = 'postgresql://robert@/wold'
APICS = 'postgresql://robert@/apics'


def load(id_, data):
    old_db = create_engine(DB)
    apics_db = create_engine(APICS)

    #
    # migrate semantic_field table: complete
    #
    for row in old_db.execute("select * from semantic_field"):
        if row['id'] not in data['SemanticField']:
            kw = dict((key, row[key]) for key in ['id', 'name', 'description'])
            data.add(models.SemanticField, row['id'], **kw)

    #
    # migrate language table: complete
    # recipient flag is replaced by vocabulary_pk!
    #
    for row in old_db.execute("select * from language order by id"):
        if row['recipient']:
            kw = dict((key, row[key]) for key in ['name', 'latitude', 'longitude'])
            data.add(common.Language, row['id'], id=str(row['id']), **kw)
    DBSession.flush()

    example_map = {}
    for row in apics_db.execute("select * from sentence where language_pk = 56"):
        kw = {}
        kw.update(row)
        kw['language_pk'] = data['Language'][7].pk
        data.add(common.Sentence, row['id'], **kw)
        if row['analyzed']:
            for part in row['analyzed'].split('\t'):
                if part.endswith('.'):
                    part = part[:-1]
                if part in example_map:
                    example_map[part].append(row['id'])
                else:
                    example_map[part] = [row['id']]

    #
    # migrate language_code table: complete
    #
    for row in old_db.execute("select * from language_code"):
        _id = '%(type)s-%(code)s' % row
        data.add(common.Identifier, _id, id=_id, type=row['type'], name=row['code'])
    DBSession.flush()

    #
    # migrate language_code_language table: complete
    #
    for row in old_db.execute("select * from language_code_language"):
        if row['language_id'] not in data['Language']:
            continue
        _id = '%(type)s-%(code)s' % row
        data.add(
            common.LanguageIdentifier, '%s-%s' % (_id, row['language_id']),
            identifier_pk=data['Identifier'][_id].pk,
            language_pk=data['Language'][row['language_id']].pk)
    DBSession.flush()

    #
    # migrate contributor table: complete
    #
    for row in old_db.execute("select * from contributor"):
        data.add(
            common.Contributor, row['id'], id=row['id'],
            name='%(firstname)s %(lastname)s' % row,
            url=row['homepage'],
            description=row['note'],
            email=row['email'],
            address=row['address'])
    DBSession.flush()

    #
    # migrate vocabulary table: complete
    #
    number = max([int(d.id) for d in data['Dictionary'].values()] + [0])
    for i, row in enumerate(old_db.execute("select * from vocabulary order by id")):
        if row['language_id'] not in data['Language']:
            continue
        vocab = data.add(
            models.Dictionary, row['id'], id=str(number + i + 1),
            name=row['name'],
            language=data['Language'][row['language_id']],
            published=date(2009, 5, 5))
        DBSession.flush()

        for key in row.keys():
            if key.startswith('fd_') or key in ['other_information', 'color', 'abbreviations']:
                DBSession.add(common.Contribution_data(object_pk=vocab.pk, key=key, value=row[key]))
    DBSession.flush()

    #
    # migrate contact_situation and age tables: complete
    # contact situations and ages are unitdomainelements!
    #
    contact_situation = common.UnitParameter(id='cs', name='Contact Situation')
    age = common.UnitParameter(id='a', name='Age')

    DBSession.add(contact_situation)
    DBSession.add(age)
    DBSession.flush()

    for row in old_db.execute("select * from contact_situation"):
        if row['vocabulary_id'] not in data['Language']:
            continue
        kw = dict((key, row[key]) for key in ['description', 'id', 'name'])
        kw['id'] = 'cs-%s' % kw['id']
        p = data.add(common.UnitDomainElement, row['id'], **kw)
        p.unitparameter_pk = contact_situation.pk

    for row in old_db.execute("select * from age"):
        if row['vocabulary_id'] not in data['Language']:
            continue
        id_ = '%(vocabulary_id)s-%(label)s' % row
        kw = dict((key, row[key]) for key in ['start_year', 'end_year'])
        p = data.add(common.UnitDomainElement, id_, id='a-%s' % id_, name=row['label'],
                description=row['description'], jsondata=kw)
        p.unitparameter_pk = age.pk

    #
    # migrate meaning table: complete
    #
    meaning_map = {}
    for row in old_db.execute("select * from meaning"):
        if row['id'] not in data['Meaning']:
            kw = dict((key, row[key] or None) for key in [
                'description', 'ids_code', 'semantic_category'])
            p = data.add(models.Meaning, row['id'], id=row['id'].replace('.', '-'), name=row['label'], **kw)
            p.semantic_field = data['SemanticField'][row['semantic_field_id']]
            DBSession.flush()
        else:
            p = data['Meaning'][row['id']]

        for contrib_id, contrib in data['Dictionary'].items():
            data.add(
                common.ValueSet, '%s-%s' % (contrib_id, row['id']),
                id='%s-%s' % (contrib_id, row['id'].replace('.', '-')),
                language=contrib.language,
                contribution=contrib,
                parameter=p)

    DBSession.flush()

    #
    # migrate word table:
    #
    word_to_vocab = {}
    words = list(old_db.execute("select * from word"))
    for row in words:
        if row['vocabulary_id'] not in data['Language']:
            continue

        word_to_vocab[row['id']] = row['vocabulary_id']
        kw = dict((key, row[key]) for key in ['id'])
        w = data.add(models.Word, row['id'], name=row['form'], description=row['free_meaning'], **kw)
        w.language = data['Dictionary'][row['vocabulary_id']].language
        w.dictionary = data['Dictionary'][row['vocabulary_id']]

        for j, pos in enumerate(set(filter(None, [r[0] for r in old_db.execute("""\
select semantic_category from word_meaning, meaning
where meaning_id = id and  word_id = '%s'""" % row['id'])]))):
            if j > 0:
                # we only allow one part-of-speech value per dictionary entry!
                continue
            DBSession.add(common.UnitValue(
                id='pos-%s' % row['id'],
                unit=w,
                unitparameter=data['UnitParameter']['pos'],
                unitdomainelement=data['UnitDomainElement'][pos.lower()],
                contribution=data['Dictionary'][row['vocabulary_id']],
            ))

        if row['age_label']:
            DBSession.add(common.UnitValue(
                id='%(id)s-a' % row,
                unit=w,
                unitparameter=age,
                unitdomainelement=data['UnitDomainElement']['%(vocabulary_id)s-%(age_label)s' % row],
                contribution=data['Dictionary'][row['vocabulary_id']],
            ))

        if row['contact_situation_id'] and row['contact_situation_id'] != '9129144185487768':
            DBSession.add(common.UnitValue(
                id='%(id)s-cs' % row,
                unit=w,
                unitparameter=contact_situation,
                unitdomainelement=data['UnitDomainElement'][row['contact_situation_id']],
                contribution=data['Dictionary'][row['vocabulary_id']],
            ))

        if row['vocabulary_id'] == 7:
            for example_id in example_map.get(row['form'], []):
                DBSession.add(models.WordSentence(word=w, sentence=data['Sentence'][example_id]))

    DBSession.flush()

    #
    # migrate word_meaning table: complete
    #
    for i, row in enumerate(old_db.execute("select * from word_meaning")):
        if row['word_id'] not in data['Word']:
            continue
        value = data.add(
            models.Counterpart, i,
            id=i,
            description='%(relationship)s (%(comment_on_relationship)s)' % row,
            name=data['Word'][row['word_id']].name,
            valueset=data['ValueSet']['%s-%s' % (word_to_vocab[row['word_id']], row['meaning_id'])],
            word=data['Word'][row['word_id']])
    DBSession.flush()

    #
    # migrate vocabulary_contributor table: complete
    #
    for row in old_db.execute("select * from vocabulary_contributor"):
        if row['vocabulary_id'] not in data['Language']:
            continue
        DBSession.add(common.ContributionContributor(
            ord=row['ordinal'],
            primary=row['primary'],
            contributor_pk=data['Contributor'][row['contributor_id']].pk,
            contribution_pk=data['Dictionary'][row['vocabulary_id']].pk))

    DBSession.flush()
