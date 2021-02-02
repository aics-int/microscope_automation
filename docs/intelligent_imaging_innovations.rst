.. contents::

.. _imports_intelligent_imaging_innovations:

**********
3i Imports
**********
There is a submodule, ``imports``, which puts all the imports for a single microscope
into one statement. For example, by running the below code you will import
:ref:`hardware_control_3i` as ``hardware_control``, :ref:`slidebook_experiment_info` as
``experiment_info``, and all the 3i connectors, i.e. :ref:`connect_slidebook` under
the name ``slidebook``.

.. code-block:: python

  import microscope_automation.imports.intelligent_imaging_innovations as slidebook
  slidebook.connect_slidebook.ConnectMicroscope()
