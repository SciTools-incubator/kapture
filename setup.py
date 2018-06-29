#!/usr/bin/env python

from __future__ import print_function

import os
from setuptools import setup, find_packages
import setuptools
from distutils.version import LooseVersion


if LooseVersion(setuptools.__version__) < LooseVersion('38.6.0'):
    raise RuntimeError('Installation requires setuptools >= 38.6.0')

NAME = 'kapture'
DIR = os.path.abspath(os.path.dirname(__file__))


def extract_packages():
    packages = []
    root = os.path.join(DIR, NAME)
    offset = len(os.path.dirname(root)) + 1
    for dpath, dnames, fnames in os.walk(root):
        if os.path.exists(os.path.join(dpath, '__init__.py')):
            package = dpath[offset:].replace(os.path.sep, '.')
            packages.append(package)
    return packages


def extract_version():
    version = None
    fname = os.path.join(DIR, NAME, '__init__.py')
    with open(fname) as fin:
        for line in fin:
            if (line.startswith('__version__')):
                _, version = line.split('=')
                version = version.strip()[1:-1]  # Remove quotation.
                break
    return version


def read(*parts):
    result = None
    fname = os.path.join(DIR, *parts)
    if os.path.isfile(fname):
        with open(fname, 'rb') as fh:
            result = fh.read().decode('utf-8')
    return result


setup_args = dict(
    name = NAME,
    version = extract_version(),
    author = 'SciTools',
    author_email = 'scitools-iris@googlegroups.com',
    url = 'https://github.com/scitools-incubator/kapture',
    description = 'Kapture: a simple sampling profiler for Python',
    long_description ='{}'.format(read('README.md')),
    long_description_content_type='text/markdown',
    platforms = ['Linux', 'Mac OS X', 'Windows'],
    license = 'BSD 3-clause',
    packages = find_packages(),
    classifiers      = [
        'License :: OSI Approved :: BSD License',
        'Development Status :: 1 - Planning Development Status',
        'Programming Language :: Python :: 2.7',
        'Operating System :: OS Independent',
        'Intended Audience :: Science/Research',
        'Intended Audience :: Developers',
        'Natural Language :: English',
        'Topic :: Scientific/Engineering',
        'Topic :: Software Development :: Libraries'],
)


if __name__ == "__main__":
    setup(**setup_args)
