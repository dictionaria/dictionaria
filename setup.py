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
    author_email='forkel@shh.mpg.de',
    url='http://clld.org',
    keywords='web pyramid pylons',
    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,
    install_requires=[
        'clld>=7.4.2',
        'clldmpg>=3.3.1',
        'clld-glottologfamily-plugin>=4.0',
        'gitpython',
        'transliterate',
        'pyconcepticon>=1.1.0',
        'beautifulsoup4==4.6.0',
        'html5lib',
        'sqlalchemy',
        'waitress',
    ],
    extras_require={
        'dev': [
            'flake8',
            'tox'
        ],
        'test': [
            'psycopg2',
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
