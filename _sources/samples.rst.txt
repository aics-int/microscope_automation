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

class Background(ImagingSystem)
===============================
Class used for background correction of plates.

.. autoclass:: microscope_automation.samples.samples.Background
    :members:

class PlateHolder(ImagingSystem)
================================
Class which describes a plate holder. A plate holder is the container object
which holds plates, slides, and other samples.

.. autoclass:: microscope_automation.samples.samples.PlateHolder
    :members:

class ImmersionDelivery(ImagingSystem)
======================================
Class which interacts with :ref:`hardware_components_Pump`.

.. autoclass:: microscope_automation.samples.samples.ImmersionDelivery
    :members:

class Plate(ImagingSystem)
==========================
Class which describes a plate. A plate is the container object which holds wells.

.. autoclass:: microscope_automation.samples.samples.Plate
    :members:

class Slide(ImagingSystem)
==========================

.. autoclass:: microscope_automation.samples.samples.Slide
    :members:

class Well(ImagingSystem)
=========================
Class which describes a well. A plate is the container object which holds
barcodes and colonies.

.. autoclass:: microscope_automation.samples.samples.Well
    :members:

class Barcode(ImagingSystem)
============================

.. autoclass:: microscope_automation.samples.samples.Barcode
    :members:

class Sample(ImagingSystem)
===========================

.. autoclass:: microscope_automation.samples.samples.Sample
    :members:

class Colony(ImagingSystem)
===========================
Class which describes a colony. A colony is the container object which holds cells.

.. autoclass:: microscope_automation.samples.samples.Colony
    :members:

class Cell(ImagingSystem)
=========================

.. autoclass:: microscope_automation.samples.samples.Cell
    :members:

Helper Methods
==============
These helper functions are used when manually setting up samples objects is needed,
such as while testing.

.. autofunction:: microscope_automation.samples.samples.create_rect_tile
.. autofunction:: microscope_automation.samples.samples.create_plate
.. autofunction:: microscope_automation.samples.samples.create_plate_holder_manually
