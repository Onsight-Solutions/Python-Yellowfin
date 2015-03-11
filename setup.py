from setuptools import setup, find_packages
from codecs import open
from os import path

here = path.abspath(path.dirname(__file__))

with open(path.join(here, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='Yellowfin',
    version='1.0.2',

    description='A Python module to handle Yellowfin BI Tool',
    long_description=long_description,

    url='https://github.com/Onsight-Solutions/Python-Yellowfin',

    author='Onsight Solutions',
    author_email='mss@onsight.nl',
    license='GPLv2',

    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU General Public License v2 (GPLv2)',
        'Natural Language :: English',
        'Programming Language :: Python :: 2.7',
    ],

    keywords='yellowfin BI API',
    packages=find_packages(),
    install_requires=[
        "dicttoxml",
        "suds",
    ]
)
