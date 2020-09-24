.. contents::

.. _connect_zen_blue:

****************
connect_zen_blue
****************
The communication layer of the ZenBlue API. This software is used to control
Zeiss spinning disk microscopes. ZEN Blue uses Iron Python as macro
language. This macro interface allows fine grained control of almost
all aspects of the microscope. A subset of the classes used in the macro
language are exposed as dll and are called by the :ref:`connect_zen_blue_ConnectMicroscope`
in module :ref:`connect_zen_blue`.

.. _connect_zen_blue_ConnectMicroscope:

class ConnectMicroscope()
=========================
Class to control Zeiss hardware through the Zeiss software Zen Blue.
To use this class dll have to be exported.

To be able to use ZEN services in a COM environment,
the ZEN functionality must be registered as follows as administrator (right click when opening command prompt to run as administrator
(you might have to update versions)):

.. code-block:: powershell

  pushd "C:\Windows\Microsoft.NET\Framework64\v4.0.30319"
  SET dll-1="C:\Program Files\Carl Zeiss\ZEN 2\ZEN 2 (blue edition)\Zeiss.Micro.Scripting.dll"
  regasm /u /codebase /tlb %dll-1%
  regasm /codebase /tlb %dll-1%

  SET dll-2="C:\Program Files\Carl Zeiss\ZEN 2\ZEN 2 (blue edition)\Zeiss.Micro.LM.Scripting.dll"

  regasm /u /codebase /tlb %dll-2%
  regasm /codebase /tlb %dll-2%
  popd

Methods for Experiment Settings
----------------------------------------
.. autofunction:: microscope_automation.zeiss.connect_zen_blue.ConnectMicroscope.create_experiment_path

Methods to Save and Load Images
-------------------------------
.. autofunction:: microscope_automation.zeiss.connect_zen_blue.ConnectMicroscope.save_image
.. autofunction:: microscope_automation.zeiss.connect_zen_blue.ConnectMicroscope.load_image

Methods to Acquire Images
-------------------------
.. autofunction:: microscope_automation.zeiss.connect_zen_blue.ConnectMicroscope.snap_image
.. autofunction:: microscope_automation.zeiss.connect_zen_blue.ConnectMicroscope.close_experiment
.. autofunction:: microscope_automation.zeiss.connect_zen_blue.ConnectMicroscope.get_experiment_folder
.. autofunction:: microscope_automation.zeiss.connect_zen_blue.ConnectMicroscope.wait_for_experiment
.. autofunction:: microscope_automation.zeiss.connect_zen_blue.ConnectMicroscope.wait_for_objective
.. autofunction:: microscope_automation.zeiss.connect_zen_blue.ConnectMicroscope.execute_experiment
.. autofunction:: microscope_automation.zeiss.connect_zen_blue.ConnectMicroscope.live_mode_start
.. autofunction:: microscope_automation.zeiss.connect_zen_blue.ConnectMicroscope.live_mode_stop

Methods to Interact with Image Display
--------------------------------------
.. autofunction:: microscope_automation.zeiss.connect_zen_blue.ConnectMicroscope.show_image
.. autofunction:: microscope_automation.zeiss.connect_zen_blue.ConnectMicroscope.remove_all

Methods to Control XY Stage
---------------------------
.. autofunction:: microscope_automation.zeiss.connect_zen_blue.ConnectMicroscope.get_stage_pos
.. autofunction:: microscope_automation.zeiss.connect_zen_blue.ConnectMicroscope.move_stage_to

Methods to Control Focus
------------------------
.. autofunction:: microscope_automation.zeiss.connect_zen_blue.ConnectMicroscope.set_autofocus_ready
.. autofunction:: microscope_automation.zeiss.connect_zen_blue.ConnectMicroscope.set_autofocus_not_ready
.. autofunction:: microscope_automation.zeiss.connect_zen_blue.ConnectMicroscope.get_autofocus_ready
.. autofunction:: microscope_automation.zeiss.connect_zen_blue.ConnectMicroscope.set_last_known_focus_position
.. autofunction:: microscope_automation.zeiss.connect_zen_blue.ConnectMicroscope.get_last_known_focus_position
.. autofunction:: microscope_automation.zeiss.connect_zen_blue.ConnectMicroscope.recover_focus
.. autofunction:: microscope_automation.zeiss.connect_zen_blue.ConnectMicroscope.find_autofocus
.. autofunction:: microscope_automation.zeiss.connect_zen_blue.ConnectMicroscope.find_surface
.. autofunction:: microscope_automation.zeiss.connect_zen_blue.ConnectMicroscope.store_focus
.. autofunction:: microscope_automation.zeiss.connect_zen_blue.ConnectMicroscope.recall_focus
.. autofunction:: microscope_automation.zeiss.connect_zen_blue.ConnectMicroscope.get_focus_pos
.. autofunction:: microscope_automation.zeiss.connect_zen_blue.ConnectMicroscope.move_focus_to
.. autofunction:: microscope_automation.zeiss.connect_zen_blue.ConnectMicroscope.z_relative_move
.. autofunction:: microscope_automation.zeiss.connect_zen_blue.ConnectMicroscope.z_down_relative
.. autofunction:: microscope_automation.zeiss.connect_zen_blue.ConnectMicroscope.z_up_relative
.. autofunction:: microscope_automation.zeiss.connect_zen_blue.ConnectMicroscope.set_focus_work_position
.. autofunction:: microscope_automation.zeiss.connect_zen_blue.ConnectMicroscope.set_focus_load_position
.. autofunction:: microscope_automation.zeiss.connect_zen_blue.ConnectMicroscope.move_focus_to_load
.. autofunction:: microscope_automation.zeiss.connect_zen_blue.ConnectMicroscope.move_focus_to_work

Methods to Interact with Objectives
-----------------------------------
.. autofunction:: microscope_automation.zeiss.connect_zen_blue.ConnectMicroscope.get_all_objectives
.. autofunction:: microscope_automation.zeiss.connect_zen_blue.ConnectMicroscope.switch_objective
.. autofunction:: microscope_automation.zeiss.connect_zen_blue.ConnectMicroscope.get_objective_magnification
.. autofunction:: microscope_automation.zeiss.connect_zen_blue.ConnectMicroscope.get_objective_name
.. autofunction:: microscope_automation.zeiss.connect_zen_blue.ConnectMicroscope.get_objective_position
.. autofunction:: microscope_automation.zeiss.connect_zen_blue.ConnectMicroscope.run_macro

Methods to Control Immersion Water Delivery
-------------------------------------------
.. autofunction:: microscope_automation.zeiss.connect_zen_blue.ConnectMicroscope.trigger_pump

Methods to Collect Microscope Information
-----------------------------------------
.. autofunction:: microscope_automation.zeiss.connect_zen_blue.ConnectMicroscope.get_microscope_name
.. autofunction:: microscope_automation.zeiss.connect_zen_blue.ConnectMicroscope.stop

Methods to Collect Experiment Information
-----------------------------------------
.. autofunction:: microscope_automation.zeiss.connect_zen_blue.ConnectMicroscope.validate_experiment
.. autofunction:: microscope_automation.zeiss.connect_zen_blue.ConnectMicroscope.is_z_stack
.. autofunction:: microscope_automation.zeiss.connect_zen_blue.ConnectMicroscope.z_stack_range
.. autofunction:: microscope_automation.zeiss.connect_zen_blue.ConnectMicroscope.is_tile_scan
.. autofunction:: microscope_automation.zeiss.connect_zen_blue.ConnectMicroscope.update_tile_positions
.. autofunction:: microscope_automation.zeiss.connect_zen_blue.ConnectMicroscope.get_objective_position_from_experiment_file
.. autofunction:: microscope_automation.zeiss.connect_zen_blue.ConnectMicroscope.get_focus_settings

Testing
=======
The following functions were written to test the connect_zen_blue module.

.. autofunction:: microscope_automation.zeiss.connect_zen_blue.test_definite_focus
.. autofunction:: microscope_automation.zeiss.connect_zen_blue.test_connect_zen_blue
