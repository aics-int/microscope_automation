"""
Classes to describe and control hardware.
Bridge between automation software and hardware specific implementations.
Created on Jul 7, 2016
Split into hardware_control and hardware_components on May 25, 2020

@author: winfriedw
"""

import collections
from ..automation_exceptions import (
    HardwareError,
    AutofocusError,
    HardwareCommandNotDefinedError,
    LoadNotDefinedError,
    CrashDangerError,
)

from . import hardware_components

# setup logging
import logging

logger = logging


logging.basicConfig(level=logging.WARNING)
logging.debug('Switched on debug level logging in module "{}'.format(__name__))


# keep track of xPos, yPos, and zPos of stage and focus for debugging purposes
xPos = hardware_components.xPos
yPos = hardware_components.yPos
zPos = hardware_components.zPos


class BaseMicroscope(object):
    """Minimum set of attributes and methods required by Automation Software"""

    def __init__(
        self,
        name=None,
        control_software_object=None,
        experiments_folder=None,
        microscope_components=None,
    ):
        """Base class for any type of microscope
        (e.g. Spinning Disk 3i, ZEN Blue, ZEN Black)

        Input:
         name: optional string with microscope name

         controlSoftwareObject: object for software connection to microscope,
         typically created with class ControlSoftware

         experiments_folder: path to folder of microscope software defined experiments.
         Path does not include experiment

         microscope_components: optional list with component objects

        Output:
         none
        """
        hardware_components.log_method(self, "__init__")

        self.name = name

        # add control software object (only one is allowed) to Microscope
        self.add_control_software(control_software_object)

        # add components to microscope
        self.microscope_components_ordered_dict = collections.OrderedDict()
        self.add_microscope_object(microscope_components)

        # track last used experiment for test if microscope is ready
        self.experiment_folder = experiments_folder
        self.last_experiment = None

        # Track objectives that have been initialized
        self.last_objective_position = None
        self.objective_ready_dict = {}

    def not_implemented(self, method_name):
        """Raise exception if method is not implemented.

        Input:
         method_name: method that calls this method
        """
        raise HardwareCommandNotDefinedError(method_name + " is not implemented")

    def recover_hardware(self, error):
        """Execute hardwareFunction and try to recover from failure.

        Input:
         autofocusFunction: function that that interacts with microscope autofocus

         args: arguments for autofocusFunction

        Output:
         returnValue: return value from autofocusFunction

        autofocusFunction has to throw exception AutofocusError in error case
        """

        if isinstance(error, AutofocusError):
            return_dialog = error.error_dialog()
            if return_dialog == 1:
                # use ['no_find_surface'] for action_list
                # to disable 'find_surface' during auto-focus initialization
                self.initialize_hardware(
                    initialize_components_ordered_dict={
                        error.error_component.get_id(): ["no_find_surface"]
                    },
                    reference_object_id=error.focus_reference_obj_id,
                    verbose=False,
                )
            return return_dialog
        if isinstance(error, LoadNotDefinedError):
            return_dialog = error.error_dialog()
            if return_dialog == 1:
                self.initialize_hardware(
                    initialize_components_ordered_dict={
                        error.error_component.get_id(): ["set_load"]
                    },
                    reference_object_id=None,
                    verbose=False,
                )
            return return_dialog
        if isinstance(error, CrashDangerError):
            return error.error_dialog("Move stage to safe area.")
        if isinstance(error, HardwareError):
            return error.error_dialog()

    def microscope_is_ready(
        self,
        experiment,
        component_dict,
        focus_drive_id,
        objective_changer_id,
        safety_object_id,
        reference_object_id=None,
        load=True,
        make_ready=True,
        trials=3,
        verbose=True,
    ):
        """Check if microscope is ready and setup up for data acquisition.

        Input:
         experiment: string with name of experiment as defined in microscope software

         compenent_dict: dictionary with component_id as key and list of actions

         focus_drive_id: string id for focus drive

         objective_changer_id: string id for objective changer parfocality
          and parcentricity has to be calibrated

         safety_object_id: string id for safety area

         reference_object_id: ID of object used to set parfocality and parcentricity

         load: move objective into load position before moving stage

         make_ready: if True, make attempt to ready microscope, e.g. setup autofocus
         (Default: True)

         trials: maximum number of attempt to initialize microscope.
         Will allow user to make adjustments on microscope. (Default: 3)

         verbose: print debug messages (Default: True)

        Output:
         ready: True if microscope is ready for use, False if not
        """
        is_ready = {}
        # Test if com
        for component_id, action in component_dict.items():
            is_ready[component_id] = True
        is_ready["Microscope"] = all(is_ready.values())
        return is_ready

    def live_mode(self, camera_id, experiment=None, live=True):
        """Start/stop live mode of ZEN software.

        Input:
         camera_id: string id for camera

         experiment: name of ZEN experiment (default = None)

         live: switch live mode on (True = default) or off (False)

        Output:
         None
        """
        self.not_implemented("live_mode")
