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
    HardwareDoesNotExistError,
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
        """Try to recover from failure of a hardware function

        Input:
         error: exception to recover from

        Output:
         return_dialog: value of the error dialog
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

    def goto_load(self, focus_drive_id):
        """Set focus position to load position.

        Input:
         focus_drive_id: id of focus drive to set load position on

        Output:
         z_load: load position in mum
        """
        focus_drive_object = self._get_microscope_object(focus_drive_id)
        communication_object = self._get_control_software().connection

        return focus_drive_object.goto_load(communication_object)

    def add_control_software(self, control_software_object):
        """Add object that connects this code to the  vendor specific microscope
        control code to Microscope.

        Input:
         controlSoftwareObject: single object connecting to vendor software

        Output:
         none
        """
        hardware_components.log_method(self, "add_control_software")
        self.__control_software = control_software_object

    def _get_control_software(self):
        """Returns object that connects this code to the vendor specific
         microscope control code to Microscope.

        Input:
         none

        Output:
         controlSoftwareObject: single object connecting to vendor software

        """
        hardware_components.log_method(self, "_get_control_software")
        return self.__control_software

    def add_microscope_object(self, component_objects):
        """Add component to microscope.

        Input:
         component_objects: object of a component class (e.g. Stage, Camera)
         or list of component classes

        Output:
         none
        """
        if not isinstance(component_objects, list):
            component_objects = [component_objects]

        for component_object in component_objects:
            if isinstance(component_object, hardware_components.MicroscopeComponent):
                self.microscope_components_ordered_dict[
                    component_object.get_id()
                ] = component_object
                # attach microscope to let component know to what microscope it belongs
                component_object.microscope = self

    def _get_microscope_object(self, component_id):
        """Get component of microscope.

        Input:
         component_id: Unique string id for microscope component

        Output:
         component_object: object of a component class (e.g. Stage, Camera)
         or list of component classes
        """
        # Test if component exists.
        # If component does note exist raise exeption
        if component_id not in list(self.microscope_components_ordered_dict.keys()):
            raise HardwareDoesNotExistError(error_component=component_id)
        return self.microscope_components_ordered_dict[component_id]

    def get_load_position(self, focus_drive_id):
        """Get load position of focus drive.

        Input:
         focus_drive_id: id of focus drive to get load position of

        Output:
         z_load: load position in mum
        """
        focus_drive_object = self._get_microscope_object(focus_drive_id)

        return focus_drive_object.get_load_position()

    def _get_focus_id(self, reference_object_id):
        """Set reference position in object coordinates.

        Input:
         reference_object_id: ID of plate, plate holder or other sample object
         the hardware is initialized for. Used for setting up of autofocus

        Output:
         focus_id: ID of focus drive attached to the reference object
        """
        self.not_implemented("_get_focus_id")

    def _get_safety_id(self, reference_object_id):
        """Set reference position in object coordinates.

        Input:
         reference_object_id: ID of plate, plate holder or other sample object
         the hardware is initialized for. Used for setting up of autofocus

        Output:
         safety: ID of safety attached to the reference object
        """
        self.not_implemented("_get_safety_id")

    def _get_objective_changer_id(self, reference_object_id):
        """Set reference position in object coordinates.

        Input:
         reference_object_id: ID of plate, plate holder or other sample object
         the hardware is initialized for. Used for setting up of autofocus

        Output:
         obj_changer_id: ID of objective changer attached to the reference object
        """
        self.not_implemented("_get_objective_changer_id")

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

    def recall_focus(self, auto_focus_id, reference_object_id=None, pre_set_focus=True):
        """Find difference between stored focus position and actual autofocus position.
        Recall focus will move the focus drive to it's stored position.

        Input:
         auto_focus_id: string id for camera

         reference_object_id: name of ZEN experiment (default = None)

         pre_set_focus: Move focus to previous auto-focus position.
         This makes definite focus more robust

        Output:
         delta_z: difference between stored z position of focus drive
         and position after recall focus
        """
        communication_object = self._get_control_software().connection
        autofocus = self._get_microscope_object(auto_focus_id)
        return autofocus.recall_focus(
            communication_object, reference_object_id, pre_set_focus=pre_set_focus
        )

    def trigger_pump(self, pump_id):
        """Triggers pump of pump_id.

        Raises HardwareDoesNotExistError if pump is not attached to microscope

        Input:
         pump_id: pump to trigger

        Output:
         none
        """
        communication_object = self._get_control_software().connection
        pump = self._get_microscope_object(pump_id)
        pump.trigger_pump(communication_object)

    def change_magnification(
        self,
        objective_changer_id,
        magnification,
        sample_object,
        use_safe_position=True,
        verbose=True,
        load=True,
    ):
        """Change to objective with given magnification.

        Input:
         magnification: magnification of selected objective as float.
         Not well defined if multiple objectives with identical magnification exist.

         sample_object: object that has safe coordinates attached.
         If use_safe_position == True than stage and focus drive will move to
         this position before magnification is changed to avoid collision
         between objective and stage.

         use_safe_position: move stage and focus drive to safe position before switching
         magnification to minimize risk of collision (Default: True)

         verbose: if True print debug information (Default = True)

         load: if True, move objective to load position before switching (Default: True)

        Output:
         objective_name: name of new objective
        """
        communication_object = self._get_control_software().connection
        obj_changer = self._get_microscope_object(objective_changer_id)
        objective_name = obj_changer.change_magnification(
            communication_object,
            magnification,
            sample_object,
            use_safe_position,
            verbose,
            load,
        )

        return objective_name
