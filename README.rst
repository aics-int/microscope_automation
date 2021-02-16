*********************
Microscope Automation
*********************

.. image::
   https://github.com/aics-int/microscope_automation/workflows/Build%20Master/badge.svg
   :height: 30
   :target: https://github.com/aics-int/microscope_automation/actions
   :alt: Build Status

.. image::
   https://github.com/aics-int/microscope_automation/workflows/Documentation/badge.svg
   :height: 30
   :target: https://aics-int.github.io/microscope_automation
   :alt: Documentation

.. image::
   https://codecov.io/gh/aics-int/microscope_automation/branch/master/graph/badge.svg
   :height: 30
   :target: https://codecov.io/gh/aics-int/microscope_automation
   :alt: Code Coverage

Automation software for a variety of popular microscopes, such as Zeiss and 3i.

Installation
============
To install the ZIP Version:

1. Copy the zip from the `latest release <https://github.com/aics-int/microscope_automation/releases/>`_

2. For ZEN systems, run `Export_ZEN_COM_Objects.bat <https://github.com/aics-int/microscope_automation/blob/master/scripts/Export_ZEN_COM_Objects.bat>`_

  a. You may have to run as an administrator for it to work properly.

3. Run ``microscope_automation.exe`` from inside the unzipped folder.

You can also use PyPI as follows:

**Stable Release:** ``pip install microscope_automation``

**Development Head:** ``pip install git+https://github.com/aics-int/microscope_automation.git``

Complete installation instructions available `here <https://aics-int.github.io/microscope_automation/installation.html/>`_.

Development
===========
See `CONTRIBUTING <https://github.com/aics-int/microscope_automation/blob/master/CONTRIBUTING.rst/>`_
for information related to developing the code.

The Four Commands You Need To Know
==================================

1. ``pip install -e .[dev]``

    This will install your package in editable mode with all the required development
    dependencies (i.e. ``tox``).

2. ``make build``

    This will run ``tox`` which will run all your tests in both Python 3.7
    and Python 3.8 as well as linting your code.

3. ``make clean``

    This will clean up various Python and build generated files so that you can ensure
    that you are working in a clean environment.

4. ``make docs``

    This will generate and launch a web browser to view the most up-to-date
    documentation for your Python package.

Legal Documents
===============

- `LICENSE <https://github.com/aics-int/microscope_automation/blob/master/LICENSE.txt/>`_
- `CONTRIBUTING <https://github.com/aics-int/microscope_automation/blob/master/CONTRIBUTING.rst/>`_
