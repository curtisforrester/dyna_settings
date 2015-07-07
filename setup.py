#!/usr/bin/env python
# -*- coding: utf-8 -*-


try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup


with open('README.rst') as readme_file:
    readme = readme_file.read()

with open('HISTORY.rst') as history_file:
    history = history_file.read().replace('.. :changelog:', '')

requirements = [

]

test_requirements = [

]

setup(
    name='dyna_settings',
    version='0.1.1',
    description="Dynamic project settings to automatically switch settings by environment detection.",
    long_description=readme + '\n\n' + history,
    author="Curtis Forrester",
    author_email='curtis@bredbeddle.net',
    url='https://github.com/curtisforrester/dyna_settings',
    packages=[
        'dyna_settings',
    ],
    package_dir={'dyna_settings':
                 'dyna_settings'},
    include_package_data=True,
    install_requires=requirements,
    license="BSD",
    zip_safe=False,
    keywords='dyna_settings',
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Natural Language :: English',
        "Programming Language :: Python :: 2",
        'Programming Language :: Python :: 2.7',
    ],
    test_suite='tests',
    tests_require=test_requirements
)
