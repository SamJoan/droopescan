
from setuptools import setup, find_packages
from {{ label }}.core.version import get_version

VERSION = get_version()

f = open('README.md', 'r')
LONG_DESCRIPTION = f.read()
f.close()

setup(
    name='{{ label }}',
    version=VERSION,
    description='{{ description }}',
    long_description=LONG_DESCRIPTION,
    long_description_content_type='text/markdown',
    author='{{ creator }}',
    author_email='{{ creator_email }}',
    url='{{ url }}',
    license='{{ license }}',
    packages=find_packages(exclude=['ez_setup', 'tests*']),
    package_data={'{{ label }}': ['templates/*']},
    include_package_data=True,
    entry_points="""
        [console_scripts]
        {{ label }} = {{ label }}.main:main
    """,
)
