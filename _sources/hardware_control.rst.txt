.. contents::

.. _hardware_control:

****************
hardware_control
****************
This module contains the base class, :ref:`hardware_control_BaseMicroscope`, to control specific hardware.
This class is then extended by :ref:`hardware_control_3i` and :ref:`hardware_control_zeiss`
the workflow and sample components of the Microscope Automation Software.
At this moment the following microscope classes are implemented:

These classes have a vendor independent API and connect through vendor
software specific connect modules to the specific hardware.
We strongly recommend to access hardware functionality always through
the API exposed by classes from the various ``hardware_control`` modules.

The classes are build around a list of objects of :ref:`hardware_components_MicroscopeComponent`.
These objects are defined in module :ref:`hardware_components`.
Most of these objects implement methods to control the hardware and store its
state.

.. _hardware_control_BaseMicroscope:

class BaseMicroscope(object)
============================
Base class with minimum functionality. The following public methods are implemented:

.. autoclass:: microscope_automation.hardware.hardware_control.BaseMicroscope
    :members:
