.. contents::

.. highlight:: shell

============
Installation
============

Full release
------------

To install Microscope Automation for use on a ZEN Microscope, follow these steps:

1. Copy the zip from the `latest release <https://github.com/aics-int/microscope_automation/releases/>`_

2. Unzip it wherever you would like to run the program from.

3. Run ``microscope_automation.exe`` from inside the unzipped folder.

  a. It should create a GeneralSettings folder automatically, but you can change the preferences to point to a different location.

  b. The ZEN communication DLLs should be run as part of the installation, which requires admin privileges.

4. Fixing installation errors

  a. If ``3a`` didn't happen run `Make_Folders.exe <https://github.com/aics-int/microscope_automation/blob/master/scripts/Make_Folders.exe>`_

  b. If ``3b`` didn't happen run `Export_ZEN_COM_Objects.exe <https://github.com/aics-int/microscope_automation/blob/master/scripts/Export_ZEN_COM_Objects.exe>`_

Stable release
--------------

To install Microscope Automation, run this command in your terminal:

.. code-block:: console

    $ pip install microscope_automation

This is the preferred method to install Microscope Automation, as it will always install the most recent stable release.

If you don't have `pip`_ installed, this `Python installation guide`_ can guide
you through the process.

.. _pip: https://pip.pypa.io
.. _Python installation guide: http://docs.python-guide.org/en/latest/starting/installation/


From sources
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


=================
Packaging the ZIP
=================

1. Clone `the repository`_ and navigate to ``scripts`` folder

2. Run ``installer.bat``

3. If you get an error like ``ImportError No system module 'pywintypes' (pywintypes38.dll)``, follow `this StackOverflow fix <https://stackoverflow.com/questions/25254285/pyinstaller-importerror-no-system-module-pywintypes-pywintypes27-dll/>`_

  a. Navigate to ``<pythonpath>\lib\site-packages\pywin32_system32``

  b. Copy ``pywintypes38.dll`` to ``<pythonpath>\lib\site-packages\win32\lib``

4. If you get an error like "resource type and/or name not specified", remember that only .exe and .dll files can be packaged as resources by PyInstaller.

  a. If you need to package a batch script, I recommend converting it to an exe first with `BatToExe`_

5. Rerun ``installer.bat``

6. Try launching ``dist\microscope_automation\microscope_automation.exe`` from the command prompt so you can check error output

7. If you get an error like ``ModuleNotFoundError: No module named 'skimage.filters.rank.core_cy_3d'``, add ``skimage.filters.rank.core_cy_3d`` to ``hiddenimports`` in ``microscope_automation.spec``

8. Once ``microscope_automation.exe`` runs successfully, package the entire ``dist/microscope_automation`` folder in a ZIP.

9. Create a new release on GitHub following these instructions: :ref:`CONTRIBUTING_Deploying`

10. Attach ``microscope_automation.zip`` to the new release.


.. _the repository: https://github.com/aics-int/microscope_automation
.. _BatToExe: https://sourceforge.net/projects/bat-to-exe/
