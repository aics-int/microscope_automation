"""
Main script for Microscope automation
Created on Jun 9, 2016

@author: winfriedw
"""

# import libraries
# store all images as numpy arrays
import numpy
import math
# use sys library to abort script and for other system operations
import sys
# use shutil for file manipulations
import shutil
# use logging, setup will happen in module error_handling
import logging
import argparse
import string
import inspect
import copy
from collections import OrderedDict
from matplotlib.pyplot import imsave

# import external modules written for MicroscopeAutomation
try:
    from microscope_automation import preferences
    from microscope_automation import automation_messages_form_layout as message
    # from readBarcode import read_barcode
    from microscope_automation import error_handling
    from microscope_automation import setup_samples
    from microscope_automation import setup_microscope
    from microscope_automation.get_path import *
    from microscope_automation import samples
    from microscope_automation import hardware_control
    from microscope_automation import hardware_components
    from microscope_automation.metaDataFile import meta_data_file
    from microscope_automation.automation_exceptions import StopCollectingError, HardwareError, \
        HardwareDoesNotExistError, AutomationError, HardwareCommandNotDefinedError
    from microscope_automation.softwareState import State
    from microscope_automation.experiment_info import ZenExperiment
    from microscope_automation.findPositions import create_output_objects_from_parent_object, convert_location_list
    from microscope_automation.writeZENTilesExperiment import save_position_list

except:
    from . import preferences
    from . import automation_messages_form_layout as message
    # from readBarcode import read_barcode
    from . import error_handling
    from . import setup_samples
    from . import setup_microscope
    from .get_path import *
    from . import samples
    from . import hardware_control
    from . import hardware_components
    from .metaDataFile import meta_data_file
    from .automation_exceptions import StopCollectingError, HardwareError, AutomationError
    from .softwareState import State
    from .experiment_info import ZenExperiment
    from .findPositions import create_output_objects_from_parent_object, convert_location_list
    from .writeZENTilesExperiment import save_position_list
from .well_segmentation_refined import WellSegmentation

import pickle
import pyqtgraph
from pyqtgraph.Qt import QtGui
# from PySide import QtGui
from aicsimageio import AICSImage
from .image_AICS import ImageAICS
import csv

import tkinter as tk
import tkinter.filedialog as filedialog

# from Tkinter import filedialog

################################################################################
#
# constants with valid preferences values
#
################################################################################
VALID_FUNCTIONNAME = ['initialize_microscope',
                      'set_objective_offset',
                      'set_up_objectives',
                      'update_plate_zZero',
                      'calculate_plate_correction',
                      'calculate_all_wells_correction',
                      'setup_immersion_system',
                      'scan_plate',
                      'segment_wells',
                      'scan_samples',
                      'run_macro']
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
VALID_TILE_OBJECT = ['NoTiling', 'Fixed', 'ColonySize', 'Well', 'Automatic']
VALID_FINDTYPE = ['None', 'copy_zero_position', 'copy_image_position', 'Interactive', 'CenterMassCellProfiler',
                  'TwofoldDistanceMap',
                  'InteractiveDistanceMap']
VALID_WELLS = [x + str(y) for x in string.ascii_uppercase[0:8] for y in range(1, 13)]
VALID_BLOCKING = [True, False]


################################################################################
#
# local maintenance functions
#
################################################################################


def stop_script(messageText=None, allowContinue=False):
    """Stop processing and ask to leave automation script.

    Input:
     messageText: Message to user explaining why processing should be stopped.
     allowContinue: if True, allow user to continue. Default: False

    Script will stop all Microscope action immediately and ask user to stop execution of script or to continue.
    Returns if user selects 'Continue', otherwise calls sys.exit()
    """

    #     Microscope.stop_microscope()
    if allowContinue:
        if messageText is None:
            messageText = 'If you want to abort script press ok.\notherwise Continue'
        con = message.information_message('Exit script', messageText, returnCode=True)
    else:
        if messageText is None:
            messageText = 'Exit'
        con = message.information_message('Exit script', messageText, returnCode=False)
        con = 0

    if con == 0:
        # logger.info('User aborted operation')
        print('User aborted operation')
        sys.exit()


##############################################################################################


def set_up_objectives(set_up_settings, plate_holder_instance, _experiment):
    """Retrieve objectives mounted at microscope.

    Input:
     set_up_settings: dictionary with preferences
     plate_holder_instance: object of type PlateHolder from module sample with well information
     _experiment: not used, necessary for compatibility

    Return:
     none
    """
    # set debugging level
    verbose = set_up_settings.getPref('Verbose', validValues=VALID_VERBOSE)
    print('\n\nSet-up objectives (set_up_objectives)')

    # move stage and focus drive to safe position before switching objectives
    x_pos = set_up_settings.getPref('xSetUpObjectives')
    y_pos = set_up_settings.getPref('ySetUpObjectives')
    z_pos = set_up_settings.getPref('zSetUpObjectives')

    # retrieve information about mounted objectives
    # This part will detect all objectives defined in the touch pad software.
    microscope_instance = plate_holder_instance.get_microscope()
    objective_changer_instance = microscope_instance.get_microscope_object(
        plate_holder_instance.objective_changer_id)
    communication_object = microscope_instance.get_control_software().connection
    objectives_dict = objective_changer_instance.get_all_objectives(communication_object)
    objective_information = objective_changer_instance.objective_information

    # step through all objectives and determine parfocality and parcentrizity settings
    # create ordered dictionary with immersions to ensure that we start with air and end with oil objectives
    magnifications_list = sorted([magnification for magnification, objective in objectives_dict.items() if
                                  not objective['Name'] == 'none'], reverse=True)
    immersions_list = ['air', 'water', 'glycerol', 'oil']

    # the offset for each objective will be calculated relative to the highest resolution air objective
    # (water if air does not exist)
    x_reference_position = None
    y_reference_position = None
    z_reference_position = None

    for immersion in immersions_list:
        immersion_objectives = [(name, info) for name, info in objective_information.items() if
                                info['immersion'] == immersion]
        for magnification in magnifications_list:
            experiments = [(name, objective['experiment'], objective['camera'], objective['autofocus']) for
                           name, objective in immersion_objectives if objective['magnification'] == magnification]
            for name, experiment, camera, auto_focus in experiments:
                # store status of auto-focus and switch offs
                auto_focus_status = microscope_instance.set_microscope(settings_dict={auto_focus: {}})
                microscope_instance.set_microscope(settings_dict={auto_focus: {'use_auto_focus': False}})

                microscope_instance.live_mode(camera_id=camera,
                                              experiment=experiment,
                                              live=True)
                # make sure that correct objective is selected
                plate_holder_instance.move_to_abs_position(x=x_pos, y=y_pos, z=z_pos, load=False, verbose=verbose)
                message.operate_message(message='Please move to and focus on reference position.', returnCode=False)
                microscope_instance.live_mode(camera_id=camera,
                                              experiment=experiment,
                                              live=False)

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
                objective_information[name]['x_offset'] = x_offset
                objective_information[name]['y_offset'] = y_offset
                objective_information[name]['z_offset'] = z_offset

                print(('New offset values for objective {}:\nx_offset: {}\ny_offset: {}\nz_offset: {}'.format(name,
                                                                                                             x_offset,
                                                                                                             y_offset,
                                                                                                             z_offset)))
                microscope_instance.set_microscope(
                    settings_dict={auto_focus: {'use_auto_focus': auto_focus_status}})
    return


class MicroscopeAutomation(object):

    def __init__(self):
        self.prefs = preferences.Preferences(get_prefs_path())
        recovery_file_path = get_recovery_settings_path(self.prefs)

        # Create the recovery folder if it does not exist.
        rec_folder_path = os.path.dirname(recovery_file_path)
        if not os.path.exists(rec_folder_path):
            os.mkdir(rec_folder_path)
        # Create and save the pickle file
        self.state = State(recovery_file_path)
        self.state.save_state()
        self.less_dialog = self.prefs.getPref('LessDialog')
        if self.less_dialog is None:
            self.less_dialog = False

        self.failed_wells = []

    def get_well_object(self, plateHolderObject, plateName, well):
        """Return well object for given well.

        Input:
         plateHolderObject: object for plateholder that contains well
         plateName: name for plate, typically barcode
         well: name of well in form 'A1;

        Output:
         wellObject: object for well
        """
        # get dictionary of all plates associated with plate holder
        plateObjects = plateHolderObject.get_plates()

        # get object for plate with name plateName, typically the barcode
        plateObject = plateObjects[plateName]

        # get object for well with name well
        wellObject = plateObject.get_well(well)

        return wellObject

    ##############################################################################################

    def get_barcode_object(self, wellObject, barcode):
        """Return Barcode object for given well.

        Input:
         wellObject: object for well that contains barcode
         barcode: string of name for barcode

        Output:
         barcodeObject: object for barcode
        """

        # get dictionary of all samples associated with well
        sampleObjects = wellObject.get_samples()
        barcodeObject = sampleObjects[barcode]

        return barcodeObject

    ##############################################################################################

    def read_barcode(self, prefs, plateHolderObject, barcode, well=None, barcodeName=None):
        """Move manually to barcode, read and decipher barcode.

        Input:
         prefs: dictionary with preferences
         plateHolderObject: object of type PlateHolder from module sample with well information
         barcode: barcode for plate, often used as plate name
         well: well the barcode is associated with in format 'A1'. If empty ask user to navigate to barcode.

        Return:
         barcode: id encoded in barcode
        """
        # set debugging level
        verbose = prefs.getPref('Verbose', validValues=VALID_VERBOSE)
        print('\n\nStart reading barcode (read_barcode)')

        # Move to well and get wellObject
        # If no well is given retrieve it from preferences file and ask user to navigate to position.
        # If well is given, move automatically to well.
        if well is None:
            well = prefs.getPref('WellBarcode')
            barcodeName = prefs.getPref('NameBarcode')
            ms = message.operate_message("Please focus on barcode in well " + well)
            wellObject = self.get_well_object(plateHolderObject, barcode, well)
        else:
            wellObject = self.get_well_object(plateHolderObject, barcode, well)
            wellObject.move_to_well()

        # get barcode object
        barcodeObject = self.get_barcode_object(wellObject, barcodeName)

        # get name for microscope settings as defined within microscope software
        experiment = prefs.getPref('ExperimentBarcode')
        cameraID = prefs.getPref('CameraBarcode')

        # Define and if necessary create folder for images
        imageDir = get_references_path(prefs)

        # acquire image
        filePath = imageDir + barcodeName + '.czi'
        barcode = barcodeObject.read_barcode(experiment, cameraID, filePath, verbose=verbose)
        return barcode

    ##############################################################################################

    def calculate_all_wells_correction(self, prefs, plateHolderObject, experiment):
        """Calculate correction factor for well coordinate system for all wells.

        Input:
         prefs: dictionary with preferences
         plateHolderObject: object for plateholder that contains well
         experiment: dictionary with keys 'Experiment', Repetitions', 'Input', 'Output']
                         from workflow with information about specific experiment
        Output:
         none
        """

        # iterate through all plates on plate holder
        plates = plateHolderObject.get_plates()

        for plateName, plateObject in plates.items():
            wells = plateObject.get_wells()
            referenceWell_1 = prefs.getPref('WellCalibrateWell_1')
            measuredDiameter_1 = plateObject.get_well(referenceWell_1).get_measuredDiameter()

            referenceWell_2 = prefs.getPref('WellCalibrateWell_2')
            measuredDiameter_2 = plateObject.get_well(referenceWell_2).get_measuredDiameter()

            referenceWell_3 = prefs.getPref('WellCalibrateWell_3')
            measuredDiameter_3 = plateObject.get_well(referenceWell_3).get_measuredDiameter()

            measuredDiameter = numpy.mean([measuredDiameter_1, measuredDiameter_2, measuredDiameter_3])

            # set measuredDiameter for all wells to measuredDiameter from reference well
            # update calibration correction for all wells
            for wellName, wellObject in wells.items():
                wellObject.set_measuredDiameter(measuredDiameter)
                xCorrection = wellObject.get_measuredDiameter() / wellObject.get_setDiameter()
                yCorrection = xCorrection
                wellObject.set_correction(xCorrection, yCorrection)

    ##############################################################################################

    def setup_immersion_system(self, prefs, plate_holder_instance):
        """Setup system to deliver immersion water

        Input:
         prefs: dictionary with preferences
         plate_holder_instance: instance for plateholder that contains well

        Output:
         none
        """

        # TODO: this function should be part of pump.initialize() in module hardware_control.py
        # set debugging level
        verbose = prefs.getPref('Verbose', validValues=VALID_VERBOSE)
        print('\n\nSet-up water immersion system (setup_immersion_system)')

        # get immersion delivery system object
        immersion_delivery = plate_holder_instance.immersionDeliverySystem

        # move objective under immersion water outlet and assign position of outlet to immersionDelivery object
        focus_drive = plate_holder_instance.get_focus()
        load_position = focus_drive.get_load_position()

        # get communication object
        communication_object = plate_holder_instance.microscope.get_control_software().connection

        # Make sure load position is defined for focus drive
        if load_position is None:
            message.operate_message("Move objective to load position.")
            focus_drive.define_load_position(communication_object)
            load_position = focus_drive.get_load_position()

        x_pos = prefs.getPref('xImmersionSystem')
        y_pos = prefs.getPref('yImmersionSystem')

        # Execute experiment before moving stage to ensure that proper objective
        # (typically 10x) in in place to avoid collision.
        experiment = prefs.getPref('ExperimentSetupImmersionSystem')
        camera_id = prefs.getPref('CameraSetupImmersionSystem')

        immersion_delivery.execute_experiment(experiment,
                                              camera_id,
                                              filePath=None,
                                              verbose=verbose)
        immersion_delivery.move_to_abs_position(x_pos, y_pos,
                                                load_position,
                                                reference_object=plate_holder_instance.get_reference_object(),
                                                load=True, verbose=verbose)

        # take image of water outlet
        immersion_delivery.live_mode_start(camera_id, experiment)
        message.operate_message("Move objective under water outlet.\nUse flashlight from below stage to see outlet.")
        immersion_delivery.live_mode_stop(camera_id, experiment)

        # drop objective to load position and store position for water delivery
        # water will always be delivered with objective in load position to avoid collision
        focus_drive.goto_load(communication_object)
        immersion_delivery.set_zero(verbose=verbose)

        # move away from delivery system to avoid later collisions
        immersion_delivery.move_to_safe()
        magnification = prefs.getPref('MaginificationImmersionSystem')
        immersion_delivery.magnification = magnification

    ##############################################################################################

    def set_objective_offset(self, offsetPrefs, plate_holder_object, _experiment):
        """Set parfocality and parcentricity for objectives used in experiments.

        Input:
         offsetPrefs: dictionary with preferences based on preferences.yml
         plate_holder_object: plateHolderObject: object that contains all plates and all wells with sample information.
         _experiment: dictionary with keys 'Experiment', Repetitions', 'Input', 'Output'] (not used, for compatibility only)
                         from workflow with information about specific experiment

        Output:
         none
        """
        verbose = offsetPrefs.getPref('Verbose', validValues=VALID_VERBOSE)
        microscope_object = plate_holder_object.get_microscope()

        # retrieve list with experiments used to find objective offset and iterate through them
        experiments_list = offsetPrefs.getPref('ExperimentsList')

        # iterate through all plates on plate holder
        plates = plate_holder_object.get_plates()

        for plateName, plateObject in plates.items():
            for experiment in experiments_list:
                experiment_path = microscope_object.create_experiment_path(experiment)

                objective_changer_id = plateObject.get_objective_changer_id()
                objective_changer = microscope_object.get_microscope_object(objective_changer_id)
                objective_changer.set_init_experiment(experiment)

                microscope_object.initialize_hardware(
                    initialize_components_ordered_dict={objective_changer_id: {'no_find_surface'}},
                    reference_object=plateObject.get_reference_object(),
                    trials=3,
                    verbose=verbose)

    def set_up_Koehler(self, initializePrefs, plateObject):
        """Set up Koehler illumination.

        Input:
         initializePrefs: dictionary with preferences based on preferences.yml
         plateObject: object of class plate

        Output:
         none
        """
        # get settings from preferences.yml
        camera_id = initializePrefs.getPref('Camera')
        zen_experiment = initializePrefs.getPref('Experiment')
        well_name = initializePrefs.getPref('Well')
        load = initializePrefs.getPref('Load')
        use_reference = initializePrefs.getPref('UseReference', validValues=VALID_USEREFERENCE)
        use_auto_focus = initializePrefs.getPref('UseAutoFocus', validValues=VALID_USEAUTOFOCUS)
        trials = initializePrefs.getPref('NumberTrials')
        verbose = initializePrefs.getPref('Verbose')

        microscope_object = plateObject.get_microscope()
        well_object = plateObject.get_well(well_name)
        if well_object.microscope_is_ready(experiment=zen_experiment,
                                           reference_object=well_object.get_reference_object(),
                                           load=load,
                                           use_reference=use_reference,
                                           use_auto_focus=use_auto_focus,
                                           make_ready=True,
                                           trials=trials,
                                           verbose=verbose):
            well_object.move_to_zero(load=load, verbose=verbose)
        else:
            raise AutomationError(
                'Microscope not ready in update_plate_zZero with experiment {}'.format(zen_experiment))

        microscope_object.live_mode(camera_id, experiment=zen_experiment, live=True)
        message.operate_message('Set-up Koehler illumination.')
        microscope_object.live_mode(camera_id, experiment=zen_experiment, live=False)

    def initialize_microscope(self, initializePrefs, plate_holder_object, experiment):
        '''Update z positions for plate (upper side of coverslip)
        Set load and work positions for focus drive.

        Input:
         initializePrefs: dictionary with preferences
         plate_holder_object: object of type PlateHolder from module sample with well information
         experiment: dictionary with keys 'Experiment', Repetitions', 'Input', 'Output']
                         from workflow with information about specific experiment

        Return:
         none
        '''

        if initializePrefs.getPref('CopyColonyFile', validValues=VALID_COPYCOLONYFILES):
            # copy colony file
            colonyRemoteDir = get_colony_remote_dir_path(initializePrefs)
            if initializePrefs.getPref('AddColonies', validValues=VALID_ADDCOLONIES) is True:
                # Add colonies is in the list of experiment, show the options for csv file
                colonyRemoteFile = message.file_select_dialog(colonyRemoteDir, returnCode=True)
                # continue if user did not press cancel
                if colonyRemoteFile != 0:
                    sourcePath = os.path.normpath(os.path.join(colonyRemoteDir, colonyRemoteFile))
                    destinationPath = get_colony_dir_path(initializePrefs)
                    shutil.copy2(sourcePath, destinationPath)

        # initialize microscope hardware (e.g. auto-focus) for each plate within plateholder
        trials = initializePrefs.getPref('NumberTrials')
        verbose = initializePrefs.getPref('Verbose', validValues=VALID_VERBOSE)
        initialization_experiment = initializePrefs.getPref('Experiment')
        microscope_object = plate_holder_object.get_microscope()
        for barcode, plate in plate_holder_object.get_plates().items():
            if initializePrefs.getPref('Hardware', validValues=VALID_VERBOSE):
                # initialize_components_ordered_dict = None to initialize all components attached to microscope_object
                initialization_dict = OrderedDict([(plate.get_focus_id(), ['set_load']),
                                                   (plate.get_stage_id(), []),
                                                   (plate.get_objective_changer_id(), [])])
                #                                                    (plate.get_auto_focus_id(), ['no_find_surface'])])
                microscope_object.initialize_hardware(initialize_components_ordered_dict=initialization_dict,
                                                      reference_object=plate.get_reference_object(),
                                                      trials=trials,
                                                      verbose=verbose)

                for key, value in list(microscope_object.microscope_components_ordered_dict.items()):
                    if isinstance(value, hardware_control.AutoFocus):
                        self.state.reference_object = value.get_focus_reference_obj()
                        # Autosave
                        self.state.save_state()

            # set Koehler illumination
            if initializePrefs.getPref('Koehler', validValues=VALID_KOEHLER):
                self.set_up_Koehler(initializePrefs, plate)

        # ask user to enable laser safety
        if initializePrefs.getPref('LaserSafety', validValues=VALID_LASERSAFETY):
            message.operate_message(
                'Please enable laser safety.\nDisable parfocality and parcentralicy\nSecure sample from sliding.')

    ##############################################################################################

    def update_plate_zZero(self, imagingSettings, plateHolderObject, experiment):
        """Update z positions for plate (upper side of coverslip)
        Set load and work positions for focus drive.

        Input:
         imagingSettings: dictionary with preferences
         plateHolderObject: object of type PlateHolder from module sample with well information
         experiment: dictionary with keys 'Experiment', Repetitions', 'Input', 'Output']
                         from workflow with information about specific experiment

        Return:
         none
        """
        # set debugging level
        verbose = imagingSettings.getPref('Verbose', validValues=VALID_VERBOSE)
        print('\n\nStart to update z zero settings for plates (update_plate_zZero)')

        trials = imagingSettings.getPref('NumberTrials')
        # iterate through all plates on plate holder
        plates = plateHolderObject.get_plates()

        for plateName, plateObject in plates.items():
            # get preferences
            zenExperiment = imagingSettings.getPref('Experiment')
            cameraID = imagingSettings.getPref('Camera')
            well_name = imagingSettings.getPref('Well', validValues=VALID_WELLS)
            load = imagingSettings.getPref('Load', validValues=VALID_LOAD)
            use_reference = imagingSettings.getPref('UseReference', validValues=VALID_USEREFERENCE)
            use_auto_focus = imagingSettings.getPref('UseAutoFocus', validValues=VALID_USEAUTOFOCUS)
            # find zero z-position for plate (upper side of cover slip
            plateObject.live_mode_start(cameraID, zenExperiment)
            well_object = plateObject.get_well(well_name)
            microscope_object = well_object.get_microscope()

            if well_object.microscope_is_ready(experiment=zenExperiment,
                                               reference_object=well_object.get_reference_object(),
                                               load=load,
                                               use_reference=use_reference,
                                               use_auto_focus=use_auto_focus,
                                               make_ready=True,
                                               trials=trials,
                                               verbose=verbose):

                if plateObject.update_z_zero_pos:
                    plateObject.move_to_xyz(*plateObject.update_z_zero_pos, load=load, verbose=verbose)
                else:
                    well_object.move_to_zero(load=load, verbose=verbose)
            else:
                raise AutomationError(
                    'Microscope not ready in update_plate_zZero with experiment {}'.format(zenExperiment))

            # User has to set focus position for following experiments
            return_code = message.operate_message("Please set the focus for your acquisition", returnCode=True)

            if return_code == 0:
                self.state.save_state_and_exit()
            plateObject.live_mode_stop(cameraID, zenExperiment)

            # get actual z-position for plate and set as new z_zero position
            _x, _y, z_new = plateObject.get_container().get_pos_from_abs_pos(verbose=verbose)
            plateObject.update_zero(z=z_new, verbose=verbose)

            # store position used for focusing, will make later focusing with higher magnification easier
            plateObject.update_z_zero_pos = plateObject.get_pos_from_abs_pos(verbose=verbose)

            for key, value in list(plateHolderObject.microscope.microscope_components_ordered_dict.items()):
                if isinstance(value, hardware_control.AutoFocus):
                    self.state.reference_object = value.get_focus_reference_obj()
                    # Autosave
                    self.state.save_state()
                # Passage the previous experiment's objects if being called as a separate workflow experiment
                workflow_list = experiment['WorkflowList']
                original_workflow = experiment['OriginalWorkflow']
                if experiment['Experiment'] in workflow_list:
                    previous_experiment = original_workflow[original_workflow.index(experiment['Experiment']) - 1]
                    if previous_experiment in list(self.state.next_experiment_objects.keys()):
                        next_exp_objects = self.state.next_experiment_objects[previous_experiment]
                        self.state.add_next_experiment_object(experiment['Experiment'], next_exp_objects)
                        # Autosave
                        self.state.save_state()

    ##############################################################################################

    def calculate_plate_correction(self, prefs, plateHolderObject, experiment):
        """Calculate correction factor for plate coordinate system.

        Input:
         prefs: dictionary with preferences
         plateHolderObject: object for plate that contains well
         experiment: dictionary with keys 'Experiment', Repetitions', 'Input', 'Output']
                         from workflow with information about specific experiment
        Output:
         none
        """
        # set debugging level
        verbose = prefs.getPref('Verbose', validValues=VALID_VERBOSE)
        print('\n\nStart to acquire images for plate correction (calculate_plate_correction)')

        # iterate through all plates on plate holder
        plates = plateHolderObject.get_plates()

        for plateName, plateObject in plates.items():
            # Acquire images of edges of three reference wells  and use them to determine the well center
            # Get names of reference wells
            wellNames = [prefs.getPref("WellCalibrateWell_{}".format(i)) for i in range(1, 4)]

            # get well objects
            wellObjects = [plateObject.get_well(well) for well in wellNames]

            # get imaging parameters
            zenExperiment = prefs.getPref('Experiment')
            wellDiameter = prefs.getPref('WellDiameterCalibrateWell')
            cameraID = prefs.getPref('Camera')
            filePath = get_references_path(prefs)

            # Move objective to load position before moving to next calibration well?
            load = prefs.getPref('Load', validValues=VALID_LOAD)
            trials = prefs.getPref('NumberTrials')

            if not plateObject.microscope_is_ready(experiment=zenExperiment,
                                                   reference_object=plateObject.get_reference_object(),
                                                   load=load,
                                                   make_ready=True,
                                                   trials=trials,
                                                   verbose=verbose):
                raise AutomationError(
                    'Microscope not ready in update_plate_zZero with experiment {}'.format(zenExperiment))

            def find_well_center(wellObject, wellIndex, verbose=verbose):
                wellObject.move_delta_xyz(-wellDiameter / 2, 0, 0, load=False, verbose=verbose)
                wellObject.live_mode_start(cameraID=cameraID, experiment=zenExperiment)
                return_code = message.operate_message(
                    "Please focus with 10x on left edge of well {}\nto find zero position for plate {}"
                    .format(wellNames[wellIndex], plateObject.get_name()), returnCode=True)
                if return_code == 0:
                    self.state.save_state_and_exit()

                # find center of well in absolute stage coordinates
                return wellObjects[wellIndex].find_well_center_fine(experiment=zenExperiment, wellDiameter=wellDiameter,
                                                                    cameraID=cameraID, dictPath=filePath,
                                                                    verbose=verbose)

            # find center of wells
            wellCentersAbs = []

            # The stored z position for wells is not necessarily the actual one.
            # store the difference between the z-position on file and the last measured z-position as delta_z
            # apply this delta to the next well to be closer at the actual position
            delta_z = 0

            for ind, wellObject in enumerate(wellObjects):
                # Make sure that microscope is ready and correct objective is used
                wellObject.microscope_is_ready(experiment=zenExperiment,
                                               reference_object=wellObject.get_reference_object(),
                                               load=load,
                                               make_ready=True,
                                               trials=trials,
                                               verbose=verbose)
                wellObject.move_to_zero(load=load, verbose=verbose)
                wellObject.move_delta_xyz(0, 0, delta_z, load=False, verbose=verbose)
                xPosAbs, yPosAbs, zPosAbs = wellObject.get_abs_position()

                wellCenterAbs = find_well_center(wellObject,
                                                 ind,
                                                 verbose=verbose)
                # difference between actual z position of well and position on file
                delta_z = wellObject.get_abs_zero()[2] - wellCenterAbs[2]
                wellCentersAbs.append(wellCenterAbs)

            # Calculate values for transformation from plate holder coordinates to plate coordinates
            # get plate coordinates for well centers from zero positions of wells in plate coordinate
            plateCenters = [wellObjects[ind].get_zero() for ind in range(len(wellObjects))]

            # Subtract x and y values to get distance between wells
            xPlateDistance = plateCenters[1][0] - plateCenters[0][0]
            yPlateDistance = plateCenters[2][1] - plateCenters[1][1]

            # get plate holder coordinates for plate holder based on measured well centers
            plateHolderObject = plateObject.get_container()
            plateHolderCenters = [plateHolderObject.get_pos_from_abs_pos(*centers, verbose=verbose) for centers in
                                  wellCentersAbs]

            xPlateHolderDistance = plateHolderCenters[1][0] - plateHolderCenters[0][0]
            yPlateHolderDistance = plateHolderCenters[2][1] - plateHolderCenters[1][1]

            # calculate corrections
            xPlateHolderCorrection = xPlateHolderDistance / xPlateDistance
            yPlateHolderCorrection = yPlateHolderDistance / yPlateDistance
            zPlateHolderCorrection = 1

            # Describe not leveled plate as plane of form ax + bx + cx = d
            # Calculate 2 vectors from 3 points, and use cross product to find normal vector for plane <a, b, c>
            # Dot normal vector and point to get offset (d)
            p = [numpy.array(center).astype(numpy.float) for center in plateHolderCenters]
            v1 = p[1] - p[0]
            v2 = p[2] - p[0]
            plane = numpy.cross(v1, v2)

            # normalize normal vector to avoid large numbers
            normFactor = math.sqrt(plane[0] ** 2 + plane[1] ** 2 + plane[2] ** 2)
            norm = plane / normFactor
            # the plane can be described in the form ax + by +cz = d
            # a,b,c are the components of the normal vector and determine the slope
            zCorrectionXSlope = norm[0]
            zCorrectionYSlope = norm[1]
            zCorrectionZSlope = norm[2]

            # We will choose the offset d so that it equals 0 at the position
            #  where zZero was defined for the plate in update_plate_well_z_zero
            #  xPosAbs = prefs.getPref('xUpdatePlateWellZero')
            #  yPosAbs = prefs.getPref('yUpdatePlateWellZero')
            xPos, yPos, zPos = plateObject.get_pos_from_abs_pos(x=xPosAbs, y=yPosAbs, z=0, verbose=verbose)
            zCorrectionOffset = zCorrectionXSlope * xPos + zCorrectionYSlope * yPos

            plateObject.set_correction(x_correction=xPlateHolderCorrection, y_correction=yPlateHolderCorrection,
                                       z_correction=zPlateHolderCorrection,
                                       z_correction_x_slope=zCorrectionXSlope,
                                       z_correction_y_slope=zCorrectionYSlope,
                                       z_correction_z_slope=zCorrectionZSlope,
                                       z_correction_offset=zCorrectionOffset)

            # set zero position for plate
            # transform stage center coordinates into plate coordinates
            centerPlate = plateObject.get_pos_from_abs_pos(*wellCentersAbs[0], verbose=verbose)

            # set zero position for plate
            # transform stage center coordinates into plate coordinates
            centerPlate = plateObject.get_pos_from_abs_pos(*wellCentersAbs[0], verbose=verbose)

            # get center of well in plate coordinates.
            # This is equivalent to the distance to the center of well A1 = plate zero
            plateDistances = wellObjects[0].get_zero()
            # get center of well in plate coordinates.
            # This is equivalent to the distance to the center of well A1 = plate zero
            plateDistances = wellObjects[0].get_zero()

            plateOriginal = plateObject.get_zero()

            # Update zero position for plate
            plateObject.set_zero(plateOriginal[0] + (centerPlate[0] - plateDistances[0]),
                                 plateOriginal[1] + (centerPlate[1] - plateDistances[1]),
                                 plateOriginal[2], verbose=verbose)

            for j in range(len(wellNames)):
                print(("Center of well {} in stage coordinates: {}".format(wellNames[j],
                                                                          wellObjects[j].get_abs_zero(verbose=verbose))))
        print(("Zero position of plate {} in stage coordinates: {}".format(plateObject.get_name(),
                                                                           plateObject.get_abs_zero(verbose=verbose))))

    ##############################################################################################

    def scan_wells_zero(self, prefs, plateHolderObject, barcode):
        """Scan selected wells at center.

        Input:
         prefs: dictionary with preferences
         plateHolderObject: object of type PlateHolder from module sample with well information
         barcode: barcode for plate, often used as plate name

        Return:
         none

        This method is mainly used to test calibrations.
        """
        # set debugging level
        verbose = prefs.getPref('Verbose', validValues=VALID_VERBOSE)
        print('\n\nStart scanning well centers (scan_wells_zero)')

        # get names of wells to scan
        wellsString = prefs.getPref('WellsScanWellsZero')
        wells = [i.strip() for i in wellsString.split(',')]

        # name for settings as defined within microscope software
        experiment = prefs.getPref('ExperimentScanWellsZero')
        cameraID = prefs.getPref('CameraScanWellsZero')

        # Define and if necessary create folder for images
        imageDir = get_images_path(prefs)

        # iterate through all wells
        for well in wells:
            wellObject = self.get_well_object(plateHolderObject, barcode, well)
            wellObject.microscope_is_ready(experiment=experiment,
                                           reference_object=wellObject.get_reference_object(),
                                           load=False,
                                           make_ready=True,
                                           trials=3,
                                           verbose=verbose)
            x, y, z = wellObject.move_to_zero(verbose=verbose)
            imagePath = imageDir + well + '_zero.czi'
            wellObject.execute_experiment(experiment, cameraID, filePath=imagePath, verbose=verbose)
            print('Well: ', wellObject.name, ' at position (x,y,z): ', x, y, z)

    ##############################################################################################

    ##############################################################################################
    #
    # Scan colonies and cells
    #
    ##############################################################################################

    def scan_single_ROI(self, imagingSettings, experiment_dict, sampleObject, reference_object, imagePath, metaDict,
                        verbose=True, numberSelectedPostions=0, repetition=0):
        """Acquire tiled image as defined in posList

        Input:
         imagingSettings: dictionary with preferences
         sampleObject: object of a sample type (e.g. cell, colony) to be imaged
         reference_object: object used to set parfocality and parcentricity, typically a well in plate
         experiment_dict: The dictionary with full information about the experiment
         imagePath: string for filename with path to save image in original format
                    or tuple with string to directory and list with template for file name.
                    Default=None: no saving
         metaDict: directory with additional meta data, e.g. {'aics_well':, 'A1'}
         manualRefocus: if true allow user to reposition sample
         load: move objective to load position before moving stage
         verbose: if True print debug information (Default = True)
         numberSelectedPostions: number of positions collected so far
         repetition: counter for time lapse experiments

        Return:
         returnDict: dictionary of form {'Image': image, 'Continue': True/False}
        """
        if verbose:
            print('\n\nStart scanning ', sampleObject.get_name(), ' (scan_single_ROI)')

        # name for settings as defined within microscope software
        experiment = imagingSettings.getPref('Experiment')
        cameraID = imagingSettings.getPref('Camera')

        trials = imagingSettings.getPref('NumberTrials')
        use_auto_focus = imagingSettings.getPref('UseAutoFocus', validValues=VALID_USEAUTOFOCUS)
        use_reference = imagingSettings.getPref('UseReference', validValues=VALID_USEREFERENCE)

        # Allow user to manually adjust focus position selected by auto focus
        manualRefocus = imagingSettings.getPref('ManualRefocus', validValues=VALID_MANUELREFOCUS)
        if manualRefocus:
            manualRefocusAfterRepetitions = imagingSettings.getPref('ManualRefocusAfterRepetitions')
            if manualRefocusAfterRepetitions == 0:
                if repetition > 0:
                    manualRefocus = False
            else:
                if repetition % manualRefocusAfterRepetitions != 0:
                    manualRefocus = False

        if verbose:
            print('Image Object ', sampleObject.get_name())
        returnDict = {'Image': None, 'Continue': True}

        # check if microscope is ready for imaging and tries to execute missing initializations
        if not sampleObject.microscope_is_ready(experiment=experiment,
                                                reference_object=sampleObject.get_reference_object(),
                                                load=False,
                                                use_reference=use_reference,
                                                use_auto_focus=use_auto_focus,
                                                make_ready=True,
                                                trials=trials,
                                                verbose=verbose):
            raise HardwareError('Microscope not ready for imaging')

        sampleObject.move_to_zero(load=False, verbose=verbose)
        # manual focus adjustment. New value is stored for future use
        if manualRefocus:
            if verbose:
                print('\n\n============================== Before re-focus ========================================')
                print('Image object ', sampleObject.get_name(), 'Colony position before re-adjustment:', sampleObject.get_zero(), 'Stage position:', sampleObject.get_abs_position())

            # start live mode again because redefinition of auto-focus might stop live_mode
            sampleObject.live_mode_start(cameraID=cameraID, experiment=experiment)
            selectResult = message.select_message(
                'Focus on center of ' + sampleObject.get_name() + '\nCheck box below if you want to include position in further experiments.',
                count=numberSelectedPostions)
            sampleObject.live_mode_stop(cameraID=cameraID)

            returnDict['Continue'] = selectResult['Continue']
            if selectResult['Include']:
                # set center of sample object to new position
                sampleObject.set_zero(verbose=verbose)
                sampleObject.set_image(True)
            else:
                # label object to not be included in future imaging
                sampleObject.set_image(False)

            if verbose:
                print('\n\n============================== After re-focus ========================================')
                print('Image colony ', sampleObject.get_name(), 'Colony position after re-adjustment:', sampleObject.get_zero(), 'Stage position:', sampleObject.get_abs_position(), 'Included in future imaging: ', sampleObject.get_image())

        if (imagingSettings.getPref('SnapImage', validValues=VALID_SNAPIMAGE)
                or ((imagingSettings.getPref('FindType', validValues=VALID_FINDTYPE) is not None)
                    and (imagingSettings.getPref('FindType', validValues=VALID_FINDTYPE) != 'None')
                    and (imagingSettings.getPref('FindType', validValues=VALID_FINDTYPE) != 'Copy'))
                and sampleObject.get_image()):

            tile_object = imagingSettings.getPref('Tile', validValues=VALID_TILE_OBJECT)
            posList = sampleObject.get_tile_positions_list(imagingSettings, tile_type=tile_object, verbose=verbose)
            images = sampleObject.acquire_images(experiment,
                                                 cameraID,
                                                 reference_object=reference_object,
                                                 filePath=imagePath,
                                                 posList=posList,
                                                 load=False,
                                                 use_reference=use_reference,
                                                 use_auto_focus=use_auto_focus,
                                                 metaDict=metaDict,
                                                 verbose=verbose)
            returnDict['Image'] = images
        else:
            returnDict['Image'] = None
        return returnDict

    ##############################################################################################

    def scan_all_objects(self, imagingSettings, sampleList, plateObject, experiment, repetition=0,
                         wait_after_image=None):
        """Scan all objects in dictionary.

        Input:
         imagingSettings: dictionary with preferences
         sampleList: list with all objects to scan
         plateObject: object for plate objectList belongs to
         experiment: dictionary with keys 'Experiment', Repetitions', 'Input', 'Output']
                         from workflow with information about specific experiment
         repetition: counter for time lapse experiments
         wait_after_image: wait preferences as dictionary to determine whether to wait after
                        Image: Wait after each image
                        Plate: Reset wait status after each plate
                        Repetition: Reset wait status after each repetition


        Return:
         none
        """
        # get settings from imagingSettings
        loadBetweenObjects = imagingSettings.getPref('Load', validValues=VALID_LOAD)
        loadBetweenWells = imagingSettings.getPref('LoadBetweenWells', validValues=VALID_LOADBETWEENWELLS)
        verbose = imagingSettings.getPref('Verbose', validValues=VALID_VERBOSE)

        find_type = imagingSettings.getPref('FindType', validValues=VALID_FINDTYPE)
        tileImage = None

        # Define and if necessary create folder for images
        objectFolder = imagingSettings.getPref('Folder')
        imageDir = get_images_path(imagingSettings, objectFolder)
        imageFileNameTemplate = imagingSettings.getPref('FileName')
        imagePath = (imageDir, imageFileNameTemplate)

        # Get immersion water delivery object and initialize counter
        addImmersionWater = imagingSettings.getPref('AddImmersionWater', validValues=VALID_ADDIMERSIONWATER)

        if addImmersionWater:
            ImmersionDeliveryName = imagingSettings.getPref('NameImmersionSystem')
            immersionDelivery = plateObject.get_immersionDeliverySystem(ImmersionDeliveryName)
            _ = immersionDelivery.reset_counter()
            counterStopValue = imagingSettings.getPref('WellsBeforeAddImmersionWater')
            immersionDelivery.set_counter_stop_value(counterStopValue)
            MaginificationImmersionSystem = immersionDelivery.get_magnification()
            usePump = imagingSettings.getPref('UsePump', validValues=VALID_USEPUMP)
            immersionDelivery.get_water(objectiveMagnification=MaginificationImmersionSystem, verbose=verbose,
                                        automatic=usePump)

        # There is Zen's bug where the focus strategy keeps changing to "Z value defined by tile set up" after being
        # repeatedly setup to "None".
        # To find a workaround for this for now, this piece of code loads the experiment into Zen software so that
        # all the settings are visible and then asks the user to confirm those settings. Here user can change the
        # focus strategy in Zen and it stays "None" throughout the scan
        experiment_name = imagingSettings.getPref('Experiment')
        cameraID = imagingSettings.getPref('Camera')
        # The reason for startimg live mode and stopping it is because in Zen there is no way of just loading
        # the experiment in Zen software where all the settings are visible unless you call an operation on it
        # This way, from the UI side, it loads the experiment without doing anything (instant start & stop).
        try:
            sampleList[0].live_mode_start(cameraID, experiment_name)
            sampleList[0].live_mode_stop(cameraID)
        except HardwareCommandNotDefinedError:
            # not all microscopes have live mode implemented
            pass

        message.information_message('Execute Experiment', 'In Zen, check the following settings: \n\n'
                                                          '1) Focus Strategy is set to none\n'
                                                          '2) 1 tile region is set up with 66 tiles\n'
                                                          '3) 10x objective is checked in the light path\n'
                                                          '4) Hit live and check the brightness of TL\n'
                                                          '5) Save Experiment')
        currentWell = None
        load = loadBetweenObjects
        nextExperimentObjects = []
        all_objects_dict = {}
        all_objects_list = []
        for sampleCounter, sampleObject in enumerate(sampleList, 1):
            # move stage and focus to new object
            if currentWell != sampleObject.get_well_object():
                if addImmersionWater:
                    immersionDelivery.count_and_get_water(objectiveMagnification=MaginificationImmersionSystem,
                                                          verbose=verbose, automatic=usePump)
                if loadBetweenWells:
                    load = True
                    # Removed, stage will move in scan_single_ROI
            #             _, _, _ = sampleObject.move_to_zero(load = load, verbose = verbose)
            currentWell = sampleObject.get_well_object()
            load = loadBetweenObjects

            metaDict = {'aics_well': currentWell.get_name(),
                        'aics_SampleType': sampleObject.get_sample_type(),
                        'aics_SampleName': sampleObject.get_name(),
                        'aics_barcode': sampleObject.get_barcode(),
                        'aics_repetition': repetition}

            print(('{} {} is {} {} out of {} in {}. Repetition: {}'.format(sampleObject.get_sample_type(),
                                                                           sampleObject.get_name(),
                                                                           sampleObject.get_sample_type(),
                                                                           sampleCounter,
                                                                           len(sampleList),
                                                                           plateObject.get_name(),
                                                                           repetition)))

            returnDict = self.scan_single_ROI(imagingSettings=imagingSettings,
                                              experiment_dict=experiment,
                                              sampleObject=sampleObject,
                                              reference_object=plateObject.get_reference_object(),
                                              imagePath=imagePath,
                                              metaDict=metaDict,
                                              verbose=verbose,
                                              numberSelectedPostions=len(nextExperimentObjects),
                                              repetition=repetition)
            images = returnDict['Image']

            # Update the positions that are imaged - for substeps in 100X z-stack scans
            if isinstance(sampleObject, samples.Cell):
                self.state.add_last_experiment_object(sampleObject.get_name())
                # Autosave
                self.state.save_state()

            # Find objects for next experiment (e.g. cells within colonies)
            # check if output list was requested
            if experiment['Output'] != 'None':
                # create tile
                x_border_list = []  # list of border coordinates when tiles images are put together
                y_border_list = []  # Used for segmentation later when recommending imageable locations

                tileImage = None
                try:
                    if len(images) > 1:
                        tileImage, x_border_list, y_border_list = sampleObject.tile_images(images, imagingSettings)
                    else:
                        image = images[0]
                        tileImage = sampleObject.get_microscope().load_image(image,
                                                                             getMeta=True)  # loads the image & metadata
                except:
                    tileImage = None
                    raise

                # iterate over all requested output lists and find next objects
                for output_name, output_class in experiment['Output'].items():
                    nextExperimentObjectsList = create_output_objects_from_parent_object(find_type=find_type,
                                                                                         sample_object=sampleObject,
                                                                                         imaging_settings=imagingSettings,
                                                                                         image=tileImage,
                                                                                         output_class=output_class,
                                                                                         app=app,
                                                                                         offset=(0, 0, 0))
                    nextExperimentObjects = nextExperimentObjectsList[0]
                    plateObject.add_to_image_dir(listName=output_name,
                                                 sampleObject=nextExperimentObjects)
                    # Populate objects for multiple wells/colonies/cells in one common dictionary
                    nextExperimentObjectsDict = nextExperimentObjectsList[1]
                    for object in nextExperimentObjectsDict:
                        all_objects_dict[object] = nextExperimentObjectsDict[object]

            # Wait for user interaction before continuing
            if wait_after_image['Status']:
                if self.less_dialog:
                    # Fake user press (return False) if less dialog option is enabled
                    wait_after_image['Status'] = False
                else:
                    wait_after_image['Status'] = message.wait_message('Remove image on display and continue imaging')

            # close all images in microscope software
            sampleObject.remove_images(tileImage)

            if not returnDict['Continue']:
                raise StopCollectingError('Stop collecting {}'.format(sampleObject.get_sample_type()))

        self.state.add_next_experiment_object(experiment['Experiment'], all_objects_list)
        # Autosave
        self.state.save_state()

        # Once the experiment with multiple objects is finished, if interrupt is true, pickle and exit
        # If the experiment needs to be interrupted, save the positions and exit
        pickle_dict = {}
        pickle_dict["next_object_dict"] = all_objects_dict
        # Pickle the reference object - needed for continuation
        for key, value in list(plateObject.container.microscope.microscope_components_ordered_dict.items()):
            try:
                if isinstance(value, hardware_control.AutoFocus):
                    pickle_dict["reference_object"] = value.get_focus_reference_obj()
                    self.state.reference_object = value.get_focus_reference_obj()
                    # Autosave
                    self.state.save_state()
            except AttributeError as exception:
                # pass if microscope has no autofocus
                pass
        if 'Interrupt' in list(experiment.keys()) and experiment['Interrupt'] and experiment['WorkflowType'] == 'new':
            for object in list(all_objects_dict.values()):
                while object.container is not None:
                    if isinstance(object.container, samples.PlateHolder):
                        object.container.microscope = None
                    object = object.container
            # Generate the file name for the particular interrupt
            filename = get_recovery_settings_path(experiment['RecoverySettingsFilePath'])
            with open(filename, 'wb') as f:
                pickle.dump(pickle_dict, f, pickle.HIGHEST_PROTOCOL)
                stop_script("Interruption Occurred. Data saved!")

    ##############################################################################################

    def segment_wells(self, imagingSettings, plateHolderObject, experiment, repetition, wait_after_image=None):

        # Get all the well overview images in ImageAICS format
        source_folder = imagingSettings.getPref('SourceFolder')
        image_dir = get_images_path(imagingSettings, source_folder)
        images_name_list = [file for file in os.listdir(image_dir) if file.endswith(".czi")]
        images_list = []

        # Get the well names and plates
        wellNamesList = imagingSettings.getPref('Wells', validValues=VALID_WELLS)
        plates = plateHolderObject.get_plates()

        # To preserve the order defined in the preferences, we need to gp through well list
        # and create the image list in that particular order
        for well in wellNamesList:
            # Get the image file name associated with this well
            for image_filename in images_name_list:
                # File name format = barcode_mag_date_wellid.czi
                well_name = (image_filename.split('_')[3]).split('.')[0]
                if well_name == well:
                    im_path = os.path.join(image_dir, image_filename)
                    aics_image = AICSImage(im_path, max_workers=1)
                    image_data = numpy.transpose(aics_image.data[0, 0, 0])
                    pixel_size = aics_image.get_physical_pixel_size()
                    image_meta = {'Size': image_data.shape, 'aics_well': well_name, 'aics_filePath': im_path,
                                  'PhysicalSizeX': pixel_size[0], 'PhysicalSizeY': pixel_size[1]}
                    images_list.append(ImageAICS(image_data, image_meta))

        segmentation_info_dict = OrderedDict()
        # Segment each image and store the points found
        for plateCounter, (plateName, plateObject) in enumerate(iter(plates.items()), 1):
            for image in images_list:
                well_name = image.get_meta('aics_well')
                image_data = image.get_data()
                if image_data.ndim == 3:
                    # Remove the channel dimension before calling the location_picker module
                    image_data = image_data[:, :, 0]
                # Call segment well module to find imageable positions
                filters = imagingSettings.getPref('Filters')
                try:
                    canny_sigma = imagingSettings.getPref('CannySigma')
                    canny_low_threshold = imagingSettings.getPref('CannyLowThreshold')
                    remove_small_holes_area_threshold = imagingSettings.getPref('RemoveSmallHolesAreaThreshold')
                    segmented_well = WellSegmentation(image_data, colony_filters_dict=filters, mode='A',
                                                      canny_sigma=canny_sigma, canny_low_threshold=canny_low_threshold,
                                                      remove_small_holes_area_threshold=remove_small_holes_area_threshold)
                except:
                    # if the preferences are not set, call with default ones
                    segmented_well = WellSegmentation(image_data, colony_filters_dict=filters)

                segmented_well.segment_and_find_positions()
                segmented_position_list = segmented_well.point_locations

                well_object = plateObject.get_well(well_name)
                segmentation_info_dict.update({well_object: {"image": image, "position_list": segmented_position_list}})

        all_objects_dict = {}
        all_objects_list = []
        position_number = 1
        # List of lists to store the CSV file info
        # 1. To store the list of positions in the format specific to Zen Blue software for 100X imaging.
        position_list_for_csv = []
        # 2. To store positions and respective well IDs for post processing (splitting and aligning)
        image_location_list_for_csv = []
        # Initialize the csv file to store the positions after approval
        position_csv_filepath, position_wellid_csv_filepath, failed_csv_filepath = get_position_csv_path(
            imagingSettings)
        # DefaultZ since the z position is not available at this point
        defualtZ = imagingSettings.getPref('PositionDefaultZ')
        position_list_for_csv.append(['Name', 'X', 'Y', 'Z', 'Width', 'Height', 'ContourType'])
        image_location_list_for_csv.append(['Name', 'WellID', 'X', 'Y', 'Z', 'Width', 'Height', 'ContourType'])
        try:
            # Display each image for point approval

            for well_object in list(segmentation_info_dict.keys()):
                image_data = segmentation_info_dict[well_object]["image"].get_data()
                segmented_position_list = segmentation_info_dict[well_object]["position_list"]
                # Store each image (with red +) in the target folder
                # location_list will be an empty list if user determines well is failed
                location_list = well_object.set_interactive_positions(image_data, segmented_position_list, app)
                # save the image
                self.save_segmented_image(imagingSettings, image_data, location_list, plateObject, well_object)
                correct_location_list = convert_location_list(location_list, image, 'czi')
                # Create cell objects and attach them properly to the parent object
                for key in list(experiment['Output'].keys()):
                    output_name = key
                    output_class = experiment['Output'][key]
                class_ = getattr(samples, output_class)
                ind = 1
                new_objects_list = []
                new_objects_dict = {}
                for location in correct_location_list:
                    new_object_name = well_object.get_name() + "_{:04}".format(ind)
                    ind = ind + 1
                    new_object = class_(new_object_name, [location[0], location[1], 0], well_object)
                    new_objects_list.append(new_object)
                    new_objects_dict[new_object_name] = new_object
                    # Add P number to match the format currently being used in the pipeline
                    position_name = 'P' + str(position_number)
                    # The positions in this list are relative to the center of well
                    # To get the absolute stage coordinates - we will have to add well.zero position + plate.zero position
                    # And we will also need to add the objective offset for 100X to correct for parcentricity
                    x_obj_offset, y_obj_offset = self.get_objective_offsets(plateHolderObject, 100)
                    x_offset = well_object.xZero + well_object.container.xZero + x_obj_offset
                    y_offset = well_object.yZero + well_object.container.yZero + y_obj_offset
                    x_pos = location[0] + x_offset
                    y_pos = location[1] + y_offset
                    pos_info = [position_name, x_pos, y_pos, defualtZ]
                    well_info = [position_name, well_object.get_name(), location[0], location[1], defualtZ]
                    position_list_for_csv.append(pos_info)
                    image_location_list_for_csv.append(well_info)
                    position_number += 1
                well_object.add_samples(new_objects_dict)
                plateObject.add_to_image_dir(listName=output_name, sampleObject=new_objects_list)
                all_objects_list.extend(new_objects_list)
                for object in new_objects_dict:
                    all_objects_dict[object] = new_objects_dict[object]
        finally:
            # write each position to the file
            with open(str(position_csv_filepath), mode='ab') as position_file:
                position_writer = csv.writer(position_file, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
                for position in position_list_for_csv:
                    position_writer.writerow(position)
            with open(str(position_wellid_csv_filepath), mode='ab') as position_wellid_file:
                position_wellid_writer = csv.writer(position_wellid_file, delimiter=',', quotechar='"',
                                                    quoting=csv.QUOTE_MINIMAL)
                for position_wellid in image_location_list_for_csv:
                    position_wellid_writer.writerow(position_wellid)
            with open(str(failed_csv_filepath), mode='ab') as fail_position_file:
                fail_position_writer = csv.writer(fail_position_file, quotechar='"', quoting=csv.QUOTE_MINIMAL)
                fail_position_writer.writerow(["well_id", "plate_barcode"])
                for failed in self.failed_wells:
                    fail_position_writer.writerow([failed.__self__.name, failed.__self__.container.barcode])

        self.state.add_next_experiment_object(experiment['Experiment'], all_objects_list)
        # Autosave
        self.state.save_state()
        pickle_dict = {}
        pickle_dict["next_object_dict"] = all_objects_dict
        # pickle the reference object - needed for continuation
        for key, value in list(plateHolderObject.microscope.microscope_components_ordered_dict.items()):
            if isinstance(value, hardware_control.AutoFocus):
                pickle_dict["reference_object"] = value.get_focus_reference_obj()
                self.state.reference_object = value.get_focus_reference_obj()
                # Autosave
                self.state.save_state()
        # Once the experiment with multiple objects is finished, if interrupt is true, pickle and exit
        # If the experiment needs to be interrupted, save the positions and exit
        if 'Interrupt' in list(experiment.keys()) and experiment['Interrupt'] and experiment['WorkflowType'] == 'new':
            for object in list(all_objects_dict.values()):
                # Remove the communication object because it can't be pickled
                while object.container is not None:
                    if isinstance(object.container, samples.PlateHolder):
                        object.container.microscope = None
                    object = object.container
            # Generate the file name for the particular interrupt
            filename = get_recovery_settings_path(experiment['RecoverySettingsFilePath'])
            with open(filename, 'wb') as f:
                pickle.dump(pickle_dict, f, pickle.HIGHEST_PROTOCOL)
                stop_script("Interruption Occurred. Data saved!")
        pos_list_saver = save_position_list(self.prefs.prefs["Info"]["System"], plateObject.barcode,
                                            self.prefs.prefs["PathDailyFolder"])
        position_list_for_csv = pos_list_saver.convert_to_stage_coords(positions_list=position_list_for_csv)
        pos_list_saver.write(converted=position_list_for_csv, dummy=self.prefs.prefs["PathDummy"])

    def get_objective_offsets(self, plateHolderObject, magnification):
        """
        Function to return the objective offsets
        :param plateHolderObject: Plate Holder object containing all the information
        :param magnification: Int defining which objective to get offsets for
        :return: x and y offsets for objectives
        """
        objective_changer = None
        x_obj_offset = 0
        y_obj_offset = 0
        component_dict = plateHolderObject.microscope.microscope_components_ordered_dict
        for component_name, component in component_dict.items():
            if isinstance(component, hardware_control.ObjectiveChanger):
                objective_changer = component
                break
        for objective, information in objective_changer.objective_information.items():
            if information['magnification'] == magnification:
                x_obj_offset = information['x_offset']
                y_obj_offset = information['y_offset']
                break
        return x_obj_offset, y_obj_offset

    ##############################################################################################

    def scan_plate(self, imagingSettings, plateHolderObject, experiment, repetition=0, wait_after_image=None):
        """Scan selected wells in plate to create overview.

        Input:
         imagingSettings: dictionary with preferences
         plateHolderObject: object of type PlateHolder from module sample with well information
         experiment: dictionary with keys 'Experiment', Repetitions', 'Input', 'Output']
                         from workflow with information about specific experiment
         repetition: counter for time lapse experiments
         wait_after_image: wait preferences as dictionary to determine whether to wait after
                            Image: Wait after each image
                            Plate: Reset wait status after each plate
                            Repetition: Reset wait status after each repetition

        Return:
         none
        """

        # get names of wells to scan
        wellNamesList = imagingSettings.getPref('Wells', validValues=VALID_WELLS)

        # iterate through all plates on plate holder
        plates = plateHolderObject.get_plates()

        try:
            for plateCounter, (plateName, plateObject) in enumerate(iter(plates.items()), 1):
                if experiment['WorkflowType'] == 'continue' and experiment['ObjectsDict'] is not None:
                    self.recover_previous_settings(plateHolderObject, plateObject, experiment)

                # get objects for wells in welNamesList
                wellsList = [plateObject.get_well(wellName) for wellName in wellNamesList]
                self.scan_all_objects(imagingSettings,
                                      sampleList=wellsList,
                                      plateObject=plateObject,
                                      experiment=experiment,
                                      repetition=repetition,
                                      wait_after_image=wait_after_image)
            # Wait for user interaction before continuing
            if wait_after_image['Plate'] and not wait_after_image['Status']:
                wait_after_image['Plate'] = message.wait_message('New plate: do you want to stop after the next image?')

        except StopCollectingError as error:
            error.error_dialog()

    ##############################################################################################
    def run_macro(self, imagingSettings, plateHolderObject, experiment, repetition=0, wait_after_image=None,
                  macro_param=None):
        """

        :param imagingSettings: Preference Files Settings
        :param plateHolderObject: PlateHolder Settings
        :param experiment:  Not being used - But needs to follow the function signature structure
        :param repetition:  Not being used - But needs to follow the function signature structure
        :param wait_after_image: Not being used - But needs to follow the function signature structure
        :param macro_param: Parameter to use when calling zen macro
        :return:
        """
        # get name of macro within microscope software
        macro_name = imagingSettings.getPref('MacroName')

        # create folders needed for macro if they do not exist
        folder_list = imagingSettings.getPref('Folder')

        param_list = imagingSettings.getPref('MacroParams')

        # Check for no params passed in preferences file
        # No param key,      empty string,   empty list
        if not param_list:
            plateHolderObject.microscope.run_macro(macro_name)
            return

        # we require params as list, even if there is only one element
        elif isinstance(param_list, str):
            param_list = [param_list]

        if param_list[0].startswith('#'):
            # Ensure we parse if user gives # convention from ImageAICS
            i = ImageAICS()
            i.add_meta({"aics_barcode": self.read_first_barcode_from_plateholderobject(plateHolderObject)})
            i.add_meta({"aics_microscope": plateHolderObject.microscope.name})
            param_list = [i.parse_file_template(param_list)]

        plateHolderObject.microscope.run_macro(macro_name, param_list)

    ##############################################################################################

    def read_first_barcode_from_plateholderobject(self, plateHolderObject):
        """Given platerholderobject that can store one plate, return that plate's barcode

        Input:
         plateHolderObject: object of type PlateHolder from module sample with well information

        Return:
         barcode: barcode of plate in plateholderobject
        """

        return list(plateHolderObject.get_plates().values())[0].barcode

    def recover_previous_settings(self, plateHolderObject, plateObject, experiment):
        """
        Recover the the objects created in the last experiment and attach them to the right objects
        :param plateHolderObject:
        :param plateObject:
        :param experiment: experiment dictionary with information about input and output parameters
        :return:
        """
        nextExperimentObjects = []
        next_experiment_objects_dict = experiment['ObjectsDict']
        # Add the microscope object to each plateholder that was removed when the dict was pickled
        for object in list(next_experiment_objects_dict.values()):
            while object.container is not None:
                if isinstance(object.container, samples.PlateHolder):
                    object.container.microscope = plateHolderObject.microscope
                object = object.container
        # Add the object to the plates
        for object in next_experiment_objects_dict:
            nextExperimentObjects.append(next_experiment_objects_dict[object])
        listName = experiment['Input']
        plateObject.add_to_image_dir(listName=listName, sampleObject=nextExperimentObjects)

    ##############################################################################################

    def save_segmented_image(self, imagingSettings, image_data, location_list, plateObject, well_object):
        """
        A simple function to save the positions that were a result of well segmentation and represent which positions
        will be imaged in 100X
        :param imagingSettings: yaml preferences
        :param image_data: pixel data of the image
        :param location_list: list of positions approved by the user
        :param plateObject: plate object
        :param well_object: well object associated with the image
        :return:
        """

        # Determine the folder where the images will be stored
        segmented_images_folder = imagingSettings.getPref('Folder')
        segmented_image_dir = get_images_path(imagingSettings, segmented_images_folder)
        imageFileNameTemplate = imagingSettings.getPref('FileName')

        microscope_object = plateObject.container.microscope
        # make a copy because the pixel values are being changed only for saving part
        image_data_save = image_data.copy()
        # Plot the positions on the image as a set of white pixels
        for location in location_list:
            pixel_width = int(math.ceil(image_data.shape[0] / 1000)) + 2
            image_data_save[int(location[0]) - pixel_width:int(location[0]) + pixel_width,
            int(location[1]) - pixel_width:int(location[1]) + pixel_width] = 0
        image_aics = ImageAICS(image_data_save)
        info_dict = microscope_object.get_information()
        # Add relevant meta data
        image_aics.add_meta(
            {'aics_objectiveMagnification': int(
                info_dict[plateObject.container.objective_changer_id]['magnification'])})
        image_aics.add_meta({'aics_well': well_object.get_name()})
        image_aics.add_meta({'aics_barcode': plateObject.get_barcode()})
        date_short = str(date.today()).replace("-", "")
        image_aics.add_meta({'aics_dateStartShort': date_short})
        # Create the file path based on the meta data and save the image as a tiff file
        image_path = image_aics.create_file_name((segmented_image_dir, imageFileNameTemplate))
        imsave(image_path, image_data_save.T, cmap='gray')

    ##############################################################################################

    def scan_samples(self, imagingSettings, plateHolderObject, experiment, repetition=0, wait_after_image=None):
        """Step through all plates and call scan_all_objects.

        Input:
         imagingSettings: dictionary with preferences
         plateHolderObject: object of type PlateHolder from module sample with well information
         experiment: dictionary with keys 'Experiment', Repetitions', 'Input', 'Output']
                         from workflow with information about specific experiment
         repetition: counter for time lapse experiments
         wait_after_image: wait preferences as dictionary to determine whether to wait after
                            Image: Wait after each image
                            Plate: Reset wait status after each plate
                            Repetition: Reset wait status after each repetition

        Return:
         none
        """
        plates = plateHolderObject.get_plates()
        listName = experiment['Input']

        # Iterate through all plates on plate holder
        for plateCounter, (plateName, plateObject) in enumerate(iter(plates.items()), 1):
            sampleList = plateObject.get_from_image_dir(listName)
            current_samples = copy.copy(sampleList)

            workflow_list = experiment['WorkflowList']

            # Recover the positions that were imaged & the ones that need to be imaged
            if experiment['WorkflowType'] == 'continue':

                # Recover positions to be imaged next
                if experiment['ObjectsDict'] is not None:
                    self.recover_previous_settings(plateHolderObject, plateObject, experiment)

                # Readjust the focus if continuing from scanCells
                # To readjust the focus get the experiment name of the focusing block from the pref file
                update_z_function_name = imagingSettings.getPref('DefineFocusBlockName')
                if update_z_function_name is None:
                    update_z_function_name = 'UpdatePlateWellZero_100x'
                settings = imagingSettings.parentPrefs.getPrefAsMeta(update_z_function_name)
                workflow = imagingSettings.parentPrefs.getPref('Workflow')
                update_plate_exp = [update_plate_exp for update_plate_exp in workflow if
                                    update_plate_exp['Experiment'] == update_z_function_name]
                experiment_dict = update_plate_exp[0]
                experiment_dict['RecoverySettingsFilePath'] = experiment['RecoverySettingsFilePath']
                experiment_dict['WorkflowList'] = experiment['WorkflowList']
                experiment_dict['OriginalWorkflow'] = experiment['OriginalWorkflow']
                if update_z_function_name not in workflow_list:
                    self.update_plate_zZero(settings, plateHolderObject, experiment_dict)

                # Extract the sample list
                sampleList = plateObject.get_from_image_dir(listName)
                current_samples = copy.copy(sampleList)
                # Update the sample list by removing the positions that were imaged already
                last_exp_objects = experiment['LastExpObjects']
                if sampleList is not None:
                    for sample in sampleList:
                        name = sample.get_name()
                        if name in last_exp_objects:
                            current_samples.remove(sample)

            if current_samples is not None:
                self.scan_all_objects(imagingSettings,
                                      sampleList=current_samples,
                                      plateObject=plateObject,
                                      experiment=experiment,
                                      repetition=repetition,
                                      wait_after_image=wait_after_image)

        # Update the reference object
        for key, value in list(plateHolderObject.microscope.microscope_components_ordered_dict.items()):
            if isinstance(value, hardware_control.AutoFocus):
                self.state.reference_object = value.get_focus_reference_obj()
                # Autosave
                self.state.save_state()

    ##############################################################################################

    def validate_experiment(self, imaging_settings, microscope_object):
        """
        If the experiment is not defined in Zen, give the user two tries to create it
        :param imagingSettings: preferences from the yaml file
        :param microscope_object: microscope hardware object
        :return:
        """

        # Initialize a Experiment object
        experiment_name = imaging_settings.getPref('Experiment')

        # Check if the experiment is actually needed (for example, segmentation doesn't need a Zen experiment)
        if experiment_name != 'NoExperiment':
            experiment_path = get_experiment_path(imaging_settings)
            microscope_software_experiment = hardware_components.Experiment(experiment_path, experiment_name,
                                                                            microscope_object)
            # Check if experiment exists in Microscope software
            # Give the user 2 tries to add the experiment
            valid_experiment = microscope_software_experiment.validate_experiment()
            num_try = 1
            while valid_experiment is False and num_try <= 2:
                message.information_message("Error", "The experiment " + experiment_name
                                            + " is not defined in the microscope software. Please add it now and "
                                              "continue the experiment")
                valid_experiment = microscope_software_experiment.validate_experiment()
                num_try = num_try + 1
            if valid_experiment is False:
                stop_script("The Experiment " + experiment_name +
                            " is not defined in the microscope software. Exiting the software.")

    ##############################################################################################

    def control_autofocus(self, sample_object, imaging_settings):
        """ Switch on/off autofocus.

        Input:
         sample_object: object of class inherited from ImagingSystem in module samples.py
         imaging_settings: settings derived from preferences file

        Output:
         none
        """
        use_auto_focus = imaging_settings.getPref('UseAutoFocus', validValues=VALID_USEAUTOFOCUS)
        # set autofocus, exception if autofocus does not exist
        try:
            sample_object.set_use_autofocus(flag=use_auto_focus)
        except HardwareDoesNotExistError as e:
            if use_auto_focus:
                e.error_dialog('Set UseAutoFocus to False in preferences file.')

    ##############################################################################################
    #
    # Main function for microscope automation.
    # Start this function to start automation.
    #
    ##############################################################################################

    def microscope_automation(self):
        """Main script for Microscope automation.

        Input:
         none

        Output:
         none
        """""
        # get all information about experiment
        prefs = preferences.Preferences(get_prefs_path())

        # start local logging
        error_handling.setup_logger(self.prefs)
        logger = logging.getLogger('MicroscopeAutomation.microscope_automation')
        logger.info('automation protocol started')

        # setup microscope
        microscopeObject = setup_microscope.setup_microscope(self.prefs)

        # get list of experiments to perform on given plate
        workflow = self.prefs.getPref('Workflow')

        # Setting up continuation
        # Dialog box
        continue_check_box_list = [('Start new workflow', True), ('Continue last workflow', False)]
        continue_dialog_box = message.check_box_message('Please select workflow type:',
                                                        continue_check_box_list, returnCode=False)

        if continue_dialog_box[0][1] is True:
            workflow_type = 'new'
        elif continue_dialog_box[1][1] is True:
            workflow_type = 'continue'

        # Update workflow based on workflow type
        if workflow_type == 'new':
            checkBoxList = [('{} x {}'.format(i['Repetitions'], i['Experiment']), True) for i in workflow]
            newCheckBoxList = message.check_box_message('Please select experiment to execute:', checkBoxList,
                                                        returnCode=False)
            workflow = [workflow[i] for i, box in enumerate(newCheckBoxList) if box[1] is True]
            workflowExperiments = [step['Experiment'] for step in workflow]
            original_workflow = copy.copy(workflowExperiments)

        else:
            # Read the preference file and find which to continue from
            workflow_list = []
            for exp in workflow:
                workflow_list.append(exp['Experiment'])
            continue_experiment = message.pull_down_select_dialog(workflow_list,
                                                                  "Please select the experiment to continue from:")
            workflowExperiments = [step['Experiment'] for step in workflow]
            original_workflow = copy.copy(workflowExperiments)
            # Update the experiment list with experiments starting from continue_experiment and the ones after it
            for step in workflow:
                if step['Experiment'] != continue_experiment:
                    workflowExperiments.remove(step['Experiment'])
                else:
                    break

            # Update the workflow with new sets of experiments
            new_workflow = copy.deepcopy(workflow)
            for step in workflow:
                if step['Experiment'] not in workflowExperiments:
                    new_workflow.remove(step)
            workflow = new_workflow

            # Ask to pick the file again if the user picks blank file name
            pickle_file = ''
            while pickle_file == '':
                # Ask user which pickle file to recover settings from
                file_dir = self.prefs.getPref('RecoverySettingsFilePath')
                pickle_file = message.file_select_dialog(file_dir, filePattern='*.pickle',
                                                         comment='Please select the file to recover settings from.')

            # Recover the objects dictionary
            file_path = os.path.normpath(os.path.join(file_dir, pickle_file))
            (next_objects_dict, reference_object, last_experiment_objects,
             hardware_status_dict) = self.state.recover_objects(file_path)
            # Set up the reference object
            for key, value in list(microscopeObject.microscope_components_ordered_dict.items()):
                if isinstance(value, hardware_control.AutoFocus):
                    reference_object.microscope = microscopeObject
                    reference_object.container.microscope = microscopeObject
                    value.set_focus_reference_obj(reference_object)
                    break
            # Set up the hardware status in the microscope object
            microscopeObject.objective_ready_dict = hardware_status_dict
            # Set up objects dict for backtracking - remove unnecessary objects
            # won't work for planned interruption workflow so only do it if its of the type unplanned
            # planned interruptions dict value are objects, unplanned ones are list
            objects_dict = OrderedDict()
            if isinstance(list(next_objects_dict.values()), list):
                try:
                    previous_experiment = workflow_list[workflow_list.index(continue_experiment) - 1]
                    objects_list = next_objects_dict[previous_experiment]
                    for obj in objects_list:
                        objects_dict.update({obj.get_name(): obj})
                except:
                    objects_dict = None
            else:
                objects_dict = next_objects_dict

        # setup plate holder with plate, wells, and colonies
        colonyFile = None
        if 'AddColonies' in workflowExperiments:
            addColoniesPrefs = self.prefs.getPrefAsMeta('AddColonies')
            colonyFileDirectory = get_colony_dir_path(self.prefs)
            fileName = addColoniesPrefs.getPref('FileName')
            colonyFile = message.file_select_dialog(colonyFileDirectory, filePattern=fileName,
                                                    comment='''Please select csv file with colony data.''')
            experiment = [experiment for experiment in workflow if experiment['Experiment'] == 'AddColonies']
            workflow.remove(experiment[0])
            self.state.workflow_pos.append('AddColonies')

        plateHolderObject = setup_samples.setup_plate(self.prefs, colonyFile, microscopeObject)

        # Set up the Daily folder with plate barcode
        # Currently only one plate supported so barcode is extracted from that
        plates = plateHolderObject.get_plates()
        barcode = list(plates.keys())[-1]
        # Set up the high level folder with plate barcode
        dailyFolder = get_daily_folder(self.prefs, barcode)
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
                                image_folder.append(get_images_path(self.prefs, folder))
                        else:
                            image_folder = (get_images_path(self.prefs, pref_value))
                    # Set up the subfolders for each image folder
                    if pref == "SubFolders":
                        for subfolder in pref_value:
                            if isinstance(image_folder, list):
                                for folder in image_folder:
                                    set_up_subfolders(self.prefs, folder, subfolder)
                            else:
                                set_up_subfolders(self.prefs, image_folder, subfolder)

        # set-up meta data file object
        metaDataFilePath = get_meta_data_path(self.prefs)
        metaDataFormat = self.prefs.getPref('MetaDataFormat')
        metaDataFileObject = meta_data_file(metaDataFilePath, metaDataFormat)
        plateHolderObject.add_meta_data_file(metaDataFileObject)

        # cycle through all plates
        platesObjects = plateHolderObject.get_plates()
        for barcode, plateObject in platesObjects.items():
            # execute each measurement based on experiment in workflow
            for experiment in workflow:
                # attach additional parameters to experiment to propagate into all the scanning functions
                experiment['WorkflowList'] = workflowExperiments
                experiment['OriginalWorkflow'] = original_workflow
                experiment['WorkflowType'] = workflow_type
                workflow_interrupt = self.prefs.getPref('WorkflowInterrupt')
                if workflow_interrupt is not None:
                    if workflow_interrupt == experiment['Experiment']:
                        experiment['Interrupt'] = True
                    else:
                        experiment['Interrupt'] = False

                recovery_settings_file_path = self.prefs.getPref('RecoverySettingsFilePath')

                if recovery_settings_file_path is not None:
                    experiment['RecoverySettingsFilePath'] = recovery_settings_file_path
                if workflow_type == 'continue':
                    experiment['ObjectsDict'] = objects_dict
                    experiment['LastExpObjects'] = last_experiment_objects
                imagingSettings = self.prefs.getPrefAsMeta(experiment['Experiment'])
                self.validate_experiment(imagingSettings, microscopeObject)

                # read wait preferences as dictionary to determine whether to wait after
                # Image: Wait after each image
                # Plate: Reset wait status after each plate
                # Repetition: Reset wait status after each repetition
                wait_after_image = imagingSettings.getPref('Wait')
                wait_after_image['Status'] = wait_after_image['Image']

                # set blocking/non-blocking for error messages
                # TODO - blocking is not used anywhere - inquire!
                blocking = imagingSettings.getPref('Blocking', VALID_BLOCKING)
                # get function to perform experiment
                functionName = imagingSettings.getPref('FunctionName', validValues=VALID_FUNCTIONNAME)
                functionToUse = getattr(self, functionName)
                # For segment wells, it is better to not display the dialog box
                # Reason - to make the workflow more seamless for the scientists
                # With this, they can leave after starting the 10X scan and come back after segmentation
                # to approve positions. Instead of coming after the 10x scan to press ok for segment wells
                if functionName != 'segment_wells':
                    if self.less_dialog:
                        # if less dialog option enabled, fake user press and continue (return code 1)
                        return_code = 1
                    else:
                        return_code = message.information_message('{}'.format(experiment['Experiment']), "",
                                                                  returnCode=True)
                        # " Output = "+str(experiment['Output']) +
                        # "\n Input = "+str(experiment['Input']) +
                        # "\n Repetitions = "+str(experiment['Repetitions']),
                        # returnCode=True)
                # If return_code is 0, user pressed cancel
                else:
                    return_code = 1
                if return_code == 0:
                    self.state.save_state_and_exit()

                self.control_autofocus(plateObject, imagingSettings)
                self.state.hardware_status_dict = microscopeObject.objective_ready_dict
                for i in range(experiment['Repetitions']):
                    # execute experiment for each repetition
                    try:
                        args = inspect.getargspec(functionToUse)
                        if 'repetition' in args.args:
                            functionToUse(imagingSettings,
                                          plateHolderObject,
                                          experiment,
                                          repetition=i,
                                          wait_after_image=wait_after_image)
                        else:
                            functionToUse(imagingSettings, plateHolderObject, experiment)
                        self.state.workflow_pos.append(experiment['Experiment'])
                    except StopCollectingError as error:
                        error.error_dialog()
                        break
                    # Wait for user interaction before continuing
                    if wait_after_image['Repetition'] and not wait_after_image['Status']:
                        wait_after_image['Repetition'] = message.wait_message('New repetition: do you want to '
                                                                              'stop after the next image?')
                        wait_after_image['Status'] = wait_after_image['Repetition']

        print('Finished with plate scan')


def main():
    # Regularized argument parsing
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument('-p', '--preferences', help="path to the preferences file")
    args = arg_parser.parse_args()
    # Check if argument is given and is a valid path.
    if args.preferences is not None and os.path.isfile(args.preferences):
        set_pref_file(args.preferences)
    else:
        # Use UI file selector to prompt user for preferences file
        fSelect = tk.Tk()
        fSelect.withdraw()
        set_pref_file(filedialog.askopenfilename(title='Select Preferences File to Use'))

    # initialize the pyqt application object here (not in the location picker module)
    # as it only needs to be initialized once
    global app
    app = QtGui.QApplication([])
    try:
        mic = MicroscopeAutomation()
        mic.microscope_automation()
    except KeyboardInterrupt:
        pyqtgraph.exit()
        # mic.state.save_state_and_exit()
        sys.exit()
    print('Done')
    # Properly close pyqtgraph to avoid exit crash
    pyqtgraph.exit()


if __name__ == '__main__':
    main()
