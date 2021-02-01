"""
Test control of microscope
Created on May 25, 2020

@author: winfriedw
"""

import pytest
from mock import patch
from microscope_automation.util.image_AICS import ImageAICS
from microscope_automation.util.automation_exceptions import (
    AutomationError,
    AutofocusError,
    CrashDangerError,
    HardwareError,
    LoadNotDefinedError,
)
import os

os.chdir(os.path.dirname(__file__))

# set skip_all_tests = True to focus on single test
skip_all_tests = False


@patch("microscope_automation.util.automation_exceptions.HardwareError.error_dialog")
@patch("microscope_automation.util.automation_exceptions.AutofocusError.error_dialog")
@patch("microscope_automation.util.automation_exceptions.CrashDangerError.error_dialog")
@patch(
    "microscope_automation.util.automation_exceptions.LoadNotDefinedError.error_dialog"
)
@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    "prefs_path, error, expected",
    [
        ("data/preferences_ZSD_test.yml", AutomationError, None),
        ("data/preferences_ZSD_test.yml", AutofocusError, "AutofocusError"),
        ("data/preferences_ZSD_test.yml", CrashDangerError, "CrashDangerError"),
        ("data/preferences_ZSD_test.yml", HardwareError, "HardwareError"),
        ("data/preferences_ZSD_test.yml", LoadNotDefinedError, "LoadNotDefinedError"),
        ("data/preferences_3i_test.yml", AutomationError, None),
        ("data/preferences_3i_test.yml", AutofocusError, "AutofocusError"),
        ("data/preferences_3i_test.yml", CrashDangerError, "CrashDangerError"),
        ("data/preferences_3i_test.yml", HardwareError, "HardwareError"),
        ("data/preferences_3i_test.yml", LoadNotDefinedError, "LoadNotDefinedError"),
    ],
)
def test_recover_hardware(
    mock_error_diag0,
    mock_error_diag1,
    mock_error_diag2,
    mock_error_diag3,
    prefs_path,
    error,
    expected,
    helpers,
):
    """Test recovering from hardware error"""
    microscope = helpers.setup_local_microscope(prefs_path)
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


@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    "prefs_path, experiment, expected_path",
    [
        (
            "data/preferences_ZSD_test.yml",
            "WellTile_10x_true.czexp",
            "data/Experiment Setup/WellTile_10x_true.czexp",
        ),
        (
            "data/preferences_3i_test.yml",
            "test_communication.exp.prefs",
            "data/SlideBook 6.0/test_communication.exp.prefs",
        ),
    ],
)
def test_create_experiment_path(prefs_path, experiment, expected_path, helpers):
    """Test creation of experiment path"""
    microscope = helpers.setup_local_microscope(prefs_path)
    experiment_path = microscope.create_experiment_path(experiment)
    assert os.path.abspath(expected_path) == os.path.abspath(experiment_path)


@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    "prefs_path, software",
    [
        ("data/preferences_ZSD_test.yml", "ZEN Blue Dummy"),
        ("data/preferences_3i_test.yml", "Slidebook Dummy"),
    ],
)
def test_stop_microscope(prefs_path, software, helpers):
    """Test creation of experiment path"""
    microscope = helpers.setup_local_microscope(prefs_path)

    if software:
        control_software = helpers.setup_local_control_software(software)
        microscope.add_control_software(control_software)

    microscope.stop_microscope()

    assert True


@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize("find_surface", [True, False])
@pytest.mark.parametrize(
    "prefs_path, ref_obj_id, expected",
    [
        ("data/preferences_ZSD_test.yml", None, "AutofocusNoReferenceObjectError"),
        ("data/preferences_ZSD_test.yml", "test", "HardwareCommandNotDefinedError"),
        ("data/preferences_3i_test.yml", None, "HardwareCommandNotDefinedError"),
    ],
)
def test_reference_position(prefs_path, find_surface, ref_obj_id, expected, helpers):
    """Test correction in xyz between objectives"""
    microscope = helpers.setup_local_microscope(prefs_path)
    try:
        result = microscope.reference_position(
            find_surface=find_surface, reference_object_id=ref_obj_id, verbose=False
        )
    except Exception as err:
        result = type(err).__name__
    assert result == expected


@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    (
        "prefs_path, experiment, component_dict, focus_drive_id, "
        "objective_changer_id, objectives, safety_object_id, "
        "safe_verts, safe_area_id, z_max, stage_id, "
        "auto_focus_id, expected"
    ),
    [
        (
            "data/preferences_3i_test.yml",
            "test_communication.exp.prefs",
            {},
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            {"Microscope": True},
        ),
        (
            "data/preferences_3i_test.yml",
            "test_communication.exp.prefs",
            {"MotorizedFocus": ["test"]},
            "MotorizedFocus",
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            {"Microscope": True, "MotorizedFocus": True},
        ),
        (
            "data/preferences_ZSD_test.yml",
            "WellTile_10x_true.czexp",
            {},
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            "HardwareDoesNotExistError",
        ),
        (
            "data/preferences_ZSD_test.yml",
            "WellTile_10x_true.czexp",
            {},
            "MotorizedFocus",
            "6xMotorizedNosepiece",
            None,
            "ZSD_01_plate",
            None,
            None,
            None,
            None,
            None,
            {"Microscope": True},
        ),
        (
            "data/preferences_ZSD_test.yml",
            "WellTile_10x_true.czexp",
            {"MotorizedFocus": ["test"], "6xMotorizedNosepiece": ["test"]},
            "MotorizedFocus",
            "6xMotorizedNosepiece",
            None,
            "ZSD_01_plate",
            None,
            None,
            None,
            None,
            None,
            {"Microscope": True, "MotorizedFocus": True, "6xMotorizedNosepiece": True},
        ),
        (
            "data/preferences_ZSD_test.yml",
            "WellTile_10x_true.czexp",
            {
                "MotorizedFocus": ["test"],
                "6xMotorizedNosepiece": ["test"],
                "Marzhauser": ["test"],
                "DefiniteFocus2": ["test"],
            },
            "MotorizedFocus",
            "6xMotorizedNosepiece",
            None,
            "ZSD_01_plate",
            None,
            None,
            None,
            "Marzhauser",
            "DefiniteFocus2",
            "TypeError",
        ),
        (
            "data/preferences_ZSD_test.yml",
            "WellTile_10x_true.czexp",
            {
                "MotorizedFocus": ["test"],
                "6xMotorizedNosepiece": ["test"],
                "Marzhauser": ["test"],
                "DefiniteFocus2": ["test"],
            },
            "MotorizedFocus",
            "6xMotorizedNosepiece",
            {
                "Plan-Apochromat 10x/0.45": {
                    "x_offset": -19,
                    "y_offset": 15,
                    "z_offset": 10,
                    "magnification": 10,
                    "immersion": "air",
                    "experiment": "WellTile_10x_true",
                    "camera": "Camera1 (back)",
                    "autofocus": "DefiniteFocus2",
                }
            },
            "ZSD_01_plate",
            None,
            None,
            None,
            "Marzhauser",
            "DefiniteFocus2",
            "UnboundLocalError",
        ),
        (
            "data/preferences_ZSD_test.yml",
            "WellTile_10x_true.czexp",
            {
                "MotorizedFocus": ["test"],
                "6xMotorizedNosepiece": ["test"],
                "Marzhauser": ["test"],
            },
            "MotorizedFocus",
            "6xMotorizedNosepiece",
            {
                "Plan-Apochromat 10x/0.45": {
                    "x_offset": -19,
                    "y_offset": 15,
                    "z_offset": 10,
                    "magnification": 10,
                    "immersion": "air",
                    "experiment": "WellTile_10x_true",
                    "camera": "Camera1 (back)",
                    "autofocus": "DefiniteFocus2",
                }
            },
            "ZSD_01_plate",
            [(3270, 1870), (108400, 1870), (108400, 71200), (3270, 71200)],
            "StageArea",
            9900,
            "Marzhauser",
            "DefiniteFocus2",
            {
                "Microscope": True,
                "MotorizedFocus": True,
                "6xMotorizedNosepiece": True,
                "Marzhauser": True,
            },
        ),
        (
            "data/preferences_ZSD_test.yml",
            "WellTile_10x_true.czexp",
            {
                "MotorizedFocus": ["test"],
                "6xMotorizedNosepiece": ["test"],
                "DefiniteFocus2": ["test"],
                "Marzhauser": ["test"],
            },
            "MotorizedFocus",
            "6xMotorizedNosepiece",
            {
                "Plan-Apochromat 10x/0.45": {
                    "x_offset": -19,
                    "y_offset": 15,
                    "z_offset": 10,
                    "magnification": 10,
                    "immersion": "air",
                    "experiment": "WellTile_10x_true",
                    "camera": "Camera1 (back)",
                    "autofocus": "DefiniteFocus2",
                }
            },
            "ZSD_01_plate",
            [(3270, 1870), (108400, 1870), (108400, 71200), (3270, 71200)],
            "StageArea",
            9900,
            "Marzhauser",
            "DefiniteFocus2",
            {
                "Microscope": False,
                "MotorizedFocus": True,
                "6xMotorizedNosepiece": True,
                "DefiniteFocus2": False,
                "Marzhauser": True,
            },
        ),
        (
            "data/preferences_ZSD_test.yml",
            "WellTile_10x_true.czexp",
            {
                "MotorizedFocus": ["test"],
                "6xMotorizedNosepiece": ["test"],
                "DefiniteFocus2": None,
                "Marzhauser": ["test"],
            },
            "MotorizedFocus",
            "6xMotorizedNosepiece",
            {
                "Plan-Apochromat 10x/0.45": {
                    "x_offset": -19,
                    "y_offset": 15,
                    "z_offset": 10,
                    "magnification": 10,
                    "immersion": "air",
                    "experiment": "WellTile_10x_true",
                    "camera": "Camera1 (back)",
                    "autofocus": "DefiniteFocus2",
                }
            },
            "ZSD_01_plate",
            [(3270, 1870), (108400, 1870), (108400, 71200), (3270, 71200)],
            "StageArea",
            9900,
            "Marzhauser",
            "DefiniteFocus2",
            {
                "Microscope": True,
                "MotorizedFocus": True,
                "6xMotorizedNosepiece": True,
                "DefiniteFocus2": True,
                "Marzhauser": True,
            },
        ),
    ],
)
def test_microscope_is_ready(
    prefs_path,
    experiment,
    component_dict,
    focus_drive_id,
    objective_changer_id,
    objectives,
    safety_object_id,
    safe_verts,
    safe_area_id,
    z_max,
    stage_id,
    auto_focus_id,
    expected,
    helpers,
):
    microscope = helpers.setup_local_microscope(prefs_path)

    if focus_drive_id:
        focus_drive = helpers.setup_local_focus_drive(helpers, focus_drive_id)
        microscope.add_microscope_object(focus_drive)

    if objective_changer_id:
        obj_changer = helpers.setup_local_obj_changer(
            helpers, objective_changer_id, objectives=objectives, prefs_path=prefs_path
        )
        microscope.add_microscope_object(obj_changer)

    if safety_object_id:
        safety_obj = helpers.setup_local_safety(safety_object_id)
        if safe_area_id:
            safety_obj.add_safe_area(safe_verts, safe_area_id, z_max)
        microscope.add_microscope_object(safety_obj)

    if stage_id:
        stage = helpers.setup_local_stage(
            helpers,
            stage_id,
            safe_area=safe_area_id,
            objective_changer=objective_changer_id,
            prefs_path=prefs_path,
        )
        microscope.add_microscope_object(stage)

    if auto_focus_id:
        autofocus = helpers.setup_local_autofocus(
            helpers, auto_focus_id, obj_changer=obj_changer, prefs_path=prefs_path
        )
        microscope.add_microscope_object(autofocus)

    try:
        result = microscope.microscope_is_ready(
            experiment,
            component_dict,
            focus_drive_id,
            objective_changer_id,
            safety_object_id,
        )
    except Exception as err:
        result = type(err).__name__
    assert result == expected


@patch(
    "microscope_automation.hardware.hardware_control_zeiss.SpinningDiskZeiss.recover_hardware"  # noqa
)
@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    ("prefs_path, software, experiment, " "objective_changer_id, objectives, expected"),
    [
        (
            "data/preferences_ZSD_test.yml",
            None,
            "WellTile_10x_true.czexp",
            None,
            None,
            "AttributeError",
        ),
        (
            "data/preferences_ZSD_test.yml",
            "ZEN Blue Dummy",
            "WellTile_10x_true.czexp",
            "6xMotorizedNosepiece",
            {
                "Plan-Apochromat 10x/0.45": {
                    "x_offset": -19,
                    "y_offset": 15,
                    "z_offset": 10,
                    "magnification": 10,
                    "immersion": "air",
                    "experiment": "WellTile_10x_true",
                    "camera": "Camera1 (back)",
                    "autofocus": "DefiniteFocus2",
                }
            },
            "LoadNotDefinedError",
        ),
    ],
)
def test_change_objective(
    mock_rec_hard,
    prefs_path,
    software,
    experiment,
    objective_changer_id,
    objectives,
    expected,
    helpers,
):
    microscope = helpers.setup_local_microscope(prefs_path)

    if software:
        control_software = helpers.setup_local_control_software(software)
        microscope.add_control_software(control_software)

    if objective_changer_id:
        obj_changer = helpers.setup_local_obj_changer(
            helpers, objective_changer_id, objectives=objectives, prefs_path=prefs_path
        )
        microscope.add_microscope_object(obj_changer)
    else:
        obj_changer = None

    try:
        result = microscope.change_objective(experiment, obj_changer)
    except Exception as err:
        result = type(err).__name__

    assert result == expected


@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    "prefs_path", ["data/preferences_ZSD_test.yml", "data/preferences_3i_test.yml"]
)
@pytest.mark.parametrize(
    ("auto_focus_id, use_auto_focus, expected"),
    [
        (None, False, "HardwareDoesNotExistError"),
        ("DefiniteFocus2", False, {"DefiniteFocus2": {"use_auto_focus": False}}),
        ("DefiniteFocus2", True, {"DefiniteFocus2": {"use_auto_focus": True}}),
    ],
)
def test_set_microscope(prefs_path, auto_focus_id, use_auto_focus, expected, helpers):
    microscope = helpers.setup_local_microscope(prefs_path)

    if auto_focus_id:
        autofocus = helpers.setup_local_autofocus(helpers, auto_focus_id)
        microscope.add_microscope_object(autofocus)

    try:
        result = microscope.set_microscope(
            {auto_focus_id: {"use_auto_focus": use_auto_focus}}
        )
    except Exception as err:
        result = type(err).__name__

    assert result == expected


@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    ("prefs_path, objective_info, ref_obj_id, expected"),
    [
        (
            "data/preferences_ZSD_test.yml",
            {
                "magnification": 10,
                "name": "Dummy Objective",
                "position": 0,
                "experiment": "WellTile_10x_true",
            },
            None,
            {None: set([0])},
        ),
        (
            "data/preferences_ZSD_test.yml",
            [
                {
                    "magnification": 10,
                    "name": "Dummy Objective",
                    "position": 0,
                    "experiment": "WellTile_10x_true",
                },
                {
                    "magnification": 10,
                    "name": "Dummy Objective",
                    "position": 1,
                    "experiment": "WellTile_10x_true",
                },
            ],
            ["test1", "test1"],
            {"test1": set([0, 1])},
        ),
        (
            "data/preferences_ZSD_test.yml",
            [
                {
                    "magnification": 10,
                    "name": "Dummy Objective",
                    "position": 0,
                    "experiment": "WellTile_10x_true",
                },
                {
                    "magnification": 10,
                    "name": "Dummy Objective",
                    "position": 1,
                    "experiment": "WellTile_10x_true",
                },
            ],
            ["test1", "test2"],
            "KeyError",
        ),
    ],
)
def test_set_objective_is_ready(
    prefs_path, objective_info, ref_obj_id, expected, helpers
):
    microscope = helpers.setup_local_microscope(prefs_path)

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


@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    ("prefs_path, objective_info, ref_obj_id, set_first, " "expected"),
    [
        (
            "data/preferences_ZSD_test.yml",
            {
                "magnification": 10,
                "name": "Dummy Objective",
                "position": 0,
                "experiment": "WellTile_10x_true",
            },
            None,
            True,
            True,
        ),
        (
            "data/preferences_ZSD_test.yml",
            {
                "magnification": 10,
                "name": "Dummy Objective",
                "position": 0,
                "experiment": "WellTile_10x_true",
            },
            "test",
            True,
            True,
        ),
        (
            "data/preferences_ZSD_test.yml",
            {
                "magnification": 10,
                "name": "Dummy Objective",
                "position": 0,
                "experiment": "WellTile_10x_true",
            },
            "test",
            False,
            False,
        ),
    ],
)
def test_get_objective_is_ready(
    prefs_path, objective_info, ref_obj_id, set_first, expected, helpers
):
    microscope = helpers.setup_local_microscope(prefs_path)

    try:
        if set_first:
            microscope.set_objective_is_ready(objective_info, ref_obj_id)
        result = microscope.get_objective_is_ready(
            objective_info["position"], ref_obj_id
        )
    except Exception as err:
        result = type(err).__name__

    assert result == expected


@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    ("prefs_path, expected"), [("data/preferences_ZSD_test.yml", "TypeError")]
)
def test_is_ready_errors(prefs_path, expected, helpers):
    microscope = helpers.setup_local_microscope(prefs_path)

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
        result = microscope._auto_focus_is_ready(
            microscope, None, ["find_surface"], None
        )
    except Exception as err:
        result = type(err).__name__

    assert result == expected


@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    "prefs_path", ["data/preferences_ZSD_test.yml", "data/preferences_3i_test.yml"]
)
@pytest.mark.parametrize(
    ("object_to_get, expected"), [(None, "HardwareDoesNotExistError"), ("test", "test")]
)
def test__get_microscope_object(prefs_path, object_to_get, expected, helpers):
    microscope = helpers.setup_local_microscope(prefs_path)

    if object_to_get:
        focus_drive = helpers.setup_local_focus_drive(helpers, object_to_get)
        microscope.add_microscope_object(focus_drive)

    try:
        result = microscope._get_microscope_object(object_to_get).id
    except Exception as err:
        result = type(err).__name__

    assert result == expected


@patch("microscope_automation.connectors.connect_zen_blue.ConnectMicroscope.live_mode_start")
@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    ("prefs_path, experiment, objective_changer_id, " "camera_id, expected"),
    [
        (
            "data/preferences_3i_test.yml",
            "test_communication.exp.prefs",
            None,
            None,
            "AttributeError",
        ),
        (
            "data/preferences_3i_test.yml",
            "test_communication.exp.prefs",
            "6xMotorizedNosepiece",
            None,
            "HardwareDoesNotExistError",
        ),
        (
            "data/preferences_3i_test.yml",
            "test_communication.exp.prefs",
            "6xMotorizedNosepiece",
            "Camera1 (back)",
            "HardwareCommandNotDefinedError",
        ),
        (
            "data/preferences_3i_test.yml",
            None,
            "6xMotorizedNosepiece",
            "Camera1 (back)",
            "HardwareCommandNotDefinedError",
        ),
        (
            "data/preferences_ZSD_test.yml",
            "WellTile_10x_true.czexp",
            None,
            None,
            "AttributeError",
        ),
        (
            "data/preferences_ZSD_test.yml",
            "WellTile_10x_true.czexp",
            "6xMotorizedNosepiece",
            None,
            "HardwareDoesNotExistError",
        ),
        (
            "data/preferences_ZSD_test.yml",
            "WellTile_10x_true.czexp",
            "6xMotorizedNosepiece",
            "Camera1 (back)",
            None,
        ),
        (
            "data/preferences_ZSD_test.yml",
            None,
            "6xMotorizedNosepiece",
            "Camera1 (back)",
            None,
        ),
    ],
)
def test_setup_microscope_for_initialization(
    mock_func,
    prefs_path,
    experiment,
    objective_changer_id,
    camera_id,
    expected,
    helpers,
):
    microscope = helpers.setup_local_microscope(prefs_path)

    if objective_changer_id:
        obj_changer = helpers.setup_local_obj_changer(
            helpers, objective_changer_id, prefs_path=prefs_path
        )
        microscope.add_microscope_object(obj_changer)

        if camera_id:
            obj_changer.default_camera = camera_id
            microscope.add_microscope_object(helpers.setup_local_camera(camera_id))
    else:
        obj_changer = None

    try:
        result = microscope.setup_microscope_for_initialization(obj_changer, experiment)
    except Exception as err:
        result = type(err).__name__

    assert result == expected


@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    ("prefs_path, software, focus_drive_id, expected"),
    [
        (
            "data/preferences_3i_test.yml",
            "Slidebook Dummy",
            None,
            "HardwareDoesNotExistError",
        ),
        (
            "data/preferences_3i_test.yml",
            "Slidebook Dummy",
            "MotorizedFocus",
            "ConnectionError",
        ),
        ("data/preferences_ZSD_test.yml", None, None, "HardwareDoesNotExistError"),
        (
            "data/preferences_ZSD_test.yml",
            "ZEN Blue Dummy",
            "MotorizedFocus",
            {
                "load_position": None,
                "work_position": None,
                "absolute": 500,
                "focality_corrected": None,
                "z_focus_offset": None,
            },
        ),
    ],
)
def test_get_z_position(prefs_path, software, focus_drive_id, expected, helpers):
    microscope = helpers.setup_local_microscope(prefs_path)

    if software:
        control_software = helpers.setup_local_control_software(software)
        microscope.add_control_software(control_software)

    if focus_drive_id:
        focus_drive = helpers.setup_local_focus_drive(helpers, focus_drive_id)
        microscope.add_microscope_object(focus_drive)

    try:
        result = microscope.get_z_position(focus_drive_id)
    except Exception as err:
        result = type(err).__name__

    assert result == expected


@patch(
    "microscope_automation.hardware.hardware_control_zeiss.SpinningDiskZeiss.recover_hardware"  # noqa
)
@patch("microscope_automation.hardware.hardware_components.Safety.show_safe_areas")
@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    (
        "prefs_path, software, focus_drive_id, "
        "max_load_position, min_work_position, objective_changer_id, "
        "objectives, safety_object_id, "
        "safe_verts, safe_area_id, z_max, stage_id, "
        "auto_focus_id, expected"
    ),
    [
        (
            "data/preferences_3i_test.yml",
            "Slidebook Dummy",
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            "Marzhauser",
            None,
            "HardwareError",
        ),
        (
            "data/preferences_ZSD_test.yml",
            "ZEN Blue Dummy",
            "MotorizedFocus",
            500,
            100,
            "6xMotorizedNosepiece",
            {
                "Plan-Apochromat 10x/0.45": {
                    "x_offset": -19,
                    "y_offset": 15,
                    "z_offset": 10,
                    "magnification": 10,
                    "immersion": "air",
                    "experiment": "WellTile_10x_true",
                    "camera": "Camera1 (back)",
                    "autofocus": "DefiniteFocus2",
                }
            },
            "ZSD_01_plate",
            [(3270, 1870), (108400, 1870), (108400, 71200), (3270, 71200)],
            "StageArea",
            9900,
            "Marzhauser",
            "DefiniteFocus2",
            "CrashDangerError",
        ),
        (
            "data/preferences_ZSD_test.yml",
            "ZEN Blue Dummy",
            "MotorizedFocus",
            None,
            None,
            "6xMotorizedNosepiece",
            {
                "Plan-Apochromat 10x/0.45": {
                    "x_offset": -19,
                    "y_offset": 15,
                    "z_offset": 10,
                    "magnification": 10,
                    "immersion": "air",
                    "experiment": "WellTile_10x_true",
                    "camera": "Camera1 (back)",
                    "autofocus": "DefiniteFocus2",
                }
            },
            "ZSD_01_plate",
            [(-1, -1), (108400, -1), (108400, 71200), (-1, 71200)],
            "StageArea",
            9900,
            "Marzhauser",
            "DefiniteFocus2",
            "LoadNotDefinedError",
        ),
        (
            "data/preferences_ZSD_test.yml",
            "ZEN Blue Dummy",
            "MotorizedFocus",
            500,
            100,
            "6xMotorizedNosepiece",
            {
                "Plan-Apochromat 10x/0.45": {
                    "x_offset": -19,
                    "y_offset": 15,
                    "z_offset": 10,
                    "magnification": 10,
                    "immersion": "air",
                    "experiment": "WellTile_10x_true",
                    "camera": "Camera1 (back)",
                    "autofocus": "DefiniteFocus2",
                }
            },
            "ZSD_01_plate",
            [(-1, -1), (108400, -1), (108400, 71200), (-1, 71200)],
            "StageArea",
            9900,
            "Marzhauser",
            "DefiniteFocus2",
            (0, 0, 500),
        ),
    ],
)
def test_move_to_abs_pos(
    mock_func1,
    mock_func2,
    prefs_path,
    software,
    focus_drive_id,
    max_load_position,
    min_work_position,
    objective_changer_id,
    objectives,
    safety_object_id,
    safe_verts,
    safe_area_id,
    z_max,
    stage_id,
    auto_focus_id,
    expected,
    helpers,
):
    microscope = helpers.setup_local_microscope(prefs_path)

    if software:
        control_software = helpers.setup_local_control_software(software)
        microscope.add_control_software(control_software)

    if focus_drive_id:
        focus_drive = helpers.setup_local_focus_drive(
            helpers,
            focus_drive_id,
            max_load_position=max_load_position,
            min_work_position=min_work_position,
            prefs_path=prefs_path,
            objective_changer=objective_changer_id,
        )
        focus_drive.z_load = 500
        if max_load_position:
            focus_drive.initialize(
                control_software.connection,
                action_list=["set_load"],
                verbose=False,
                test=True,
            )
        microscope.add_microscope_object(focus_drive)

    if objective_changer_id:
        obj_changer = helpers.setup_local_obj_changer(
            helpers, objective_changer_id, objectives=objectives, prefs_path=prefs_path
        )
        microscope.add_microscope_object(obj_changer)

    if safety_object_id:
        safety_obj = helpers.setup_local_safety(safety_object_id)
        if safe_area_id:
            safety_obj.add_safe_area(safe_verts, safe_area_id, z_max)
        microscope.add_microscope_object(safety_obj)

    if stage_id:
        stage = helpers.setup_local_stage(
            helpers,
            stage_id,
            safe_area=safe_area_id,
            objective_changer=objective_changer_id,
            prefs_path=prefs_path,
        )
        microscope.add_microscope_object(stage)

    if auto_focus_id:
        autofocus = helpers.setup_local_autofocus(
            helpers, auto_focus_id, obj_changer=obj_changer, prefs_path=prefs_path
        )
        microscope.add_microscope_object(autofocus)

    try:
        result = microscope.move_to_abs_pos(
            stage_id,
            focus_drive_id,
            objective_changer_id,
            auto_focus_id,
            safety_object_id,
        )
    except Exception as err:
        result = type(err).__name__
    assert result == expected


@patch("microscope_automation.util.automation_messages_form_layout.read_string")
@patch("microscope_automation.zeiss.connect_zen_blue_dummy.Application.RunMacro_2")
@patch("microscope_automation.zeiss.connect_zen_blue_dummy.Application.RunMacro")
@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    (
        "prefs_path, macro_name, macro_param, run_result, "
        "read_string_result, expected"
    ),
    [
        (
            "data/preferences_ZSD_test.yml",
            "10x_stitch",
            None,
            (
                "C:\\Users\\winfriedw\\Documents\\Carl Zeiss\\ZEN\\Documents\\Macros\\"
                "10x_stitch.czmac(6):Could not find a part of the path 'D:\\Production"
                "\\3500003095\\ZSD1\\10XwellScan\\TapeOnly'."
            ),
            "10x_stitch",
            "AutomationError",
        ),
        (
            "data/preferences_ZSD_test.yml",
            "10x_stitch",
            None,
            (
                "C:\\Users\\winfriedw\\Documents\\Carl Zeiss\\ZEN\\Documents\\Macros\\"
                "10x_stitch.czmac(6):Could not find a part of the path 'D:\\Production"
                "\\3500003095\\ZSD1\\10XwellScan\\TapeOnly'."
            ),
            0,
            "AutomationError",
        ),
        ("data/preferences_ZSD_test.yml", "test", None, "ok", None, None),
        ("data/preferences_ZSD_test.yml", "test", ["test_param"], "ok", None, None),
    ],
)
def test_run_macro(
    mock_run,
    mock_run_2,
    mock_read_string,
    prefs_path,
    macro_name,
    macro_param,
    run_result,
    read_string_result,
    expected,
    helpers,
):
    mock_run.return_value = run_result
    mock_run_2.return_value = run_result
    mock_read_string.return_value = read_string_result

    microscope = helpers.setup_local_microscope(prefs_path)

    try:
        result = microscope.run_macro(macro_name, macro_param)
    except Exception as err:
        result = type(err).__name__
    assert result == expected


@patch("microscope_automation.connectors.connect_zen_blue.ConnectMicroscope.save_image")
@patch(
    "microscope_automation.connectors.connect_zen_blue.ConnectMicroscope.close_experiment"
)
@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    ("prefs_path, software, experiment, file_path, " "z_start, expected"),
    [
        (
            "data/preferences_3i_test.yml",
            "Slidebook Dummy",
            "test_communication.exp.prefs",
            None,
            None,
            ImageAICS,
        ),
        (
            "data/preferences_3i_test.yml",
            "Slidebook Dummy",
            "test_communication.exp.prefs",
            "/data/test_image.png",
            None,
            "HardwareCommandNotDefinedError",
        ),
        (
            "data/preferences_ZSD_test.yml",
            "ZEN Blue Dummy",
            "WellTile_10x_true.czexp",
            None,
            "F",
            ImageAICS,
        ),
        (
            "data/preferences_ZSD_test.yml",
            "ZEN Blue Dummy",
            "WellTile_10x_true.czexp",
            None,
            "L",
            ImageAICS,
        ),
        (
            "data/preferences_ZSD_test.yml",
            "ZEN Blue Dummy",
            "WellTile_10x_true.czexp",
            "/data/test_image.png",
            "C",
            ImageAICS,
        ),
    ],
)
def test_execute_experiment(
    mock_func1,
    mock_func2,
    prefs_path,
    software,
    experiment,
    file_path,
    z_start,
    expected,
    helpers,
):
    microscope = helpers.setup_local_microscope(prefs_path)

    if software:
        control_software = helpers.setup_local_control_software(software)
        microscope.add_control_software(control_software)

    try:
        result = microscope.execute_experiment(experiment, file_path, z_start)
        result = result.__class__
    except Exception as err:
        result = type(err).__name__

    assert result == expected


@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    ("prefs_path, software, camera_id, experiment, " "live, expected"),
    [
        (
            "data/preferences_ZSD_test.yml",
            "ZEN Blue Dummy",
            "Camera1 (back)",
            "WellTile_10x_true.czexp",
            True,
            None,
        ),
        (
            "data/preferences_ZSD_test.yml",
            "ZEN Blue Dummy",
            "Camera1 (back)",
            "WellTile_10x_true.czexp",
            False,
            None,
        ),
    ],
)
def test_live_mode(
    prefs_path, software, camera_id, experiment, live, expected, helpers
):
    microscope = helpers.setup_local_microscope(prefs_path)
    microscope.add_microscope_object(helpers.setup_local_camera(camera_id))

    if software:
        control_software = helpers.setup_local_control_software(software)
        microscope.add_control_software(control_software)

    result = microscope.live_mode(camera_id, experiment, live)

    assert result == expected


@patch("microscope_automation.connectors.connect_zen_blue.ConnectMicroscope.save_image")
@patch(
    "microscope_automation.connectors.connect_zen_blue.ConnectMicroscope.close_experiment"
)  # noqa
@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    (
        "prefs_path, software, camera_id, experiment, "
        "file_path, interactive, expected"
    ),
    [
        (
            "data/preferences_3i_test.yml",
            "Slidebook Dummy",
            "Camera1 (back)",
            "test_communication.exp.prefs",
            "/data/test_image.png",
            True,
            "HardwareCommandNotDefinedError",
        ),
        (
            "data/preferences_ZSD_test.yml",
            "ZEN Blue Dummy",
            "Camera1 (back)",
            "WellTile_10x_true.czexp",
            "/data/test_image.png",
            True,
            ImageAICS,
        ),
        (
            "data/preferences_ZSD_test.yml",
            "ZEN Blue Dummy",
            "Camera1 (back)",
            "WellTile_10x_true.czexp",
            None,
            False,
            "TypeError",
        ),
        (
            "data/preferences_ZSD_test.yml",
            "ZEN Blue Dummy",
            "Camera1 (back)",
            "WellTile_10x_true.czexp",
            "/data/test_image.png",
            False,
            ImageAICS,
        ),
    ],
)
def test_save_image(
    mock_func1,
    mock_func2,
    prefs_path,
    software,
    camera_id,
    experiment,
    file_path,
    interactive,
    expected,
    helpers,
):
    microscope = helpers.setup_local_microscope(prefs_path)
    microscope.add_microscope_object(helpers.setup_local_camera(camera_id))

    if software:
        control_software = helpers.setup_local_control_software(software)
        microscope.add_control_software(control_software)

    try:
        image = microscope.execute_experiment(experiment)
        result = microscope.save_image(file_path, image, interactive)
        result = result.__class__
    except Exception as err:
        result = type(err).__name__

    assert result == expected


@patch("microscope_automation.connectors.connect_zen_blue.ConnectMicroscope.load_image")
@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    ("prefs_path, software, camera_id, experiment, " "image, get_meta, expected"),
    [
        (
            "data/preferences_ZSD_test.yml",
            "ZEN Blue Dummy",
            "Camera1 (back)",
            "WellTile_10x_true.czexp",
            ImageAICS(),
            True,
            "<class 'mock.mock.MagicMock'>",
        ),
        (
            "data/preferences_ZSD_test.yml",
            "ZEN Blue Dummy",
            "Camera1 (back)",
            "WellTile_10x_true.czexp",
            ImageAICS(),
            False,
            "<class 'mock.mock.MagicMock'>",
        ),
        (
            "data/preferences_3i_test.yml",
            "Slidebook Dummy",
            "Camera1 (back)",
            "test_communication.exp.prefs",
            ImageAICS(),
            False,
            "ConnectionError",
        ),
    ],
)
def test_load_image(
    mock_func1,
    prefs_path,
    software,
    camera_id,
    experiment,
    image,
    get_meta,
    expected,
    helpers,
):
    microscope = helpers.setup_local_microscope(prefs_path)
    microscope.add_microscope_object(helpers.setup_local_camera(camera_id))

    if software:
        control_software = helpers.setup_local_control_software(software)
        microscope.add_control_software(control_software)

    try:
        result = microscope.load_image(image, get_meta)
        result = str(result.__class__)
    except Exception as err:
        result = type(err).__name__

    assert result == expected


@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    ("prefs_path, software, expected"),
    [
        ("data/preferences_ZSD_test.yml", "ZEN Blue Dummy", None),
        ("data/preferences_3i_test.yml", "Slidebook Dummy", "ConnectionError"),
    ],
)
def test_remove_images(prefs_path, software, expected, helpers):
    microscope = helpers.setup_local_microscope(prefs_path)

    if software:
        control_software = helpers.setup_local_control_software(software)
        microscope.add_control_software(control_software)

    try:
        result = microscope.remove_images()
    except Exception as err:
        result = type(err).__name__

    assert result == expected
