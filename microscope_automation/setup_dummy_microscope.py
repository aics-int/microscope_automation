from .setup_microscope_helper import setup_cameras, setup_pump, setup_stages, \
    setup_autofocus, setup_obj_changer, setup_focus_drive, setup_safe_areas
from . import hardware_components
from . import automation_exceptions as ae
from .get_path import get_hardware_settings_path, get_experiment_path
from . import preferences
from .hardware_control import BaseMicroscope


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
        print (e)
        # use data from development environment if not using real setup
        pathMicroscopeSpecs_RD = '../GeneralSettings/microscopeSpecifications.yml'
        specs = preferences.Preferences(pathMicroscopeSpecs_RD)
        print((("Could not read microscope specifications from {}.\nRead from"
               " R&D environment from {}.").format(path_microscope_specs,
                                                   pathMicroscopeSpecs_RD)))

    # get object to connect to software based on software name
    software = specs.getPref('Software')
    connect_object = hardware_components.ControlSoftware(software)

    # create microscope
    microscope = specs.getPrefAsMeta('Microscope')
    if microscope.getPref('Type') == "SpinningDisk_3i":
        microscope_object = BaseMicroscope(control_software_object=connect_object,
                                           name=microscope.getPref('Name'),
                                           experiments_folder=get_experiment_path(prefs, dir=True))
    else:
        raise ae.HardwareDoesNotExistError("Microscope not defined in module "
                                           "hardware_control.py")

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

    # initialize microscope hardware moved to initialize_microscope in module
    # microscopeAutomation.py: microscopeObject.initialize_hardware()
    return microscope_object
