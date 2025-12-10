
from setuptools import setup, find_packages
from todo.core.version import get_version

VERSION = get_version()

f = open('README.md', 'r')
LONG_DESCRIPTION = f.read()
f.close()

setup(
    name='todo',
    version=VERSION,
    description='A Simple TODO Application',
    long_description=LONG_DESCRIPTION,
    long_description_content_type='text/markdown',
    author='Your Name',
    author_email='you@yourdomain.com',
    url='https://github.com/yourname/todo',
    license='unlicensed',
    packages=find_packages(exclude=['ez_setup', 'tests*']),
    package_data={'todo': ['templates/*']},
    include_package_data=True,
    entry_points="""
        [console_scripts]
        todo = todo.main:main
    """,
)
