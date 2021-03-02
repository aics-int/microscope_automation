.. contents::

.. highlight:: shell

============
Installation
============

.. _Installation_Full_release:

ZIP Release
-----------

To install Microscope Automation for use on a ZEN Microscope, follow these steps:

1. Copy the ZIP from the latest release by clicking `here <https://github.com/aics-int/microscope_automation/releases/>`_ and selecting ``microscope_automation.zip``

2. Extract the contents of ``microscope_automation.zip`` to the location of your choice.

3. Run `Export_ZEN_COM_Objects.bat <https://github.com/aics-int/microscope_automation/blob/master/scripts/Export_ZEN_COM_Objects.bat>`_ from inside the extracted folder.

  a. You may have to run as an administrator for it to work properly.

4. Start the microscope and run XY stage, focus, and any other necessary calibrations.

5. Run ``microscope_automation.exe`` from inside the extracted folder.

  a. When prompted, select the workflow preference file you wish to use, first checking all settings are configured as you wish.

For non-ZEN systems, simply skip ``Step 3``.

Pip Installation
----------------

To install Microscope Automation, run this command in your terminal:

.. code-block:: console

    $ pip install microscope_automation

This is the preferred method to install Microscope Automation, as it will always install the most recent stable release.

If you don't have `pip`_ installed, this `Python installation guide`_ can guide
you through the process.

.. _pip: https://pip.pypa.io
.. _Python installation guide: http://docs.python-guide.org/en/latest/starting/installation/

From Sources
------------

The sources for Microscope Automation can be downloaded from the `Github repo`_.

You can either clone the public repository:

.. code-block:: console

    $ git clone git://github.com/aics-int/microscope_automation

Or download the `tarball`_:

.. code-block:: console

    $ curl  -OL https://github.com/aics-int/microscope_automation/tarball/master

Once you have a copy of the source, you can install it with:

.. code-block:: console

    $ python setup.py install

.. _Github repo: https://github.com/aics-int/microscope_automation
.. _tarball: https://github.com/aics-int/microscope_automation/tarball/master

.. _Installation_Packaging:

=================
Packaging the ZIP
=================

Simply follow the instructions on :ref:`CONTRIBUTING_Deploying` in :ref:`CONTRIBUTING`.

GitHub Actions is configured to package the ZIP and publish to PyPI whenever a new version
is pushed to the ``stable`` branch.

.. _the repository: https://github.com/aics-int/microscope_automation
.. _BatToExe: https://sourceforge.net/projects/bat-to-exe/
