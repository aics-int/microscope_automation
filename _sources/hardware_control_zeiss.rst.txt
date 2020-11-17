.. contents::

.. _hardware_control_zeiss:

**********************
hardware_control_zeiss
**********************
This module contains the class to control specific hardware for Zeiss Microscopes.
This class is the link between the workflow and sample components of the Microscope Automation Software.
It extends :ref:`hardware_control_BaseMicroscope`

The class uses an API to interact with :ref:`connect_zen_blue`.
We strongly recommend to always access hardware functionality through
the API exposed by :ref:`hardware_control_zeiss`.

The classes are built around a list of objects of :ref:`hardware_components_MicroscopeComponent`.
These objects are defined in module :ref:`hardware_components`.
Most of these objects implement methods to control the hardware and store its
state.

.. _hardware_control_zeiss_SpinningDiskZeiss:

class SpinningDiskZeiss(BaseMicroscope)
=======================================
Class to control a Carl Zeiss CellObserver microscope with a spinning disk head
CSU-X1 from Yokogawa. The vendor software is ZEN blue. Most aspects
of this microscope can be controlled through an extensive macro language
based on `IronPython <http://www.ironpython.net/>`_. A subset of the functionality of
this macro language can be exposed as dll.

The :ref:`hardware_control_zeiss_SpinningDiskZeiss`
uses objects from :ref:`hardware_components`. that
call the ZEN blue specific :ref:`connect_zen_blue_ConnectMicroscope`.

ZEN blue uses the concept of "experiments" for a collection of microscope
settings and actions. The user defines these "experiments" through a graphical
user interface. The information is saved on disk as xml file. These
"experiments" are equivalent to "capture settings" within the 3i Slidebook software.
To acquire an image or trigger other functions of the microscope we
use in most cases "experiments". The user defines these "experiments"
within ZEN blue and provides the name of the "experiment" in a :ref:`preferences`
file.

Most of the methods described below take this "experiment" name as input.
The most important methods are:

.. autofunction:: microscope_automation.zeiss.hardware_control_zeiss.SpinningDiskZeiss.add_control_software
.. autofunction:: microscope_automation.zeiss.hardware_control_zeiss.SpinningDiskZeiss.add_microscope_object
.. autofunction:: microscope_automation.zeiss.hardware_control_zeiss.SpinningDiskZeiss.change_objective
.. autofunction:: microscope_automation.zeiss.hardware_control_zeiss.SpinningDiskZeiss.create_experiment_path
.. autofunction:: microscope_automation.zeiss.hardware_control_zeiss.SpinningDiskZeiss.execute_experiment
.. autofunction:: microscope_automation.zeiss.hardware_control_zeiss.SpinningDiskZeiss.get_information
.. autofunction:: microscope_automation.zeiss.hardware_control_zeiss.SpinningDiskZeiss.get_objective_is_ready
.. autofunction:: microscope_automation.zeiss.hardware_control_zeiss.SpinningDiskZeiss.initialize_hardware
.. autofunction:: microscope_automation.zeiss.hardware_control_zeiss.SpinningDiskZeiss.live_mode
.. autofunction:: microscope_automation.zeiss.hardware_control_zeiss.SpinningDiskZeiss.load_image
.. autofunction:: microscope_automation.zeiss.hardware_control_zeiss.SpinningDiskZeiss.microscope_is_ready
.. autofunction:: microscope_automation.zeiss.hardware_control_zeiss.SpinningDiskZeiss.move_to_abs_pos
.. autofunction:: microscope_automation.zeiss.hardware_control_zeiss.SpinningDiskZeiss.remove_images
.. autofunction:: microscope_automation.zeiss.hardware_control_zeiss.SpinningDiskZeiss.run_macro
.. autofunction:: microscope_automation.zeiss.hardware_control_zeiss.SpinningDiskZeiss.save_image
.. autofunction:: microscope_automation.zeiss.hardware_control_zeiss.SpinningDiskZeiss.set_microscope
.. autofunction:: microscope_automation.zeiss.hardware_control_zeiss.SpinningDiskZeiss.stop_microscope
