#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""The setup script."""

from setuptools import setup, find_packages

with open('README.rst') as readme_file:
    readme = readme_file.read()

with open('HISTORY.rst') as history_file:
    history = history_file.read()

requirements = [
    'Click>=6.0',
    'numpy',
    'bson',
    'biopython>=1.70'
    # TODO: put package requirements here
]

setup_requirements = [
    'pytest-runner',
    'pip',
    'bumpversion',
    'wheel',
    'watchdog',
    'flake8',
    'tox',
    'coverage',
    'Sphinx',
    'pytest',
    'pytest-runner',
    # TODO(chrisbarnettster): put setup requirements (distutils extensions, etc.) here
]

test_requirements = [
    'pytest',
    # TODO: put package test requirements here
]

setup(
    name='tessellate',
    version='0.3.5',
    description="A package for quantifying cyclic molecule conformations.",
    long_description=readme + '\n\n' + history,
    author="Christopher Bevan Barnett",
    author_email='chrisbarnettster@gmail.com',
    url='https://github.com/chrisbarnettster/tessellate',
    # packages=find_packages(include=['tessellate']),
    packages=find_packages(),
    entry_points={
        'console_scripts': [
            'tessellate=tessellate.cli:main'
        ]
    },
    include_package_data=True,
    install_requires=requirements,
    license="Apache Software License 2.0",
    zip_safe=False,
    keywords='tessellate',
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: Apache Software License',
        'Natural Language :: English',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
    ],
    test_suite='tests',
    tests_require=test_requirements,
    setup_requires=setup_requirements,
    python_requires='>=3',
)
