import os
from setuptools import setup, find_packages

def read(*paths):
    with open(os.path.join(*paths), 'r') as f:
        return f.read()

def read_first_line(f):
    with open(f, 'r') as f:
        first_line = f.readline()

    return first_line.strip()


setup(
    name='droopescan',
    version=read_first_line('CHANGELOG'),
    description='A plugin-based scanner that aids security researchers in identifying issues with several CMSs, mainly Drupal & Silverstripe.',
    author_email='pedro.worcel@security-assessment.com',
    author='Pedro Worcel',
    include_package_data=True,
    license='GPL',
    long_description=(read('CHANGELOG')),
    packages=find_packages('.', exclude=['tests', '.update-workspace']),
    url='http://github.com/droope/droopescan/',
    scripts=['droopescan'],
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'License :: OSI Approved :: GNU General Public License (GPL)',
        'Operating System :: Unix',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
    ],
    install_requires=[
        'cement>=2.2,<2.2.99',
        'requests',
        'pystache',
        'futures'
    ],
)

