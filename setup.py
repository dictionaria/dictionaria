from setuptools import setup, find_packages


setup(
    name='dictionaria',
    version='0.0',
    description='dictionaria',
    long_description='',
    classifiers=[
        "Programming Language :: Python",
        "Framework :: Pyramid",
        "Topic :: Internet :: WWW/HTTP",
        "Topic :: Internet :: WWW/HTTP :: WSGI :: Application",
    ],
    author='Robert Forkel',
    author_email='robert_forkel@eva.mpg.de',
    url='http://clld.org',
    keywords='web pyramid pylons',
    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,
    install_requires=[
        'clldmpg~=3.1',
        'clld-glottologfamily-plugin>=2.0.0',
        'transliterate',
        'pyconcepticon>=1.1.0',
        'beautifulsoup4==4.6.0',
        'html5lib',
    ],
    extras_require={
        'dev': ['flake8', 'waitress'],
        'test': [
            'psycopg2',
            'tox',
            'mock',
            'pytest>=3.1',
            'pytest-clld',
            'pytest-mock',
            'pytest-cov',
            'coverage>=4.2',
            'selenium',
            'zope.component>=3.11.0',
        ],
    },
    test_suite="dictionaria",
    entry_points="""\
        [paste.app_factory]
        main = dictionaria:main
""")
