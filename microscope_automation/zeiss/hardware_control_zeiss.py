"""
Classes to describe and control 3i spinning disk hardware.
Bridge between automation software and hardware specific implementations.
Created on Jul 7, 2016
Split into hardware_control and hardware_components on May 25, 2020
Split into hardware_control and hardware_control_zeiss on Sept. 22 2020

@author: fletcher.chapin
"""

import datetime
import time
import os
import collections
from .. import automation_messages_form_layout as message
from ..hardware.hardware_control import BaseMicroscope
from ..hardware import hardware_components
from . import test_zen_experiment
from . import zen_experiment_info
from ..automation_exceptions import (
    HardwareError,
    AutofocusError,
    CrashDangerError,
    LoadNotDefinedError,
    AutomationError,
    AutofocusNoReferenceObjectError,
    FileExistsError,
    HardwareNotReadyError,
)
from ..image_AICS import ImageAICS

# setup logging
import logging

logger = logging


logging.basicConfig(level=logging.WARNING)
logging.debug('Switched on debug level logging in module "{}'.format(__name__))


# keep track of xPos, yPos, and zPos of stage and focus for debugging purposes
xPos = hardware_components.xPos
yPos = hardware_components.yPos
zPos = hardware_components.zPos


class SpinningDiskZeiss(BaseMicroscope):
    """Collection class to describe and operate Zeiss spinning disk microscope"""

    def __init__(
        self,
        name=None,
        control_software_object=None,
        experiments_folder=None,
        safeties=None,
        microscope_components=None,
    ):
        """Describe and operate Microscope

        Input:
         name: optional string with microscope name

         control_software_object: object for software connection to microscope,
         typically created with class ControlSoftware

         experiments_folder: path to folder of microscope software defined experiments.
         Path does not include experiment.

         safeties: optional list with safety objects

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
        self.add_microscope_object(safeties)
        self.add_microscope_object(microscope_components)

        # track last used experiment for test if microscope is ready
        self.experiment_folder = experiments_folder
        self.last_experiment = None
        # Use objective position because objectives are named differently
        # inside ZEN software and experiment files.
        # A call like objRevolver.ActualPositionName returns the objective name.
        # In the experiment files objectives are identified by their order number.
        # Position would allow identical objectives at different positions
        self.last_objective_position = None
        self.objective_ready_dict = {}

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

    def create_experiment_path(self, experiment):
        """Creates complete path to experiment (Zen) or capture settings (Slidebook).
        Raises exception if experiment does not exist.

        Input:
         experiment: string with name of experiment or capture settings
         (with or w/o extension .czexp or .exp.prefs)

        Output:
         experiment_path: path to experiment or capture settings
        """
        # get communications object as link to microscope hardware
        communicatons_object = self._get_control_software().connection
        experiment_path = communicatons_object.create_experiment_path(
            experiment, self.experiment_folder
        )
        # For Zen Black implementation, there is no experiment path, hence left as "NA"
        # self._get_control_software()
        # if self.experiment_path == 'NA':
        #     return self.experiment_path
        # # check if experiment has proper extension
        # extension = os.path.splitext(experiment)[1]
        # if extension != '.czexp':
        #     experiment = experiment + '.czexp'
        # experiment_path = os.path.normpath(os.path.join(self.experiment_path,
        #                                                 experiment))
        # if not os.path.exists(experiment_path):
        #     raise ExperimentNotExistError(
        #         'Could not create experiment path {}.'.format(
        #             experiment_path), experiment)
        return experiment_path

    def set_objective_is_ready(self, objective_info, reference_object_id=None):
        """Create list with all objective positions initialized for reference_object.

        Input:
         objective_info: information for objective that was initialized

         reference_object_id: ID of reference object (e.g. well)
         which objective was initialized for

        Output:
         none
        """
        # Each dictionary entry is a set of objective positions
        # create set if dictionary is empty, otherwise add new position,
        # if position is already set, nothing will change
        if self.objective_ready_dict:
            self.objective_ready_dict[reference_object_id].add(
                objective_info["position"]
            )
        else:
            objective_positions = set()
            objective_positions.add(objective_info["position"])
            self.objective_ready_dict[reference_object_id] = objective_positions

    def get_objective_is_ready(self, objective_position, reference_object_id=None):
        """Test if objective was initialized.

        Input:
         objective_position: position of objective in objective changer

         reference_object_id: ID of reference object (e.g. well)
         which objective was initialized for

        Output:
         objective_is_ready: True, if offset for objective was set
        """
        try:
            objective_is_ready = (
                objective_position in self.objective_ready_dict[reference_object_id]
            )
            return objective_is_ready
        except KeyError:
            return False

    def change_objective(self, experiment, objective_changer_object, trials=3):
        """Switch to objective used in experiment.

        Input:
         experiment: string with name of experiment as defined in microscope software

         objective_changer_object: object for objective changer objective is mounted to

         trials: number of times system tries to recover

        Output:
         objective_name: name of objective in new position
        """
        experiment_path = self.create_experiment_path(experiment)
        experiment_object = hardware_components.Experiment(
            experiment_path, experiment, microscope_object=self
        )
        communication_object = self._get_control_software().connection

        try:
            experiment_objective_pos = experiment_object.get_objective_position()
        except Exception as e:
            print(("Could not find objective for experiment {}".format(experiment)))
            raise e

        trials_count = trials
        success = False
        load = True
        while not success and trials_count >= 0:
            try:
                objective_name = objective_changer_object.change_position(
                    experiment_objective_pos, communication_object, load=load
                )
                success = True
            except LoadNotDefinedError as error:
                if self.recover_hardware(error) == -1:
                    load = False
                if trials_count == 0:
                    raise (error)
            except AutomationError as error:
                self.recover_hardware(error)
                if trials_count == 0:
                    raise (error)
            trials_count = trials_count - 1
        return objective_name

    def _make_ready(
        self,
        is_ready,
        make_ready,
        component_id,
        action_list=[],
        reference_object_id=None,
        trials=3,
        verbose=True,
    ):
        """Check if component is ready and initialize if requested.

        Input:
         is_ready: Flag if component is initialized

         make_ready: if True, initialize component if not ready

         component_id: string id for component to initialize

         action_list: list with component specific instructions for initialization

         reference_object_id: object used to set parfocality and parcentricity

         trials: maximum number of attempts to initialize hardware.
         Gives user the option to interact with microscope hardware.

         verbose: if True print debug information (Default = True)

        Output:
         is_ready: True if initialization was sucessful
        """
        if not is_ready and make_ready:
            try:
                initialize_components_ordered_dict = {component_id: action_list}
                self.initialize_hardware(
                    initialize_components_ordered_dict,
                    reference_object_id,
                    trials,
                    verbose,
                )
                return True
            except Exception:
                return False
        else:
            return True

    def _focus_drive_is_ready(
        self,
        focus_drive_object,
        action_list,
        reference_object_id=None,
        trials=3,
        make_ready=True,
        verbose=True,
    ):
        """Test if focus drive is ready and optionally initialize it

        Input:
         focus_drive_object: object of class AutoFocus

         action_list: list with component specific instructions for initialization

         reference_object_id: ID of object used to set parfocality and parcentricity

         trials: maximum number of attempts to initialize hardware.
         Gives user the option to interact with microscope hardware.

         make_ready: if True, make attempt to initialize auto-focus if necessary
         (Default: True)

         verbose: if True print debug information (Default = True)

        Output:
         is_ready: True if ready
        """
        # test if object is of class FocusDrive
        if type(focus_drive_object) is not hardware_components.FocusDrive:
            raise TypeError("Object not of type FocusDrive in _focus_is_ready")

        focus_drive_id = focus_drive_object.get_id()
        focus_drive_info = self.get_information([focus_drive_id])[focus_drive_id]

        is_ready = True

        if "set_load" in action_list:
            is_ready = focus_drive_info["load_position"] is not None

        if "set_work" in action_list:
            is_ready = focus_drive_info["work_position"] is not None and is_ready

        # Initialize objective changer
        is_ready = self._make_ready(
            is_ready,
            make_ready,
            focus_drive_id,
            action_list=action_list,
            reference_object_id=reference_object_id,
            trials=trials,
            verbose=verbose,
        )
        return is_ready

    def _objective_changer_is_ready(
        self,
        objective_changer_object,
        objective_position,
        action_list=[],
        reference_object_id=None,
        trials=3,
        make_ready=True,
        verbose=True,
    ):
        """Test if objective changer is ready and optionally initialize it

        Input:
         objective_changer_object: object of class ObjectiveChanger

         objective_position: position of objective that will be used for experiment

         action_list: list with item 'set_reference'. If empty no action.

         reference_object_id: ID of object used to set parfocality and parcentricity

         trials: maximum number of attempts to initialize hardware.
         Gives user the option to interact with microscope hardware.

         make_ready: if True, make attempt to initialize auto-focus if necessary
         (Default: True)

         verbose: if True print debug information (Default = True)

        Output:
         is_ready: True if ready
        """
        # test if object is of class ObjectiveChanger
        if type(objective_changer_object) is not hardware_components.ObjectiveChanger:
            raise TypeError(
                "Object not of type ObjectiveChanger in _objective_changer_is_ready"
            )

        # test if stage position is in safe area
        objective_changer_object_id = objective_changer_object.get_id()

        is_ready = self.get_objective_is_ready(
            objective_position, reference_object_id=reference_object_id
        )

        # Initialize objective changer
        is_ready = self._make_ready(
            is_ready,
            make_ready,
            objective_changer_object_id,
            action_list=action_list,
            reference_object_id=reference_object_id,
            trials=trials,
            verbose=verbose,
        )
        return is_ready

    def _stage_is_ready(
        self,
        stage_object,
        focus_object,
        safety_object,
        reference_object_id=None,
        trials=3,
        make_ready=True,
        verbose=True,
    ):
        """Test if stage is ready and optionally initialize it

        Input:
         stage_object: object of class Stage

         focus_object: object of class FocusDrive

         safety_object: object of class Safety

         reference_object_id: ID of object used to set parfocality and parcentricity

         trials: maximum number of attempts to initialize hardware.
         Gives user the option to interact with microscope hardware.

         make_ready: if True, make attempt to initialize auto-focus if necessary
         (Default: True)

         verbose: if True print debug information (Default = True)

        Output:
         is_ready: True if ready
        """
        # test if object is of class Stage
        if type(stage_object) is not hardware_components.Stage:
            raise TypeError("Object not of type Stage in _stage_is_ready")

        # test if stage position is in safe area
        stage_id = stage_object.get_id()
        focus_id = focus_object.get_id()

        x, y = self.get_information([stage_id])[stage_id]["absolute"]
        z = self.get_information([focus_id])[focus_id]["absolute"]
        is_ready = safety_object.is_safe_position(x, y, z, safe_area_id="Compound")

        # Initialize auto-focus
        is_ready = self._make_ready(
            is_ready,
            make_ready,
            stage_id,
            action_list=[],
            reference_object_id=reference_object_id,
            trials=trials,
            verbose=verbose,
        )
        return is_ready

    def _auto_focus_is_ready(
        self,
        auto_focus_object,
        experiment_object,
        action_list,
        objective_changer_object,
        reference_object_id=None,
        load=True,
        trials=3,
        make_ready=True,
        verbose=True,
    ):
        """Test if auto-focus is ready and optionally initialize it

        Input:
         auto_focus_object: object of class AutoFocus

         experiment_object: object of type experiment to test

         action_list: list with component specific instructions for initialization

         objective_changer_object: object of class ObjectiveChanger

         reference_object_id: ID of object used to set parfocality and parcentricity

         load: if True, move objective to load position before any stage movement

         trials: maximum number of attempts to initialize hardware.
         Gives user the option to interact with microscope hardware.

         make_ready: if True, make attempt to initialize auto-focus if necessary
         (Default: True)

         verbose: if True print debug information (Default = True)

        Output:
         is_ready: True if ready
        """
        is_ready = True
        if action_list:
            # test if object is of class AutoFocus
            if type(auto_focus_object) is not hardware_components.AutoFocus:
                raise TypeError("Object not of type AutoFocus in _auto_focus_is_ready")

            # find objective position that will be used for experiment
            try:
                objective_position = experiment_object.get_objective_position()
            except Exception:
                print(
                    (
                        "Could not find objective for experiment {}".format(
                            experiment_object.experiment_name
                        )
                    )
                )
                raise

            # if objective will be changed auto-focus has to be set new
            if objective_position != self.last_objective_position:
                is_ready = False

            # check if auto-focus hardware is ready, e.g. autofocus was set
            if not auto_focus_object.get_autofocus_ready(
                communication_object=self._get_control_software().connection
            ):
                is_ready = False

            # Initialize auto-focus
            if not is_ready and make_ready:
                communication_object = self._get_control_software().connection
                if objective_position != self.last_objective_position:
                    try:
                        objective_changer_object.change_position(
                            position=objective_position,
                            communication_object=communication_object,
                            load=load,
                        )
                    except Exception:
                        return False
                try:
                    initialize_components_ordered_dict = {
                        auto_focus_object.get_id(): action_list
                    }
                    self.initialize_hardware(
                        initialize_components_ordered_dict,
                        reference_object_id,
                        trials,
                        verbose,
                    )
                    is_ready = True
                except Exception:
                    return False
        return is_ready

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

         compenent_dict: dictionary with component_id as key and list actions

         focus_drive_id: string id for focus drive

         objective_changer_id: string id for objective changer parfocality
         and parcentricity has to be calibrated

         safety_object_id: string id for safety area

         reference_object_id: ID object used to set parfocality and parcentricity

         load: move objective into load position before moving stage

         make_ready: if True, make attempt to ready microscope, e.g. setup autofocus
         (Default: True)

         trials: maximum number of attempt to initialize microscope.
         Will allow user to make adjustments on microscope. (Default: 3)

         verbose: print debug messages (Default: True)

        Output:
         is_ready: dictionary of all components that are ready
        """
        # find objective position that will be used for experiment
        experiment_path = self.create_experiment_path(experiment)
        experiment_object = hardware_components.Experiment(
            experiment_path, experiment, self
        )

        try:
            objective_position = experiment_object.get_objective_position()
        except Exception as e:
            print(("Could not find objective for experiment {}".format(experiment)))
            raise e

        # get objects for components that are used for initializations
        focus_object = self._get_microscope_object(focus_drive_id)
        objective_changer_object = self._get_microscope_object(objective_changer_id)
        safety_object = self._get_microscope_object(safety_object_id)
        current_init_experiment_dict = {}
        communication_object = self._get_control_software().connection

        # Set the initialize experiments to the experiment being executed.
        # Reason for doing them in a separate loop -
        # To make sure that all the init _experiments are set  before the components
        # are initialized individually. In some cases the components are intialized
        # indirectly through other components(eg. DF can be initialized in
        # objectiveChanger if it fails and goes to recovery).
        # In that case the component should have the correct init_experiment.
        for component_id, action in component_dict.items():
            component = self._get_microscope_object(component_id)
            # Save the original init_experiments
            # restore them after the specific initialization is done
            current_init_experiment_dict[component_id] = component.get_init_experiment(
                communication_object
            )
            self._get_microscope_object(component_id).set_init_experiment(experiment)

        is_ready = {}
        for component_id, action in component_dict.items():
            component = self._get_microscope_object(component_id)

            # use type and not isinstance because we want to exclude subclasses
            if type(component) is hardware_components.Stage:
                if self._stage_is_ready(
                    stage_object=component,
                    focus_object=focus_object,
                    safety_object=safety_object,
                    reference_object_id=reference_object_id,
                    trials=trials,
                    make_ready=make_ready,
                    verbose=verbose,
                ):
                    is_ready[component_id] = True
                else:
                    is_ready[component_id] = False

            if type(component) is hardware_components.ObjectiveChanger:
                if self._objective_changer_is_ready(
                    objective_changer_object=component,
                    objective_position=objective_position,
                    action_list=action,
                    reference_object_id=reference_object_id,
                    trials=trials,
                    make_ready=make_ready,
                    verbose=verbose,
                ):
                    is_ready[component_id] = True
                else:
                    is_ready[component_id] = False

            if type(component) is hardware_components.FocusDrive:
                if self._focus_drive_is_ready(
                    focus_drive_object=component,
                    action_list=action,
                    reference_object_id=reference_object_id,
                    trials=trials,
                    make_ready=make_ready,
                    verbose=verbose,
                ):
                    is_ready[component_id] = True
                else:
                    is_ready[component_id] = False

            if type(component) is hardware_components.AutoFocus:
                if self._auto_focus_is_ready(
                    auto_focus_object=component,
                    experiment_object=experiment_object,
                    action_list=action,
                    objective_changer_object=objective_changer_object,
                    reference_object_id=reference_object_id,
                    load=load,
                    trials=trials,
                    make_ready=make_ready,
                    verbose=verbose,
                ):
                    is_ready[component_id] = True
                else:
                    is_ready[component_id] = False

            # set experiment for initializations back to initial experiment
            component.set_init_experiment(current_init_experiment_dict[component_id])
        is_ready["Microscope"] = all(is_ready.values())
        return is_ready

    def stop_microscope(self):
        """Stop Microscope immediately in emergency situation"""
        hardware_components.log_method(self, "stop_microscope")

        self._get_control_software().connection.stop()

        logger.info("Microscope stopped")

    def setup_microscope_for_initialization(
        self, component_object, experiment=None, before_initialization=True
    ):
        """Setup microscope before initialization of individual components.
        Method starts and stops live image mode.

        Input:
         component_object: instance of component class

         experiment: Name of experiment setting in ZEN blue used
         for microscope initialization (e.g. used for live mode)

         before_initialization: if True setup microscope, if False reset

        Output:
         None
        """
        if component_object.use_live_mode:
            if experiment is None:
                experiment = component_object.get_init_experiment()
            # save live mode status to keep camera on post-initialization if it was on
            if before_initialization:
                self.live_mode_status = self.get_information(
                    components_list=[component_object.default_camera]
                )[component_object.default_camera]["live"]

            self.live_mode(
                camera_id=component_object.default_camera,
                experiment=experiment,
                live=before_initialization or self.live_mode_status,
            )
            self.last_experiment = experiment

    def initialize_hardware(
        self,
        initialize_components_ordered_dict=None,
        reference_object_id=None,
        trials=3,
        verbose=True,
    ):
        """Initialize all hardware components.

        Input:
         initialize_components_ordered_dict: directory with names of components
         to initialize and list of initialization steps.
         Default: None = initialize all components in order as assigned
         to microscope object

         reference_object_id: Used for setting up of autofocus

         trials: number of trials before initialization is aborted

         verbose: if True print debug information (Default = True)

        Output:
         none
        """
        # create directory for default initialization for all components
        # if component_dir is None. empty dictionary indicates default initializations
        if initialize_components_ordered_dict is None:
            component_names = list(self.microscope_components_ordered_dict.keys())
            initialize_components_ordered_dict = collections.OrderedDict(
                (name, []) for name in component_names
            )

        # get communications object as link to microscope hardware
        communicatons_object = self._get_control_software().connection
        # initialize all components
        # if a component has no initialize method,
        # it is handed to default method of super class MicroscopeComponent
        for component_id, action_list in initialize_components_ordered_dict.items():
            component_object = self._get_microscope_object(component_id)
            trials_count = trials
            while trials_count > 0:
                try:
                    trials_count = trials_count - 1
                    component_object.initialize(
                        communicatons_object,
                        action_list,
                        reference_object_id=reference_object_id,
                        verbose=verbose,
                    )
                except AutofocusNoReferenceObjectError:
                    raise
                except HardwareError as error:
                    if trials_count > 0:
                        result = error.error_dialog()
                        if result == -1:
                            trials_count = 0
                    else:
                        raise HardwareError(
                            "Component {} not initialized.".format(component_id)
                        )
                else:
                    trials_count = 0

    def set_microscope(self, settings_dict={}):
        """Set status flags for microscope.

        Input:
         settings_dict: dictionary {component_id: {settings}}
                         supported flags:
                          autofocus_id: {use_auto_focus: True/False}

        Output:
         new_settings_dict: return all current settings
        """
        new_settings_dict = {}
        for component_id, settings in settings_dict.items():
            component_object = self._get_microscope_object(component_id)
            settings = component_object.set_component(settings)
            new_settings_dict[component_id] = settings
        return new_settings_dict

    def get_information(self, components_list=[]):
        """Get positions for hardware components.

        Input:
         components_list: list with names of components to retrieve positions
         Default: None = get positions for all components

        Output:
         positions_dict: dictionary {component_id: positions}.
         Positions are dictionaries if multiple positions can be retrieved
        """
        # create directory for default initialization for all components
        # if component_dir is None. empty list indicates default initializations
        if not len(components_list):
            components_list = list(self.microscope_components_ordered_dict.keys())

        # create list if components_list is only a single string
        if isinstance(components_list, str):
            components_list = [components_list]
        # get communications object as link to microscope hardware
        communicatons_object = self._get_control_software().connection

        # create dictionary with positions for all components in components_list
        positions_dict = {}
        for component_id in components_list:
            component_instance = self._get_microscope_object(component_id)
            positions_dict[component_id] = component_instance.get_information(
                communicatons_object
            )

        return positions_dict

    def get_z_position(
        self,
        focus_drive_id=None,
        auto_focus_id=None,
        force_recall_focus=False,
        trials=3,
        reference_object_id=None,
        verbose=True,
    ):
        """Get current position of focus drive.

        Input:
         focus_drive_id: string id for focus drive to get the position for

         auto_focus_id: string id for auto focus to use (None: do not use auto-focus)

         force_recall_focus: if True, recall focus, otherwise use old values.
         Default: False

         trials: number of trials to retrieve z position before procedure is aborted

         reference_object_id: ID of object of Sample class used to correct for xyz
         offset between different objectives

         verbose: if True, print debug messages (Default: False)

        Output:
         positions_dict: dictionary {component_id: positions}.
                          positions are dictionaries with

                           'absolute': absolute position of focus drive as shown
                           in software

                           'z_focus_offset': parfocality offset

                           'focality_corrected': absolute focus position -
                           z_focus_offset

                           'auto_focus_offset': change in autofocus position

                           'focality_drift_corrected': focality_corrected position -
                           auto_focus_offset

                           'load_position': load position of focus drive

                           'work_position': work position of focus drive

                          with focus positions in um
        """
        # get communications object as link to microscope hardware
        communications_object = self._get_control_software().connection
        focus_drive_instance = self._get_microscope_object(focus_drive_id)
        z_positions = focus_drive_instance.get_information(communications_object)
        return z_positions

    def _get_reference_position(self, reference_object_id):
        """Set reference position in object coordinates.

        Input:
         reference_object_id: ID of plate, plate holder or other sample object
         the hardware is initialized for. Used for setting up of autofocus

        Output:
         x, y, z: position of reference structure in object coordinates
        """
        self.not_implemented("_get_reference_position")

    def _set_reference_position(
        self, reference_object_id, find_surface=False, verbose=True
    ):
        """Set reference position in object coordinates.

        Input:
         reference_object_id: ID of plate, plate holder or other sample object
         the hardware is initialized for. Used for setting up of autofocus

         find_surface: if True use find surface of definite focus

         verbose: if True print debug information (Default = True)

        Output:
         objective_info: information for objective that was used to update offset
        """
        self.not_implemented("_set_reference_position")
        # TODO: recreate following logic once Samples API is written

        # auto_focus_object = self._get_microscope_object(
        #     reference_object.get_auto_focus_id())
        # communication_object = self._get_control_software().connection
        #
        # reference_object.move_to_zero(load=False, verbose=verbose)
        #
        # if find_surface:
        #     auto_focus_object.find_surface(communication_object)
        #
        # message.operate_message(
        #     message='Please move to and focus on reference position.',
        #     return_code=False)
        # #    _z_abs = auto_focus_object.store_focus(
        # #        communication_object, focus_reference_obj=reference_object)
        #
        # x_reference, y_reference, z_reference = reference_object.get_pos_from_abs_pos(
        #     verbose=verbose)
        # # retrieve information for actual objective
        # objective_changer_object = self._get_microscope_object(
        #     reference_object.get_objective_changer_id())
        # objective_info = objective_changer_object.get_information(
        #     communication_object)
        #
        # reference_object.set_reference_position(x_reference, y_reference, z_reference)
        # print('Store new reference position in reference object coordinates: {}, {}, {}'.format(x_reference,  # noqa
        #                                                                                         y_reference,  # noqa
        #                                                                                         z_reference))  # noqa
        # return objective_info

    def _update_objective_offset(
        self, reference_object_id, find_surface=False, verbose=True
    ):
        """Find reference position and update offset for objective.

        Input:
         communication_object: Object that connects to microscope specific software

         reference_object_id: plate, plate holder or other sample object
         the hardware is initialized for. Used for setting up of autofocus

         find_surface: if True use find surface of definite focus

         verbose: if True print debug information (Default = True)

        Output:
         objective_info: information for objective that was used to update offset
        """
        self.not_implemented("_update_objective_offset")
        # TODO: recreate following logic once Samples API is written

        # move to position that was used to define reference positions
        # to calculate par-focality and par-centricity
        # if auto-focus was on, switch off autofocus
        # auto_focus_object = self._get_microscope_object(
        #     reference_object.get_auto_focus_id())
        # objective_changer_object = self._get_microscope_object(
        #     reference_object.get_objective_changer_id())
        # communication_object = self._get_control_software().connection
        #
        # auto_focus_status = auto_focus_object.use_autofocus
        # auto_focus_object.set_use_autofocus(False)
        #
        # x_reference, y_reference, z_reference = reference_object.get_reference_position()  # noqa
        # print('Reference position in reference object coordinates before adjustments: {}, {}, {}'.format(x_reference,  # noqa
        #                                                                                                  y_reference,  # noqa
        #                                                                                                  z_reference))  # noqa
        #
        # # when moving to reference position with new objective,
        # # Microscope.move_to_abs_pos() takes objective into account
        # reference_object.move_to_xyz(x=x_reference,
        #                              y=y_reference,
        #                              z=z_reference,
        #                              load=False, verbose=verbose)
        #
        # if find_surface:
        #     self.find_surface(communication_object)
        #
        # message.operate_message(
        #     message='Please move to and focus on reference position.',
        #     return_code=False)

        # get new position for reference in object coordinates and check if it changed.
        # This new position is already corrected with current objective offset
        # new_x_reference, new_y_reference, new_z_reference = \
        #     reference_object.get_pos_from_abs_pos(verbose=verbose)
        # print('New reference position in reference coordinates: {}, {}, {}'.format(
        #     new_x_reference, new_y_reference, new_z_reference))
        #
        # # retrieve information for actual objective
        # objective_info = objective_changer_object.get_information(
        #     communication_object)
        #
        # x_delta = new_x_reference - x_reference
        # y_delta = new_y_reference - y_reference
        # z_delta = new_z_reference - z_reference
        #
        # if abs(x_delta) + abs(y_delta) + abs(z_delta) > 0:
        #     # update offset for objective
        #     offset = objective_changer_object.get_objective_information(
        #         communication_object)
        #     x_offset = x_delta + offset['x_offset']
        #     y_offset = y_delta + offset['y_offset']
        #     z_offset = z_delta + offset['z_offset']
        #
        #     # update objective offset for current objective with new offset
        #     objective_changer_object.update_objective_offset(communication_object,
        #                                                      x_offset, y_offset,
        #                                                      z_offset,
        #                                                      objective_name=None)
        #     print('New offset: {}, {}, {}'.format(x_offset, y_offset, z_offset))
        # auto_focus_object.set_use_autofocus(auto_focus_status)
        #
        # return objective_info

    def reference_position(
        self, find_surface=False, reference_object_id=None, verbose=True
    ):
        """Initialize and update reference position to correct for xyz offset
        between different objectives.

        Input:
         find_surface: if True auto-focus will try to find cover slip
         before operator refocuses. Default: False

         reference_object_id: ID of plate, plate holder, or other sample object
          the hardware is initialized for. Used for setting up of autofocus

         verbose: if True print debug information (Default = True)

        Output:
         none
        """
        if reference_object_id is None:
            raise AutofocusNoReferenceObjectError(
                "Reference object needed to set reference_position"
            )

        # make sure that proper objective is in place
        # and all relevant components are initialized
        communication_object = self._get_control_software().connection
        objective_changer_id = self._get_objective_changer_id(reference_object_id)
        objective_changer_object = self._get_microscope_object(objective_changer_id)

        # Make sure that objective is in place and not still moving
        experiment = objective_changer_object.get_init_experiment()
        experiment_path = self.create_experiment_path(experiment)
        experiment_object = zen_experiment_info.ZenExperiment(
            experiment_path, experiment
        )
        objective_changer_object.get_objective_information(communication_object)

        counter = 0
        while (
            experiment_object.get_objective_position()
            != objective_changer_object.get_information(communication_object)[
                "position"
            ]
        ):
            # wait one second
            time.sleep(1)

            counter = counter + 1
            if counter == 5:
                raise HardwareNotReadyError(
                    message="Objective not ready for experiment {}.".format(
                        objective_changer_object.get_init_experiment()
                    ),
                    error_component=objective_changer_object,
                )

        # if reference position is not set, set it,
        # otherwise use stored reference position and correct for offset.
        x, y, z = self._get_reference_position(reference_object_id)
        if x is None or y is None or z is None:
            # reference position was never defined
            objective_info = self._set_reference_position(
                reference_object_id, find_surface=find_surface, verbose=verbose
            )
        else:
            objective_info = self._update_objective_offset(
                reference_object_id, find_surface=find_surface, verbose=verbose
            )
        self.set_objective_is_ready(objective_info, reference_object_id)

    def move_to_abs_pos(
        self,
        stage_id=None,
        focus_drive_id=None,
        objective_changer_id=None,
        auto_focus_id=None,
        safety_id=None,
        safe_area="Compound",
        x_target=None,
        y_target=None,
        z_target=None,
        z_focus_preset=None,
        reference_object_id=None,
        load=True,
        trials=3,
        verbose=False,
    ):
        """Move stage and focus drive to position (x, y, z)
        in absolute system coordinates.

        Input:
         stage_id, focus_drive_id: strings to identify stage and focus drive

         objective_changer_id: string to identify objective changer

         safety_id: string to identify safety object

         safe_area: name of safe area withing safety object
         (default: 'compound' = combine all areas)

         x_target, y_target: coordinates of stage after movement
         (none = do not move stage)

         z_target: coordinate for focus position after movement
         (none = do not move focus, but engage auto-focus)

         z_focus_preset: z position for focus before focus recall to make
         autofocus more reliable (Default: None, do not use feature)

         reference_object_id: ID of object of type sample (ImagingSystem).
         Used to correct for xyz offset between different objectives

         load: Move focus in load position before move. Default: True

         trials: number of trials to retrieve z position before procedure is aborted

        Ouput:
         x_final, y_final, z_final: coordinates after move
        """
        hardware_components.log_method(self, "move_to_abs_pos")

        # retrieve stage, focus, objective changer, and safety objects
        focus_drive_object = self._get_microscope_object(focus_drive_id)
        objective_changer_object = self._get_microscope_object(objective_changer_id)
        auto_focus_object = self._get_microscope_object(auto_focus_id)
        stage_object = self._get_microscope_object(stage_id)
        safety_object = self._get_microscope_object(safety_id)
        communication_object = self._get_control_software().connection

        # retrieve current positions for travel path calculation
        # in case they will stay the same
        stage_info = stage_object.get_information(communication_object)
        x_current, y_current = stage_info["centricity_corrected"]
        focus_drive_info = focus_drive_object.get_information(communication_object)
        z_current = focus_drive_info["focality_corrected"]

        if x_target is None:
            x_target = x_current
        if y_target is None:
            y_target = y_current
        if z_target is None:
            z_target = z_current

        # set final positions that will be returned to current positions
        # in case stage or focus do not move
        x_final, y_final, z_final = x_current, y_current, z_current

        trials_count = trials
        success = False
        while not success:
            # adjust target positions for mechanical offset between different objectives
            # add offset within loop to use updated offset in case objective was swapped
            offset = objective_changer_object.get_objective_information(
                communication_object
            )
            x_target_offset = x_target + offset["x_offset"]
            y_target_offset = y_target + offset["y_offset"]
            z_target_offset = z_target + offset["z_offset"]
            z_target_delta = None
            try:
                # check if stage and objective can safely move
                # from current position to new target positions
                xy_path = stage_object.move_to_position(
                    communication_object, x_target_offset, y_target_offset, test=True
                )
                if load:
                    z_max_pos = focus_drive_object.z_load
                else:
                    z_max_pos = max([focus_drive_info["absolute"], z_target_offset])
                if safety_object.is_safe_move_from_to(
                    safe_area,
                    xy_path,
                    z_max_pos,
                    x_current=stage_info["absolute"][0],
                    y_current=stage_info["absolute"][1],
                    z_current=focus_drive_info["absolute"],
                    x_target=x_target_offset,
                    y_target=y_target_offset,
                    z_target=z_target_offset,
                    verbose=verbose,
                ):
                    if load:
                        z_final = focus_drive_object.goto_load(communication_object)
                    x_final, y_final = stage_object.move_to_position(
                        communication_object,
                        x_target_offset,
                        y_target_offset,
                        test=False,
                    )

                    # check if autofocus position has changed
                    # and update z_target if necessary
                    # move focus close to correct position.
                    # This will make autofocus more reliable.
                    if z_focus_preset:
                        focus_drive_object.move_to_position(
                            communication_object, z_focus_preset
                        )
                    else:
                        focus_drive_object.move_to_position(
                            communication_object, z_target_offset
                        )
                    # pre_set_focus = False prevents system from moving
                    # to last focus position before recalling
                    deltaZ = auto_focus_object.recall_focus(
                        communication_object,
                        reference_object_id,
                        verbose=verbose,
                        pre_set_focus=False,
                    )
                    if deltaZ is not None:
                        z_target_delta = z_target_offset + deltaZ
                    else:
                        z_target_delta = z_target_offset
                    z_final = focus_drive_object.move_to_position(
                        communication_object, z_target_delta
                    )
                else:
                    safety_object.show_safe_areas(path=xy_path)
                    raise CrashDangerError(
                        "Danger of hardware crash detected when attempting to move stage from ({}, {}, {}) to ({}, {}, {})".format(  # noqa
                            stage_info["absolute"][0],
                            stage_info["absolute"][1],
                            focus_drive_info["absolute"],
                            x_target_offset,
                            y_target_offset,
                            z_target_offset,
                        )
                    )
                success = True
            except AutomationError as error:
                trials_count = trials_count - 1
                if trials_count > 0:

                    result = self.recover_hardware(error)
                    if result == -1:
                        success = True
                else:
                    raise
        return x_final, y_final, z_final

    def run_macro(self, macro_name=None, macro_param=None):
        """Function to run a given Macro in the Zen Software

        Input:
         macro_name: Name of the Macro

        Output:
         none
        """
        communication_object = self._get_control_software().connection
        communication_object.run_macro(macro_name, macro_param)

    def execute_experiment(
        self, experiment=None, file_path=None, z_start="C", interactive=False
    ):
        """Trigger microscope to execute experiment defined within vendor software.
        Class ImageAICS is a container for meta and image data.
        To add image data use method load_image.
        Do not try to recover from exceptions on this level.

        Input:
         experiment: string with name of experiment defined within Microscope software.
         If None use actual experiment.

         file_path: string with path to save image do not save if None (default)

         z_start: define where to start z-stack
         ('F'= first slice, 'C' = center, 'L' = last slice). Default: 'F'

         interactive: if True, allow user to modify file name if file exists

        Output:
         image: image of class ImageAICS to hold metadata.
         Does not contain image data at this moment.
        """
        hardware_components.log_method(self, "execute_experiment")
        # call execute_experiment method in ConnectMicroscope instance.
        # This instance will be based on a microscope specific connect module.
        timeStart = datetime.datetime.now()

        communication_object = self._get_control_software().connection

        # adjust position for z-stack and tile scan
        # ZEN acquires z-stack with center of current positions
        experiment_object = hardware_components.Experiment(
            self.create_experiment_path(experiment), experiment, self
        )
        if experiment_object.is_z_stack():
            if not test_zen_experiment.test_FocusSetup(experiment_object, verbose=True):
                print("Focus setup not valid")
            z_stack_range = experiment_object.z_stack_range() * 1e6
            if z_start == "F":
                communication_object.z_up_relative(z_stack_range / 2)
            if z_start == "L":
                communication_object.z_down_relative(z_stack_range / 2)

        if experiment_object.is_tile_scan():
            # use current position and set as center of tile_scan
            x, y = communication_object.get_stage_pos()
            z = communication_object.get_focus_pos()
            experiment_object.update_tile_positions(x, y, z)
            # force reload experiment so that the changes are reflected in Zen Software
            communication_object.close_experiment(experiment)

        try:
            communication_object.execute_experiment(experiment)
            self.last_experiment = experiment
            self.last_objective_position = communication_object.get_objective_position()
        except AutomationError as error:
            self.recover_hardware(error)

        timeEnd = datetime.datetime.now()

        image = ImageAICS(meta={"aics_Experiment": experiment})
        #         image.add_meta(self.settings)

        # add meta data about acquisition time
        timeDuration = (timeEnd - timeStart).total_seconds()
        image.add_meta(
            {
                "aics_dateStartShort": timeStart.strftime("%Y%m%d"),
                "aics_dateEndShort": timeEnd.strftime("%Y%m%d"),
                "aics_dateStart": timeStart.strftime("%m/%d/%Y"),
                "aics_dateEnd": timeEnd.strftime("%m/%d/%Y"),
                "aics_timeStart": timeStart.strftime("%H:%M:%S"),
                "aics_timeEnd": timeEnd.strftime("%H:%M:%S"),
                "aics_timeDuration": timeDuration,
            }
        )

        # save image
        if file_path:
            image = self.save_image(file_path, image, interactive=interactive)

        return image

    def live_mode(self, camera_id, experiment=None, live=True):
        """Start/stop live mode of ZEN software.

        Input:
         camera_id: string id for camera

         experiment: name of ZEN experiment (default = None)

         live: switch live mode on (True = default) or off (False)

        Output:
         none
        """

        communication_object = self._get_control_software().connection
        camera_instance = self._get_microscope_object(camera_id)

        try:
            if live:
                camera_instance.live_mode_start(communication_object, experiment)
                self.last_experiment = experiment
                self.last_objective_position = (
                    communication_object.get_objective_position()
                )
            else:
                camera_instance.live_mode_stop(communication_object, experiment)
                self.last_objective_position = (
                    communication_object.get_objective_position()
                )
        except AutomationError as error:
            self.recover_hardware(error)

    def save_image(self, file_path, image, interactive=False):
        """Save last Microscope ImageAICS taken from within Microscope software.
        Methods adds file_path to meta data.

        Input:
         file_path: filename with path to save ImageAICS

         image: image of class ImageAICS

         interactive: if True, allow update of filename if it already exists

        Output:
         image: image of class ImageAICS
        """
        hardware_components.log_method(self, "save_image")
        # raise exception if image with name file_path already exists

        if interactive:
            for i in range(3):
                if os.path.isfile(file_path):
                    directory, file_name = os.path.split(file_path)
                    new_file_name = message.read_string(
                        "File exists",
                        label="Modify new filename",
                        default=file_name,
                        return_code=False,
                    )
                    file_path = os.path.normcase(os.path.join(directory, new_file_name))
                else:
                    break

        if os.path.isfile(file_path):
            raise FileExistsError("File with path {} already exists.".format(file_path))

        communication_object = self._get_control_software().connection
        communication_object.save_image(file_path)
        image.add_meta({"aics_filePath": file_path})

        return image

    def load_image(self, image, get_meta=False):
        """Load image and return it as class ImageAICS.
        Methods adds image and meta data to image.
        Methods passes load image to microscope specific load method.

        Input:
         communication_object: Object that connects to microscope specific software

         image: image object of class ImageAICS. Holds meta data at this moment,
         no image data.

         get_meta: if true, retrieve meta data from file. Default is False

        Output:
         image: image with data and meta data as ImageAICS class
        """
        hardware_components.log_method(self, "load_image")
        communication_object = self._get_control_software().connection
        image = communication_object.load_image(image, get_meta)
        return image

    def remove_images(self):
        """Remove all images from display in microscope software

        Input:
         communication_object: Object that connects to microscope specific software

        Output:
         none
        """
        hardware_components.log_method(self, "remove_images")
        communication_object = self._get_control_software().connection
        communication_object.remove_all()
