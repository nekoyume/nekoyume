from setuptools import setup, find_packages
from codecs import open
from os import path


here = path.abspath(path.dirname(__file__))

with open(path.join(here, 'README.rst'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='nekoyume',
    version='0.0.1',
    description='Decentralized MMORPG based on Dungeon World',
    long_description=long_description,
    url='https://github.com/nekoyume/nekoyume',
    license='LICENSE.txt',
    author='JC Kim',
    author_email='jc@nekoyu.me',
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Other Audience',
        'Topic :: Database :: Database Engines/Servers',
        'Topic :: Games/Entertainment :: Role-Playing',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3.6',
    ],
    keywords='blockchain mmorpg game',
    packages=find_packages(exclude=['contrib', 'docs', 'tests']),
    install_requires=[
        'bencode.py >= 2.0.0, < 2.1.0',
        'celery >= 4.1.0, < 4.2.0',
        'click >= 6.7, < 7.0',
        'Flask >= 0.12.2, < 0.13.0',
        'Flask-Babel >= 0.11.2, < 0.12.0',
        'Flask-Cache >= 0.13.1, < 0.14.0',
        'Flask-SQLAlchemy >= 2.3.2, < 2.4.0',
        'gevent == 1.3.1',
        'gunicorn >= 19.7.1, < 19.8.0',
        'ptpython == 0.41',
        'pycrypto == 2.6',
        'python_bitcoinlib == 0.9.0',
        'pytz >= 2018.3',
        'redis >= 2.10.6, < 2.11.0',
        'requests >= 2.18.4, < 2.19.0',
        'seccure >= 0.3.2, < 0.4.0',
        'SQLAlchemy >= 1.2.2, < 1.3.0',
        'tablib >= 0.12.1, < 0.13.0',
    ],
    extras_require={
        'dev': [
            'flake8 >= 3.5.0, < 3.6.0',
            'recommonmark==0.4.0',
            'Sphinx >= 1.7.1, < 1.8.0',
            'sphinx-rtd-theme==0.2.4',
        ],
        'test': [
            'pytest >= 3.4.2, < 3.5.0',
            'pytest-localserver >= 0.4.1, < 0.5',
            'codecov >= 2.0.15, < 2.1.0',
        ],
    },
    package_data={
        'nekoyume': ['data/*', 'templates/*.html'],
    },
    entry_points={
        'console_scripts': [
            'nekoyume = nekoyume.cli:cli',
        ],
    },
    project_urls={
        'Bug Reports': 'https://github.com/nekoyume/nekoyume/issues',
        'Funding': 'https://nekoyu.me/',
        'Source': 'https://github.com/nekoyume/nekoyume/',
    },
)
