"""
Classes to describe and control 3i spinning disk hardware.
Bridge between automation software and hardware specific implementations.
Created on Jul 7, 2016
Split into hardware_control and hardware_components on May 25, 2020
Split into hardware_control and hardware_control_3i on Aug. 15, 2020 by Winfried

@author: winfriedw
"""

import os
import collections
import datetime
from ..image_AICS import ImageAICS
from ..automation_exceptions import (
    AutomationError,
    HardwareError,
    AutofocusNoReferenceObjectError,
    FileExistsError,
)
from ..hardware import hardware_components
from ..hardware.hardware_control import BaseMicroscope

# setup logging
import logging
from .. import automation_messages_form_layout as message

logger = logging


logging.basicConfig(level=logging.WARNING)
logging.debug('Switched on debug level logging in module "{}'.format(__name__))


class SpinningDisk3i(BaseMicroscope):
    """Collection class to describe and operate 3i spinning disk microscope"""

    def create_experiment_path(self, experiment):
        """Creates complete path to capture settings (Slidebook).
        Raises exception if experiment does not exist.

        Input:
         experiment: string with name of capture settings
         (with or w/o extension .exp.prefs)

        Output:
         experiment_path: path to experiment or capture settings
        """
        # get communications object as link to microscope hardware
        communicatons_object = self._get_control_software().connection
        experiment_path = communicatons_object.create_experiment_path(
            experiment, self.experiment_folder
        )
        return experiment_path

    def stop_microscope(self):
        """Stop Microscope immediately in emergency situation

        Input:
         none

        Output:
         none"""
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

         experiment: Name of experiment setting in ZEN blue used for microscope
         initialization (e.g. used for live mode)

         before_initialization: if True setup microscope, if False reset

        Output:
         none
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
         component_OrderedDict: directory with names of components to initialize
         and list of initialization steps. Default: None = initialize all
         components in order as assigned to microscope object

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

         reference_object_id: ID of object of Sample class used to correct for
         xyz offset between different objectives

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
        communicatons_object = self._get_control_software().connection
        focus_drive_instance = self._get_microscope_object(focus_drive_id)
        z_positions = focus_drive_instance.get_information(communicatons_object)
        return z_positions

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

         z_focus_preset: z position for focus before focus recall
         to make autofocus more reliable. (Default: None, do not use feature)

         reference_object_id: ID of object of Sample class used to correct for xyz
         offset between different objectives

         load: Move focus in load position before move. Default: True

         trials: number of trials to retrieve z position before procedure is aborted

        Ouput:
         x_final, y_final, z_final: coordinates after move
        """
        hardware_components.log_method(self, "move_to_abs_pos")

        communication_object = self._get_control_software().connection
        stage_object = self._get_microscope_object(stage_id)
        x_final, y_final, z_final = stage_object.move_to_position(
            communication_object, x_target, y_target, z_target, test=False
        )
        return x_final, y_final, z_final

    def execute_experiment(
        self,
        capture_settings=None,
        file_path=None,
        position_list=None,
        interactive=False,
    ):
        """Trigger microscope to execute experiment defined within vendor software.
        Class ImageAICS is a container for meta and image data.
        To add image data use method load_image.
        Do not try to recover from exceptions on this level.

        Input:
         capture_settings: string or list of strings with names of capture settings
         as defined within 3i Slidebook software. If one capture setting is provided
         execute same settings at all positions. If list with capture settings is
         provided, execute each setting on each position. The number of positions
         has to be identical as the number of capture strings.

         file_path: string with path to save image to. Do not save if None (default)

         position_list: list with stage coordinates for images

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
        try:
            if position_list is None:
                service_response = communication_object.snap_image(capture_settings)
            else:
                service_response = communication_object.execute_experiment(
                    capture_settings, position_list
                )
            self.last_experiment = capture_settings
        except AutomationError as error:
            self.recover_hardware(error)

        timeEnd = datetime.datetime.now()

        image = ImageAICS(meta={"aics_Experiment": capture_settings})
        #         image.add_meta(self.settings)

        # add meta data about acquisition time
        timeDuration = (timeEnd - timeStart).total_seconds()
        image.add_meta(service_response)
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

    def save_image(self, file_path, image, interactive=False):
        """Save last Microscope ImageAICS taken from within Microscope software.
        Method adds file_path to meta data.

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
        Methods ads image and meta data to image.
        Methods passes load image to microscope specific load method.

        Input:
         communication_object: Object that connects to microscope specific software

         image: image object of class ImageAICS.
         Holds meta data at this moment, no image data.

         get_meta: if true, retrieve meta data from file. Default is False

        Output:
         image: image with data and meta data as ImageAICS class
        """
        hardware_components.log_method(self, "load_image")
        communication_object = self._get_control_software().connection
        image = communication_object.load_image(image, get_meta)
        return image

    def remove_images(self):
        """Remove all images from queue on data service.

        Input:
         communication_object: Object that connects to microscope specific software

        Output:
         none
        """
        hardware_components.log_method(self, "remove_images")
        communication_object = self._get_control_software().connection
        communication_object.remove_all()

    def reference_position(
        self, find_surface=False, reference_object_id=None, verbose=True
    ):
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
        self.not_implemented("reference_position")
