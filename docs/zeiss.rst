.. contents::

.. _imports_zeiss:

*************
Zeiss Imports
*************
There is a submodule, ``imports``, which puts all the imports for a single microscope
into one statement. For example, by running the below code you will import
:ref:`hardware_control_zeiss` as ``hardware_control``, :ref:`zen_experiment_info` as
``experiment_info``, and all the ZEN connectors, i.e. :ref:`connect_zen_blue` and
:ref:`connect_zen_black`, under the name ``zeiss``.

.. code-block:: python

  import microscope_automation.imports.zeiss as zeiss
  zeiss.connect_zen_blue.ConnectMicroscope()
