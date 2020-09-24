.. contents::

.. _automation_exceptions:

*********************
automation_exceptions
*********************
This module consists of a various classes of exceptions which are used throughout
the project.

.. _automation_exceptions_AutomationError:

Base Exception
==============
``AutomationError`` is the base class for all exceptions in this package.

.. autoclass:: microscope_automation.automation_exceptions.AutomationError
    :members:

.. _automation_exceptions_HardwareError:

Hardware Exceptions
===================
The following exceptions are used for hardware-related errors. The first,
``HardwareError``, extends :ref:`automation_exceptions_AutomationError` and is
the base class for the others.

.. autoclass:: microscope_automation.automation_exceptions.HardwareError
    :members:

.. autoclass:: microscope_automation.automation_exceptions.HardwareDoesNotExistError
    :members:

.. autoclass:: microscope_automation.automation_exceptions.CrashDangerError
    :members:

.. autoclass:: microscope_automation.automation_exceptions.HardwareNotReadyError
    :members:

.. autoclass:: microscope_automation.automation_exceptions.HardwareCommandNotDefinedError
    :members:

Autofocus Exceptions
====================
The following exceptions are used for autofocus-related errors. The first,
``AutofocusError``, extends :ref:`automation_exceptions_HardwareError` and is
the base class for the others.

.. autoclass:: microscope_automation.automation_exceptions.AutofocusError
    :members:

.. autoclass:: microscope_automation.automation_exceptions.AutofocusObjectiveChangedError
    :members:

.. autoclass:: microscope_automation.automation_exceptions.AutofocusNotSetError
    :members:

.. autoclass:: microscope_automation.automation_exceptions.AutofocusNoReferenceObjectError
    :members:

Focus Drive Exceptions
======================
The following exceptions are used for focus drive related errors. They
extend :ref:`automation_exceptions_HardwareError`.

.. autoclass:: microscope_automation.automation_exceptions.LoadNotDefinedError
    :members:

.. autoclass:: microscope_automation.automation_exceptions.WorkNotDefinedError
    :members:

Objective Changer Exceptions
============================
The following exception is used for objective changer related errors. It extends
:ref:`automation_exceptions_HardwareError`.

.. autoclass:: microscope_automation.automation_exceptions.ObjectiveNotDefinedError
    :members:

Experiment Exceptions
=====================
he following exceptions are used for experiment-related errors. The first,
``ExperimentError``, extends :ref:`automation_exceptions_HardwareError` and is
the base class for the others.

.. autoclass:: microscope_automation.automation_exceptions.ExperimentError
    :members:

.. autoclass:: microscope_automation.automation_exceptions.ExperimentNotExistError
    :members:

I/O Exceptions
==============
The following exceptions are used for read and write errors. The first,
``IOError``, extends :ref:`automation_exceptions_AutomationError` and is
the base class for the others.

.. autoclass:: microscope_automation.automation_exceptions.IOError
    :members:

.. autoclass:: microscope_automation.automation_exceptions.FileExistsError
    :members:

.. autoclass:: microscope_automation.automation_exceptions.MetaDataNotSavedError
    :members:

Program Flow Exceptions
=======================
The following exception, which extends :ref:`automation_exceptions_AutomationError`
is thrown when the automated workflow is stopped and images are no longer being taken.

.. autoclass:: microscope_automation.automation_exceptions.StopCollectingError
    :members:

Helper Functions
================

.. autofunction:: microscope_automation.automation_exceptions.set_error_blocking
.. autofunction:: microscope_automation.automation_exceptions.get_error_blocking
