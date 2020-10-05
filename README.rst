# Microscope Automation

.. image::
   https://github.com/aics-int/microscope_automation/workflows/Build%20Master/badge.svg
   :width: 300
   :target: https://github.com/aics-int/microscope_automation/actions
   :alt: Build Status

Automation software for a variety of popular microscopes, such as Zeiss and 3i.

Installation
============
**Stable Release:** ``pip install microscope_automation``

**Development Head:** ``pip install git+https://github.com/aics-int/microscope_automation.git``

Development
===========
See :ref:`CONTRIBUTING` for information related to developing the code.

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

- :ref:`LICENSE`
- :ref:`CONTRIBUTING`