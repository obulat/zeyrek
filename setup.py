#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""The setup script."""

from setuptools import setup

with open('README.rst', encoding='utf-8') as readme_file:
    readme = readme_file.read()

with open('HISTORY.rst') as history_file:
    history = history_file.read()

requirements = ['nltk>=3']

setup_requirements = ['pytest-runner']

test_requirements = ['pytest', ]

setup(
    author="Olga Bulat",
    author_email='obulat@gmail.com',
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Natural Language :: English',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
    ],
    description="Python morphological analyzer and lemmatizer for Turkish",
    install_requires=requirements,
    license="MIT license",
    long_description=readme,
    long_description_content_type='text/x-rst',
    include_package_data=True,
    keywords='zeyrek',
    name='zeyrek',
    packages=['zeyrek'],
    setup_requires=setup_requirements,
    test_suite='tests',
    tests_require=test_requirements,
    url='https://github.com/obulat/trLemmer',
    version='0.1.1-alpha',
    zip_safe=False,
)
