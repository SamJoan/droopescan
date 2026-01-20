import os
from setuptools import setup, find_packages
from setuptools.command.install import install

def read(*paths):
    with open(os.path.join(*paths), 'r') as f:
        return f.read()

def read_first_line(f):
    with open(f, 'r') as f:
        first_line = f.readline()

    return first_line.strip()

def _post_install():
    os.system("chmod +x /usr/local/bin/droopescan");

class PostInstall(install):

    def run(self):
        install.run(self)
        self.execute(_post_install, [],  msg="Running post install task")

setup(
    name='droopescan',
    version=read_first_line('CHANGELOG'),
    description='A plugin-based scanner that aids security researchers in identifying issues with several CMSs: Drupal, Wordpress, Moodle and SilverStripe. https://github.com/droope/droopescan',
    author_email='pedro@worcel.com',
    author='Pedro Worcel',
    include_package_data=True,
    license='GPL',
    long_description=(read('CHANGELOG')),
    packages=find_packages('.', exclude=['tests', '.update-workspace']),
    url='http://github.com/droope/droopescan/',
    scripts=['droopescan'],
    data_files=[
        ('/etc/bash_completion.d/', ['dscan/droopescan_completion'])
    ],
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'License :: OSI Approved :: GNU General Public License (GPL)',
        'Operating System :: Unix',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
    ],
    install_requires=[
        'cement>=3.0',
        'requests',
        'pystache',
    ],
    extras_require={
        ':python_version == "2.7"': ['futures']
    },
    cmdclass={'install': PostInstall}
)

