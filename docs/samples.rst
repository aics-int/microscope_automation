.. contents::

.. _samples:

*******
samples
*******
The samples module contains classes which define different objects that can be imaged,
e.g. plates, slides, wells, and cells. These classes all have a microscope object attribute
which defines the :ref:`hardware_control` method like :ref:`hardware_control_3i_SpinningDisk3i`
or :ref:`hardware_control_zeiss_SpinningDiskZeiss`.

class ImagingSystem(object)
===========================
This is the parent class of all other objects in the :ref:`samples` module.

.. autoclass:: microscope_automation.samples.samples.ImagingSystem
    :members:

Helper Methods
==============
These helper functions are used when manually setting up samples objects is needed,
such as while testing.

.. autofunction:: microscope_automation.samples.samples.create_rect_tile
.. autofunction:: microscope_automation.samples.samples.create_plate
.. autofunction:: microscope_automation.samples.samples.create_plate_holder_manually
