#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""The setup script."""

from setuptools import find_packages, setup

with open("README.rst") as readme_file:
    readme = readme_file.read()

setup_requirements = []

test_requirements = [
    "black>=19.10b0",
    "codecov>=2.1.4",
    "flake8>=3.8.3",
    "flake8-debugger>=3.2.1",
    "pytest>=5.4.3",
    "pytest-cov>=2.9.0",
    "pytest-raises>=0.11",
    "pytest-runner>=5.2",
    "pytest-html>=2.1.1",
    "mock>=4.0.2"
]

dev_requirements = [
    *setup_requirements,
    *test_requirements,
    "bumpversion>=0.6.0",
    "coverage>=5.1",
    "ipython>=7.15.0",
    "pytest-runner>=5.2",
    "Sphinx>=3",
    "sphinx_rtd_theme>=0.4.3",
    "tox>=3.15.2",
    "twine>=3.1.1",
    "wheel>=0.34.2",
]

requirements = [
    'tifffile>=2020.8.25',
    'aicsimageio>=3.2.3',
    'pandas>=1.1.1',
    'numpy>=1.19.1',
    'pyyaml>=5.3.1',
    'pyqtgraph>=0.11.0',
    'PyQt5>=5.12.3',
    'matplotlib>=3.3.1',
    'formlayout>=1.2.0',
    'lxml>=4.5.2',
    'pathlib>=1.0.1',
    'pyserial>=3.4',
    'scikit-image>=0.16.2'
]

extra_requirements = {
    "setup": setup_requirements,
    "test": test_requirements,
    "dev": dev_requirements,
    "all": [
        *requirements,
        *dev_requirements,
    ]
}

setup(
    author="Allen Institute for Cell Science",
    author_email="fletcher.chapin@alleninstitute.org",
    classifiers=[
        "Development Status :: 2 - Pre-Alpha",
        "Intended Audience :: Developers",
        "License :: Free for non-commercial use",
        "Natural Language :: English",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
    ],
    description="Automation software for the AICS Microscopes.",
    entry_points={},
    install_requires=requirements,
    license="Allen Institute Software License",
    long_description=readme,
    long_description_content_type="text/markdown",
    include_package_data=True,
    keywords="microscope_automation",
    name="microscope_automation",
    packages=find_packages(exclude=["tests", "*.tests", "*.tests.*"]),
    python_requires=">=3.7",
    setup_requires=setup_requirements,
    test_suite="microscope_automation/tests",
    tests_require=test_requirements,
    extras_require=extra_requirements,
    url="https://github.com/aics-int/microscope_automation",
    # Do not edit this string manually, always use bumpversion
    # Details in CONTRIBUTING.rst
    version="0.0.1",
    zip_safe=False,
)
