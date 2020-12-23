"""
Main script for Microscope automation
Created on Jun 9, 2016

@author: winfriedw
"""

# store all images as numpy arrays
import numpy
import math

# use sys library to abort script and for other system operations
import sys
import os

# use shutil for file manipulations
import shutil

# use logging, setup will happen in module error_handling
import logging
import argparse
import string
import inspect
import copy
from collections import OrderedDict
from datetime import date
from matplotlib.pyplot import imsave

from microscope_automation import preferences
from microscope_automation import automation_messages_form_layout as message
from microscope_automation.hardware import setup_microscope
from microscope_automation import error_handling
from microscope_automation.samples.setup_samples import setup_plate
from microscope_automation.get_path import (
    set_up_subfolders,
    get_daily_folder,
    get_recovery_settings_path,
    get_references_path,
    get_images_path,
    get_position_csv_path,
    get_colony_dir_path,
    get_colony_remote_dir_path,
    get_experiment_path,
    get_meta_data_path,
    get_valid_path_from_prefs,
)
from microscope_automation.samples import samples
from microscope_automation.hardware import hardware_components
from microscope_automation.meta_data_file import MetaDataFile
from microscope_automation.automation_exceptions import (
    StopCollectingError,
    HardwareError,
    AutomationError,
)
from microscope_automation.software_state import State
from microscope_automation.find_positions import (
    create_output_objects_from_parent_object,
    convert_location_list,
)
from microscope_automation.zeiss.write_zen_tiles_experiment import PositionWriter
from microscope_automation.image_AICS import ImageAICS
from microscope_automation.samples.well_segmentation_refined import WellSegmentation

import pickle
import pyqtgraph
from pyqtgraph.Qt import QtGui
from aicsimageio import AICSImage
import csv

import tkinter as tk
from tkinter import filedialog

################################################################################
#
# constants with valid preferences values
#
################################################################################
VALID_FUNCTIONNAME = [
    "initialize_microscope",
    "set_objective_offset",
    "set_up_objectives",
    "update_plate_z_zero",
    "calculate_plate_correction",
    "calculate_all_wells_correction",
    "setup_immersion_system",
    "scan_plate",
    "segment_wells",
    "scan_samples",
    "run_macro",
]
VALID_SETUPFOLDERS = [True, False]
VALID_COPYCOLONYFILES = [True, False]
VALID_ADDCOLONIES = [True, False]
VALID_FINDLOAD = [True, False]
VALID_USEREFERENCE = [True, False]
VALID_LASERSAFETY = [True, False]
VALID_KOEHLER = [True, False]
VALID_VERBOSE = [True, False]
VALID_USEAUTOFOCUS = [True, False]
VALID_MANUELREFOCUS = [True, False]
VALID_SNAPIMAGE = [True, False]
VALID_WAIT = [True, False]
VALID_LOAD = [True, False]
VALID_LOADBETWEENWELLS = [True, False]
VALID_ADDIMERSIONWATER = [True, False]
VALID_USEPUMP = [True, False]
VALID_TILE_OBJECT = ["NoTiling", "Fixed", "ColonySize", "Well", "Automatic"]
VALID_FINDTYPE = [
    "None",
    "copy_zero_position",
    "copy_image_position",
    "Interactive",
    "CenterMassCellProfiler",
    "TwofoldDistanceMap",
    "InteractiveDistanceMap",
]
VALID_WELLS = [x + str(y) for x in string.ascii_uppercase[0:8] for y in range(1, 13)]
VALID_BLOCKING = [True, False]

################################################################################
#
# local maintenance functions
#
################################################################################


def stop_script(message_text=None, allow_continue=False):
    """Stop processing and ask to leave automation script.

    Input:
     message_text: Message to user explaining why processing should be stopped.

     allow_continue: if True, allow user to continue. Default: False

    Output:
     none if user selects 'Continue', otherwise calls sys.exit()

    Script will stop all Microscope action immediately and
    ask user to stop execution of script or to continue.
    """
    # Microscope.stop_microscope()
    if allow_continue:
        if message_text is None:
            message_text = "If you want to abort script press ok.\notherwise Continue"
        con = message.information_message("Exit script", message_text, return_code=True)
    else:
        if message_text is None:
            message_text = "Exit"
        con = message.information_message(
            "Exit script", message_text, return_code=False
        )
        con = 0

    if con == 0:
        # logger.info('User aborted operation')
        print("User aborted operation")
        sys.exit()


################################################################################


class MicroscopeAutomation(object):
    def __init__(self, prefs_path):
        self.prefs = preferences.Preferences(prefs_path)
        recovery_file_path = get_recovery_settings_path(self.prefs)

        # Create the recovery folder if it does not exist.
        rec_folder_path = os.path.dirname(recovery_file_path)
        if not os.path.exists(rec_folder_path):
            os.mkdir(rec_folder_path)
        # Create and save the pickle file
        self.state = State(recovery_file_path)
        self.state.save_state()
        self.less_dialog = self.prefs.get_pref("LessDialog")
        if self.less_dialog is None:
            self.less_dialog = False

        self.failed_wells = []

    def get_well_object(self, plate_holder_object, plate_name, well):
        """Return well object for given well.

        Input:
         plate_holder_object: object for plateholder that contains well

         plate_name: name for plate, typically barcode

         well: name of well in form 'A1'

        Output:
         well_object: object for well
        """
        # get dictionary of all plates associated with plate holder
        plate_objects = plate_holder_object.get_plates()

        # get object for plate with name plateName, typically the barcode
        plate_object = plate_objects[plate_name]

        # get object for well with name well
        well_object = plate_object.get_well(well)

        return well_object

    ################################################################################

    def get_barcode_object(self, well_object, barcode):
        """Return Barcode object for given well.

        Input:
         well_object: object for well that contains barcode

         barcode: string of name for barcode

        Output:
         barcode_object: object for barcode
        """
        # get dictionary of all samples associated with well
        sample_objects = well_object.get_samples()
        barcode_object = sample_objects[barcode]

        return barcode_object

    ################################################################################

    def read_barcode(
        self, prefs, plate_holder_object, barcode, well=None, barcode_name=None
    ):
        """Move manually to barcode, read and decipher barcode.

        Input:
         prefs: dictionary with preferences

         plate_holder_object: object of type PlateHolder
         from module sample with well information

         barcode: barcode for plate, often used as plate name

         well: well the barcode is associated with in format 'A1'.
         If empty ask user to navigate to barcode.

        Output:
         barcode: id encoded in barcode
        """
        # set debugging level
        verbose = prefs.get_pref("Verbose", valid_values=VALID_VERBOSE)
        print("\n\nStart reading barcode (read_barcode)")

        # Move to well and get wellObject
        # If no well is given retrieve it from preferences file
        # and ask user to navigate to position.
        # If well is given, move automatically to well.
        if well is None:
            well = prefs.get_pref("WellBarcode")
            barcode_name = prefs.get_pref("NameBarcode")
            message.operate_message("Please focus on barcode in well " + well)
            well_object = self.get_well_object(plate_holder_object, barcode, well)
        else:
            well_object = self.get_well_object(plate_holder_object, barcode, well)
            well_object.get_container().move_to_well(well)

        # get barcode object
        barcode_object = self.get_barcode_object(well_object, barcode_name)

        # get name for microscope settings as defined within microscope software
        experiment = prefs.get_pref("ExperimentBarcode")
        camera_id = prefs.get_pref("CameraBarcode")

        # Define and if necessary create folder for images
        image_dir = get_references_path(prefs)

        # acquire image
        file_path = image_dir + barcode_name + ".czi"
        barcode = barcode_object.read_barcode(
            experiment, camera_id, file_path, verbose=verbose
        )
        return barcode

    ################################################################################

    def calculate_all_wells_correction(self, prefs, plate_holder_object, _experiment):
        """Calculate correction factor for well coordinate system for all wells.

        Input:
         prefs: dictionary with preferences

         plate_holder_object: object for plateholder that contains well

         _experiment: not used, necessary for compatibility

        Output:
         none
        """
        # iterate through all plates on plate holder
        plates = plate_holder_object.get_plates()

        for plate_name, plate_object in plates.items():
            wells = plate_object.get_wells()
            reference_well_1 = prefs.get_pref("WellCalibrateWell_1")
            measured_diameter_1 = plate_object.get_well(
                reference_well_1
            ).get_measured_diameter()

            reference_well_2 = prefs.get_pref("WellCalibrateWell_2")
            measured_diameter_2 = plate_object.get_well(
                reference_well_2
            ).get_measured_diameter()

            reference_well_3 = prefs.get_pref("WellCalibrateWell_3")
            measured_diameter_3 = plate_object.get_well(
                reference_well_3
            ).get_measured_diameter()

            measured_diameter = numpy.mean(
                [measured_diameter_1, measured_diameter_2, measured_diameter_3]
            )

            # set measuredDiameter for all wells to measuredDiameter from reference well
            # update calibration correction for all wells
            for well_name, well_object in wells.items():
                well_object.set_measured_diameter(measured_diameter)
                x_correction = (
                    well_object.get_measured_diameter()
                    / well_object.get_assigned_diameter()
                )
                y_correction = x_correction
                well_object.set_correction(x_correction, y_correction)

    ################################################################################

    def setup_immersion_system(self, prefs, plate_holder_instance):
        """Setup system to deliver immersion water

        Input:
         prefs: dictionary with preferences

         plate_holder_instance: instance for plateholder that contains immersion system

        Output:
         none
        """

        # TODO: this function should be part of pump.initialize() in module hardware.py
        # set debugging level
        verbose = prefs.get_pref("Verbose", valid_values=VALID_VERBOSE)
        print("\n\nSet-up water immersion system (setup_immersion_system)")

        # get immersion delivery system object
        immersion_delivery = plate_holder_instance.immersion_delivery_system

        # move objective under immersion water outlet and assign position
        # of outlet to immersion delivery object
        microscope = plate_holder_instance.get_microscope()
        focus_id = plate_holder_instance.get_focus_id()
        focus_drive = microscope._get_microscope_object(focus_id)
        load_position = focus_drive.get_load_position()

        # get communication object
        communication_object = (
            plate_holder_instance.microscope._get_control_software().connection
        )

        # Make sure load position is defined for focus drive
        if load_position is None:
            message.operate_message("Move objective to load position.")
            focus_drive.define_load_position(communication_object)
            load_position = focus_drive.get_load_position()

        x_pos = prefs.get_pref("xImmersionSystem")
        y_pos = prefs.get_pref("yImmersionSystem")

        # Execute experiment before moving stage to ensure that proper objective
        # (typically 10x) in in place to avoid collision.
        experiment = prefs.get_pref("ExperimentSetupImmersionSystem")
        camera_id = prefs.get_pref("CameraSetupImmersionSystem")

        immersion_delivery.execute_experiment(
            experiment, camera_id, file_path=None, verbose=verbose
        )
        immersion_delivery.move_to_abs_position(
            x_pos,
            y_pos,
            load_position,
            reference_object=plate_holder_instance.get_reference_object(),
            load=True,
            verbose=verbose,
        )

        # take image of water outlet
        immersion_delivery.live_mode_start(camera_id, experiment)
        message.operate_message(
            "Move objective under water outlet."
            "\nUse flashlight from below stage to see outlet."
        )
        immersion_delivery.live_mode_stop(camera_id, experiment)

        # drop objective to load position and store position for water delivery
        # water is always delivered with objective in load position to avoid collision
        focus_drive.goto_load(communication_object)
        immersion_delivery.set_zero(verbose=verbose)

        # move away from delivery system to avoid later collisions
        immersion_delivery.move_to_safe()
        magnification = prefs.get_pref("MaginificationImmersionSystem")
        immersion_delivery.magnification = magnification

    ################################################################################

    def set_up_objectives(self, set_up_settings, plate_holder_instance, _experiment):
        """Retrieve objectives mounted at microscope.

        Input:
         set_up_settings: dictionary with preferences

         plate_holder_instance: object of type PlateHolder
         from module sample with well information

         _experiment: not used, necessary for compatibility

        Output:
         none
        """
        # set debugging level
        verbose = set_up_settings.get_pref("Verbose", valid_values=VALID_VERBOSE)
        print("\n\nSet-up objectives (set_up_objectives)")

        # move stage and focus drive to save position before switching objectives
        x_pos = set_up_settings.get_pref("xSetUpObjectives")
        y_pos = set_up_settings.get_pref("ySetUpObjectives")
        z_pos = set_up_settings.get_pref("zSetUpObjectives")

        # retrieve information about mounted objectives
        # This part will detect all objectives defined in the touch pad software.
        microscope_instance = plate_holder_instance.get_microscope()
        objective_changer_instance = microscope_instance._get_microscope_object(
            plate_holder_instance.objective_changer_id
        )
        communication_object = microscope_instance._get_control_software().connection
        objectives_dict = objective_changer_instance.get_all_objectives(
            communication_object
        )
        objective_information = objective_changer_instance.objective_information

        # step through all objectives and determine parfocality and parcentrizity
        # create ordered dictionary with immersions to ensure
        # that we start with air and end with oil objectives
        magnifications_list = sorted(
            [
                magnification
                for magnification, objective in objectives_dict.items()
                if not objective["Name"] == "none"
            ],
            reverse=True,
        )
        immersions_list = ["air", "water", "glycerol", "oil"]

        # the offset for each objective will be calculated relative to the highest
        # resolution air objective (water if air does not exist)
        x_reference_position = None
        y_reference_position = None
        z_reference_position = None

        for immersion in immersions_list:
            immersion_objectives = [
                (name, info)
                for name, info in objective_information.items()
                if info["immersion"] == immersion
            ]
            for magnification in magnifications_list:
                experiments = [
                    (
                        name,
                        objective["experiment"],
                        objective["camera"],
                        objective["autofocus"],
                    )
                    for name, objective in immersion_objectives
                    if objective["magnification"] == int(magnification)
                ]
                for name, experiment, camera, auto_focus in experiments:
                    # store status of auto-focus and switch offs
                    auto_focus_status = microscope_instance.set_microscope(
                        settings_dict={auto_focus: {}}
                    )
                    microscope_instance.set_microscope(
                        settings_dict={auto_focus: {"use_auto_focus": False}}
                    )

                    microscope_instance.live_mode(
                        camera_id=camera, experiment=experiment, live=True
                    )
                    # make sure that correct objective is selected
                    plate_holder_instance.move_to_abs_position(
                        x=x_pos, y=y_pos, z=z_pos, load=False, verbose=verbose
                    )
                    message.operate_message(
                        message="Please move to and focus on reference position.",
                        return_code=False,
                    )
                    microscope_instance.live_mode(
                        camera_id=camera, experiment=experiment, live=False
                    )

                    abs_position = plate_holder_instance.get_abs_position()
                    x_pos = abs_position[0]
                    y_pos = abs_position[1]
                    z_pos = abs_position[2]
                    if x_reference_position is None:
                        x_reference_position = abs_position[0]
                    if y_reference_position is None:
                        y_reference_position = abs_position[1]
                    if z_reference_position is None:
                        z_reference_position = abs_position[2]

                    x_offset = abs_position[0] - x_reference_position
                    y_offset = abs_position[1] - y_reference_position
                    z_offset = abs_position[2] - z_reference_position

                    # this will update objective_changer_instance.objective_information
                    objective_information[name]["x_offset"] = x_offset
                    objective_information[name]["y_offset"] = y_offset
                    objective_information[name]["z_offset"] = z_offset

                    print(
                        (
                            "New offset values for objective {}:\n"
                            "x_offset: {}\ny_offset: {}\nz_offset: {}"
                        ).format(name, x_offset, y_offset, z_offset)
                    )
                    microscope_instance.set_microscope(
                        settings_dict={
                            auto_focus: {"use_auto_focus": auto_focus_status}
                        }
                    )

    ################################################################################

    def set_objective_offset(self, offset_prefs, plate_holder_object, _experiment):
        """Set parfocality and parcentricity for objectives used in experiments.

        Input:
         offset_prefs: dictionary with preferences based on preferences.yml

         plate_holder_object: object that contains all plates
         and all wells with sample information.

         _experiment: not used, necessary for compatibility

        Output:
         none
        """
        verbose = offset_prefs.get_pref("Verbose", valid_values=VALID_VERBOSE)
        microscope_object = plate_holder_object.get_microscope()

        # retrieve list with experiments used to find objective offset
        # and iterate through them
        experiments_list = offset_prefs.get_pref("ExperimentsList")

        # iterate through all plates on plate holder
        plates = plate_holder_object.get_plates()

        for plate_name, plate_object in plates.items():
            for experiment in experiments_list:
                microscope_object.create_experiment_path(experiment)

                objective_changer_id = plate_object.get_objective_changer_id()
                objective_changer = microscope_object._get_microscope_object(
                    objective_changer_id
                )
                objective_changer.set_init_experiment(experiment)

                microscope_object.initialize_hardware(
                    initialize_components_ordered_dict={
                        objective_changer_id: {"no_find_surface"}
                    },
                    reference_object_id=plate_object.get_reference_object().get_name(),
                    trials=3,
                    verbose=verbose,
                )

    def set_up_koehler(self, initialize_prefs, plate_object):
        """Set up Koehler illumination.

        Input:
         initialize_prefs: dictionary with preferences based on preferences.yml

         plate_object: object of class plate

        Output:
         none
        """
        # get settings from preferences.yml
        camera_id = initialize_prefs.get_pref("Camera")
        zen_experiment = initialize_prefs.get_pref("Experiment")
        well_name = initialize_prefs.get_pref("Well")
        load = initialize_prefs.get_pref("Load")
        use_reference = initialize_prefs.get_pref(
            "UseReference", valid_values=VALID_USEREFERENCE
        )
        use_auto_focus = initialize_prefs.get_pref(
            "UseAutoFocus", valid_values=VALID_USEAUTOFOCUS
        )
        trials = initialize_prefs.get_pref("NumberTrials")
        verbose = initialize_prefs.get_pref("Verbose")

        microscope_object = plate_object.get_microscope()
        well_object = plate_object.get_well(well_name)
        if well_object.microscope_is_ready(
            experiment=zen_experiment,
            reference_object=well_object.get_reference_object(),
            load=load,
            use_reference=use_reference,
            use_auto_focus=use_auto_focus,
            make_ready=True,
            trials=trials,
            verbose=verbose,
        ):
            well_object.move_to_zero(load=load, verbose=verbose)
        else:
            raise AutomationError(
                "Microscope not ready in set_up_koehler with experiment {}".format(
                    zen_experiment
                )
            )

        microscope_object.live_mode(camera_id, experiment=zen_experiment, live=True)
        message.operate_message("Set-up Koehler illumination.")
        microscope_object.live_mode(camera_id, experiment=zen_experiment, live=False)

    def initialize_microscope(self, initialize_prefs, plate_holder_object, _experiment):
        """Update z positions for plate (upper side of coverslip)
        Set load and work positions for focus drive.

        Input:
         initialize_prefs: dictionary with preferences

         plate_holder_object: object of type PlateHolder
         from module sample with well information

         _experiment: not used, necessary for compatibility

        Output:
         none
        """

        if initialize_prefs.get_pref(
            "CopyColonyFile", valid_values=VALID_COPYCOLONYFILES
        ):
            # copy colony file
            colony_remote_dir = get_colony_remote_dir_path(initialize_prefs)
            if (
                initialize_prefs.get_pref("AddColonies", valid_values=VALID_ADDCOLONIES)
                is True
            ):
                # Add colonies is in the list of experiment,
                # show the options for csv file
                colony_remote_file = message.file_select_dialog(
                    colony_remote_dir, return_code=True
                )
                # continue if user did not press cancel
                if colony_remote_file != 0:
                    source_path = os.path.normpath(
                        os.path.join(colony_remote_dir, colony_remote_file)
                    )
                    destination_path = get_colony_dir_path(initialize_prefs)
                    shutil.copy2(source_path, destination_path)

        # initialize microscope hardware (e.g. auto-focus)
        # for each plate within plateholder
        trials = initialize_prefs.get_pref("NumberTrials")
        verbose = initialize_prefs.get_pref("Verbose", valid_values=VALID_VERBOSE)
        microscope_object = plate_holder_object.get_microscope()
        for barcode, plate in plate_holder_object.get_plates().items():
            if initialize_prefs.get_pref("Hardware", valid_values=VALID_VERBOSE):

                initialization_dict = OrderedDict(
                    [
                        (plate.get_focus_id(), ["set_load"]),
                        (plate.get_stage_id(), []),
                        (plate.get_objective_changer_id(), []),
                    ]
                )
                microscope_object.initialize_hardware(
                    initialize_components_ordered_dict=initialization_dict,
                    reference_object_id=plate.get_reference_object().get_name(),
                    trials=trials,
                    verbose=verbose,
                )

                self.state.reference_object = plate.get_reference_object()
                # Autosave
                self.state.save_state()

            # set Koehler illumination
            if initialize_prefs.get_pref("Koehler", valid_values=VALID_KOEHLER):
                self.set_up_koehler(initialize_prefs, plate)

        # ask user to enable laser safety
        if initialize_prefs.get_pref("LaserSafety", valid_values=VALID_LASERSAFETY):
            message.operate_message(
                "Please enable laser safety.\n"
                "Disable parfocality and parcentralicy\n"
                "Secure sample from sliding."
            )

    ################################################################################

    def update_plate_z_zero(self, image_settings, plate_holder_object, experiment):
        """Update z positions for plate (upper side of coverslip)
        Set load and work positions for focus drive.

        Input:
         image_settings: dictionary with preferences

         plate_holder_object: object of type PlateHolder
         from module sample with well information

         experiment: dictionary with keys 'Experiment', Repetitions', 'Input',
         'Output', 'WorkflowList', 'WorflowType', 'ObjectsDict' and 'OriginalWorkflow'

        Output:
         none
        """
        # set debugging level
        verbose = image_settings.get_pref("Verbose", valid_values=VALID_VERBOSE)
        print("\n\nStart to update z zero settings for plates (update_plate_z_zero)")

        trials = image_settings.get_pref("NumberTrials")
        # iterate through all plates on plate holder
        plates = plate_holder_object.get_plates()

        for plate_name, plate_object in plates.items():
            # get preferences
            zen_experiment = image_settings.get_pref("Experiment")
            camera_id = image_settings.get_pref("Camera")
            well_name = image_settings.get_pref("Well", valid_values=VALID_WELLS)
            load = image_settings.get_pref("Load", valid_values=VALID_LOAD)
            use_reference = image_settings.get_pref(
                "UseReference", valid_values=VALID_USEREFERENCE
            )
            use_auto_focus = image_settings.get_pref(
                "UseAutoFocus", valid_values=VALID_USEAUTOFOCUS
            )
            # find zero z-position for plate (upper side of cover slip
            plate_object.live_mode_start(camera_id, zen_experiment)
            well_object = plate_object.get_well(well_name)

            if well_object.microscope_is_ready(
                experiment=zen_experiment,
                reference_object=well_object.get_reference_object(),
                load=load,
                use_reference=use_reference,
                use_auto_focus=use_auto_focus,
                make_ready=True,
                trials=trials,
                verbose=verbose,
            ):

                if plate_object.update_z_zero_pos:
                    plate_object.move_to_xyz(
                        *plate_object.update_z_zero_pos, load=load, verbose=verbose
                    )
                else:
                    well_object.move_to_zero(load=load, verbose=verbose)
            else:
                raise AutomationError(
                    (
                        "Microscope not ready in update_plate_z_zero"
                        " with experiment {}"
                    ).format(zen_experiment)
                )

            # User has to set focus position for following experiments
            return_code = message.operate_message(
                "Please set the focus for your acquisition", return_code=True
            )

            if return_code == 0:
                self.state.save_state_and_exit()
            plate_object.live_mode_stop(camera_id, zen_experiment)

            # get actual z-position for plate and set as new z_zero position
            _x, _y, z_new = plate_object.get_container().get_pos_from_abs_pos(
                verbose=verbose
            )
            plate_object.update_zero(z=z_new, verbose=verbose)

            # store position used for focusing,
            # will make later focusing with higher magnification easier
            plate_object.update_z_zero_pos = plate_object.get_pos_from_abs_pos(
                verbose=verbose
            )

            self.state.reference_object = plate_object.get_reference_object()
            self.state.save_state()

            for (
                key,
                value,
            ) in (
                plate_holder_object.microscope.microscope_components_ordered_dict.items()  # noqa
            ):
                # Passage the previous experiment's objects if being called
                # as a separate workflow experiment
                workflow_list = experiment["WorkflowList"]
                original_workflow = experiment["OriginalWorkflow"]
                if experiment["Experiment"] in workflow_list:
                    previous_experiment = original_workflow[
                        workflow_list.index(experiment["Experiment"]) - 1
                    ]
                    if previous_experiment in list(
                        self.state.next_experiment_objects.keys()
                    ):
                        next_exp_objects = self.state.next_experiment_objects[
                            previous_experiment
                        ]
                        self.state.add_next_experiment_object(
                            experiment["Experiment"], next_exp_objects
                        )
                        # Autosave
                        self.state.save_state()

    ################################################################################

    def calculate_plate_correction(self, prefs, plate_holder_object, _experiment):
        """Calculate correction factor for plate coordinate system.

        Input:
         prefs: dictionary with preferences

         plate_holder_object: object for plate that contains well

         _experiment: not used, necessary for compatibility

        Output:
         none
        """
        # set debugging level
        verbose = prefs.get_pref("Verbose", valid_values=VALID_VERBOSE)
        print(
            "\n\nStart to acquire images for plate correction"
            " (calculate_plate_correction)"
        )

        # iterate through all plates on plate holder
        plates = plate_holder_object.get_plates()

        for plate_name, plate_object in plates.items():
            # Acquire images of edges of three reference wells
            # and use them to determine the well center
            # Get names of reference wells
            well_names = [
                prefs.get_pref("WellCalibrateWell_{}".format(i)) for i in range(1, 4)
            ]

            # get well objects
            well_objects = [plate_object.get_well(well) for well in well_names]

            # get imaging parameters
            zen_experiment = prefs.get_pref("Experiment")
            well_diameter = prefs.get_pref("WellDiameterCalibrateWell")
            camera_id = prefs.get_pref("Camera")

            # Move objective to load position before moving to next calibration well?
            load = prefs.get_pref("Load", valid_values=VALID_LOAD)
            trials = prefs.get_pref("NumberTrials")

            if not plate_object.microscope_is_ready(
                experiment=zen_experiment,
                reference_object=plate_object.get_reference_object(),
                load=load,
                make_ready=True,
                trials=trials,
                verbose=verbose,
            ):
                raise AutomationError(
                    (
                        "Microscope not ready in calculate_plate_correction"
                        " with experiment {}"
                    ).format(zen_experiment)
                )

            def find_well_center(well_object, well_index, verbose=verbose):
                well_object.move_delta_xyz(
                    well_diameter / 2, 0, 0, load=False, verbose=verbose
                )
                well_object.live_mode_start(
                    camera_id=camera_id, experiment=zen_experiment
                )
                return_code = message.operate_message(
                    (
                        "Please focus with 10x on left edge of well {}\n"
                        "to find zero position for plate {}"
                    ).format(well_names[well_index], plate_object.get_name()),
                    return_code=True,
                )
                if return_code == 0:
                    self.state.save_state_and_exit()

                # find center of well in absolute stage coordinates
                return well_objects[well_index].find_well_center_fine(
                    zen_experiment, well_diameter, camera_id, prefs, verbose=verbose
                )

            # find center of wells
            well_center_abs = []

            # The stored z position for wells is not necessarily the actual one.
            # store the difference between the z-position on file
            # and the last measured z-position as delta_z
            # apply this delta to the next well to be closer at the actual position
            delta_z = 0

            for ind, well_object in enumerate(well_objects):
                # Make sure that microscope is ready and correct objective is used
                well_object.microscope_is_ready(
                    experiment=zen_experiment,
                    reference_object=well_object.get_reference_object(),
                    load=load,
                    make_ready=True,
                    trials=trials,
                    verbose=verbose,
                )
                well_object.move_to_zero(load=load, verbose=verbose)
                well_object.move_delta_xyz(0, 0, delta_z, load=False, verbose=verbose)
                x_pos_abs, y_pos_abs, z_pos_abs = well_object.get_abs_position()

                well_center_abs_i = find_well_center(well_object, ind, verbose=verbose)
                # difference between actual z position of well and position on file
                delta_z = well_object.get_abs_zero()[2] - well_center_abs_i[2]
                well_center_abs.append(well_center_abs_i)

            # Calculate values for transformation from plate holder coordinates
            # to plate coordinates, then get plate coordinates for well centers
            # from zero positions of wells in plate coordinate
            plate_centers = [
                well_objects[ind].get_zero() for ind in range(len(well_objects))
            ]

            # Subtract x and y values to get distance between wells
            x_plate_distance = plate_centers[1][0] - plate_centers[0][0]
            y_plate_distance = plate_centers[2][1] - plate_centers[1][1]

            # get plate holder coordinates based on measured well centers
            plate_holder_object = plate_object.get_container()
            plate_holder_centers = [
                plate_holder_object.get_pos_from_abs_pos(*centers, verbose=verbose)
                for centers in well_center_abs
            ]

            x_plate_holder_distance = (
                plate_holder_centers[1][0] - plate_holder_centers[0][0]
            )
            y_plate_holder_distance = (
                plate_holder_centers[2][1] - plate_holder_centers[1][1]
            )

            # calculate corrections
            x_plate_holder_correction = x_plate_holder_distance / x_plate_distance
            y_plate_holder_correction = y_plate_holder_distance / y_plate_distance
            z_plate_holder_correction = 1

            # Describe not leveled plate as plane of form ax + bx + cx = d
            # Calculate 2 vectors from 3 points, and use cross product
            # to find normal vector for plane <a, b, c>
            # Dot normal vector and point to get offset (d)
            p = [
                numpy.array(center).astype(numpy.float)
                for center in plate_holder_centers
            ]
            v1 = p[1] - p[0]
            v2 = p[2] - p[0]
            plane = numpy.cross(v1, v2)

            # normalize normal vector to avoid large numbers
            normFactor = math.sqrt(plane[0] ** 2 + plane[1] ** 2 + plane[2] ** 2)
            norm = plane / normFactor
            # the plane can be described in the form ax + by +cz = d
            # a,b,c are the components of the normal vector and determine the slope
            z_correction_x_slope = norm[0]
            z_correction_y_slope = norm[1]
            z_correction_z_slope = norm[2]

            # We will choose the offset d so that it equals 0 at the position
            #  where zZero was defined for the plate in update_plate_well_zZero
            #  xPosAbs = prefs.get_pref('xUpdatePlateWellZero')
            #  yPosAbs = prefs.get_pref('yUpdatePlateWellZero')
            x_pos, y_pos, z_pos = plate_object.get_pos_from_abs_pos(
                x=x_pos_abs, y=y_pos_abs, z=0, verbose=verbose
            )
            z_correction_offset = (
                z_correction_x_slope * x_pos + z_correction_y_slope * y_pos
            )

            plate_object.set_correction(
                x_correction=x_plate_holder_correction,
                y_correction=y_plate_holder_correction,
                z_correction=z_plate_holder_correction,
                z_correction_x_slope=z_correction_x_slope,
                z_correction_y_slope=z_correction_y_slope,
                z_correction_z_slope=z_correction_z_slope,
                z_correction_offset=z_correction_offset,
            )

            # set zero position for plate
            # transform stage center coordinates into plate coordinates
            center_plate = plate_object.get_pos_from_abs_pos(
                *well_center_abs[0], verbose=verbose
            )

            # set zero position for plate
            # transform stage center coordinates into plate coordinates
            center_plate = plate_object.get_pos_from_abs_pos(
                *well_center_abs[0], verbose=verbose
            )

            # get center of well in plate coordinates.
            # This is equivalent to the distance to the center of well A1 = plate zero
            plate_distances = well_objects[0].get_zero()
            plate_original = plate_object.get_zero()

            # Update zero position for plate
            plate_object.set_zero(
                plate_original[0] + (center_plate[0] - plate_distances[0]),
                plate_original[1] + (center_plate[1] - plate_distances[1]),
                plate_original[2],
                verbose=verbose,
            )

            for j in range(len(well_names)):
                print(
                    "Center of well {} in stage coordinates: {}".format(
                        well_names[j], well_objects[j].get_abs_zero(verbose=verbose)
                    )
                )
        print(
            "Zero position of plate {} in stage coordinates: {}".format(
                plate_object.get_name(), plate_object.get_abs_zero(verbose=verbose)
            )
        )

    ################################################################################

    def scan_wells_zero(self, prefs, plate_holder_object, barcode):
        """Scan selected wells at center.
        This method is mainly used to test calibrations.

        Input:
         prefs: dictionary with preferences

         plate_holder_object: object of type PlateHolder
         from module sample with well information

         barcode: barcode for plate, often used as plate name

        Output:
         none
        """
        # set debugging level
        verbose = prefs.get_pref("Verbose", valid_values=VALID_VERBOSE)
        print("\n\nStart scanning well centers (scan_wells_zero)")

        # get names of wells to scan
        wells_string = prefs.get_pref("WellsScanWellsZero")
        wells = [i.strip() for i in wells_string.split(",")]

        # name for settings as defined within microscope software
        experiment = prefs.get_pref("ExperimentScanWellsZero")
        camera_id = prefs.get_pref("CameraScanWellsZero")

        # Define and if necessary create folder for images
        image_dir = get_images_path(prefs)

        # iterate through all wells
        for well in wells:
            well_object = self.get_well_object(plate_holder_object, barcode, well)
            well_object.microscope_is_ready(
                experiment=experiment,
                reference_object=well_object.get_reference_object(),
                load=False,
                make_ready=True,
                trials=3,
                verbose=verbose,
            )
            x, y, z = well_object.move_to_zero(verbose=verbose)
            image_path = image_dir + well + "_zero.czi"
            well_object.execute_experiment(
                experiment, camera_id, file_path=image_path, verbose=verbose
            )
            print("Well: ", well_object.name, " at position (x,y,z): ", x, y, z)

    ################################################################################

    ################################################################################
    #
    # Scan colonies and cells
    #
    ################################################################################

    def scan_single_ROI(
        self,
        imaging_settings,
        experiment_dict,
        sample_object,
        reference_object,
        image_path,
        meta_dict,
        verbose=True,
        number_selected_postions=0,
        repetition=0,
    ):
        """Acquire tiled image as defined in pos_list

        Input:
         imaging_settings: dictionary with preferences

         experiment_dict: The dictionary with full information about the experiment

         sample_object: object of a sample type (e.g. cell, colony) to be imaged

         reference_object: object used to set parfocality and parcentricity,
         typically a well in plate

         image_path: string for filename with path to save image in original format
         or tuple with string to directory and list with template for file name.
         Default=None: no saving

         meta_dict: directory with additional meta data, e.g. {'aics_well':, 'A1'}

         verbose: if True print debug information (Default = True)

         number_selected_postions: number of positions collected so far

         repetition: counter for time lapse experiments

        Output:
         return_dict: dictionary of form {'Image': [images], 'Continue': True/False}
        """
        if verbose:
            print("\n\nStart scanning ", sample_object.get_name(), " (scan_single_ROI)")

        # name for settings as defined within microscope software
        experiment = imaging_settings.get_pref("Experiment")
        camera_id = imaging_settings.get_pref("Camera")

        trials = imaging_settings.get_pref("NumberTrials")
        use_auto_focus = imaging_settings.get_pref(
            "UseAutoFocus", valid_values=VALID_USEAUTOFOCUS
        )
        use_reference = imaging_settings.get_pref(
            "UseReference", valid_values=VALID_USEREFERENCE
        )

        # Allow user to manually adjust focus position selected by auto focus
        manual_refocus = imaging_settings.get_pref(
            "ManualRefocus", valid_values=VALID_MANUELREFOCUS
        )
        if manual_refocus:
            manual_refocus_after_repetitions = imaging_settings.get_pref(
                "ManualRefocusAfterRepetitions"
            )
            if manual_refocus_after_repetitions == 0:
                if repetition > 0:
                    manual_refocus = False
            else:
                if repetition % manual_refocus_after_repetitions != 0:
                    manual_refocus = False

        if verbose:
            print("Image Object ", sample_object.get_name())
        return_dict = {"Image": None, "Continue": True}

        # check if microscope is ready for imaging
        # and tries to execute missing initializations
        if not sample_object.microscope_is_ready(
            experiment=experiment,
            reference_object=sample_object.get_reference_object(),
            load=False,
            use_reference=use_reference,
            use_auto_focus=use_auto_focus,
            make_ready=True,
            trials=trials,
            verbose=verbose,
        ):
            raise HardwareError("Microscope not ready for imaging")

        sample_object.move_to_zero(load=False, verbose=verbose)
        # manual focus adjustment. New value is stored for future use
        if manual_refocus:
            if verbose:
                print(
                    "\n\n============================== Before re-focus ========================================"  # noqa
                )
                print(
                    "Image object ",
                    sample_object.get_name(),
                    "Colony position before re-adjustment:",
                    sample_object.get_zero(),
                    "Stage position:",
                    sample_object.get_abs_position(),
                )

            # start live mode again because redefinition of auto-focus might stop it
            sample_object.live_mode_start(camera_id=camera_id, experiment=experiment)
            select_result = message.select_message(
                "Focus on center of "
                + sample_object.get_name()
                + "\nCheck box below if you want to"
                + " include position in further experiments.",
                count=number_selected_postions,
            )
            sample_object.live_mode_stop(camera_id=camera_id)

            return_dict["Continue"] = select_result["Continue"]
            if select_result["Include"]:
                # set center of sample object to new position
                sample_object.set_zero(verbose=verbose)
                sample_object.set_image(True)
            else:
                # label object to not be included in future imaging
                sample_object.set_image(False)

            if verbose:
                print(
                    "\n\n============================== After re-focus ========================================"  # noqa
                )
                print(
                    "Image colony ",
                    sample_object.get_name(),
                    "Colony position after re-adjustment:",
                    sample_object.get_zero(),
                    "Stage position:",
                    sample_object.get_abs_position(),
                    "Included in future imaging: ",
                    sample_object.get_image(),
                )

        if (
            imaging_settings.get_pref("SnapImage", valid_values=VALID_SNAPIMAGE)
            or (
                (
                    imaging_settings.get_pref("FindType", valid_values=VALID_FINDTYPE)
                    is not None
                )
                and (
                    imaging_settings.get_pref("FindType", valid_values=VALID_FINDTYPE)
                    != "None"
                )
                and (
                    imaging_settings.get_pref("FindType", valid_values=VALID_FINDTYPE)
                    != "Copy"
                )
            )
            and sample_object.get_image()
        ):

            tile_object = imaging_settings.get_pref(
                "Tile", valid_values=VALID_TILE_OBJECT
            )
            pos_list = sample_object.get_tile_positions_list(
                imaging_settings, tile_object=tile_object, verbose=verbose
            )
            images = sample_object.acquire_images(
                experiment,
                camera_id,
                reference_object=reference_object,
                file_path=image_path,
                pos_list=pos_list,
                load=False,
                use_reference=use_reference,
                use_auto_focus=use_auto_focus,
                meta_dict=meta_dict,
                verbose=verbose,
            )
            return_dict["Image"] = images
        else:
            return_dict["Image"] = None
        return return_dict

    ################################################################################

    ################################################################################

    def scan_all_objects(
        self,
        imaging_settings,
        sample_list,
        plate_object,
        experiment,
        repetition=0,
        wait_after_image=None,
    ):
        """Scan all objects in dictionary.

        Input:
         imaging_settings: dictionary with preferences

         sample_list: list with all objects to scan

         plate_object: object sample list belongs to

         experiment: dictionary with keys 'Experiment', Repetitions', 'Input',
         'Output', 'WorkflowList', 'WorflowType', 'ObjectsDict' and 'OriginalWorkflow'

         repetition: counter for time lapse experiments

         wait_after_image: wait preferences as dictionary to determine whether
         to wait after execution
          Image: Wait after each image

          Plate: Reset wait status after each plate

          Repetition: Reset wait status after each repetition

          Status: Show last image and allow adjustments if True,
          enter fully automatic mode if False

        Output:
         none
        """
        # get settings from imaging_settings
        load_between_objects = imaging_settings.get_pref(
            "Load", valid_values=VALID_LOAD
        )
        load_between_wells = imaging_settings.get_pref(
            "LoadBetweenWells", valid_values=VALID_LOADBETWEENWELLS
        )
        verbose = imaging_settings.get_pref("Verbose", valid_values=VALID_VERBOSE)

        find_type = imaging_settings.get_pref("FindType", valid_values=VALID_FINDTYPE)
        tile_image = None

        # Define and if necessary create folder for images
        object_folder = imaging_settings.get_pref("Folder")
        image_dir = get_images_path(imaging_settings, object_folder)
        image_file_name_template = imaging_settings.get_pref("FileName")
        image_path = (image_dir, image_file_name_template)

        # Get immersion water delivery object and initialize counter
        add_immersion_water = imaging_settings.get_pref(
            "AddImmersionWater", valid_values=VALID_ADDIMERSIONWATER
        )

        if add_immersion_water:
            immersion_delivery_name = imaging_settings.get_pref("NameImmersionSystem")
            immersion_delivery = plate_object.get_immersionDeliverySystem(
                immersion_delivery_name
            )
            immersion_delivery.reset_counter()
            counter_stop_value = imaging_settings.get_pref(
                "WellsBeforeAddImmersionWater"
            )
            immersion_delivery.set_counter_stop_value(counter_stop_value)
            magnification_immersion_system = immersion_delivery.get_magnification()
            use_pump = imaging_settings.get_pref("UsePump", valid_values=VALID_USEPUMP)
            immersion_delivery.get_water(
                objective_magnification=magnification_immersion_system,
                verbose=verbose,
                automatic=use_pump,
            )

        # There is Zen's bug where the focus strategy keeps changing
        # to "Z value defined by tile set up" after being
        # repeatedly setup to "None".
        # To find a workaround for this for now,
        # this piece of code loads the experiment into Zen software so that
        # all the settings are visible and then asks the user to confirm those settings.
        # Here user can change the focus strategy in Zen
        # and it stays "None" throughout the scan
        experiment_name = imaging_settings.get_pref("Experiment")
        camera_id = imaging_settings.get_pref("Camera")
        # The reason for startimg live mode and stopping it is
        # because in Zen there is no way of just loading
        # the experiment in Zen software where all the settings are visible
        # unless you call an operation on it
        # This way, from the UI side,
        # it loads the experiment without doing anything (instant start & stop).
        sample_list[0].live_mode_start(camera_id, experiment_name)
        sample_list[0].live_mode_stop(camera_id)
        message.information_message(
            "Execute Experiment",
            "In Zen, check the following settings: \n\n"
            "1) Focus Strategy is set to none\n"
            "2) 1 tile region is set up with 66 tiles\n"
            "3) 10x objective is checked in the light path\n"
            "4) Hit live and check the brightness of TL\n"
            "5) Save Experiment",
        )
        current_well = None
        load = load_between_objects
        next_experiment_objects = []
        all_objects_dict = {}
        all_objects_list = []
        for sample_counter, sample_object in enumerate(sample_list, 1):
            # move stage and focus to new object
            if current_well != sample_object.get_well_object():
                if add_immersion_water:
                    immersion_delivery.count_and_get_water(
                        objective_magnification=magnification_immersion_system,
                        verbose=verbose,
                        automatic=use_pump,
                    )
                if load_between_wells:
                    load = True  # noqa
            # Removed, stage will move in scan_single_ROI
            # _, _, _ = sampleObject.move_to_zero(load = load, verbose = verbose)
            current_well = sample_object.get_well_object()
            # load = load_between_objects

            meta_dict = {
                "aics_well": current_well.get_name(),
                "aics_SampleType": sample_object.get_sample_type(),
                "aics_SampleName": sample_object.get_name(),
                "aics_barcode": sample_object.get_barcode(),
                "aics_repetition": repetition,
            }

            print(
                "{} {} is {} {} out of {} in {}. Repetition: {}".format(
                    sample_object.get_sample_type(),
                    sample_object.get_name(),
                    sample_object.get_sample_type(),
                    sample_counter,
                    len(sample_list),
                    plate_object.get_name(),
                    repetition,
                )
            )

            return_dict = self.scan_single_ROI(
                imaging_settings=imaging_settings,
                experiment_dict=experiment,
                sample_object=sample_object,
                reference_object=plate_object.get_reference_object(),
                image_path=image_path,
                meta_dict=meta_dict,
                verbose=verbose,
                number_selected_postions=len(next_experiment_objects),
                repetition=repetition,
            )
            images = return_dict["Image"]

            # Update the positions that are imaged - for substeps in 100X z-stack scans
            if isinstance(sample_object, samples.Cell):
                self.state.add_last_experiment_object(sample_object.get_name())
                # Autosave
                self.state.save_state()

            # Find objects for next experiment (e.g. cells within colonies)
            # check if output list was requested
            if experiment["Output"] != "None":
                # create tile
                x_border_list = (
                    []
                )  # list of border coordinates when tiles images are put together
                y_border_list = (
                    []
                )  # Used for segmentation later when recommending imageable locations

                tile_image = None
                try:
                    if len(images) > 1:
                        (
                            tile_image,
                            x_border_list,
                            y_border_list,
                        ) = sample_object.tile_images(images, imaging_settings)
                    else:
                        image = images[0]
                        tile_image = sample_object.get_microscope().load_image(
                            image, get_meta=True
                        )  # loads the image & metadata
                except Exception:
                    tile_image = None
                    raise

                # iterate over all requested output lists and find next objects
                for output_name, output_class in experiment["Output"].items():
                    next_experiment_objects_list = (
                        create_output_objects_from_parent_object(
                            find_type=find_type,
                            sample_object=sample_object,
                            imaging_settings=imaging_settings,
                            image=tile_image,
                            output_class=output_class,
                            app=app,
                            offset=(0, 0, 0),
                        )
                    )
                    next_experiment_objects = next_experiment_objects_list[0]
                    plate_object.add_to_image_dir(
                        list_name=output_name, sample_object=next_experiment_objects
                    )
                    # Populate objects for multiple wells/colonies/cells
                    # in one common dictionary
                    next_experiment_objects_dict = next_experiment_objects_list[1]
                    for object in next_experiment_objects_dict:
                        all_objects_dict[object] = next_experiment_objects_dict[object]

            # Wait for user interaction before continuing
            if wait_after_image["Status"]:
                if self.less_dialog:
                    # Fake user press (return False) if less dialog option is enabled
                    wait_after_image["Status"] = False
                else:
                    wait_after_image["Status"] = message.wait_message(
                        "Remove image on display and continue imaging"
                    )

            # close all images in microscope software
            sample_object.remove_images()

            if not return_dict["Continue"]:
                raise StopCollectingError(
                    "Stop collecting {}".format(sample_object.get_sample_type())
                )

        self.state.add_next_experiment_object(
            experiment["Experiment"], all_objects_list
        )
        # Autosave
        self.state.save_state()

        # Once the experiment with multiple objects is finished,
        # if interrupt is true, pickle and exit
        # If the experiment needs to be interrupted, save the positions and exit
        pickle_dict = {}
        pickle_dict["next_object_dict"] = all_objects_dict
        # Pickle the reference object - needed for continuation
        self.state.reference_object = plate_object.get_reference_object()
        pickle_dict["reference_object"] = self.state.reference_object
        # Autosave
        self.state.save_state()

        if (
            "Interrupt" in experiment.keys()
            and experiment["Interrupt"]
            and experiment["WorkflowType"] == "new"
        ):
            for object in all_objects_dict.values():
                while object.container is not None:
                    if isinstance(object.container, samples.PlateHolder):
                        object.container.microscope = None
                    object = object.container
            # Generate the file name for the particular interrupt
            filename = get_recovery_settings_path(
                experiment["RecoverySettingsFilePath"]
            )
            with open(filename, "wb") as f:
                pickle.dump(pickle_dict, f, pickle.HIGHEST_PROTOCOL)
                stop_script("Interruption Occurred. Data saved!")

    ################################################################################

    def segment_wells(
        self,
        imaging_settings,
        plate_holder_object,
        experiment,
        repetition,
        wait_after_image=None,
    ):
        """Writes a position list of segemented wells to a CSV file.

        Input:
         imaging_settings: dictionary with preferences

         plate_holder_object: Plate Holder object containing all the information

         experiment: dictionary with keys 'Experiment', Repetitions', 'Input',
         'Output', 'WorkflowList', 'WorflowType', 'ObjectsDict' and 'OriginalWorkflow'

         repetition: counter for time lapse experiments

         wait_after_image: wait preferences as dictionary to determine whether
         to wait after execution
          Image: Wait after each image

          Plate: Reset wait status after each plate

          Repetition: Reset wait status after each repetition

          Status: Show last image and allow adjustments if True,
          enter fully automatic mode if False

        Output:
         none
        """
        # Get all the well overview images in imageAICS format
        source_folder = imaging_settings.get_pref("SourceFolder")
        image_dir = get_images_path(imaging_settings, source_folder)
        images_name_list = [
            file for file in os.listdir(image_dir) if file.endswith(".czi")
        ]
        images_list = []

        # Get the well names and plates
        well_names_list = imaging_settings.get_pref("Wells", valid_values=VALID_WELLS)
        plates = plate_holder_object.get_plates()

        # To preserve the order defined in the preferences, we need to gp through
        # well list and create the image list in that particular order
        for well in well_names_list:
            # Get the image file name associated with this well
            for image_filename in images_name_list:
                # File name format = barcode_mag_date_wellid.czi
                well_name = (image_filename.split("_")[3]).split(".")[0]
                if well_name == well:
                    im_path = os.path.join(image_dir, image_filename)
                    aics_image = AICSImage(im_path, max_workers=1)
                    image_data = numpy.transpose(aics_image.data[0, 0, 0])
                    pixel_size = aics_image.get_physical_pixel_size()
                    image_meta = {
                        "Size": image_data.shape,
                        "aics_well": well_name,
                        "aics_filePath": im_path,
                        "PhysicalSizeX": pixel_size[0],
                        "PhysicalSizeY": pixel_size[1],
                    }
                    images_list.append(ImageAICS(image_data, image_meta))

        segmentation_info_dict = OrderedDict()
        # Segment each image and store the points found
        for plate_counter, (plate_name, plate_object) in enumerate(plates.items(), 1):
            for image in images_list:
                well_name = image.get_meta("aics_well")
                image_data = image.get_data()
                if image_data.ndim == 3:
                    # Remove the channel dimension before calling the location_picker
                    image_data = image_data[:, :, 0]
                # Call segment well module to find imageable positions
                filters = imaging_settings.get_pref("Filters")
                try:
                    canny_sigma = imaging_settings.get_pref("CannySigma")
                    canny_low_threshold = imaging_settings.get_pref("CannyLowThreshold")
                    remove_small_holes_area_threshold = imaging_settings.get_pref(
                        "RemoveSmallHolesAreaThreshold"
                    )
                    segmented_well = WellSegmentation(
                        image_data,
                        colony_filters_dict=filters,
                        mode="A",
                        canny_sigma=canny_sigma,
                        canny_low_threshold=canny_low_threshold,
                        remove_small_holes_area_threshold=remove_small_holes_area_threshold,  # noqa
                    )
                except Exception:
                    # if the preferences are not set, call with default ones
                    segmented_well = WellSegmentation(
                        image_data, colony_filters_dict=filters
                    )

                segmented_well.segment_and_find_positions()
                segmented_position_list = segmented_well.point_locations

                well_object = plate_object.get_well(well_name)
                segmentation_info_dict.update(
                    {
                        well_object: {
                            "image": image,
                            "position_list": segmented_position_list,
                        }
                    }
                )

        all_objects_dict = {}
        all_objects_list = []
        position_number = 1
        # List of lists to store the CSV file info
        # 1. To store the list of positions in the format specific
        # to Zen Blue software for 100X imaging.
        position_list_for_csv = []
        # 2. To store positions and respective well IDs for post processing
        # (splitting and aligning)
        image_location_list_for_csv = []
        # Initialize the csv file to store the positions after approval
        (
            position_csv_filepath,
            position_wellid_csv_filepath,
            failed_csv_filepath,
        ) = get_position_csv_path(imaging_settings)
        # DefaultZ since the z position is not available at this point
        default_z = imaging_settings.get_pref("PositionDefaultZ")
        position_list_for_csv.append(
            ["Name", "X", "Y", "Z", "Width", "Height", "ContourType"]
        )
        image_location_list_for_csv.append(
            ["Name", "WellID", "X", "Y", "Z", "Width", "Height", "ContourType"]
        )
        try:
            # Display each image for point approval

            for well_object in segmentation_info_dict.keys():
                image_data = segmentation_info_dict[well_object]["image"].get_data()
                segmented_position_list = segmentation_info_dict[well_object][
                    "position_list"
                ]
                # Store each image (with red +) in the target folder
                # location_list will be an empty list if user determines well is failed
                location_list = well_object.set_interactive_positions(
                    image_data, segmented_position_list, app
                )
                # save the image
                self.save_segmented_image(
                    imaging_settings,
                    image_data,
                    location_list,
                    plate_object,
                    well_object,
                )
                correct_location_list = convert_location_list(
                    location_list, image, "czi"
                )
                # Create cell objects and attach them properly to the parent object
                for key in experiment["Output"].keys():
                    output_name = key
                    output_class = experiment["Output"][key]
                class_ = getattr(samples, output_class)
                ind = 1
                new_objects_list = []
                new_objects_dict = {}
                for location in correct_location_list:
                    new_object_name = well_object.get_name() + "_{:04}".format(ind)
                    ind = ind + 1
                    new_object = class_(
                        new_object_name, [location[0], location[1], 0], well_object
                    )
                    new_objects_list.append(new_object)
                    new_objects_dict[new_object_name] = new_object
                    # Add P number to match the format being used in the pipeline
                    position_name = "P" + str(position_number)
                    # The positions in this list are relative to the center of well
                    # To get the absolute stage coordinates
                    # we will have to add well.zero position + plate.zero position
                    # And we will also need to add the objective offset
                    # for 100X to correct for parcentricity
                    x_obj_offset, y_obj_offset = self.get_objective_offsets(
                        plate_holder_object, 100
                    )
                    x_offset = (
                        well_object.xZero + well_object.container.xZero + x_obj_offset
                    )
                    y_offset = (
                        well_object.yZero + well_object.container.yZero + y_obj_offset
                    )
                    x_pos = location[0] + x_offset
                    y_pos = location[1] + y_offset
                    pos_info = [position_name, x_pos, y_pos, default_z]
                    well_info = [
                        position_name,
                        well_object.get_name(),
                        location[0],
                        location[1],
                        default_z,
                    ]
                    position_list_for_csv.append(pos_info)
                    image_location_list_for_csv.append(well_info)
                    position_number += 1
                well_object.add_samples(new_objects_dict)
                plate_object.add_to_image_dir(
                    list_name=output_name, sample_object=new_objects_list
                )
                all_objects_list.extend(new_objects_list)
                for object in new_objects_dict:
                    all_objects_dict[object] = new_objects_dict[object]
        finally:
            # write each position to the file
            with open(str(position_csv_filepath), mode="a") as position_file:
                position_writer = csv.writer(
                    position_file,
                    delimiter=",",
                    quotechar='"',
                    quoting=csv.QUOTE_MINIMAL,
                )
                for position in position_list_for_csv:
                    position_writer.writerow(position)
            with open(
                str(position_wellid_csv_filepath), mode="a"
            ) as position_wellid_file:
                position_wellid_writer = csv.writer(
                    position_wellid_file,
                    delimiter=",",
                    quotechar='"',
                    quoting=csv.QUOTE_MINIMAL,
                )
                for position_wellid in image_location_list_for_csv:
                    position_wellid_writer.writerow(position_wellid)
            with open(str(failed_csv_filepath), mode="a") as fail_position_file:
                fail_position_writer = csv.writer(
                    fail_position_file, quotechar='"', quoting=csv.QUOTE_MINIMAL
                )
                fail_position_writer.writerow(["well_id", "plate_barcode"])
                for failed in self.failed_wells:
                    fail_position_writer.writerow(
                        [failed.im_self.name, failed.im_self.container.barcode]
                    )

        self.state.add_next_experiment_object(
            experiment["Experiment"], all_objects_list
        )
        # Autosave
        self.state.save_state()
        pickle_dict = {}
        pickle_dict["next_object_dict"] = all_objects_dict
        self.state.reference_object = plate_holder_object.get_reference_object()
        pickle_dict["reference_object"] = self.state.reference_object
        # Autosave
        self.state.save_state()
        # Once the experiment with multiple objects is finished,
        # if interrupt is true, pickle and exit
        # If the experiment needs to be interrupted, save the positions and exit
        if (
            "Interrupt" in experiment.keys()
            and experiment["Interrupt"]
            and experiment["WorkflowType"] == "new"
        ):
            for object in all_objects_dict.values():
                # Remove the communication object because it can't be pickled
                while object.container is not None:
                    if isinstance(object.container, samples.PlateHolder):
                        object.container.microscope = None
                    object = object.container
            # Generate the file name for the particular interrupt
            filename = get_recovery_settings_path(
                experiment["RecoverySettingsFilePath"]
            )
            with open(filename, "w") as f:
                pickle.dump(pickle_dict, f, pickle.HIGHEST_PROTOCOL)
                stop_script("Interruption Occurred. Data saved!")
        daily_folder = get_valid_path_from_prefs(
            self.prefs, "PathDailyFolder", search_dir=True
        )
        pos_list_saver = PositionWriter(
            self.prefs.prefs["Info"]["System"],
            plate_object.get_barcode(),
            daily_folder,
        )
        position_list_for_csv = pos_list_saver.convert_to_stage_coords(
            positions_list=position_list_for_csv
        )
        pos_list_saver.write(
            converted=position_list_for_csv, dummy=self.prefs.prefs["PathDummy"]
        )

    def get_objective_offsets(self, plate_holder_object, magnification):
        """Function to return the objective offsets

        Input:
         plate_holder_object: Plate Holder object containing all the information

         magnification: integer defining which objective to get offsets for

        Output:
         x and y offsets for objectives
        """
        objective_changer = None
        x_obj_offset = 0
        y_obj_offset = 0
        component_dict = (
            plate_holder_object.microscope.microscope_components_ordered_dict
        )
        for component_name, component in component_dict.items():
            if isinstance(component, hardware_components.ObjectiveChanger):
                objective_changer = component
                break
        for objective, information in objective_changer.objective_information.items():
            if information["magnification"] == magnification:
                x_obj_offset = information["x_offset"]
                y_obj_offset = information["y_offset"]
                break
        return x_obj_offset, y_obj_offset

    ############################################################################

    def scan_plate(
        self,
        imaging_settings,
        plate_holder_object,
        experiment,
        repetition=0,
        wait_after_image=None,
    ):
        """Scan selected wells in plate to create overview.

        Input:
         imaging_settings: dictionary with preferences

         plate_holder_object: object of type PlateHolder
         from module sample with well information

         experiment: dictionary with keys 'Experiment', Repetitions', 'Input',
         'Output', 'WorkflowList', 'WorflowType', 'ObjectsDict' and 'OriginalWorkflow'

         repetition: counter for time lapse experiments

         wait_after_image: wait preferences as dictionary to determine whether
         to wait after execution
          Image: Wait after each image

          Plate: Reset wait status after each plate

          Repetition: Reset wait status after each repetition

          Status: Show last image and allow adjustments if True,
          enter fully automatic mode if False

        Output:
         none
        """
        # get names of wells to scan
        well_names_list = imaging_settings.get_pref("Wells", valid_values=VALID_WELLS)

        # iterate through all plates on plate holder
        plates = plate_holder_object.get_plates()

        try:
            for plate_counter, (plate_name, plate_object) in enumerate(
                plates.items(), 1
            ):
                if (
                    experiment["WorkflowType"] == "continue"
                    and experiment["ObjectsDict"] is not None
                ):
                    self.recover_previous_settings(
                        plate_holder_object, plate_object, experiment
                    )

                # get objects for wells in well_names_list
                wells_list = [
                    plate_object.get_well(well_name) for well_name in well_names_list
                ]
                self.scan_all_objects(
                    imaging_settings,
                    sample_list=wells_list,
                    plate_object=plate_object,
                    experiment=experiment,
                    repetition=repetition,
                    wait_after_image=wait_after_image,
                )
            # Wait for user interaction before continuing
            if wait_after_image["Plate"] and not wait_after_image["Status"]:
                wait_after_image["Plate"] = message.wait_message(
                    "New plate: do you want to stop after the next image?"
                )

        except StopCollectingError as error:
            error.error_dialog()

    ################################################################################

    def run_macro(
        self,
        imaging_settings,
        plate_holder_object,
        experiment=None,
        repetition=0,
        wait_after_image=None,
    ):
        """
        Input:
         imaging_settings: dictionary with preferences

         plate_holder_object: object of type PlateHolder
         from module sample with well information

         experiment: not used, necessary for compatibility

         repetition: not used, necessary for compatibility

         wait_after_image: not used, necessary for compatibility

        Output:
         none
        """
        # get name of macro within microscope software
        macro_name = imaging_settings.get_pref("MacroName")
        param_list = imaging_settings.get_pref("MacroParams")

        # Check for no params passed in preferences file
        # No param key, empty string,   empty list
        if not param_list:
            plate_holder_object.microscope.run_macro(macro_name)
            return

        # we require params as list, even if there is only one element
        elif isinstance(param_list, str):
            param_list = [param_list]

        if param_list[0].startswith("#"):
            # Ensure we parse if user gives # convention from ImageAICS
            i = ImageAICS()
            i.add_meta(
                {
                    "aics_barcode": self.read_first_barcode_from_plateholderobject(
                        plate_holder_object
                    )
                }
            )
            i.add_meta({"aics_microscope": plate_holder_object.microscope.name})
            param_list = [i.parse_file_template(param_list)]

        plate_holder_object.microscope.run_macro(macro_name, param_list)

    ################################################################################

    def read_first_barcode_from_plateholderobject(self, plate_holder_object):
        """Given plate_holder_object that can store one plate,
        return that plate's barcode.

        Input:
         plate_holder_object: object of type PlateHolder
         from module sample with well information

        Output:
         barcode: barcode of plate in plate_holder_object
        """
        return list(plate_holder_object.get_plates().values())[0].barcode

    def recover_previous_settings(self, plate_holder_object, plate_object, experiment):
        """Recover the the objects created in the last experiment
        and attach them to the right objects.

        Input:
         plate_holder_object: object of type PlateHolder
         from module sample with well information

         plate_object: object of class plate

         experiment: dictionary with keys 'Experiment', Repetitions', 'Input',
         'Output', 'WorkflowList', 'WorflowType', 'ObjectsDict' and 'OriginalWorkflow'

        Output:
         none
        """
        next_experiment_objects = []
        next_experiment_objects_dict = experiment["ObjectsDict"]
        # Add the microscope object to each plateholder that was removed
        # when the dict was pickled
        for object in next_experiment_objects_dict.values():
            while object.container is not None:
                if isinstance(object.container, samples.PlateHolder):
                    object.container.microscope = plate_holder_object.microscope
                object = object.container
        # Add the object to the plates
        for object in next_experiment_objects_dict:
            next_experiment_objects.append(next_experiment_objects_dict[object])
        list_name = experiment["Input"]
        plate_object.add_to_image_dir(
            list_name=list_name, sample_object=next_experiment_objects
        )

    ################################################################################

    def save_segmented_image(
        self, imaging_settings, image_data, location_list, plate_object, well_object
    ):
        """A simple function to save the positions that were a result of
        well segmentation and represent which positions will be imaged in 100X

        Input:
         imaging_settings: yaml preferences

         image_data: pixel data of the image

         location_list: list of positions approved by the user

         plate_object: plate object

         well_object: well object associated with the image

        Output:
         none
        """

        # Determine the folder where the images will be stored
        segmented_images_folder = imaging_settings.get_pref("Folder")
        segmented_image_dir = get_images_path(imaging_settings, segmented_images_folder)
        image_file_name_template = imaging_settings.get_pref("FileName")

        microscope_object = plate_object.container.microscope
        # make a copy because the pixel values are being changed only for saving part
        image_data_save = image_data.copy()
        # Plot the positions on the image as a set of white pixels
        for location in location_list:
            pixel_width = int(math.ceil(image_data.shape[0] / 1000)) + 2
            image_data_save[
                int(location[0]) - pixel_width : int(location[0]) + pixel_width,
                int(location[1]) - pixel_width : int(location[1]) + pixel_width,
            ] = 0
        image_aics = ImageAICS(image_data_save)
        info_dict = microscope_object.get_information()
        # Add relevant meta data
        image_aics.add_meta(
            {
                "aics_objectiveMagnification": int(
                    info_dict[plate_object.container.objective_changer_id][
                        "magnification"
                    ]
                )
            }
        )
        image_aics.add_meta({"aics_well": well_object.get_name()})
        image_aics.add_meta({"aics_barcode": plate_object.get_barcode()})
        date_short = str(date.today()).replace("-", "")
        image_aics.add_meta({"aics_dateStartShort": date_short})
        # Create the file path based on the meta data and save the image as a tiff file
        image_path = image_aics.create_file_name(
            (segmented_image_dir, image_file_name_template)
        )
        imsave(image_path, image_data_save.T, cmap="gray")

    ############################################################################

    def scan_samples(
        self,
        imaging_settings,
        plate_holder_object,
        experiment,
        repetition=0,
        wait_after_image=None,
    ):
        """Step through all plates and call scan_all_objects.

        Input:
         imaging_settings: dictionary with preferences

         plate_holder_object: object of type PlateHolder
         from module sample with well information

         experiment: dictionary with keys 'Experiment', Repetitions', 'Input',
         'Output', 'WorkflowList', 'WorflowType', 'ObjectsDict' and 'OriginalWorkflow'

         repetition: counter for time lapse experiments

         wait_after_image: wait preferences as dictionary to determine whether
         to wait after execution
          Image: Wait after each image

          Plate: Reset wait status after each plate

          Repetition: Reset wait status after each repetition

          Status: Show last image and allow adjustments if True,
          enter fully automatic mode if False

        Output:
         none
        """
        plates = plate_holder_object.get_plates()
        list_name = experiment["Input"]

        # Iterate through all plates on plate holder
        for plate_counter, (plate_name, plate_object) in enumerate(plates.items(), 1):
            sample_list = plate_object.get_from_image_dir(list_name)
            current_samples = copy.copy(sample_list)

            workflow_list = experiment["WorkflowList"]

            # Recover the positions that were imaged & the ones that need to be imaged
            if experiment["WorkflowType"] == "continue":

                # Recover positions to be imaged next
                if experiment["ObjectsDict"] is not None:
                    self.recover_previous_settings(
                        plate_holder_object, plate_object, experiment
                    )

                # Readjust the focus if continuing from scanCells
                # To readjust the focus get the experiment name
                # of the focusing block from the pref file
                update_z_function_name = imaging_settings.get_pref(
                    "DefineFocusBlockName"
                )
                if update_z_function_name is None:
                    update_z_function_name = "UpdatePlateWellZero_100x"
                settings = imaging_settings.get_parent_prefs().get_pref_as_meta(
                    update_z_function_name
                )
                workflow = imaging_settings.get_parent_prefs().get_pref("Workflow")
                update_plate_exp = [
                    update_plate_exp
                    for update_plate_exp in workflow
                    if update_plate_exp["Experiment"] == update_z_function_name
                ]
                experiment_dict = update_plate_exp[0]
                experiment_dict["RecoverySettingsFilePath"] = experiment[
                    "RecoverySettingsFilePath"
                ]
                experiment_dict["WorkflowList"] = experiment["WorkflowList"]
                experiment_dict["OriginalWorkflow"] = experiment["OriginalWorkflow"]
                if update_z_function_name not in workflow_list:
                    self.update_plate_z_zero(
                        settings, plate_holder_object, experiment_dict
                    )

                # Extract the sample list
                sample_list = plate_object.get_from_image_dir(list_name)
                current_samples = copy.copy(sample_list)
                # Update sample list by removing positions that were imaged already
                last_exp_objects = experiment["LastExpObjects"]
                if sample_list is not None:
                    for sample in sample_list:
                        name = sample.get_name()
                        if name in last_exp_objects:
                            current_samples.remove(sample)

            if current_samples is not None:
                self.scan_all_objects(
                    imaging_settings,
                    sampleList=current_samples,
                    plateObject=plate_object,
                    experiment=experiment,
                    repetition=repetition,
                    wait_after_image=wait_after_image,
                )

        # Update the reference object
        self.state.reference_object = plate_holder_object.get_reference_object()
        # Autosave
        self.state.save_state()

    ################################################################################

    def validate_experiment(self, imaging_settings, microscope_object):
        """
        If the experiment is not defined in Zen, give the user two tries to create it

        Input:
         image_settings: preferences from the yaml file

         microscope_object: microscope hardware object

        Output:
         none
        """

        # Initialize a Experiment object
        experiment_name = imaging_settings.get_pref("Experiment")

        # Check if the experiment is actually needed
        # (for example, segmentation doesn't need a Zen experiment)
        if experiment_name != "NoExperiment":
            experiment_path = get_experiment_path(imaging_settings)
            zen_experiment = hardware_components.Experiment(
                experiment_path, experiment_name, microscope_object
            )
            # Check if experiment exists in Zen blue
            # Give the user 2 tries to add the experiment in zen
            valid_experiment = zen_experiment.validate_experiment()
            num_try = 1
            while valid_experiment is False and num_try <= 2:
                message.information_message(
                    "Error",
                    "The experiment "
                    + experiment_name
                    + " is not defined in the Zen Software. Please add it now and "
                    "continue the experiment",
                )
                valid_experiment = zen_experiment.validate_experiment()
                num_try = num_try + 1
            if valid_experiment is False:
                stop_script(
                    "The Experiment "
                    + experiment_name
                    + " is not defined in the ZEN software. Exiting the software."
                )

    ################################################################################

    def control_autofocus(self, sample_object, imaging_settings):
        """Switch on/off autofocus.

        Input:
         sample_object: object of class inherited from ImagingSystem

         imaging_settings: settings derived from preferences file

        Output:
         none
        """
        use_auto_focus = imaging_settings.get_pref(
            "UseAutoFocus", valid_values=VALID_USEAUTOFOCUS
        )
        sample_object.set_use_autofocus(flag=use_auto_focus)

    ################################################################################
    #
    # Main function for microscope automation.
    # Start this function to start automation.
    #
    ################################################################################

    def microscope_automation(self):
        """Main script for Microscope automation.

        Input:
         none

        Output:
         none
        """ ""
        # start local logging
        error_handling.setup_logger(self.prefs)
        logger = logging.getLogger("MicroscopeAutomation.microscope_automation")
        logger.info("automation protocol started")

        # setup microscope
        microscope_object = setup_microscope.setup_microscope(self.prefs)

        # get list of experiments to perform on given plate
        workflow = self.prefs.get_pref("Workflow")

        # Setting up continuation
        # Dialog box
        continue_check_box_list = [
            ("Start new workflow", True),
            ("Continue last workflow", False),
        ]
        continue_dialog_box = message.check_box_message(
            "Please select workflow type:", continue_check_box_list, return_code=False
        )

        if continue_dialog_box[0][1] is True:
            workflow_type = "new"
        elif continue_dialog_box[1][1] is True:
            workflow_type = "continue"

        # Update workflow based on workflow type
        if workflow_type == "new":
            check_box_list = [
                ("{} x {}".format(i["Repetitions"], i["Experiment"]), True)
                for i in workflow
            ]
            new_check_box_list = message.check_box_message(
                "Please select experiment to execute:",
                check_box_list,
                return_code=False,
            )
            workflow = [
                workflow[i]
                for i, box in enumerate(new_check_box_list)
                if box[1] is True
            ]
            workflow_experiments = [step["Experiment"] for step in workflow]
            original_workflow = copy.copy(workflow_experiments)

        else:
            # Read the preference file and find which to continue from
            workflow_list = []
            for exp in workflow:
                workflow_list.append(exp["Experiment"])
            continue_experiment = message.pull_down_select_dialog(
                workflow_list, "Please select the experiment to continue from:"
            )
            workflow_experiments = [step["Experiment"] for step in workflow]
            original_workflow = copy.copy(workflow_experiments)
            # Update the experiment list with experiments starting
            # from continue_experiment and the ones after it
            for step in workflow:
                if step["Experiment"] != continue_experiment:
                    workflow_experiments.remove(step["Experiment"])
                else:
                    break

            # Update the workflow with new sets of experiments
            new_workflow = copy.deepcopy(workflow)
            for step in workflow:
                if step["Experiment"] not in workflow_experiments:
                    new_workflow.remove(step)
            workflow = new_workflow

            # Ask to pick the file again if the user picks blank file name
            pickle_file = ""
            while pickle_file == "":
                # Ask user which pickle file to recover settings from
                file_dir = get_valid_path_from_prefs(
                    self.prefs, "RecoverySettingsFilePath", search_dir=True
                )
                pickle_file = message.file_select_dialog(
                    file_dir,
                    filePattern="*.pickle",
                    comment="Please select the file to recover settings from.",
                )

            # Recover the objects dictionary
            file_path = os.path.normpath(os.path.join(file_dir, pickle_file))
            (
                next_objects_dict,
                reference_object,
                last_experiment_objects,
                hardware_status_dict,
            ) = self.state.recover_objects(file_path)
            # Set up the reference object
            for (
                key,
                value,
            ) in microscope_object.microscope_components_ordered_dict.items():
                if isinstance(value, hardware_components.AutoFocus):
                    reference_object.microscope = microscope_object
                    reference_object.container.microscope = microscope_object
                    value.set_focus_reference_obj(reference_object)
                    break
            # Set up the hardware status in the microscope object
            microscope_object.objective_ready_dict = hardware_status_dict
            # Set up objects dict for backtracking - remove unnecessary objects
            # won't work for planned interruption workflow
            # so only do it if its of the type unplanned
            # planned interruptions dict value are objects, unplanned ones are list
            objects_dict = OrderedDict()
            if isinstance(next_objects_dict.values(), list):
                try:
                    previous_experiment = workflow_list[
                        workflow_list.index(continue_experiment) - 1
                    ]
                    objects_list = next_objects_dict[previous_experiment]
                    for obj in objects_list:
                        objects_dict.update({obj.get_name(): obj})
                except Exception:
                    objects_dict = None
            else:
                objects_dict = next_objects_dict

        # setup plate holder with plate, wells, and colonies
        colony_file = None
        if "AddColonies" in workflow_experiments:
            add_colonies_prefs = self.prefs.get_pref_as_meta("AddColonies")
            colony_file_directory = get_colony_dir_path(self.prefs)
            file_name = add_colonies_prefs.get_pref("FileName")
            colony_file = message.file_select_dialog(
                colony_file_directory,
                filePattern=file_name,
                comment="""Please select csv file with colony data.""",
            )
            experiment = [
                experiment
                for experiment in workflow
                if experiment["Experiment"] == "AddColonies"
            ]
            workflow.remove(experiment[0])
            self.state.workflow_pos.append("AddColonies")

        plate_holder_object = setup_plate(self.prefs, colony_file, microscope_object)

        # Set up the Daily folder with plate barcode
        # Currently only one plate supported so barcode is extracted from that
        plates = plate_holder_object.get_plates()
        barcode = list(plates.keys())[-1]
        # Set up the high level folder with plate barcode
        get_daily_folder(self.prefs, barcode)
        # Set up Image Folders and Sub Folders
        image_folder = None
        # Get all the preferences
        for pref_block, func_prefs in self.prefs.prefs.items():
            if isinstance(func_prefs, dict):
                for pref, pref_value in func_prefs.items():
                    if pref == "Folder":
                        # Set up Folders for each function block
                        # Add set up for a single folder as well as a list of folders
                        if isinstance(pref_value, list):
                            image_folder = []
                            for folder in pref_value:
                                image_folder.append(
                                    get_images_path(self.prefs, folder, barcode)
                                )
                        else:
                            image_folder = get_images_path(
                                self.prefs, pref_value, barcode
                            )
                    # Set up the subfolders for each image folder
                    if pref == "SubFolders":
                        for subfolder in pref_value:
                            if isinstance(image_folder, list):
                                for folder in image_folder:
                                    set_up_subfolders(folder, subfolder)
                            else:
                                set_up_subfolders(image_folder, subfolder)

        # set-up meta data file object
        meta_data_file_path = get_meta_data_path(self.prefs, barcode)
        meta_data_format = self.prefs.get_pref("MetaDataFormat")
        meta_data_file_object = MetaDataFile(meta_data_file_path, meta_data_format)
        plate_holder_object.add_meta_data_file(meta_data_file_object)

        # cycle through all plates
        plate_objects = plate_holder_object.get_plates()
        for barcode, plate_object in plate_objects.items():
            # execute each measurement based on experiment in workflow
            for experiment in workflow:
                # attach additional parameters to experiment to propagate
                # into all the scanning functions
                experiment["WorkflowList"] = workflow_experiments
                experiment["OriginalWorkflow"] = original_workflow
                experiment["WorkflowType"] = workflow_type
                workflow_interrupt = self.prefs.get_pref("WorkflowInterrupt")
                if workflow_interrupt is not None:
                    if workflow_interrupt == experiment["Experiment"]:
                        experiment["Interrupt"] = True
                    else:
                        experiment["Interrupt"] = False

                recovery_settings_file_path = self.prefs.get_pref(
                    "RecoverySettingsFilePath"
                )

                if recovery_settings_file_path is not None:
                    experiment["RecoverySettingsFilePath"] = recovery_settings_file_path
                if workflow_type == "continue":
                    experiment["ObjectsDict"] = objects_dict
                    experiment["LastExpObjects"] = last_experiment_objects
                imaging_settings = self.prefs.get_pref_as_meta(experiment["Experiment"])
                self.validate_experiment(imaging_settings, microscope_object)

                # read wait preferences as dictionary to determine whether to wait after
                # Image: Wait after each image
                # Plate: Reset wait status after each plate
                # Repetition: Reset wait status after each repetition
                wait_after_image = imaging_settings.get_pref("Wait")
                wait_after_image["Status"] = wait_after_image["Image"]

                # set blocking/non-blocking for error messages
                # TODO - blocking is not used anywhere - inquire!
                blocking = imaging_settings.get_pref("Blocking", VALID_BLOCKING)  # noqa
                # get function to perform experiment
                function_name = imaging_settings.get_pref(
                    "FunctionName", valid_values=VALID_FUNCTIONNAME
                )
                function_to_use = getattr(self, function_name)
                # For segment wells, it is better to not display the dialog box
                # Reason - to make the workflow more seamless for the scientists
                # With this, they can leave after starting the 10X scan
                # and come back after segmentation to approve positions.
                # Instead of coming after the 10x scan to press ok for segment wells
                if function_name != "segment_wells":
                    if self.less_dialog:
                        # if less dialog option enabled, fake user press
                        # and continue (return code 1)
                        return_code = 1
                    else:
                        return_code = message.information_message(
                            "{}".format(experiment["Experiment"]), "", return_code=True
                        )

                # If return_code is 0, user pressed cancel
                else:
                    return_code = 1
                if return_code == 0:
                    self.state.save_state_and_exit()

                self.control_autofocus(plate_object, imaging_settings)
                self.state.hardware_status_dict = microscope_object.objective_ready_dict
                for i in range(experiment["Repetitions"]):
                    # execute experiment for each repetition
                    try:
                        args = inspect.getargspec(function_to_use)
                        if "repetition" in args.args:
                            function_to_use(
                                imaging_settings,
                                plate_holder_object,
                                experiment,
                                repetition=i,
                                wait_after_image=wait_after_image,
                            )
                        else:
                            function_to_use(
                                imaging_settings, plate_holder_object, experiment
                            )
                        self.state.workflow_pos.append(experiment["Experiment"])
                    except StopCollectingError as error:
                        error.error_dialog()
                        break
                    # Wait for user interaction before continuing
                    if (
                        wait_after_image["Repetition"]
                        and not wait_after_image["Status"]
                    ):
                        wait_after_image["Repetition"] = message.wait_message(
                            "New repetition: do you want to "
                            "stop after the next image?"
                        )
                        wait_after_image["Status"] = wait_after_image["Repetition"]

        print("Finished with plate scan")


def main():
    # Regularized argument parsing
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument("-p", "--preferences", help="path to the preferences file")
    args = arg_parser.parse_args()
    # Check if argument is given and is a valid path.
    if args.preferences is not None and os.path.isfile(args.preferences):
        prefs_path = args.preferences
    else:
        # Use UI file selector to prompt user for preferences file
        fSelect = tk.Tk()
        fSelect.withdraw()
        prefs_path = filedialog.askopenfilename(title="Select Preferences File to Use")

    # initialize the pyqt application object here (not in the location picker module)
    # as it only needs to be initialized once
    global app
    app = QtGui.QApplication([])
    try:
        mic = MicroscopeAutomation(prefs_path)
        mic.microscope_automation()
    except KeyboardInterrupt:
        pyqtgraph.exit()
        # mic.state.save_state_and_exit()
        sys.exit()
    print("Done")
    # Properly close pyqtgraph to avoid exit crash
    pyqtgraph.exit()


if __name__ == "__main__":
    main()
