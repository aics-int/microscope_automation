.. contents::

.. _connect_zen_black:

*****************
connect_zen_black
*****************
Control of Zeiss ZEN Black software. This software is used to control
Zeiss spinning disk microscopes. ZEN Black uses VBA as macro
language. This macro interface allows fine grained control of almost
all aspects of the microscope. A subset of the classes used in the macro
language are exposed as dll and are called by the :ref:`connect_zen_black_ConnectMicroscope`
in module :ref:`connect_zen_black`.

.. _connect_zen_black_ConnectMicroscope:

class ConnectMicroscope()
=========================
Class to control Zeiss hardware through the Zeiss software Zen Black.

Methods for Experiment Settings
-------------------------------
.. autofunction:: microscope_automation.zeiss.connect_zen_black.ConnectMicroscope.create_experiment_path

Methods to Save and Load Images
-------------------------------
.. autofunction:: microscope_automation.zeiss.connect_zen_black.ConnectMicroscope.save_image
.. autofunction:: microscope_automation.zeiss.connect_zen_black.ConnectMicroscope.load_image

Methods to Acquire Images
-------------------------
.. autofunction:: microscope_automation.zeiss.connect_zen_black.ConnectMicroscope.snap_image
.. autofunction:: microscope_automation.zeiss.connect_zen_black.ConnectMicroscope.close_experiment
.. autofunction:: microscope_automation.zeiss.connect_zen_black.ConnectMicroscope.wait_for_experiment
.. autofunction:: microscope_automation.zeiss.connect_zen_black.ConnectMicroscope.wait_for_objective
.. autofunction:: microscope_automation.zeiss.connect_zen_black.ConnectMicroscope.execute_experiment
.. autofunction:: microscope_automation.zeiss.connect_zen_black.ConnectMicroscope.live_mode_start
.. autofunction:: microscope_automation.zeiss.connect_zen_black.ConnectMicroscope.live_mode_stop

Methods to Interact with Image Display
--------------------------------------
.. autofunction:: microscope_automation.zeiss.connect_zen_black.ConnectMicroscope.show_image
.. autofunction:: microscope_automation.zeiss.connect_zen_black.ConnectMicroscope.remove_all

Methods to Control XY Stage
---------------------------
.. autofunction:: microscope_automation.zeiss.connect_zen_black.ConnectMicroscope.get_stage_pos
.. autofunction:: microscope_automation.zeiss.connect_zen_black.ConnectMicroscope.move_stage_to

Methods to Control Focus
------------------------
.. autofunction:: microscope_automation.zeiss.connect_zen_black.ConnectMicroscope.set_autofocus_ready
.. autofunction:: microscope_automation.zeiss.connect_zen_black.ConnectMicroscope.set_autofocus_not_ready
.. autofunction:: microscope_automation.zeiss.connect_zen_black.ConnectMicroscope.get_autofocus_ready
.. autofunction:: microscope_automation.zeiss.connect_zen_black.ConnectMicroscope.set_last_known_focus_position
.. autofunction:: microscope_automation.zeiss.connect_zen_black.ConnectMicroscope.get_last_known_focus_position
.. autofunction:: microscope_automation.zeiss.connect_zen_black.ConnectMicroscope.recover_focus
.. autofunction:: microscope_automation.zeiss.connect_zen_black.ConnectMicroscope.find_surface
.. autofunction:: microscope_automation.zeiss.connect_zen_black.ConnectMicroscope.store_focus
.. autofunction:: microscope_automation.zeiss.connect_zen_black.ConnectMicroscope.recall_focus
.. autofunction:: microscope_automation.zeiss.connect_zen_black.ConnectMicroscope.get_focus_pos
.. autofunction:: microscope_automation.zeiss.connect_zen_black.ConnectMicroscope.move_focus_to
.. autofunction:: microscope_automation.zeiss.connect_zen_black.ConnectMicroscope.z_relative_move
.. autofunction:: microscope_automation.zeiss.connect_zen_black.ConnectMicroscope.z_down_relative
.. autofunction:: microscope_automation.zeiss.connect_zen_black.ConnectMicroscope.z_up_relative
.. autofunction:: microscope_automation.zeiss.connect_zen_black.ConnectMicroscope.set_focus_work_position
.. autofunction:: microscope_automation.zeiss.connect_zen_black.ConnectMicroscope.set_focus_load_position
.. autofunction:: microscope_automation.zeiss.connect_zen_black.ConnectMicroscope.move_focus_to_load
.. autofunction:: microscope_automation.zeiss.connect_zen_black.ConnectMicroscope.move_focus_to_work

Methods to Interact with Objectives
-----------------------------------
.. autofunction:: microscope_automation.zeiss.connect_zen_black.ConnectMicroscope.get_all_objectives
.. autofunction:: microscope_automation.zeiss.connect_zen_black.ConnectMicroscope.switch_objective
.. autofunction:: microscope_automation.zeiss.connect_zen_black.ConnectMicroscope.get_objective_magnification
.. autofunction:: microscope_automation.zeiss.connect_zen_black.ConnectMicroscope.get_objective_name
.. autofunction:: microscope_automation.zeiss.connect_zen_black.ConnectMicroscope.get_objective_position

Methods to Control Immersion Water Delivery
-------------------------------------------
.. autofunction:: microscope_automation.zeiss.connect_zen_black.ConnectMicroscope.trigger_pump

Methods to Collect Microscope Information
-----------------------------------------
.. autofunction:: microscope_automation.zeiss.connect_zen_black.ConnectMicroscope.get_microscope_name
.. autofunction:: microscope_automation.zeiss.connect_zen_black.ConnectMicroscope.stop

Methods to Collect Experiment Information
-----------------------------------------
.. autofunction:: microscope_automation.zeiss.connect_zen_black.ConnectMicroscope.validate_experiment
.. autofunction:: microscope_automation.zeiss.connect_zen_black.ConnectMicroscope.is_z_stack
.. autofunction:: microscope_automation.zeiss.connect_zen_black.ConnectMicroscope.z_stack_range
.. autofunction:: microscope_automation.zeiss.connect_zen_black.ConnectMicroscope.is_tile_scan
.. autofunction:: microscope_automation.zeiss.connect_zen_black.ConnectMicroscope.update_tile_positions
.. autofunction:: microscope_automation.zeiss.connect_zen_black.ConnectMicroscope.get_objective_position_from_experiment_file
.. autofunction:: microscope_automation.zeiss.connect_zen_black.ConnectMicroscope.get_focus_settings
