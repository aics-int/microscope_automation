.. contents::

.. _hardware_control_3i:

*******************
hardware_control_3i
*******************
This module contains the class to control specific hardware for 3i Microscopes.
This class is the link between the workflow and sample components of the Microscope Automation Software.
It extends :ref:`hardware_control_BaseMicroscope`

The class uses an API to interact with :ref:`connect_slidebook`.
We strongly recommend to always access hardware functionality through
the API exposed by :ref:`hardware_control_3i`.

The classes are built around a list of objects of :ref:`hardware_components_MicroscopeComponent`.
These objects are defined in module :ref:`hardware_components`.
Most of these objects implement methods to control the hardware and store its
state.

.. _hardware_control_3i_SpinningDisk3i:

class SpinningDisk3i(BaseMicroscope)
====================================
Class to control a 3i spinning disk microscope with a CSU-W1 confocal head
from Yokogawa using the vendor software, Slidebook. Slidebook does not allow a
direct external control of microscope hardware components. Instead, 3i provided
a custom modification of their hierarchical and conditional capture functionality
to the Allen Institute for Cell Science.

This allows to call MATLAB functions of the form:
::

  function [N, L, C, P] = find_locations_of_interest(I, X, Y, Z,
                                                     xy_pixel_size,
                                                     z_spacing,
                                                     x_stage_direction,
                                                     y_stage_direction,
                                                     z_stage_direction)

after a hierarchical capture or
::

  function is_continue = continue_time_lapse(I)

after a time lapse capture.

The function called after a hierarchical
capture can return a list with new imaging positions and "capture
settings" that describe experiments to be performed at these locations.
"Capture settings" are defined through a graphical user interface
within Slidebook and are saved to disk at the microscope control computer.
They are equivalient to "experiments" within Zeiss ZEN blue software.

Microservices :ref:`commands_service` and :ref:`data_service <data_service>`
facilitate the communication between :ref:`hardware_control_3i_SpinningDisk3i`
and the Slidebook software that controls the 3i spinning disk microscope.

- :ref:`commands_service` implements a queue with
  commands to be executed by the microscope. `SpinningDisk3i` writes
  to this queue and the MATLAB code invoked by Slidebook pulls
  from it.
- :ref:`data_service <data_service>` implements a queue with image
  data from the microscope. Slidebook writes to this queue and
  :ref:`hardware_control_3i_SpinningDisk3i` pulls from it.
  Other microservices (at this moment mainly for visualizations and position selection)
  can pull from the queue.

The :ref:`hardware_control_3i_SpinningDisk3i` uses objects from
:ref:`hardware_components` that call the Slidebook specific
:ref:`connect_slidebook_ConnectMicroscope` as defined in the module
:ref:`connect_slidebook`.

The most important methods are:

.. autofunction:: microscope_automation.slidebook.hardware_control_3i.SpinningDisk3i.add_control_software
.. autofunction:: microscope_automation.slidebook.hardware_control_3i.SpinningDisk3i.add_microscope_object
.. autofunction:: microscope_automation.slidebook.hardware_control_3i.SpinningDisk3i.create_experiment_path
.. autofunction:: microscope_automation.slidebook.hardware_control_3i.SpinningDisk3i.execute_experiment
.. autofunction:: microscope_automation.slidebook.hardware_control_3i.SpinningDisk3i.load_image
.. autofunction:: microscope_automation.slidebook.hardware_control_3i.SpinningDisk3i.move_to_abs_pos
.. autofunction:: microscope_automation.slidebook.hardware_control_3i.SpinningDisk3i.remove_images
.. autofunction:: microscope_automation.slidebook.hardware_control_3i.SpinningDisk3i.stop_microscope
