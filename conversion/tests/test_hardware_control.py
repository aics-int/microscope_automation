"""
Test control of microscope
Created on May 25, 2020

@author: winfriedw
"""

import pytest
from mock import patch
from microscope_automation.image_AICS import ImageAICS
import microscope_automation.setup_microscope as setup_microscope
import microscope_automation.preferences as preferences
import microscope_automation.hardware_components as h_comp
from microscope_automation.automation_exceptions import AutomationError, \
    AutofocusError, CrashDangerError, HardwareError, LoadNotDefinedError
import os
os.chdir(os.path.dirname(__file__))

# set skip_all_tests = True to focus on single test
skip_all_tests = False


def setup_local_microscope(prefs_path):
    """Create microscope object"""
    prefs = preferences.Preferences(prefs_path)
    microscope_object = setup_microscope.setup_microscope(prefs)
    return microscope_object


def setup_local_control_software(software):
    """Create ControlSoftware object"""
    control_software = h_comp.ControlSoftware(software)
    return control_software


def setup_local_focus_drive(focus_drive_id, max_load_position=0, min_work_position=10,
                            auto_focus_id=None, objective_changer=None, prefs_path=None):
    """Create FocusDrive object"""
    if prefs_path:
        microscope_object = setup_local_microscope(prefs_path)
    else:
        microscope_object = None

    focus_drive = h_comp.FocusDrive(focus_drive_id, max_load_position, min_work_position,
                                    auto_focus_id, objective_changer, microscope_object)

    return focus_drive


def setup_local_obj_changer(obj_changer_id, n_positions=None,
                            objectives=None, ref_objective=None,
                            prefs_path=None):
    """Create ObjectiveChanger object"""
    if prefs_path:
        microscope_object = setup_local_microscope(prefs_path)
    else:
        microscope_object = None

    obj_changer = h_comp.ObjectiveChanger(obj_changer_id, n_positions,
                                          objectives, ref_objective, microscope_object)

    if microscope_object:
        obj_changer.microscope_object.add_microscope_object(obj_changer)

    return obj_changer


def setup_local_safety(safety_id):
    """Create Safety object"""
    safety = h_comp.Safety(safety_id)
    return safety


def setup_local_stage(stage_id, safe_area=None, safe_position=None, objective_changer=None,
                      prefs_path=None, default_experiment=None):
    """Create Stage object"""
    if prefs_path:
        microscope_object = setup_local_microscope(prefs_path)
    else:
        microscope_object = None

    stage = h_comp.Stage(stage_id, safe_area, safe_position, objective_changer,
                         microscope_object, default_experiment)
    return stage


def setup_local_autofocus(auto_focus_id, default_camera=None, obj_changer=None,
                          default_reference_position=[[50000, 37000, 6900]],
                          prefs_path=None):
    """Create AutoFocus object"""
    if prefs_path:
        microscope_object = setup_local_microscope(prefs_path)
    else:
        microscope_object = None

    autofocus = h_comp.AutoFocus(auto_focus_id, default_camera, obj_changer,
                                 default_reference_position, microscope_object)

    return autofocus


def setup_local_camera(camera_id, pixel_size=(None, None), pixel_number=(None, None),
                       pixel_type=None, name=None, detector_type='generic',
                       manufacturer=None, model=None):
    """Create Camera object"""
    camera = h_comp.Camera(camera_id, pixel_size, pixel_number, pixel_type, name,
                           detector_type, manufacturer, model)
    return camera


@patch("microscope_automation.automation_exceptions.HardwareError.error_dialog")
@patch("microscope_automation.automation_exceptions.AutofocusError.error_dialog")
@patch("microscope_automation.automation_exceptions.CrashDangerError.error_dialog")
@patch("microscope_automation.automation_exceptions.LoadNotDefinedError.error_dialog")
@pytest.mark.skipif(skip_all_tests, reason='Exclude all tests')
@pytest.mark.parametrize('prefs_path, error, expected',
                         [('test_data/preferences_ZSD_test.yml', AutomationError, None),
                          ('test_data/preferences_ZSD_test.yml', AutofocusError, 'AutofocusError'),
                          ('test_data/preferences_ZSD_test.yml', CrashDangerError, 'CrashDangerError'),
                          ('test_data/preferences_ZSD_test.yml', HardwareError, 'HardwareError'),
                          ('test_data/preferences_ZSD_test.yml', LoadNotDefinedError, 'LoadNotDefinedError'),
                          ('test_data/preferences_3i_test.yml', AutomationError, None),
                          ('test_data/preferences_3i_test.yml', AutofocusError, 'AutofocusError'),
                          ('test_data/preferences_3i_test.yml', CrashDangerError, 'CrashDangerError'),
                          ('test_data/preferences_3i_test.yml', HardwareError, 'HardwareError'),
                          ('test_data/preferences_3i_test.yml', LoadNotDefinedError, 'LoadNotDefinedError')])
def test_recover_hardware(mock_error_diag0, mock_error_diag1, mock_error_diag2,
                          mock_error_diag3, prefs_path, error, expected):
    """Test recovering from hardware error"""
    microscope = setup_local_microscope(prefs_path)
    try:
        raise error
    except LoadNotDefinedError as e0:
        result = microscope.recover_hardware(e0)
        assert mock_error_diag0.called
    except CrashDangerError as e1:
        result = microscope.recover_hardware(e1)
        assert mock_error_diag1.called
    except AutofocusError as e2:
        result = microscope.recover_hardware(e2)
        assert mock_error_diag2.called
    except HardwareError as e3:
        result = microscope.recover_hardware(e3)
        assert mock_error_diag3.called
    except AutomationError as e:
        result = microscope.recover_hardware(e)
        assert result == expected


@pytest.mark.skipif(skip_all_tests, reason='Exclude all tests')
@pytest.mark.parametrize('prefs_path, experiment, expected_path',
                         [('test_data/preferences_ZSD_test.yml',
                           'WellTile_10x_true.czexp',
                           'test_data/Experiment Setup/WellTile_10x_true.czexp'),
                          ('test_data/preferences_3i_test.yml',
                           'test_communication.exp.prefs',
                           'test_data/SlideBook 6.0/test_communication.exp.prefs')])
def test_create_experiment_path(prefs_path, experiment, expected_path):
    """Test creation of experiment path"""
    microscope = setup_local_microscope(prefs_path)
    experiment_path = microscope.create_experiment_path(experiment)
    assert os.path.abspath(expected_path) == os.path.abspath(experiment_path)


@pytest.mark.skipif(skip_all_tests, reason='Exclude all tests')
@pytest.mark.parametrize('prefs_path, software',
                         [('test_data/preferences_ZSD_test.yml', 'ZEN Blue Dummy'),
                          ('test_data/preferences_3i_test.yml', 'Slidebook Dummy')])
def test_stop_microscope(prefs_path, software):
    """Test creation of experiment path"""
    microscope = setup_local_microscope(prefs_path)

    if software:
        control_software = setup_local_control_software(software)
        microscope.add_control_software(control_software)

    microscope.stop_microscope()

    assert True


@pytest.mark.skipif(skip_all_tests, reason='Exclude all tests')
@pytest.mark.parametrize('find_surface', [True, False])
@pytest.mark.parametrize('prefs_path, ref_obj_id, expected',
                         [('test_data/preferences_ZSD_test.yml', None,
                           'AutofocusNoReferenceObjectError'),
                          ('test_data/preferences_ZSD_test.yml', 'test',
                           'HardwareCommandNotDefinedError'),
                          ('test_data/preferences_3i_test.yml', None,
                           'HardwareCommandNotDefinedError')])
def test_reference_position(prefs_path, find_surface, ref_obj_id, expected):
    """Test correction in xyz between objectives"""
    microscope = setup_local_microscope(prefs_path)
    try:
        result = microscope.reference_position(find_surface=find_surface,
                                               reference_object_id=ref_obj_id,
                                               verbose=False)
    except Exception as err:
        result = type(err).__name__
    assert result == expected


@pytest.mark.skipif(skip_all_tests, reason='Exclude all tests')
@pytest.mark.parametrize(("prefs_path, experiment, component_dict, focus_drive_id, "
                          "objective_changer_id, objectives, safety_object_id, "
                          "safe_verts, safe_area_id, z_max, stage_id, "
                          "auto_focus_id, expected"),
                         [('test_data/preferences_3i_test.yml',
                           'test_communication.exp.prefs', {}, None, None, None,
                           None, None, None, None, None, None, {'Microscope': True}),
                          ('test_data/preferences_3i_test.yml',
                           'test_communication.exp.prefs',
                           {'MotorizedFocus': ['test']}, 'MotorizedFocus', None,
                           None, None, None, None, None, None, None,
                           {'Microscope': True, 'MotorizedFocus': True}),
                          ('test_data/preferences_ZSD_test.yml',
                           'WellTile_10x_true.czexp', {}, None, None, None,
                           None, None, None, None, None, None, 'HardwareDoesNotExistError'),
                          ('test_data/preferences_ZSD_test.yml',
                           'WellTile_10x_true.czexp', {}, 'MotorizedFocus',
                           '6xMotorizedNosepiece', None, 'ZSD_01_plate',
                           None, None, None, None, None, {'Microscope': True}),
                          ('test_data/preferences_ZSD_test.yml',
                           'WellTile_10x_true.czexp',
                           {'MotorizedFocus': ['test'],
                            '6xMotorizedNosepiece': ['test']},
                           'MotorizedFocus', '6xMotorizedNosepiece', None,
                           'ZSD_01_plate', None, None, None, None, None,
                           {'Microscope': True, 'MotorizedFocus': True,
                            '6xMotorizedNosepiece': True}),
                          ('test_data/preferences_ZSD_test.yml',
                           'WellTile_10x_true.czexp',
                           {'MotorizedFocus': ['test'],
                            '6xMotorizedNosepiece': ['test'],
                            'Marzhauser': ['test'],
                            'DefiniteFocus2': ['test']},
                           'MotorizedFocus', '6xMotorizedNosepiece', None,
                           'ZSD_01_plate', None, None, None, 'Marzhauser', 'DefiniteFocus2',
                           'TypeError'),
                          ('test_data/preferences_ZSD_test.yml',
                           'WellTile_10x_true.czexp',
                           {'MotorizedFocus': ['test'],
                            '6xMotorizedNosepiece': ['test'],
                            'Marzhauser': ['test'],
                            'DefiniteFocus2': ['test']},
                           'MotorizedFocus', '6xMotorizedNosepiece',
                           {'Plan-Apochromat 10x/0.45':
                            {'x_offset': -19,
                             'y_offset': 15,
                             'z_offset': 10,
                             'magnification': 10,
                             'immersion': 'air',
                             'experiment': 'WellTile_10x_true',
                             'camera': 'Camera1 (back)',
                             'autofocus': 'DefiniteFocus2'}},
                           'ZSD_01_plate', None, None, None,
                           'Marzhauser', 'DefiniteFocus2',
                           'UnboundLocalError'),
                          ('test_data/preferences_ZSD_test.yml',
                           'WellTile_10x_true.czexp',
                           {'MotorizedFocus': ['test'],
                            '6xMotorizedNosepiece': ['test'],
                            'Marzhauser': ['test']},
                           'MotorizedFocus', '6xMotorizedNosepiece',
                           {'Plan-Apochromat 10x/0.45':
                            {'x_offset': -19,
                             'y_offset': 15,
                             'z_offset': 10,
                             'magnification': 10,
                             'immersion': 'air',
                             'experiment': 'WellTile_10x_true',
                             'camera': 'Camera1 (back)',
                             'autofocus': 'DefiniteFocus2'}},
                           'ZSD_01_plate',
                           [(3270, 1870), (108400, 1870), (108400, 71200), (3270, 71200)],
                           'StageArea', 9900,
                           'Marzhauser', 'DefiniteFocus2',
                           {'Microscope': True, 'MotorizedFocus': True,
                            '6xMotorizedNosepiece': True, 'Marzhauser': True}),
                          ('test_data/preferences_ZSD_test.yml',
                           'WellTile_10x_true.czexp',
                           {'MotorizedFocus': ['test'],
                            '6xMotorizedNosepiece': ['test'],
                            'DefiniteFocus2': ['test'],
                            'Marzhauser': ['test']},
                           'MotorizedFocus', '6xMotorizedNosepiece',
                           {'Plan-Apochromat 10x/0.45':
                            {'x_offset': -19,
                             'y_offset': 15,
                             'z_offset': 10,
                             'magnification': 10,
                             'immersion': 'air',
                             'experiment': 'WellTile_10x_true',
                             'camera': 'Camera1 (back)',
                             'autofocus': 'DefiniteFocus2'}},
                           'ZSD_01_plate', [(3270, 1870), (108400, 1870), (108400, 71200), (3270, 71200)],
                           'StageArea', 9900, 'Marzhauser', 'DefiniteFocus2',
                           {'Microscope': False, 'MotorizedFocus': True,
                            '6xMotorizedNosepiece': True, 'DefiniteFocus2': False,
                            'Marzhauser': True}),
                          ('test_data/preferences_ZSD_test.yml',
                           'WellTile_10x_true.czexp',
                           {'MotorizedFocus': ['test'],
                            '6xMotorizedNosepiece': ['test'],
                            'DefiniteFocus2': None,
                            'Marzhauser': ['test']},
                           'MotorizedFocus', '6xMotorizedNosepiece',
                           {'Plan-Apochromat 10x/0.45':
                            {'x_offset': -19,
                             'y_offset': 15,
                             'z_offset': 10,
                             'magnification': 10,
                             'immersion': 'air',
                             'experiment': 'WellTile_10x_true',
                             'camera': 'Camera1 (back)',
                             'autofocus': 'DefiniteFocus2'}},
                           'ZSD_01_plate', [(3270, 1870), (108400, 1870), (108400, 71200), (3270, 71200)],
                           'StageArea', 9900, 'Marzhauser', 'DefiniteFocus2',
                           {'Microscope': True, 'MotorizedFocus': True,
                            '6xMotorizedNosepiece': True, 'DefiniteFocus2': True,
                            'Marzhauser': True})])
def test_microscope_is_ready(prefs_path, experiment, component_dict,
                             focus_drive_id, objective_changer_id, objectives,
                             safety_object_id, safe_verts, safe_area_id, z_max,
                             stage_id, auto_focus_id, expected):
    microscope = setup_local_microscope(prefs_path)

    if focus_drive_id:
        focus_drive = setup_local_focus_drive(focus_drive_id)
        microscope.add_microscope_object(focus_drive)

    if objective_changer_id:
        obj_changer = setup_local_obj_changer(objective_changer_id,
                                              objectives=objectives,
                                              prefs_path=prefs_path)
        microscope.add_microscope_object(obj_changer)

    if safety_object_id:
        safety_obj = setup_local_safety(safety_object_id)
        if safe_area_id:
            safety_obj.add_safe_area(safe_verts, safe_area_id, z_max)
        microscope.add_microscope_object(safety_obj)

    if stage_id:
        stage = setup_local_stage(stage_id, safe_area=safe_area_id,
                                  objective_changer=objective_changer_id,
                                  prefs_path=prefs_path)
        microscope.add_microscope_object(stage)

    if auto_focus_id:
        autofocus = setup_local_autofocus(auto_focus_id, obj_changer=obj_changer,
                                          prefs_path=prefs_path)
        microscope.add_microscope_object(autofocus)

    try:
        result = microscope.microscope_is_ready(experiment, component_dict,
                                                focus_drive_id, objective_changer_id,
                                                safety_object_id)
    except Exception as err:
        result = type(err).__name__
    assert result == expected


@patch("microscope_automation.hardware_control.SpinningDiskZeiss.recover_hardware")
@pytest.mark.skipif(skip_all_tests, reason='Exclude all tests')
@pytest.mark.parametrize(("prefs_path, software, experiment, "
                          "objective_changer_id, objectives, expected"),
                         [('test_data/preferences_ZSD_test.yml', None,
                           'WellTile_10x_true.czexp',
                           None, None, 'AttributeError'),
                          ('test_data/preferences_ZSD_test.yml', 'ZEN Blue Dummy',
                           'WellTile_10x_true.czexp',
                           '6xMotorizedNosepiece',
                           {'Plan-Apochromat 10x/0.45':
                            {'x_offset': -19,
                             'y_offset': 15,
                             'z_offset': 10,
                             'magnification': 10,
                             'immersion': 'air',
                             'experiment': 'WellTile_10x_true',
                             'camera': 'Camera1 (back)',
                             'autofocus': 'DefiniteFocus2'}},
                             'LoadNotDefinedError')])
def test_change_objective(mock_rec_hard, prefs_path, software, experiment,
                          objective_changer_id, objectives, expected):
    microscope = setup_local_microscope(prefs_path)

    if software:
        control_software = setup_local_control_software(software)
        microscope.add_control_software(control_software)

    if objective_changer_id:
        obj_changer = setup_local_obj_changer(objective_changer_id,
                                              objectives=objectives,
                                              prefs_path=prefs_path)
        microscope.add_microscope_object(obj_changer)
    else:
        obj_changer = None

    try:
        result = microscope.change_objective(experiment, obj_changer)
    except Exception as err:
        result = type(err).__name__

    assert result == expected


@pytest.mark.skipif(skip_all_tests, reason='Exclude all tests')
@pytest.mark.parametrize("prefs_path", ['test_data/preferences_ZSD_test.yml',
                                        'test_data/preferences_3i_test.yml'])
@pytest.mark.parametrize(("auto_focus_id, use_auto_focus, expected"),
                         [(None, False, 'HardwareDoesNotExistError'),
                          ('DefiniteFocus2', False,
                           {'DefiniteFocus2': {'use_auto_focus': False}}),
                          ('DefiniteFocus2', True,
                           {'DefiniteFocus2': {'use_auto_focus': True}})])
def test_set_microscope(prefs_path, auto_focus_id, use_auto_focus, expected):
    microscope = setup_local_microscope(prefs_path)

    if auto_focus_id:
        autofocus = setup_local_autofocus(auto_focus_id)
        microscope.add_microscope_object(autofocus)

    try:
        result = microscope.set_microscope({auto_focus_id: {'use_auto_focus': use_auto_focus}})
    except Exception as err:
        result = type(err).__name__

    assert result == expected


@pytest.mark.skipif(skip_all_tests, reason='Exclude all tests')
@pytest.mark.parametrize(("prefs_path, objective_info, ref_obj_id, expected"),
                         [('test_data/preferences_ZSD_test.yml',
                           {'magnification': 10,
                            'name': 'Dummy Objective', 'position': 0,
                            'experiment': 'WellTile_10x_true'},
                           None, {None: set([0])}),
                          ('test_data/preferences_ZSD_test.yml',
                           [{'magnification': 10,
                             'name': 'Dummy Objective', 'position': 0,
                             'experiment': 'WellTile_10x_true'},
                            {'magnification': 10,
                             'name': 'Dummy Objective', 'position': 1,
                             'experiment': 'WellTile_10x_true'}],
                           ['test1', 'test1'], {'test1': set([0, 1])}),
                          ('test_data/preferences_ZSD_test.yml',
                           [{'magnification': 10,
                             'name': 'Dummy Objective', 'position': 0,
                             'experiment': 'WellTile_10x_true'},
                            {'magnification': 10,
                             'name': 'Dummy Objective', 'position': 1,
                             'experiment': 'WellTile_10x_true'}],
                           ['test1', 'test2'], 'KeyError')])
def test_set_objective_is_ready(prefs_path, objective_info, ref_obj_id, expected):
    microscope = setup_local_microscope(prefs_path)

    try:
        if isinstance(objective_info, list):
            microscope.set_objective_is_ready(objective_info[0], ref_obj_id[0])
            microscope.set_objective_is_ready(objective_info[1], ref_obj_id[1])
        else:
            microscope.set_objective_is_ready(objective_info, ref_obj_id)
        result = microscope.objective_ready_dict
    except Exception as err:
        result = type(err).__name__

    assert result == expected


@pytest.mark.skipif(skip_all_tests, reason='Exclude all tests')
@pytest.mark.parametrize(("prefs_path, objective_info, ref_obj_id, set_first, expected"),
                         [('test_data/preferences_ZSD_test.yml',
                           {'magnification': 10,
                            'name': 'Dummy Objective', 'position': 0,
                            'experiment': 'WellTile_10x_true'},
                           None, True, True),
                          ('test_data/preferences_ZSD_test.yml',
                           {'magnification': 10,
                            'name': 'Dummy Objective', 'position': 0,
                            'experiment': 'WellTile_10x_true'},
                           'test', True, True),
                          ('test_data/preferences_ZSD_test.yml',
                           {'magnification': 10,
                            'name': 'Dummy Objective', 'position': 0,
                            'experiment': 'WellTile_10x_true'},
                           'test', False, False)])
def test_get_objective_is_ready(prefs_path, objective_info, ref_obj_id, set_first, expected):
    microscope = setup_local_microscope(prefs_path)

    try:
        if set_first:
            microscope.set_objective_is_ready(objective_info, ref_obj_id)
        result = microscope.get_objective_is_ready(objective_info['position'], ref_obj_id)
    except Exception as err:
        result = type(err).__name__

    assert result == expected


@pytest.mark.skipif(skip_all_tests, reason='Exclude all tests')
@pytest.mark.parametrize(("prefs_path, expected"),
                         [('test_data/preferences_ZSD_test.yml', 'TypeError')])
def test_is_ready_errors(prefs_path, expected):
    microscope = setup_local_microscope(prefs_path)

    try:
        result = microscope._objective_changer_is_ready(microscope, None)
    except Exception as err:
        result = type(err).__name__

    assert result == expected

    try:
        result = microscope._focus_drive_is_ready(microscope, [])
    except Exception as err:
        result = type(err).__name__

    assert result == expected

    try:
        result = microscope._stage_is_ready(microscope, None, None)
    except Exception as err:
        result = type(err).__name__

    assert result == expected

    try:
        result = microscope._auto_focus_is_ready(microscope, None, ['find_surface'], None)
    except Exception as err:
        result = type(err).__name__

    assert result == expected


@pytest.mark.skipif(skip_all_tests, reason='Exclude all tests')
@pytest.mark.parametrize('prefs_path', ['test_data/preferences_ZSD_test.yml',
                                        'test_data/preferences_3i_test.yml'])
@pytest.mark.parametrize(("object_to_get, expected"),
                         [(None, 'HardwareDoesNotExistError'),
                          ('test', 'test')])
def test_get_microscope_object(prefs_path, object_to_get, expected):
    microscope = setup_local_microscope(prefs_path)

    if object_to_get:
        focus_drive = setup_local_focus_drive(object_to_get)
        microscope.add_microscope_object(focus_drive)

    try:
        result = microscope.get_microscope_object(object_to_get).id
    except Exception as err:
        result = type(err).__name__

    assert result == expected


@patch("microscope_automation.connect_zen_blue.ConnectMicroscope.live_mode_start")
@pytest.mark.skipif(skip_all_tests, reason='Exclude all tests')
@pytest.mark.parametrize(("prefs_path, experiment, objective_changer_id, "
                          "camera_id, expected"),
                         [('test_data/preferences_3i_test.yml',
                           'test_communication.exp.prefs', None, None, 'AttributeError'),
                          ('test_data/preferences_3i_test.yml',
                           'test_communication.exp.prefs', '6xMotorizedNosepiece',
                           None, 'HardwareDoesNotExistError'),
                          ('test_data/preferences_3i_test.yml',
                           'test_communication.exp.prefs', '6xMotorizedNosepiece',
                           'Camera1 (back)', 'HardwareCommandNotDefinedError'),
                          ('test_data/preferences_3i_test.yml',
                           None, '6xMotorizedNosepiece',
                           'Camera1 (back)', 'HardwareCommandNotDefinedError'),
                          ('test_data/preferences_ZSD_test.yml',
                           'WellTile_10x_true.czexp', None, None, 'AttributeError'),
                          ('test_data/preferences_ZSD_test.yml',
                           'WellTile_10x_true.czexp', '6xMotorizedNosepiece',
                           None, 'HardwareDoesNotExistError'),
                          ('test_data/preferences_ZSD_test.yml',
                           'WellTile_10x_true.czexp', '6xMotorizedNosepiece',
                           'Camera1 (back)', None),
                          ('test_data/preferences_ZSD_test.yml',
                           None, '6xMotorizedNosepiece', 'Camera1 (back)', None)])
def test_setup_microscope_for_initialization(mock_func, prefs_path, experiment,
                                             objective_changer_id, camera_id, expected):
    microscope = setup_local_microscope(prefs_path)

    if objective_changer_id:
        obj_changer = setup_local_obj_changer(objective_changer_id,
                                              prefs_path=prefs_path)
        microscope.add_microscope_object(obj_changer)

        if camera_id:
            obj_changer.default_camera = camera_id
            microscope.add_microscope_object(setup_local_camera(camera_id))
    else:
        obj_changer = None

    try:
        result = microscope.setup_microscope_for_initialization(obj_changer, experiment)
    except Exception as err:
        result = type(err).__name__

    assert result == expected


@pytest.mark.skipif(skip_all_tests, reason='Exclude all tests')
@pytest.mark.parametrize(("prefs_path, software, focus_drive_id, expected"),
                         [('test_data/preferences_3i_test.yml',
                           'Slidebook Dummy', None, 'HardwareDoesNotExistError'),
                          ('test_data/preferences_3i_test.yml',
                           'Slidebook Dummy', 'MotorizedFocus',
                           'ConnectionError'),
                          ('test_data/preferences_ZSD_test.yml',
                           None, None, 'HardwareDoesNotExistError'),
                          ('test_data/preferences_ZSD_test.yml',
                           'ZEN Blue Dummy', 'MotorizedFocus',
                           {'load_position': None, 'work_position': None,
                            'absolute': 500, 'focality_corrected': None,
                            'z_focus_offset': None})])
def test_get_z_position(prefs_path, software, focus_drive_id, expected):
    microscope = setup_local_microscope(prefs_path)

    if software:
        control_software = setup_local_control_software(software)
        microscope.add_control_software(control_software)

    if focus_drive_id:
        focus_drive = setup_local_focus_drive(focus_drive_id)
        microscope.add_microscope_object(focus_drive)

    try:
        result = microscope.get_z_position(focus_drive_id)
    except Exception as err:
        result = type(err).__name__

    assert result == expected


@patch("microscope_automation.hardware_control.SpinningDiskZeiss.recover_hardware")
@patch("microscope_automation.hardware_components.Safety.show_safe_areas")
@pytest.mark.skipif(skip_all_tests, reason='Exclude all tests')
@pytest.mark.parametrize(("prefs_path, software, focus_drive_id, "
                          "max_load_position, min_work_position, objective_changer_id, "
                          "objectives, safety_object_id, "
                          "safe_verts, safe_area_id, z_max, stage_id, "
                          "auto_focus_id, expected"),
                         [('test_data/preferences_3i_test.yml',
                           'Slidebook Dummy', None, None, None, None, None,
                           None, None, None, None, 'Marzhauser', None, 'HardwareError'),
                          ('test_data/preferences_ZSD_test.yml',
                           'ZEN Blue Dummy',
                           'MotorizedFocus', 500, 100, '6xMotorizedNosepiece',
                           {'Plan-Apochromat 10x/0.45':
                            {'x_offset': -19,
                             'y_offset': 15,
                             'z_offset': 10,
                             'magnification': 10,
                             'immersion': 'air',
                             'experiment': 'WellTile_10x_true',
                             'camera': 'Camera1 (back)',
                             'autofocus': 'DefiniteFocus2'}},
                           'ZSD_01_plate', [(3270, 1870), (108400, 1870), (108400, 71200), (3270, 71200)],
                           'StageArea', 9900, 'Marzhauser', 'DefiniteFocus2',
                           'CrashDangerError'),
                          ('test_data/preferences_ZSD_test.yml',
                           'ZEN Blue Dummy',
                           'MotorizedFocus', None, None, '6xMotorizedNosepiece',
                           {'Plan-Apochromat 10x/0.45':
                            {'x_offset': -19,
                             'y_offset': 15,
                             'z_offset': 10,
                             'magnification': 10,
                             'immersion': 'air',
                             'experiment': 'WellTile_10x_true',
                             'camera': 'Camera1 (back)',
                             'autofocus': 'DefiniteFocus2'}},
                           'ZSD_01_plate', [(-1, -1), (108400, -1), (108400, 71200), (-1, 71200)],
                           'StageArea', 9900, 'Marzhauser', 'DefiniteFocus2',
                           'LoadNotDefinedError'),
                          ('test_data/preferences_ZSD_test.yml',
                           'ZEN Blue Dummy',
                           'MotorizedFocus', 500, 100, '6xMotorizedNosepiece',
                           {'Plan-Apochromat 10x/0.45':
                            {'x_offset': -19,
                             'y_offset': 15,
                             'z_offset': 10,
                             'magnification': 10,
                             'immersion': 'air',
                             'experiment': 'WellTile_10x_true',
                             'camera': 'Camera1 (back)',
                             'autofocus': 'DefiniteFocus2'}},
                           'ZSD_01_plate', [(-1, -1), (108400, -1), (108400, 71200), (-1, 71200)],
                           'StageArea', 9900, 'Marzhauser', 'DefiniteFocus2',
                           (0, 0, 500))])
def test_move_to_abs_pos(mock_func1, mock_func2, prefs_path, software, focus_drive_id,
                         max_load_position, min_work_position, objective_changer_id,
                         objectives, safety_object_id, safe_verts, safe_area_id,
                         z_max, stage_id, auto_focus_id, expected):
    microscope = setup_local_microscope(prefs_path)

    if software:
        control_software = setup_local_control_software(software)
        microscope.add_control_software(control_software)

    if focus_drive_id:
        focus_drive = setup_local_focus_drive(focus_drive_id, max_load_position=max_load_position,
                                              min_work_position=min_work_position, prefs_path=prefs_path,
                                              objective_changer=objective_changer_id)
        if max_load_position:
            focus_drive.initialize(control_software.connection,
                                   action_list=['set_load'], verbose=False, test=True)
        microscope.add_microscope_object(focus_drive)

    if objective_changer_id:
        obj_changer = setup_local_obj_changer(objective_changer_id,
                                              objectives=objectives,
                                              prefs_path=prefs_path)
        microscope.add_microscope_object(obj_changer)

    if safety_object_id:
        safety_obj = setup_local_safety(safety_object_id)
        if safe_area_id:
            safety_obj.add_safe_area(safe_verts, safe_area_id, z_max)
        microscope.add_microscope_object(safety_obj)

    if stage_id:
        stage = setup_local_stage(stage_id, safe_area=safe_area_id,
                                  objective_changer=objective_changer_id,
                                  prefs_path=prefs_path)
        microscope.add_microscope_object(stage)

    if auto_focus_id:
        autofocus = setup_local_autofocus(auto_focus_id, obj_changer=obj_changer,
                                          prefs_path=prefs_path)
        microscope.add_microscope_object(autofocus)

    try:
        result = microscope.move_to_abs_pos(stage_id,  focus_drive_id,
                                            objective_changer_id, auto_focus_id,
                                            safety_object_id)
    except Exception as err:
        result = type(err).__name__
    assert result == expected


@pytest.mark.skipif(skip_all_tests, reason='Exclude all tests')
@pytest.mark.parametrize(("prefs_path, macro_name, macro_param, expected"),
                         [('test_data/preferences_ZSD_test.yml', None, None, None)])
def test_run_macro(prefs_path, macro_name, macro_param, expected):
    microscope = setup_local_microscope(prefs_path)

    result = microscope.run_macro(macro_name, macro_param)

    assert result == expected


@patch("microscope_automation.connect_zen_blue.ConnectMicroscope.save_image")
@patch("microscope_automation.connect_zen_blue.ConnectMicroscope.close_experiment")
@pytest.mark.skipif(skip_all_tests, reason='Exclude all tests')
@pytest.mark.parametrize(("prefs_path, software, experiment, file_path, "
                          "z_start, expected"),
                         [('test_data/preferences_3i_test.yml', 'Slidebook Dummy',
                           'test_communication.exp.prefs', None, 'F', ImageAICS),
                          ('test_data/preferences_3i_test.yml', 'Slidebook Dummy',
                           'test_communication.exp.prefs',
                           '/test_data/test_image.png', 'F',
                           'HardwareCommandNotDefinedError'),
                          ('test_data/preferences_ZSD_test.yml', 'ZEN Blue Dummy',
                           'WellTile_10x_true.czexp', None, 'F', ImageAICS),
                          ('test_data/preferences_ZSD_test.yml', 'ZEN Blue Dummy',
                           'WellTile_10x_true.czexp', None, 'L', ImageAICS),
                          ('test_data/preferences_ZSD_test.yml', 'ZEN Blue Dummy',
                           'WellTile_10x_true.czexp', '/test_data/test_image.png',
                           'C', ImageAICS)])
def test_execute_experiment(mock_func1, mock_func2, prefs_path, software,
                            experiment, file_path, z_start, expected):
    microscope = setup_local_microscope(prefs_path)

    if software:
        control_software = setup_local_control_software(software)
        microscope.add_control_software(control_software)

    try:
        result = microscope.execute_experiment(experiment, file_path, z_start)
        result = result.__class__
    except Exception as err:
        result = type(err).__name__

    assert result == expected


@pytest.mark.skipif(skip_all_tests, reason='Exclude all tests')
@pytest.mark.parametrize(("prefs_path, software, camera_id, experiment, "
                          "live, expected"),
                         [('test_data/preferences_ZSD_test.yml', 'ZEN Blue Dummy',
                           'Camera1 (back)', 'WellTile_10x_true.czexp',
                           True, None),
                          ('test_data/preferences_ZSD_test.yml', 'ZEN Blue Dummy',
                           'Camera1 (back)', 'WellTile_10x_true.czexp',
                           False, None)])
def test_live_mode(prefs_path, software, camera_id, experiment, live, expected):
    microscope = setup_local_microscope(prefs_path)
    microscope.add_microscope_object(setup_local_camera(camera_id))

    if software:
        control_software = setup_local_control_software(software)
        microscope.add_control_software(control_software)

    result = microscope.live_mode(camera_id, experiment, live)

    assert result == expected


@patch("microscope_automation.connect_zen_blue.ConnectMicroscope.save_image")
@patch("microscope_automation.connect_zen_blue.ConnectMicroscope.close_experiment")
@pytest.mark.skipif(skip_all_tests, reason='Exclude all tests')
@pytest.mark.parametrize(("prefs_path, software, camera_id, experiment, "
                          "file_path, interactive, expected"),
                         [('test_data/preferences_3i_test.yml', 'Slidebook Dummy',
                           'Camera1 (back)', 'test_communication.exp.prefs',
                           '/test_data/test_image.png', True,
                           'HardwareCommandNotDefinedError'),
                          ('test_data/preferences_ZSD_test.yml', 'ZEN Blue Dummy',
                           'Camera1 (back)', 'WellTile_10x_true.czexp',
                           '/test_data/test_image.png', True, ImageAICS),
                          ('test_data/preferences_ZSD_test.yml', 'ZEN Blue Dummy',
                           'Camera1 (back)', 'WellTile_10x_true.czexp', None,
                           False, 'TypeError'),
                          ('test_data/preferences_ZSD_test.yml', 'ZEN Blue Dummy',
                           'Camera1 (back)', 'WellTile_10x_true.czexp',
                           '/test_data/test_image.png', False, ImageAICS)])
def test_save_image(mock_func1, mock_func2, prefs_path, software, camera_id,
                    experiment, file_path, interactive, expected):
    microscope = setup_local_microscope(prefs_path)
    microscope.add_microscope_object(setup_local_camera(camera_id))

    if software:
        control_software = setup_local_control_software(software)
        microscope.add_control_software(control_software)

    try:
        image = microscope.execute_experiment(experiment)
        result = microscope.save_image(file_path, image, interactive)
        result = result.__class__
    except Exception as err:
        result = type(err).__name__

    assert result == expected


@patch("microscope_automation.connect_zen_blue.ConnectMicroscope.load_image")
@pytest.mark.skipif(skip_all_tests, reason='Exclude all tests')
@pytest.mark.parametrize(("prefs_path, software, camera_id, experiment, "
                          "image, get_meta, expected"),
                         [('test_data/preferences_ZSD_test.yml', 'ZEN Blue Dummy',
                           'Camera1 (back)', 'WellTile_10x_true.czexp', ImageAICS(),
                           True, "<class 'mock.mock.MagicMock'>"),
                          ('test_data/preferences_ZSD_test.yml', 'ZEN Blue Dummy',
                           'Camera1 (back)', 'WellTile_10x_true.czexp', ImageAICS(),
                           False, "<class 'mock.mock.MagicMock'>"),
                          ('test_data/preferences_3i_test.yml', 'Slidebook Dummy',
                           'Camera1 (back)', 'test_communication.exp.prefs', ImageAICS(),
                           False, 'ConnectionError')])
def test_load_image(mock_func1, prefs_path, software, camera_id,
                    experiment, image, get_meta, expected):
    microscope = setup_local_microscope(prefs_path)
    microscope.add_microscope_object(setup_local_camera(camera_id))

    if software:
        control_software = setup_local_control_software(software)
        microscope.add_control_software(control_software)

    try:
        result = microscope.load_image(image, get_meta)
        result = str(result.__class__)
    except Exception as err:
        result = type(err).__name__

    assert result == expected


@pytest.mark.skipif(skip_all_tests, reason='Exclude all tests')
@pytest.mark.parametrize(("prefs_path, software, expected"),
                         [('test_data/preferences_ZSD_test.yml', 'ZEN Blue Dummy',
                           None),
                          ('test_data/preferences_3i_test.yml', 'Slidebook Dummy',
                           'ConnectionError')])
def test_remove_images(prefs_path, software, expected):
    microscope = setup_local_microscope(prefs_path)

    if software:
        control_software = setup_local_control_software(software)
        microscope.add_control_software(control_software)

    try:
        result = microscope.remove_images()
    except Exception as err:
        result = type(err).__name__

    assert result == expected
