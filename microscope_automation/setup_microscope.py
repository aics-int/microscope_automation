"""
Function to setup microscope hardware based on reference files
Created on Aug 1, 2016
Split into it's own module: May 21, 2020

@author: winfriedw
"""

import preferences
from hardware_control_zeiss import SpinningDiskZeiss
from hardware_control_3i import SpinningDisk3i
import hardware_components
import automation_exceptions as ae
from get_path import get_hardware_settings_path, get_experiment_path
# create logger
import logging

logger = logging.getLogger('microscopeAutomation')


def setup_cameras(specs, microscope):
    """Setup cameras and add to microscope object

    Input:
     specs: hardware specifications which info on cameras will be retrieved from

     microscope: microscope object which cameras will be added to

    Output:
     none
    """
    cameras = specs.getPref('Cameras')
    if cameras:
        for name, camera in cameras.iteritems():
            try:
                pixel_number = (int(camera['pixelNumber_x']), int(camera['pixelNumber_x']))
            except Exception:
                pixel_number = (0, 0)
            camera_object = hardware_components.Camera(name,
                                                       pixel_size=(float(camera['pixelSize_x']), float(camera['pixelSize_y'])),
                                                       pixel_number=pixel_number,
                                                       pixel_type=camera['pixelType'],
                                                       name=camera['name'],
                                                       detector_type=camera['detectorType'],
                                                       manufacturer=camera['manufacturer'])
            microscope.add_microscope_object(camera_object)


def setup_safe_areas(specs, microscope):
    """Setup safe area to prevent crashes between stage and objective.
    Adds safe areas to microscope object

    Input:
     specs: hardware specifications which info on safe areas will be retrieved from

     microscope: microscope object which safe areas will be added to

    Output:
     none
    """
    safe_areas = specs.getPref('SafeAreas')
    if safe_areas:
        for name, areas in safe_areas.iteritems():
            safe_area_object = hardware_components.Safety(name)
            for safe_area_id, area in areas.iteritems():
                safe_area_object.add_safe_area(area['area'], safe_area_id, area['zMax'])

            microscope.add_microscope_object(safe_area_object)


def setup_stages(specs, microscope):
    """Setup stages and add to microscope object

    Input:
     specs: hardware specifications which info on stages will be retrieved from

     microscope: microscope object which stages will be added to

    Output:
     none
    """
    stages_specifications = specs.getPref('Stages')
    if stages_specifications:
        for name, stage in stages_specifications.iteritems():
            stage_object = hardware_components.Stage(stage_id=name,
                                                     safe_area=stage['SafeArea'],
                                                     safe_position=stage['SafePosition'],
                                                     objective_changer=stage['ObjectiveChanger'],
                                                     default_experiment=stage['DefaultExperiment'],
                                                     microscope_object=microscope)
            microscope.add_microscope_object(stage_object)


def setup_focus_drive(specs, microscope, obj_changer_id=None):
    """Setup focus drive and add to microscope object

    Input:
     specs: hardware specifications which info on focus drive will be retrieved from

     microscope: microscope object which focus drive will be added to

    Output:
     none
    """
    focus_specifications = specs.getPrefAsMeta('Focus')
    if focus_specifications:
        focus_drive_object = hardware_components.FocusDrive(focus_drive_id=focus_specifications.getPref('Name'),
                                                            max_load_position=focus_specifications.getPref('MaxLoadPosition'),
                                                            min_work_position=focus_specifications.getPref('MinWorkPosition'),
                                                            auto_focus_id=focus_specifications.getPref('AutoFocus'),
                                                            objective_changer=obj_changer_id,
                                                            microscope_object=microscope)
        microscope.add_microscope_object(focus_drive_object)


def setup_obj_changer(specs, microscope):
    """Setup objective changer and add to microscope object

    Input:
     specs: hardware specifications which info on objective changer will be retrieved from

     microscope: microscope object which objective changer will be added to

    Output:
     objective_changer_object: instance of ObjectiveChanger which was just added to microscope
    """
    obj_changer_specifications = specs.getPrefAsMeta('ObjectiveChanger')
    objective_changer_object = None
    if obj_changer_specifications:
        objective_changer_object = \
            hardware_components.ObjectiveChanger(objective_changer_id=obj_changer_specifications.getPref('Name'),
                                                 n_positions=obj_changer_specifications.getPref('Positions'),
                                                 objectives=obj_changer_specifications.getPref('Objectives'),
                                                 ref_objective=obj_changer_specifications.getPref('ReferenceObjective'),
                                                 microscope_object=microscope)
        microscope.add_microscope_object(objective_changer_object)

    return objective_changer_object


def setup_autofocus(specs, microscope, obj_changer=None):
    """Setup autofocus and add to microscope object

    Input:
     specs: hardware specifications which info on autofocus will be retrieved from

     microscope: microscope object which autofocus will be added to

     obj_changer: objective changer object to attach to this autofocus (Defult: None)

    Output:
     none
    """
    autofocus_specifications = specs.getPrefAsMeta('AutoFocus')
    if autofocus_specifications:
        autofocus_object = hardware_components.AutoFocus(auto_focus_id=autofocus_specifications.getPref('Name'),
                                                         default_camera=autofocus_specifications.getPref('DefaultCamera'),
                                                         objective_changer_instance=obj_changer,
                                                         default_reference_position=autofocus_specifications.getPref(
                                                         'DefaultReferencePosition'))

        microscope.add_microscope_object(autofocus_object)


def setup_pump(specs, microscope):
    """Setup autofocus and add to microscope object

    Input:
     specs: hardware specifications which info on autofocus will be retrieved from

     microscope: microscope object which autofocus will be added to

     obj_changer: objective changer object to attach to this autofocus (Defult: None)

    Output:
     none
    """
    pump_specifications = specs.getPrefAsMeta('Pump')
    if pump_specifications:
        pump_object = hardware_components.Pump(pump_id=pump_specifications.getPref('Name'),
                                               seconds=pump_specifications.getPref('TimePump'),
                                               port=pump_specifications.getPref('ComPortPump'),
                                               baudrate=pump_specifications.getPref('BaudratePump'))
        microscope.add_microscope_object(pump_object)


def setup_microscope(prefs):
    """Create object of class Microscope from module hardware.

    Input:
     prefs: preferences with information about microscope hardware

    Output:
     microscope: object of class Microscope
    """
    # get description about microscope
    path_microscope_specs = get_hardware_settings_path(prefs)

    # load specs for hardware
    try:
        specs = preferences.Preferences(path_microscope_specs)
    except Exception as e:
        print(e)
        # use data from development environment if not using real setup
        pathMicroscopeSpecs_RD = '../GeneralSettings/microscopeSpecifications.yml'
        specs = preferences.Preferences(pathMicroscopeSpecs_RD)
        print('Could not read microscope specifications from {}.\nRead from R&D environment from {}.'.format(
            path_microscope_specs, pathMicroscopeSpecs_RD))

    # get object to connect to software based on software name
    software = specs.getPref('Software')
    connect_object = hardware_components.ControlSoftware(software)

    # create microscope
    microscope = specs.getPrefAsMeta('Microscope')
    if microscope.getPref('Type') == "SpinningDisk_Zeiss":
        microscope_object = SpinningDiskZeiss(control_software_object=connect_object,
                                              name=microscope.getPref('Name'),
                                              experiments_folder=get_experiment_path(prefs, dir=True))
    elif microscope.getPref('Type') == "SpinningDisk_3i":
        microscope_object = SpinningDisk3i(control_software_object=connect_object,
                                           name=microscope.getPref('Name'),
                                           experiments_folder=get_experiment_path(prefs, dir=True))
    else:
        raise ae.HardwareDoesNotExistError('Microscope not defined in module hardware_control.py')

    setup_cameras(specs, microscope_object)
    setup_safe_areas(specs, microscope_object)
    setup_stages(specs, microscope_object)
    obj_changer = setup_obj_changer(specs, microscope_object)
    if obj_changer:
        setup_focus_drive(specs, microscope_object, obj_changer.get_id())
        setup_autofocus(specs, microscope_object, obj_changer)
    else:
        setup_focus_drive(specs, microscope_object)
        setup_autofocus(specs, microscope_object)
    setup_pump(specs, microscope_object)

    # initialize microscope hardware moved to initialize_microscope in module microscopeAutomation.py
    #     microscopeObject.initialize_hardware()
    return microscope_object


###########################################################################
#
# Test functions
#
############################################################################

if __name__ == '__main__':
    # get all information about experiment

    try:
        # location of preferences file on Mac
        prefsFile = '../GeneralSettings/preferences.yml'
        dirPath = '/Users/winfriedw/Documents/Programming/ResultTestImages/'
        barcode = '3500000077'
        colonyFile = 'PipelineData_Celigo.csv'

        colonyPath = '../PlateSpecifications/PipelineData_Celigo.csv'
        # test function setup_microscope
        prefs = preferences.Preferences(prefsFile)
    except Exception:
        # location of preferences file on Zeiss SD 1
        prefsFile = 'D:\\Winfried\\Production\\GeneralSettings\\preferences_ZSD3_drugScreen_Winfried.yml'
        dirPath = 'D:\\Winfried\\Production\\'
        barcode = '3500000093'
        colonyFile = '3500000860_ColonyDATA.csv'
        colonyPath = 'D:\\Winfried\\Production\\Daily\\2017_5_10\\PlateSpecifications\\3500000860_ColonyDATA.csv'

        # test function setup_microscope
        prefs = preferences.Preferences(prefsFile)

    microscopeObject = setup_microscope(prefs)
    print('Microscope Object created')
    print(microscopeObject)