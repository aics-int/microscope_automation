.. contents::

.. _software_state:

**************
software_state
**************
This module contains two classes, :ref:`software_state_State` and
:ref:`software_state_DiagnosticPickler`, which are used to save the state of the
software so it can restart at the same point in an experiment at which it crashed.

.. _software_state_DiagnosticPickler:

class DiagnosticPickler(pickle.Pickler)
=======================================

.. autoclass:: microscope_automation.util.software_state.DiagnosticPickler
    :members:

.. _software_state_State:

class State(object)
===================
.. autoclass:: microscope_automation.util.software_state.State
    :members:
