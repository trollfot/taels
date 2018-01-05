# -*- coding: utf-8 -*-

from os import path
from setuptools import setup, find_packages


def read(filename):
    with open(path.join(path.dirname(__file__), filename)) as f:
        return f.read()


install_requires = [
    'sanic',
    ]

tests_require = [
    
    ]

setup(name='taels',
      version='0.1.dev0',
      description="Sanic-based web framework",
      long_description="%s\n\n%s" % (
          read('README.txt'), read(path.join('docs', 'HISTORY.txt'))),
      keywords="web publish traverse traversing route routing url",
      author="",
      author_email="",
      license="BSD",
      packages=find_packages('src', exclude=['ez_setup']),
      package_dir={'': 'src'},
      include_package_data=True,
      zip_safe=False,
      install_requires=install_requires,
      extras_require={'test': tests_require},
      entry_points="",
      )
