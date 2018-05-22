import pytest


@pytest.mark.parametrize(
    "method,path",
    [
        ('get_html', '/'),
        ('get_dt', '/sentences'),
        ('get_dt', '/contributors'),
        ('get_dt', '/contributions'),
        ('get_dt', '/units'),
        ('get_html', '/contributions/daakaka'),
    ])
def test_pages(app, method, path):
    getattr(app, method)(path)
