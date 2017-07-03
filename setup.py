#!/usr/bin/env python3

from distutils.core import setup

setup(
    name='faice',
    version='0.1',
    summary="""FAICE (Fair Collaboration and Experiments) is a tool suite,
    helping researchers to work with experiments published in the FAICE description format.""",
    description="""FAICE (Fair Collaboration and Experiments) is a tool suite,
    helping researchers to work with experiments published in the FAICE description format.""",
    author='Christoph Jansen',
    author_email='Christoph.Jansen@htw-berlin.de',
    url='https://github.com/curiouscontainers/faice',
    scripts=['bin/faice'],
    packages=['faice_tools'],
    license='GPL-3.0',
    platforms=['any'],
    install_requires=['jinja2', 'requests', 'jsonschema']
)
