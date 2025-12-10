from setuptools import setup, find_packages

setup(
    name="droopescan",
    version="1.45.2",  # Bump for the fix
    description="A plugin-based scanner that aids security researchers in identifying issues with several CMSs, mainly Drupal & Silverstripe.",
    long_description=open("README.md").read(),
    author="droope (forked by SamJoan, fixed by Nasaltron)",
    author_email="droope@gmail.com",
    url="https://github.com/SamJoan/droopescan",
    packages=find_packages(),
    entry_points={
        "console_scripts": [
            "droopescan = dscan.droopescan:main",
        ],
    },
    install_requires=[
        "cement>=3.0.8",
        "pystache",
        "requests>=2.4.0",
        "six",
    ],
    python_requires=">=3.9",
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "License :: OSI Approved :: Apache Software License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
        "Programming Language :: Python :: 3.14",
        "Topic :: Security",
    ],
)
