"""Custom views for dictionaria."""

from clld.db.models.common import Language, Unit

from dictionaria.models import Dictionary


def download(request):
    """Return view data for the download page."""
    return {'dictionaries': request.db.query(Dictionary).order_by(Dictionary.number)}


def home(request):
    """Return view data for the home page."""
    word1 = (
        request.db.query(Unit)
        .join(Language)
        .filter(Unit.name == 'caa')
        .filter(Language.name == 'Hooca\u0328k')
        .first())
    return {'example1': word1, 'example2': Unit.get('72141525536263472')}
