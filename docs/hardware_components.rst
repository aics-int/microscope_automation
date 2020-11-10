.. contents::

.. _hardware_components:

*******************
hardware_components
*******************
The hardware_components module contains abstract classes that define common microscope components.
These components are system independent, so not all microscopes implement all classes.
They are the bridge between automation software and hardware specific implementations.
These classes should only be called by the :ref:`hardware_control` modules like
:ref:`hardware_control_3i` and :ref:`hardware_control_zeiss`.

class Experiment(object)
========================
This class contains methods which validate and edit experiment files.

.. autoclass:: microscope_automation.hardware.hardware_components.Experiment
    :members:

.. _hardware_components_MicroscopeComponent:

class MicroscopeComponent(object)
=================================
Base class which all microscope component subclasses will inherit.

.. autoclass:: microscope_automation.hardware.hardware_components.MicroscopeComponent
    :members:

class ControlSoftware(MicroscopeComponent)
==========================================
This class imports the correct control software based on what microscope is being used.

.. autoclass:: microscope_automation.hardware.hardware_components.ControlSoftware
    :members:

class Safety(MicroscopeComponent)
=================================
This class contains methods to avoid damaging the microscope's hardware,
such as determining a safe area and whether a position is within that area.

.. autoclass:: microscope_automation.hardware.hardware_components.Safety
    :members:

class Camera(MicroscopeComponent, ImageAICS)
============================================
This class defines and operates the microscope camera.
To accomplish this, it inherits the :ref:`image_AICS_ImageAICS` in addition to
the :ref:`hardware_components_MicroscopeComponent`

.. autoclass:: microscope_automation.hardware.hardware_components.Camera
    :members:

class Stage(MicroscopeComponent)
================================
This class contains methods which define and operate the microscope's stage.

.. autoclass:: microscope_automation.hardware.hardware_components.Stage
    :members:

class ObjectiveChanger(MicroscopeComponent)
===========================================
This class contains a wide array of methods to view and modify objectives.

.. autoclass:: microscope_automation.hardware.hardware_components.ObjectiveChanger
    :members:

class FocusDrive(MicroscopeComponent)
=====================================
This class controls focus drive.

.. autoclass:: microscope_automation.hardware.hardware_components.FocusDrive
    :members:

class AutoFocus(MicroscopeComponent)
====================================
This class obtains autofocus settings from the microscope and sets new
autofocus configurations.

.. autoclass:: microscope_automation.hardware.hardware_components.AutoFocus
    :members:

.. _hardware_components_Pump:

class Pump(MicroscopeComponent)
===============================
This class describes, sets up, and triggers pump operation.

.. autoclass:: microscope_automation.hardware.hardware_components.Pump
    :members:

Logging
=======
The module includes the following functions to log various information:

.. autofunction:: microscope_automation.hardware.hardware_components.log_message
.. autofunction:: microscope_automation.hardware.hardware_components.log_method
.. autofunction:: microscope_automation.hardware.hardware_components.log_warning
