"""
Classes to describe and control hardware. Bridge between automation software and
hardware specific implementations.
Created on Jul 7, 2016
Split into hardware_control and hardware_components on May 25, 2020

@author: winfriedw
"""

import collections
from . import hardware_components
from .automation_exceptions import HardwareError, CrashDangerError, \
    AutofocusError, HardwareCommandNotDefinedError, LoadNotDefinedError, \
    HardwareDoesNotExistError, AutofocusNoReferenceObjectError, AutomationError

# setup logging
import logging

logger = logging


logging.basicConfig(level=logging.WARNING)
logging.debug('Switched on debug level logging in module "{}'.format(__name__))


# keep track of xPos, yPos, and zPos of stage and focus for debugging purposes
xPos = hardware_components.xPos
yPos = hardware_components.yPos
zPos = hardware_components.zPos


#################################################################################

class BaseMicroscope(object):
    """Minimum set of attributes and methods required by Automation Software"""

    def __init__(self, name=None, control_software_object=None,
                 experiments_folder=None,
                 microscope_components=None):
        """Base class for any type of microscope
        (e.g. Spinning Disk 3i, ZEN Blue, ZEN Black)

        Input:
         name: optional string with microscope name

         control_software_object: object for software connection to microscope,
         typically created with class ControlSoftware

         experiments_folder: path to folder of microscope software defined experiments.
         Path does not include experiment

         microscope_components: optional list with component objects

        Output:
         none
        """
        hardware_components.log_method(self, '__init__')

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
        raise HardwareCommandNotDefinedError(method_name + ' is not implemented')

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
                    initialize_components_ordered_dict={error.error_component.get_id():
                                                        ['no_find_surface']},
                    reference_object_id=error.focus_reference_obj_id, verbose=False)
            return return_dialog
        if isinstance(error, LoadNotDefinedError):
            return_dialog = error.error_dialog()
            if return_dialog == 1:
                self.initialize_hardware(
                    initialize_components_ordered_dict={error.error_component.get_id():
                                                        ['set_load']},
                    reference_object_id=None, verbose=False)
            return return_dialog
        if isinstance(error, CrashDangerError):
            return error.error_dialog('Move stage to safe area.')
        if isinstance(error, HardwareError):
            return error.error_dialog()

    def add_control_software(self, controlSoftwareObject):
        """add object that connects this code to the  vendor specific microscope
        control code to Microscope.

        Input:
         controlSoftwareObject: single object connecting to vendor software

        Output:
         none
        """
        hardware_components.log_method(self, 'add_control_software')
        self.__control_software = controlSoftwareObject

    def get_control_software(self):
        """Returns object that connects this code to the  vendor specific
        microscope control code to Microscope.

        Input:
         none

        Output:
         controlSoftwareObject: single object connecting to vendor software

        """
        hardware_components.log_method(self, 'get_control_software')
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
                self.microscope_components_ordered_dict[component_object.get_id()] = \
                    component_object
                # attach microscope to tell component what microscope it belongs to
                component_object.microscope = self

    def get_microscope_object(self, component_id):
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

    def get_information(self, components_list=[]):
        """Get positions for hardware components.

        Input:
         components_list: list with names of components to retrieve positions
         Default: None = get positions for all components

        Output:
         positions_dict: dictionary {component_id: positions}. Positions are
         dictionaries if multiple positions can be retrieved
        """
        # if component_dir is None,
        # create directory for default initialization for all components
        # empty list indicates default initializations
        if not len(components_list):
            components_list = list(self.microscope_components_ordered_dict.keys())

        # create list if components_list is only a single string
        if isinstance(components_list, str):
            components_list = [components_list]
        # get communications object as link to microscope hardware
        communicatons_object = self.get_control_software().connection

        # create dictionary with positions for all components in components_list
        positions_dict = {}
        for component_id in components_list:
            component_instance = self.get_microscope_object(component_id)
            positions_dict[component_id] = component_instance.get_information(
                communicatons_object)

        return positions_dict

    def setup_microscope_for_initialization(self, component_object, experiment=None,
                                            before_initialization=True):
        """Setup microscope before initialization of individual components.
        Method starts and stops live image mode.

        Input:
         component_object: instance of component class

         experiment: Name of experiment setting in ZEN blue used for microscope
         initialization (e.g. used for live mode)

         before_initialization: if True setup microscope, if False reset

        Output:
         none
        """
        if component_object.use_live_mode:
            if experiment is None:
                experiment = component_object.get_init_experiment()
            # record status of live mode
            # to keep camera on after initialization if it was on
            if before_initialization:
                self.live_mode_status = self.get_information(components_list=[
                    component_object.default_camera])[
                    component_object.default_camera]['live']

            self.live_mode(camera_id=component_object.default_camera,
                           experiment=experiment,
                           live=before_initialization or self.live_mode_status)
            self.last_experiment = experiment

    def microscope_is_ready(self, experiment, component_dict, focus_drive_id,
                            objective_changer_id, safety_object_id,
                            reference_object_id=None, load=True, make_ready=True,
                            trials=3, verbose=True):
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
        is_ready['Microscope'] = all(is_ready.values())
        return is_ready

    def live_mode(self, camera_id, experiment=None, live=True):
        """Start/stop live mode of ZEN software.

        Input:
         camera_id: string id for camera

         experiment: name of ZEN experiment (default = None)

         live: switch live mode on (True = default) or off (False)

        Output:
         none
        """

        communication_object = self.get_control_software().connection
        camera_instance = self.get_microscope_object(camera_id)

        try:
            if live:
                camera_instance.live_mode_start(communication_object, experiment)
                self.last_experiment = experiment
                self.last_objective_position = communication_object.get_objective_position()  # noqa
            else:
                camera_instance.live_mode_stop(communication_object, experiment)
                self.last_objective_position = communication_object.get_objective_position()  # noqa
        except AutomationError as error:
            self.recover_hardware(error)

    def reference_position(self, find_surface=False, reference_object_id=None,
                           verbose=True):
        """Included for parity with ZEN Microscopes.
        Raises HardwareCommandNotDefinedError.

        Input:
         find_surface: if True auto-focus will try to find cover slip before
         operator refocuses. Default: False

         reference_object_id: ID of plate, plate holder, or other sample object
         the hardware is initialized for. Used for setting up of autofocus

         verbose: if True print debug information (Default = True)

        Output:
         none
        """
        if reference_object_id is None:
            raise AutofocusNoReferenceObjectError(
                'Reference object needed to set reference_position')

        self.not_implemented('reference_position')
