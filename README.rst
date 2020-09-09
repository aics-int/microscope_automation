# Microscope Automation

.. image::
   https://github.com/aics-int/microscope_automation/workflows/Build%20Master/badge.svg
   :width: 300
   :target: https://github.com/aics-int/microscope_automation/actions
   :alt: Build Status

Automation software for the AICS Microscopes. This package is not meant to be
used alone, but contains core modules which are extended by microscope-specific
packages, such as
`microscope_automation_zen_blue <https://github.com/aics-int/microscope_automation_zen_blue/>`_ and
`microscope_automation_slidebook <https://github.com/aics-int/microscope_automation_slidebook/>`_,
which are the entry points for the user.

Installation
============
**Stable Release:** ``pip install microscope_automation_slidebook``

**Development Head:** ``pip install git+https://github.com/aics-int/microscope_automation_zen_blue.git``

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
