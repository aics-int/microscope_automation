"""
Test helper classes which define different microscope components.
Created on July 7, 2020

@author: fletcher.chapin
"""

import pytest
import numpy
from lxml import etree
from mock import patch
from matplotlib.path import Path as mpl_path
from microscope_automation.zeiss.zen_experiment_info import ZenExperiment
import os

os.chdir(os.path.dirname(__file__))

# set skip_all_tests = True to focus on single test
skip_all_tests = False

###############################################################################
#
# Tests for the Experiments class
#
###############################################################################


@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    "name, path, prefs_path, expected",
    [
        (
            "WellTile_10x_true.czexp",
            "data/Experiment Setup/WellTile_10x_true.czexp",
            "data/preferences_ZSD_test.yml",
            True,
        ),
        (
            "test_communication.exp.prefs",
            "data/SlideBook 6.0/test_communication.exp.prefs",
            "data/preferences_3i_test.yml",
            True,
        ),
        (
            "test_communication.exp.prefs",
            "data/Experiment Setup/test_communication.exp.prefs",
            "data/preferences_ZSD_test.yml",
            False,
        ),
        (
            "WellTile_10x_true.czexp",
            "data/SlideBook 6.0/WellTile_10x_true.czexp",
            "data/preferences_3i_test.yml",
            False,
        ),
    ],
)
def test_validate_experiment(name, path, prefs_path, expected, helpers):
    experiment = helpers.setup_local_experiment(helpers, name, path, prefs_path)
    assert experiment.validate_experiment() == expected


@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    "name, path, prefs_path, expected",
    [
        (
            "WellTile_10x_true.czexp",
            "data/Experiment Setup/WellTile_10x_true.czexp",
            "data/preferences_ZSD_test.yml",
            True,
        ),
        (
            "WellTile_10x_false.czexp",
            "data/Experiment Setup/WellTile_10x_false.czexp",
            "data/preferences_ZSD_test.yml",
            False,
        ),
        (
            "test_communication.exp.prefs",
            "data/Experiment Setup/test_communication.exp.prefs",
            "data/preferences_ZSD_test.yml",
            "ExperimentNotExistError",
        ),
        (
            "test_communication.exp.prefs",
            "data/SlideBook 6.0/test_communication.exp.prefs",
            "data/preferences_3i_test.yml",
            "HardwareCommandNotDefinedError",
        ),
    ],
)
def test_is_z_stack(name, path, prefs_path, expected, helpers):
    experiment = helpers.setup_local_experiment(helpers, name, path, prefs_path)
    try:
        result = experiment.is_z_stack()
    except Exception as err:
        result = type(err).__name__
    assert result == expected


@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    "name, path, prefs_path, expected",
    [
        (
            "WellTile_10x_true.czexp",
            "data/Experiment Setup/WellTile_10x_true.czexp",
            "data/preferences_ZSD_test.yml",
            4e-06,
        ),
        (
            "WellTile_10x_false.czexp",
            "data/Experiment Setup/WellTile_10x_false.czexp",
            "data/preferences_ZSD_test.yml",
            0,
        ),
        (
            "test_communication.exp.prefs",
            "data/Experiment Setup/test_communication.exp.prefs",
            "data/preferences_ZSD_test.yml",
            "ExperimentNotExistError",
        ),
        (
            "test_communication.exp.prefs",
            "data/SlideBook 6.0/test_communication.exp.prefs",
            "data/preferences_3i_test.yml",
            "HardwareCommandNotDefinedError",
        ),
    ],
)
def test_z_stack_range(name, path, prefs_path, helpers, expected):
    experiment = helpers.setup_local_experiment(helpers, name, path, prefs_path)
    try:
        result = experiment.z_stack_range()
    except Exception as err:
        result = type(err).__name__
    assert result == expected


@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    "name, path, prefs_path, expected",
    [
        (
            "WellTile_10x_true.czexp",
            "data/Experiment Setup/WellTile_10x_true.czexp",
            "data/preferences_ZSD_test.yml",
            True,
        ),
        (
            "WellTile_10x_false.czexp",
            "data/Experiment Setup/WellTile_10x_false.czexp",
            "data/preferences_ZSD_test.yml",
            False,
        ),
        (
            "test_communication.exp.prefs",
            "data/Experiment Setup/test_communication.exp.prefs",
            "data/preferences_ZSD_test.yml",
            "ExperimentNotExistError",
        ),
        (
            "test_communication.exp.prefs",
            "data/SlideBook 6.0/test_communication.exp.prefs",
            "data/preferences_3i_test.yml",
            "HardwareCommandNotDefinedError",
        ),
    ],
)
def test_is_tile_scan(name, path, prefs_path, expected, helpers):
    experiment = helpers.setup_local_experiment(helpers, name, path, prefs_path)
    try:
        result = experiment.is_tile_scan()
    except Exception as err:
        result = type(err).__name__
    assert result == expected


@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    "name, path, prefs_path, x, y, z, expected",
    [
        (
            "WellTile_10x_true.czexp",
            "data/Experiment Setup/WellTile_10x_true.czexp",
            "data/preferences_ZSD_test.yml",
            1000,
            1000,
            3,
            "1000,1000,3",
        ),
        (
            "test_communication.exp.prefs",
            "data/Experiment Setup/test_communication.exp.prefs",
            "data/preferences_ZSD_test.yml",
            1000,
            1000,
            3,
            "ExperimentNotExistError",
        ),
        (
            "test_communication.exp.prefs",
            "data/SlideBook 6.0/test_communication.exp.prefs",
            "data/preferences_3i_test.yml",
            1000,
            1000,
            3,
            "HardwareCommandNotDefinedError",
        ),
    ],
)
def test_update_tile_positions(name, path, prefs_path, x, y, z, expected, helpers):
    experiment = helpers.setup_local_experiment(helpers, name, path, prefs_path)
    try:
        experiment.update_tile_positions(x, y, z)

        tree = etree.parse(experiment.experiment_path)
        root = tree.getroot()

        xy = root.xpath(ZenExperiment.TAG_PATH_TILE_CENTER_XY)[0].text
        z = root.xpath(ZenExperiment.TAG_PATH_TILE_CENTER_Z)[0].text

        result = xy + "," + z
    except Exception as err:
        result = type(err).__name__
    assert result == expected


@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    "name, path, prefs_path, expected",
    [
        (
            "WellTile_10x_true.czexp",
            "data/Experiment Setup/WellTile_10x_true.czexp",
            "data/preferences_ZSD_test.yml",
            1,
        ),
        (
            "test_communication.exp.prefs",
            "data/Experiment Setup/test_communication.exp.prefs",
            "data/preferences_ZSD_test.yml",
            "ExperimentNotExistError",
        ),
        (
            "test_communication.exp.prefs",
            "data/SlideBook 6.0/test_communication.exp.prefs",
            "data/preferences_3i_test.yml",
            "HardwareCommandNotDefinedError",
        ),
    ],
)
def test_get_objective_position(name, path, prefs_path, expected, helpers):
    experiment = helpers.setup_local_experiment(helpers, name, path, prefs_path)
    try:
        result = experiment.get_objective_position()
    except Exception as err:
        result = type(err).__name__
    assert result == expected


@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    "name, path, prefs_path, expected",
    [
        (
            "WellTile_10x_true.czexp",
            "data/Experiment Setup/WellTile_10x_true.czexp",
            "data/preferences_ZSD_test.yml",
            "data/Experiment Setup/focus_settings.xml",
        ),
        (
            "test_communication.exp.prefs",
            "data/Experiment Setup/test_communication.exp.prefs",
            "data/preferences_ZSD_test.yml",
            "ExperimentNotExistError",
        ),
        (
            "test_communication.exp.prefs",
            "data/SlideBook 6.0/test_communication.exp.prefs",
            "data/preferences_3i_test.yml",
            "HardwareCommandNotDefinedError",
        ),
    ],
)
def test_get_focus_settings(name, path, prefs_path, expected, helpers):
    experiment = helpers.setup_local_experiment(helpers, name, path, prefs_path)
    try:
        settings = etree.tostring(experiment.get_focus_settings()[0])
        root = etree.tostring(etree.parse(expected).getroot())

        # there was a difference in tabs from the different xml files
        # the below trimming fixes that
        result = b"\n".join(settings.split())
        expected = b"\n".join(root.split())
    except Exception as err:
        result = type(err).__name__
    assert result == expected


###############################################################################
#
# Tests for the ControlSoftware class
#
###############################################################################


@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    "software, expected",
    [
        (
            "ZEN Blue Dummy",
            "microscope_automation.zeiss.connect_zen_blue.ConnectMicroscope",
        ),  # noqa
        (
            "Slidebook Dummy",
            "microscope_automation.slidebook.connect_slidebook.ConnectMicroscope",
        ),  # noqa
        ("Invalid Name", "AttributeError"),
    ],
)
def test_connect_to_microscope_software(software, expected, helpers):
    control_software = helpers.setup_local_control_software(software)
    try:
        result = str(control_software.connection).split()[0][1:]
    except Exception as err:
        result = type(err).__name__

    assert result == expected


###############################################################################
#
# Tests for the Safety class
#
###############################################################################


@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    "safety_id, safe_verts, safe_area_id, z_max, path_exp, z_exp",
    [
        (
            "ZSD_01_immersion",
            [(3270, 1870), (108400, 1870), (108400, 71200), (3270, 71200)],
            "StageArea",
            9900,
            (
                "Path(array([[3270.,1870.],[108400.,1870.],"
                "[108400.,71200.],[3270.,71200.],[3270.,1870.]]),"
                "array([1,2,2,2,79],dtype=uint8))"
            ),
            9900,
        ),
        (
            "ZSD_01_immersion",
            [(5400, 64300), (7400, 64300), (7400, 85100), (5400, 85100)],
            "PumpArea",
            100,
            (
                "Path(array([[5400.,64300.],[7400.,64300.],[7400.,85100.],"
                "[5400.,85100.],[5400.,64300.]]),array([1,2,2,2,79],"
                "dtype=uint8))"
            ),
            100,
        ),
    ],
)
def test_add_safe_area(
    safety_id, safe_verts, safe_area_id, z_max, path_exp, helpers, z_exp
):
    safety = helpers.setup_local_safety(safety_id)
    safety.add_safe_area(safe_verts, safe_area_id, z_max)
    # removing all whitespace to align with expected result
    path_result = "".join(str(safety.safe_areas[safe_area_id]["path"]).split())
    assert safety.safe_areas[safe_area_id]["z_max"] == z_exp and path_result == path_exp


@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests from")
@pytest.mark.parametrize(
    (
        "safety_id, safe_verts1, safe_area_id1, z_max1, "
        "safe_verts2, safe_area_id2, z_max2, path_exp, z_exp"
    ),
    [
        (
            "ZSD_01_immersion",
            [(3270, 1870), (108400, 1870), (108400, 71200), (3270, 71200)],
            "StageArea",
            9900,
            None,
            None,
            None,
            (
                "Path(array([[3270.,1870.],[108400.,1870.],"
                "[108400.,71200.],[3270.,71200.],[3270.,1870.]]),"
                "array([1,2,2,2,79],dtype=uint8))"
            ),
            9900,
        ),
        (
            "ZSD_01_immersion",
            [(3270, 1870), (108400, 1870), (108400, 71200), (3270, 71200)],
            "StageArea",
            9900,
            [(5400, 64300), (7400, 64300), (7400, 85100), (5400, 85100)],
            "PumpArea",
            100,
            (
                "Path(array([[3270.,1870.],[108400.,1870.],"
                "[108400.,71200.],[3270.,71200.],[3270.,1870.],"
                "[5400.,64300.],[7400.,64300.],[7400.,85100.],"
                "[5400.,85100.],[5400.,64300.]]),"
                "array([1,2,2,2,79,1,2,2,2,79],dtype=uint8))"
            ),
            100,
        ),
    ],
)
def test_get_safe_area(
    safety_id,
    safe_verts1,
    safe_area_id1,
    z_max1,
    safe_verts2,
    safe_area_id2,
    z_max2,
    path_exp,
    z_exp,
    helpers,
):
    safety = helpers.setup_local_safety(safety_id)
    safety.add_safe_area(safe_verts1, safe_area_id1, z_max1)
    area = safety.get_safe_area(safe_area_id1)

    if safe_area_id2:
        safety.add_safe_area(safe_verts2, safe_area_id2, z_max2)
        area = safety.get_safe_area()

    path_result = "".join(str(area["path"]).split())
    assert area["z_max"] == z_exp and path_result == path_exp


@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests from")
@pytest.mark.parametrize(
    (
        "safety_id, safe_verts1, safe_area_id1, z_max1, "
        "safe_verts2, safe_area_id2, z_max2, x, y, z, expected"
    ),
    [
        (
            "ZSD_01_immersion",
            [(3270, 1870), (108400, 1870), (108400, 71200), (3270, 71200)],
            "StageArea",
            9900,
            None,
            None,
            None,
            1,
            5000,
            10,
            False,
        ),
        (
            "ZSD_01_immersion",
            [(3270, 1870), (108400, 1870), (108400, 71200), (3270, 71200)],
            "StageArea",
            9900,
            None,
            None,
            None,
            6000,
            5000,
            10000,
            False,
        ),
        (
            "ZSD_01_immersion",
            [(3270, 1870), (108400, 1870), (108400, 71200), (3270, 71200)],
            "StageArea",
            9900,
            None,
            None,
            None,
            3270,
            1870,
            5000,
            False,
        ),
        (
            "ZSD_01_immersion",
            [(3270, 1870), (108400, 1870), (108400, 71200), (3270, 71200)],
            "StageArea",
            9900,
            None,
            None,
            None,
            3270,
            1871,
            5000,
            True,
        ),
        (
            "ZSD_01_immersion",
            [(3270, 1870), (108400, 1870), (108400, 71200), (3270, 71200)],
            "StageArea",
            9900,
            [(5400, 64300), (7400, 64300), (7400, 85100), (5400, 85100)],
            "PumpArea",
            100,
            6000,
            1000,
            10,
            False,
        ),
        (
            "ZSD_01_immersion",
            [(3270, 1870), (108400, 1870), (108400, 71200), (3270, 71200)],
            "StageArea",
            9900,
            [(5400, 64300), (7400, 64300), (7400, 85100), (5400, 85100)],
            "PumpArea",
            100,
            6000,
            65000,
            100,
            False,
        ),
        (
            "ZSD_01_immersion",
            [(3270, 1870), (108400, 1870), (108400, 71200), (3270, 71200)],
            "StageArea",
            9900,
            [(5400, 64300), (7400, 64300), (7400, 85100), (5400, 85100)],
            "PumpArea",
            100,
            6000,
            65000,
            99,
            True,
        ),
    ],
)
def test_is_safe_position(
    safety_id,
    safe_verts1,
    safe_area_id1,
    z_max1,
    safe_verts2,
    safe_area_id2,
    z_max2,
    x,
    y,
    z,
    expected,
    helpers,
):
    safety = helpers.setup_local_safety(safety_id)
    safety.add_safe_area(safe_verts1, safe_area_id1, z_max1)

    if safe_area_id2:
        safety.add_safe_area(safe_verts2, safe_area_id2, z_max2)

    assert safety.is_safe_position(x, y, z) == expected


@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests from")
@pytest.mark.parametrize(
    (
        "safety_id, safe_verts1, safe_area_id1, z_max1, "
        "safe_verts2, safe_area_id2, z_max2, xy, z, expected"
    ),
    [
        (
            "ZSD_01_immersion",
            [(3270, 1870), (108400, 1870), (108400, 71200), (3270, 71200)],
            "StageArea",
            9900,
            None,
            None,
            None,
            [(5000, 2000), (110000, 40000)],
            10,
            False,
        ),
        (
            "ZSD_01_immersion",
            [(3270, 1870), (108400, 1870), (108400, 71200), (3270, 71200)],
            "StageArea",
            9900,
            None,
            None,
            None,
            [(5000, 2000), (100000, 40000)],
            10000,
            False,
        ),
        (
            "ZSD_01_immersion",
            [(3270, 1870), (108400, 1870), (108400, 71200), (3270, 71200)],
            "StageArea",
            9900,
            None,
            None,
            None,
            [(5000, 2000), (100000, 40000)],
            9000,
            True,
        ),
        (
            "ZSD_01_immersion",
            [(3270, 1870), (108400, 1870), (108400, 71200), (3270, 71200)],
            "StageArea",
            9900,
            [(1, 1), (2000, 1), (2000, 1000), (1, 1000)],
            "TestArea",
            100,
            [(5000, 2000), (110000, 40000)],
            10,
            False,
        ),
        (
            "ZSD_01_immersion",
            [(3270, 1870), (108400, 1870), (108400, 71200), (3270, 71200)],
            "StageArea",
            9900,
            [(1, 1), (2000, 1), (2000, 1000), (1, 1000)],
            "TestArea",
            100,
            [(5000, 2000), (100000, 40000)],
            1000,
            False,
        ),
        (
            "ZSD_01_immersion",
            [(3270, 1870), (108400, 1870), (108400, 71200), (3270, 71200)],
            "StageArea",
            9900,
            [(1, 1), (2000, 1), (2000, 1000), (1, 1000)],
            "TestArea",
            100,
            [(5000, 2000), (100000, 40000)],
            99,
            True,
        ),
        (
            "ZSD_01_immersion",
            [(3270, 1870), (108400, 1870), (108400, 71200), (3270, 71200)],
            "StageArea",
            9900,
            [(1, 1), (2000, 1), (2000, 1000), (1, 1000)],
            "TestArea",
            100,
            [(1, 2), (2000, 999)],
            99,
            True,
        ),
        (
            "ZSD_01_immersion",
            [(3270, 1870), (108400, 1870), (108400, 71200), (3270, 71200)],
            "StageArea",
            9900,
            [(1, 1), (2000, 1), (2000, 1000), (1, 1000)],
            "TestArea",
            100,
            [(1, 1), (100000, 40000)],
            99,
            False,
        ),
    ],
)
def test_is_safe_travel_path(
    safety_id,
    safe_verts1,
    safe_area_id1,
    z_max1,
    safe_verts2,
    safe_area_id2,
    z_max2,
    xy,
    z,
    expected,
    helpers,
):
    safety = helpers.setup_local_safety(safety_id)
    safety.add_safe_area(safe_verts1, safe_area_id1, z_max1)

    if safe_area_id2:
        safety.add_safe_area(safe_verts2, safe_area_id2, z_max2)

    path = mpl_path(xy)
    assert safety.is_safe_travel_path(path, z, verbose=False) == expected


@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests from")
@pytest.mark.parametrize(
    (
        "safety_id, safe_verts1, safe_area_id1, z_max1, "
        "safe_verts2, safe_area_id2, z_max2, xy, z_max_pos, "
        "x_cur, y_cur, z_cur, x_tar, y_tar, z_tar, expected"
    ),
    [
        (
            "ZSD_01_immersion",
            [(3270, 1870), (108400, 1870), (108400, 71200), (3270, 71200)],
            "StageArea",
            9900,
            None,
            None,
            None,
            [(5000, 2000), (100000, 40000)],
            10,
            2000,
            2000,
            10,
            100000,
            40000,
            10,
            False,
        ),
        (
            "ZSD_01_immersion",
            [(3270, 1870), (108400, 1870), (108400, 71200), (3270, 71200)],
            "StageArea",
            9900,
            None,
            None,
            None,
            [(5000, 2000), (100000, 40000)],
            10,
            5000,
            2000,
            10,
            110000,
            40000,
            10,
            False,
        ),
        (
            "ZSD_01_immersion",
            [(3270, 1870), (108400, 1870), (108400, 71200), (3270, 71200)],
            "StageArea",
            9900,
            None,
            None,
            None,
            [(5000, 2000), (110000, 40000)],
            10,
            5000,
            2000,
            10,
            100000,
            40000,
            10,
            False,
        ),
        (
            "ZSD_01_immersion",
            [(3270, 1870), (108400, 1870), (108400, 71200), (3270, 71200)],
            "StageArea",
            9900,
            None,
            None,
            None,
            [(5000, 2000), (100000, 40000)],
            10,
            5000,
            2000,
            10,
            100000,
            40000,
            10,
            True,
        ),
        (
            "ZSD_01_immersion",
            [(3270, 1870), (108400, 1870), (108400, 71200), (3270, 71200)],
            "StageArea",
            9900,
            [(5400, 64300), (7400, 64300), (7400, 85100), (5400, 85100)],
            "PumpArea",
            100,
            [(5000, 2000), (100000, 40000)],
            100,
            5000,
            2000,
            10,
            100000,
            40000,
            10,
            False,
        ),
        (
            "ZSD_01_immersion",
            [(3270, 1870), (108400, 1870), (108400, 71200), (3270, 71200)],
            "StageArea",
            9900,
            [(5400, 64300), (7400, 64300), (7400, 85100), (5400, 85100)],
            "PumpArea",
            100,
            [(5000, 2000), (100000, 40000)],
            10,
            5000,
            2000,
            100,
            100000,
            40000,
            10,
            False,
        ),
        (
            "ZSD_01_immersion",
            [(3270, 1870), (108400, 1870), (108400, 71200), (3270, 71200)],
            "StageArea",
            9900,
            [(5400, 64300), (7400, 64300), (7400, 85100), (5400, 85100)],
            "PumpArea",
            100,
            [(5000, 2000), (100000, 40000)],
            10,
            5000,
            2000,
            10,
            100000,
            40000,
            100,
            False,
        ),
        (
            "ZSD_01_immersion",
            [(3270, 1870), (108400, 1870), (108400, 71200), (3270, 71200)],
            "StageArea",
            9900,
            [(5400, 64300), (7400, 64300), (7400, 85100), (5400, 85100)],
            "PumpArea",
            100,
            [(5000, 2000), (100000, 40000)],
            99,
            5000,
            2000,
            99,
            100000,
            40000,
            10,
            True,
        ),
    ],
)
def test_is_safe_move_from_to(
    safety_id,
    safe_verts1,
    safe_area_id1,
    z_max1,
    safe_verts2,
    safe_area_id2,
    z_max2,
    xy,
    z_max_pos,
    x_cur,
    y_cur,
    z_cur,
    x_tar,
    y_tar,
    z_tar,
    expected,
    helpers,
):
    safety = helpers.setup_local_safety(safety_id)
    safety.add_safe_area(safe_verts1, safe_area_id1, z_max1)

    if safe_area_id2:
        safety.add_safe_area(safe_verts2, safe_area_id2, z_max2)

    path = mpl_path(xy)
    area_id = "Compound"
    result = safety.is_safe_move_from_to(
        area_id,
        path,
        z_max_pos,
        x_cur,
        y_cur,
        z_cur,
        x_tar,
        y_tar,
        z_tar,
        verbose=False,
    )
    assert result == expected


@patch("matplotlib.pyplot.show")
@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests from")
@pytest.mark.parametrize(
    (
        "safety_id, safe_verts1, safe_area_id1, z_max1, "
        "safe_verts2, safe_area_id2, z_max2, xy, point"
    ),
    [
        (
            "ZSD_01_immersion",
            [(3270, 1870), (108400, 1870), (108400, 71200), (3270, 71200)],
            "StageArea",
            9900,
            None,
            None,
            None,
            None,
            None,
        ),
        (
            "ZSD_01_immersion",
            [(3270, 1870), (108400, 1870), (108400, 71200), (3270, 71200)],
            "StageArea",
            9900,
            [(5400, 64300), (7400, 64300), (7400, 85100), (5400, 85100)],
            "PumpArea",
            100,
            None,
            None,
        ),
        (
            "ZSD_01_immersion",
            [(3270, 1870), (108400, 1870), (108400, 71200), (3270, 71200)],
            "StageArea",
            9900,
            [(5400, 64300), (7400, 64300), (7400, 85100), (5400, 85100)],
            "PumpArea",
            100,
            None,
            (10000, 65000),
        ),
        (
            "ZSD_01_immersion",
            [(3270, 1870), (108400, 1870), (108400, 71200), (3270, 71200)],
            "StageArea",
            9900,
            [(5400, 64300), (7400, 64300), (7400, 85100), (5400, 85100)],
            "PumpArea",
            100,
            [(5000, 2000), (100000, 40000)],
            None,
        ),
    ],
)
def test_show_safe_areas(
    mock_show,
    safety_id,
    safe_verts1,
    safe_area_id1,
    z_max1,
    safe_verts2,
    safe_area_id2,
    z_max2,
    xy,
    point,
    helpers,
):
    safety = helpers.setup_local_safety(safety_id)
    safety.add_safe_area(safe_verts1, safe_area_id1, z_max1)

    if safe_area_id2:
        safety.add_safe_area(safe_verts2, safe_area_id2, z_max2)

    path = None
    if xy:
        path = mpl_path(xy)

    try:
        safety.show_safe_areas(path=path, point=point)
        assert True
    except Exception:
        assert False


###############################################################################
#
# Tests for the Camera class
#
###############################################################################


@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    (
        "camera_id, pixel_size, pixel_number, pixel_type, name, "
        "detector_type, manufacturer, model, live_exp, set_exp"
    ),
    [
        (
            "Camera2 (left)",
            (None, None),
            (None, None),
            None,
            None,
            "generic",
            None,
            None,
            False,
            {
                "aics_Manufacturer": None,
                "aics_PhysicalSizeY": None,
                "aics_PhysicalSizeX": None,
                "aics_Model": None,
                "aics_PhysicalSizeXUnit": "mum",
                "aics_SizeX": None,
                "aics_SizeY": None,
                "aics_PixelType": None,
                "aics_cameraID": "Camera2 (left)",
                "aics_PhysicalSizeYUnit": "mum",
                "aics_Type": "generic",
            },
        ),
        (
            "Camera1 (back)",
            (6.5, 6.5),
            (2048 / 2, 2048 / 2),
            numpy.int32,
            "Orca Flash 4.0V2",
            "sCMOS",
            "Hamamatsu",
            None,
            False,
            {
                "aics_Manufacturer": "Hamamatsu",
                "aics_PhysicalSizeY": 6.5,
                "aics_PhysicalSizeX": 6.5,
                "aics_Model": None,
                "aics_PhysicalSizeXUnit": "mum",
                "aics_SizeX": 1024,
                "aics_SizeY": 1024,
                "aics_PixelType": numpy.int32,
                "aics_cameraID": "Camera1 (back)",
                "aics_PhysicalSizeYUnit": "mum",
                "aics_Type": "sCMOS",
            },
        ),
    ],
)
def test_get_information_camera(
    camera_id,
    pixel_size,
    pixel_number,
    pixel_type,
    name,
    detector_type,
    manufacturer,
    model,
    live_exp,
    set_exp,
    helpers,
):
    camera = helpers.setup_local_camera(
        camera_id,
        pixel_size,
        pixel_number,
        pixel_type,
        name,
        detector_type,
        manufacturer,
        model,
    )
    info = camera.get_information(None)

    assert info["live"] == live_exp and info["settings"] == set_exp


@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    "camera_id, software, experiment_name, meta_expect",
    [
        (
            "Camera1 (back)",
            "ZEN Blue Dummy",
            "test_experiment",
            {
                "aics_Manufacturer": None,
                "aics_PixelType": None,
                "aics_cameraID": "Camera1 (back)",
                "aics_PhysicalSizeYUnit": "mum",
                "aics_PhysicalSizeY": None,
                "aics_PhysicalSizeX": None,
                "aics_Model": None,
                "aics_PhysicalSizeXUnit": "mum",
                "aics_Type": "generic",
                "aics_SizeX": None,
                "aics_SizeY": None,
                "aics_Experiment": "test_experiment",
            },
        ),
        ("Camera2 (left)", "ZEN Blue Dummy", None, "HardwareError"),
        (
            "Camera2 (left)",
            "Slidebook Dummy",
            "test_experiment",
            {
                "aics_Manufacturer": None,
                "aics_PixelType": None,
                "aics_cameraID": "Camera2 (left)",
                "aics_PhysicalSizeYUnit": "mum",
                "aics_PhysicalSizeY": None,
                "aics_PhysicalSizeX": None,
                "aics_Model": None,
                "aics_PhysicalSizeXUnit": "mum",
                "aics_Type": "generic",
                "aics_SizeX": None,
                "aics_SizeY": None,
                "aics_Experiment": "test_experiment",
            },
        ),
    ],
)
def test_snap_image(camera_id, software, experiment_name, meta_expect, helpers):
    control_software = helpers.setup_local_control_software(software)
    camera = helpers.setup_local_camera(camera_id)
    try:
        image = camera.snap_image(control_software.connection, experiment_name)
        result = image.meta
    except Exception as err:
        result = type(err).__name__

    assert result == meta_expect


@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    "camera_id, software, experiment_name, orig_mode, exp_mode",
    [
        ("Camera1 (back)", "ZEN Blue Dummy", "test_experiment", False, True),
        ("Camera1 (back)", "ZEN Blue Dummy", None, False, "HardwareError"),
        ("Camera2 (left)", "ZEN Blue Dummy", None, True, False),
        ("Camera2 (left)", "ZEN Blue Dummy", "test_experiment", True, False),
        (
            "Camera1 (back)",
            "Slidebook Dummy",
            "test_experiment",
            False,
            "HardwareCommandNotDefinedError",
        ),
        (
            "Camera1 (back)",
            "Slidebook Dummy",
            "test_experiment",
            True,
            "HardwareCommandNotDefinedError",
        ),
    ],
)
def test_live_mode_start_stop(
    camera_id, software, experiment_name, orig_mode, exp_mode, helpers
):
    control_software = helpers.setup_local_control_software(software)
    camera = helpers.setup_local_camera(camera_id)
    camera.live_mode_on = orig_mode

    try:
        if camera.live_mode_on:
            camera.live_mode_stop(control_software.connection, experiment_name)
            result = camera.live_mode_on
        else:
            camera.live_mode_start(control_software.connection, experiment_name)
            result = camera.live_mode_on
    except Exception as err:
        result = type(err).__name__

        assert result == exp_mode


###############################################################################
#
# Tests for the Stage class
#
###############################################################################


@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    (
        "stage_id, software, safe_area, safe_position, "
        "objective_changer, prefs_path, default_experiment, "
        "expected"
    ),
    [
        ("Marzhauser", "ZEN Blue Dummy", None, None, None, None, None, "HardwareError"),
        ("Marzhauser", "ZEN Blue Dummy", None, (1, 1), None, None, None, (1, 1)),
        (
            "Marzhauser",
            "ZEN Blue Dummy",
            "ZSD_01_plate",
            (52000, 40200),
            "6xMotorizedNosepiece",
            "data/preferences_ZSD_test.yml",
            "Setup_10x.czexp",
            (52000, 40200),
        ),
    ],
)
def test_initialize_stage(
    stage_id,
    software,
    safe_area,
    safe_position,
    objective_changer,
    prefs_path,
    default_experiment,
    expected,
    helpers,
):
    control_software = helpers.setup_local_control_software(software)
    com_object = control_software.connection
    stage = helpers.setup_local_stage(
        helpers,
        stage_id,
        safe_area,
        safe_position,
        objective_changer,
        prefs_path,
        default_experiment,
    )

    try:
        stage.initialize(com_object)
        result = com_object.get_stage_pos()
    except Exception as err:
        result = type(err).__name__

    assert result == expected


# TODO: update dummy to allow for testing values other than the hardcoded (60000, 40000)
@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    ("stage_id, software, expected"),
    [
        (
            "Marzhauser",
            "ZEN Blue Dummy",
            {"centricity_corrected": (None, None), "absolute": (60000, 40000)},
        )
    ],
)
def test_get_information_stage(stage_id, software, expected, helpers):
    control_software = helpers.setup_local_control_software(software)
    stage = helpers.setup_local_stage(helpers, stage_id)
    result = stage.get_information(control_software.connection)

    assert result == expected


@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    ("stage_id, software, x, y, test, expected"),
    [
        ("Marzhauser", "ZEN Blue Dummy", 1, 1, False, "(1,1)"),
        (
            "Marzhauser",
            "ZEN Blue Dummy",
            1,
            1,
            True,
            ("Path(array([[6.e+04,4.e+04],[1.e+00,4.e+04]," "[1.e+00,1.e+00]]),None)"),
        ),
    ],
)
def test_move_to_position_stage(stage_id, software, x, y, test, expected, helpers):
    control_software = helpers.setup_local_control_software(software)
    stage = helpers.setup_local_stage(helpers, stage_id)

    try:
        path = stage.move_to_position(control_software.connection, x, y, test=test)
        result = "".join(str(path).split())
    except Exception as err:
        result = type(err).__name__  # TODO: add tests which throw exceptions

    assert result == expected


###############################################################################
#
# Tests for the ObjectiveChanger class
#
###############################################################################


@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    (
        "objective_changer_id, software, positions, "
        "objectives, ref_obj_changer, prefs_path, action_list, "
        "ref_object_id, auto_focus_id, expected"
    ),
    [
        (
            "6xMotorizedNosepiece",
            "ZEN Blue Dummy",
            6,
            None,
            "Plan-Apochromat 20x/0.8 M27",
            "data/preferences_ZSD_test.yml",
            ["set_reference"],
            None,
            None,
            "HardwareDoesNotExistError",
        ),
        (
            "6xMotorizedNosepiece",
            "ZEN Blue Dummy",
            6,
            {
                "Plan-Apochromat 10x/0.45": {
                    "x_offset": -19,
                    "y_offset": 15,
                    "z_offset": 10,
                    "magnification": 10,
                    "immersion": "air",
                    "experiment": "Setup_10x",
                    "camera": "Camera1 (back)",
                    "autofocus": "DefiniteFocus2",
                },
                "Plan-Apochromat 20x/0.8 M27": {
                    "x_offset": 0,
                    "y_offset": 0,
                    "z_offset": 0,
                    "magnification": 20,
                    "immersion": "air",
                    "experiment": "Setup_20x",
                    "camera": "Camera1 (back)",
                    "autofocus": "DefiniteFocus2",
                },
                "C-Apochromat 100x/1.25 W Korr UV VIS IR": {
                    "x_offset": 44,
                    "y_offset": 198,
                    "z_offset": -90,
                    "magnification": 100,
                    "immersion": "water",
                    "experiment": "Setup_100x",
                    "camera": "Camera1 (back)",
                    "autofocus": "DefiniteFocus2",
                },
            },
            "Plan-Apochromat 20x/0.8 M27",
            "data/preferences_ZSD_test.yml",
            ["set_reference"],
            None,
            None,
            "AutofocusNoReferenceObjectError",
        ),
        (
            "6xMotorizedNosepiece",
            "ZEN Blue Dummy",
            6,
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
                },
                "Plan-Apochromat 20x/0.8 M27": {
                    "x_offset": 0,
                    "y_offset": 0,
                    "z_offset": 0,
                    "magnification": 20,
                    "immersion": "air",
                    "experiment": "Setup_20x",
                    "camera": "Camera1 (back)",
                    "autofocus": "DefiniteFocus2",
                },
                "C-Apochromat 100x/1.25 W Korr UV VIS IR": {
                    "x_offset": 44,
                    "y_offset": 198,
                    "z_offset": -90,
                    "magnification": 100,
                    "immersion": "water",
                    "experiment": "Setup_100x",
                    "camera": "Camera1 (back)",
                    "autofocus": "DefiniteFocus2",
                },
            },
            "Plan-Apochromat 20x/0.8 M27",
            "data/preferences_ZSD_test.yml",
            [],
            "Plate",
            None,
            True,
        ),
        (
            "6xMotorizedNosepiece",
            "ZEN Blue Dummy",
            6,
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
                },
                "Plan-Apochromat 20x/0.8 M27": {
                    "x_offset": 0,
                    "y_offset": 0,
                    "z_offset": 0,
                    "magnification": 20,
                    "immersion": "air",
                    "experiment": "Setup_20x",
                    "camera": "Camera1 (back)",
                    "autofocus": "DefiniteFocus2",
                },
                "C-Apochromat 100x/1.25 W Korr UV VIS IR": {
                    "x_offset": 44,
                    "y_offset": 198,
                    "z_offset": -90,
                    "magnification": 100,
                    "immersion": "water",
                    "experiment": "Setup_100x",
                    "camera": "Camera1 (back)",
                    "autofocus": "DefiniteFocus2",
                },
            },
            "Plan-Apochromat 20x/0.8 M27",
            "data/preferences_ZSD_test.yml",
            ["set_reference"],
            "Plate",
            None,
            # should be ExperimentNotExistError once samples API is done
            "HardwareCommandNotDefinedError",
        ),
        (
            "6xMotorizedNosepiece",
            "ZEN Blue Dummy",
            6,
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
                },
                "Plan-Apochromat 20x/0.8 M27": {
                    "x_offset": 0,
                    "y_offset": 0,
                    "z_offset": 0,
                    "magnification": 20,
                    "immersion": "air",
                    "experiment": "Setup_20x",
                    "camera": "Camera1 (back)",
                    "autofocus": "DefiniteFocus2",
                },
                "C-Apochromat 100x/1.25 W Korr UV VIS IR": {
                    "x_offset": 44,
                    "y_offset": 198,
                    "z_offset": -90,
                    "magnification": 100,
                    "immersion": "water",
                    "experiment": "Setup_100x",
                    "camera": "Camera1 (back)",
                    "autofocus": "DefiniteFocus2",
                },
            },
            "Plan-Apochromat 10x/0.45",
            "data/preferences_ZSD_test.yml",
            ["set_reference"],
            "Plate",
            None,
            # will be HardwareDoesNotExistError once samples API is done
            "HardwareCommandNotDefinedError",
        ),
        (
            "6xMotorizedNosepiece",
            "ZEN Blue Dummy",
            6,
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
                },
                "Plan-Apochromat 20x/0.8 M27": {
                    "x_offset": 0,
                    "y_offset": 0,
                    "z_offset": 0,
                    "magnification": 20,
                    "immersion": "air",
                    "experiment": "Setup_20x",
                    "camera": "Camera1 (back)",
                    "autofocus": "DefiniteFocus2",
                },
                "C-Apochromat 100x/1.25 W Korr UV VIS IR": {
                    "x_offset": 44,
                    "y_offset": 198,
                    "z_offset": -90,
                    "magnification": 100,
                    "immersion": "water",
                    "experiment": "Setup_100x",
                    "camera": "Camera1 (back)",
                    "autofocus": "DefiniteFocus2",
                },
            },
            "Plan-Apochromat 10x/0.45",
            "data/preferences_ZSD_test.yml",
            ["set_reference"],
            "Plate",
            "test",
            # will be AttributeError once samples API is done
            "HardwareCommandNotDefinedError",
        ),
        (
            "6xMotorizedNosepiece",
            "ZEN Blue Dummy",
            6,
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
                },
                "Plan-Apochromat 20x/0.8 M27": {
                    "x_offset": 0,
                    "y_offset": 0,
                    "z_offset": 0,
                    "magnification": 20,
                    "immersion": "air",
                    "experiment": "Setup_20x",
                    "camera": "Camera1 (back)",
                    "autofocus": "DefiniteFocus2",
                },
                "C-Apochromat 100x/1.25 W Korr UV VIS IR": {
                    "x_offset": 44,
                    "y_offset": 198,
                    "z_offset": -90,
                    "magnification": 100,
                    "immersion": "water",
                    "experiment": "Setup_100x",
                    "camera": "Camera1 (back)",
                    "autofocus": "DefiniteFocus2",
                },
            },
            "Plan-Apochromat 10x/0.45",
            "data/preferences_ZSD_test.yml",
            ["set_reference"],
            "PlateHolder",
            "test",
            # will be HardwareDoesNotExistError once samples API is done
            "HardwareCommandNotDefinedError",
        ),
    ],
)
def test_initialize_obj_changer(
    objective_changer_id,
    software,
    positions,
    objectives,
    ref_obj_changer,
    prefs_path,
    action_list,
    ref_object_id,
    auto_focus_id,
    expected,
    helpers,
):
    control_software = helpers.setup_local_control_software(software)
    obj_changer = helpers.setup_local_obj_changer(
        helpers,
        objective_changer_id,
        positions,
        objectives,
        ref_obj_changer,
        prefs_path,
        auto_focus_id,
    )

    # TODO: once Samples API is ready add these tests back

    # if prefs_path:
    #     microscope_object = setup_local_microscope(prefs_path)
    # else:
    #     microscope_object = None

    # if ref_object:
    #     if ref_object == "Plate":
    #         ref_object = samples.Plate()
    #     elif ref_object == "PlateHolder":
    #         ref_object = samples.PlateHolder()
    #
    #     ref_object.set_hardware(objective_changer_id=objective_changer_id,
    #                             auto_focus_id=auto_focus_id,
    #                             microscope_object=microscope_object)

    try:
        obj_changer.initialize(
            control_software.connection, action_list, ref_object_id, verbose=False
        )
        # TODO: create focus drive and check reference position for complete test
        # result = ref_object.get_reference_position()
        result = True
    except Exception as err:
        result = type(err).__name__

    assert result == expected


@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    ("objective_changer_id, positions, expected"),
    [
        ("6xMotorizedNosepiece", 6, 6),
        ("6xMotorizedNosepiece", 21, 21),
        ("6xMotorizedNosepiece", None, None),
    ],
)
def test_get_set_num_pos(objective_changer_id, positions, expected, helpers):
    obj_changer = helpers.setup_local_obj_changer(helpers, objective_changer_id)

    obj_changer.set_number_positions(positions)

    assert expected == obj_changer.get_number_positions()


@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    ("objective_changer_id, software, positions, expected"),
    [
        ("6xMotorizedNosepiece", "ZEN Blue Dummy", None, "HardwareError"),
        (
            "6xMotorizedNosepiece",
            "ZEN Blue Dummy",
            6,
            {"": {"Position": 6, "Name": ""}},
        ),
    ],
)
def test_get_all_objectives(
    objective_changer_id, software, positions, expected, helpers
):
    control_software = helpers.setup_local_control_software(software)
    obj_changer = helpers.setup_local_obj_changer(
        helpers, objective_changer_id, positions
    )

    try:
        result = obj_changer.get_all_objectives(control_software.connection)
    except Exception as err:
        result = type(err).__name__

    assert expected == result


@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    ("objective_changer_id, software, positions, expected"),
    [
        ("6xMotorizedNosepiece", "ZEN Blue Dummy", None, {}),
        (
            "6xMotorizedNosepiece",
            "ZEN Blue Dummy",
            6,
            {"": {"Position": 6, "Name": ""}},
        ),
    ],
)
def test_get_objectives_dict(
    objective_changer_id, software, positions, expected, helpers
):
    control_software = helpers.setup_local_control_software(software)
    obj_changer = helpers.setup_local_obj_changer(
        helpers, objective_changer_id, positions
    )
    if positions:
        obj_changer.get_all_objectives(control_software.connection)

    result = obj_changer.get_objectives_dict()

    assert expected == result


@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    ("objective_changer_id, software, positions, " "objectives, expected"),
    [
        ("6xMotorizedNosepiece", "ZEN Blue Dummy", None, None, "TypeError"),
        (
            "6xMotorizedNosepiece",
            "ZEN Blue Dummy",
            6,
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
            "KeyError",
        ),
        (
            "6xMotorizedNosepiece",
            "ZEN Blue Dummy",
            6,
            {
                "Dummy Objective": {
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
            {
                "magnification": 10,
                "name": "Dummy Objective",
                "position": 0,
                "experiment": "WellTile_10x_true",
            },
        ),
    ],
)
def test_get_information_obj_changer(
    objective_changer_id, software, positions, objectives, expected, helpers
):
    control_software = helpers.setup_local_control_software(software)
    obj_changer = helpers.setup_local_obj_changer(
        helpers, objective_changer_id, positions, objectives
    )
    try:
        result = obj_changer.get_information(control_software.connection)
    except Exception as err:
        result = type(err).__name__

    assert expected == result


@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    (
        "objective_changer_id, software, positions, objectives, "
        "x_off, y_off, z_off, objective_name, expected"
    ),
    [
        ("6xMotorizedNosepiece", "ZEN Blue Dummy", 6, None, 0, 0, 0, None, "TypeError"),
        (
            "6xMotorizedNosepiece",
            "ZEN Blue Dummy",
            6,
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
                },
                "Plan-Apochromat 20x/0.8 M27": {
                    "x_offset": 0,
                    "y_offset": 0,
                    "z_offset": 0,
                    "magnification": 20,
                    "immersion": "air",
                    "experiment": "Setup_20x",
                    "camera": "Camera1 (back)",
                    "autofocus": "DefiniteFocus2",
                },
                "C-Apochromat 100x/1.25 W Korr UV VIS IR": {
                    "x_offset": 44,
                    "y_offset": 198,
                    "z_offset": -90,
                    "magnification": 100,
                    "immersion": "water",
                    "experiment": "Setup_100x",
                    "camera": "Camera1 (back)",
                    "autofocus": "DefiniteFocus2",
                },
            },
            0,
            0,
            0,
            None,
            "ObjectiveNotDefinedError",
        ),
        (
            "6xMotorizedNosepiece",
            "ZEN Blue Dummy",
            6,
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
                },
                "Plan-Apochromat 20x/0.8 M27": {
                    "x_offset": 0,
                    "y_offset": 0,
                    "z_offset": 0,
                    "magnification": 20,
                    "immersion": "air",
                    "experiment": "Setup_20x",
                    "camera": "Camera1 (back)",
                    "autofocus": "DefiniteFocus2",
                },
                "C-Apochromat 100x/1.25 W Korr UV VIS IR": {
                    "x_offset": 44,
                    "y_offset": 198,
                    "z_offset": -90,
                    "magnification": 100,
                    "immersion": "water",
                    "experiment": "Setup_100x",
                    "camera": "Camera1 (back)",
                    "autofocus": "DefiniteFocus2",
                },
            },
            1,
            2,
            3,
            "Plan-Apochromat 10x/0.45",
            {
                "x_offset": 1,
                "y_offset": 2,
                "z_offset": 3,
                "magnification": 10,
                "immersion": "air",
                "experiment": "WellTile_10x_true",
                "camera": "Camera1 (back)",
                "autofocus": "DefiniteFocus2",
            },
        ),
    ],
)
def test_update_objective_offset(
    objective_changer_id,
    software,
    positions,
    objectives,
    x_off,
    y_off,
    z_off,
    objective_name,
    expected,
    helpers,
):
    control_software = helpers.setup_local_control_software(software)
    obj_changer = helpers.setup_local_obj_changer(
        helpers, objective_changer_id, positions, objectives
    )

    try:
        result = obj_changer.update_objective_offset(
            control_software.connection, x_off, y_off, z_off, objective_name
        )
    except Exception as err:
        result = type(err).__name__

    assert result == expected


@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    (
        "objective_changer_id, software, positions, "
        "magnification, sample_obj, use_safe_position, expected"
    ),
    [
        (
            "6xMotorizedNosepiece",
            "ZEN Blue Dummy",
            None,
            None,
            None,
            False,
            "HardwareError",
        ),
        (
            "6xMotorizedNosepiece",
            "ZEN Blue Dummy",
            6,
            "test",
            None,
            False,
            "ObjectiveNotDefinedError",
        ),
        (
            "6xMotorizedNosepiece",
            "ZEN Blue Dummy",
            6,
            "",
            None,
            False,
            "Dummy Objective",
        ),
    ],
)
def test_change_magnification(
    objective_changer_id,
    software,
    positions,
    magnification,
    sample_obj,
    use_safe_position,
    expected,
    helpers,
):
    control_software = helpers.setup_local_control_software(software)
    obj_changer = helpers.setup_local_obj_changer(
        helpers, objective_changer_id, positions
    )

    # TODO: add tests where use_safe_position = True
    try:
        result = obj_changer.change_magnification(
            control_software.connection,
            magnification,
            sample_obj,
            use_safe_position,
            verbose=False,
            load=False,
        )
    except Exception as err:
        result = type(err).__name__

    assert result == expected


@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    ("objective_changer_id, software, pos, expected"),
    [
        ("6xMotorizedNosepiece", "ZEN Blue Dummy", "test", "Dummy Objective"),
        ("6xMotorizedNosepiece", "ZEN Blue Dummy", None, "Dummy Objective"),
    ],
)
def test_change_position(objective_changer_id, software, pos, expected, helpers):
    control_software = helpers.setup_local_control_software(software)
    obj_changer = helpers.setup_local_obj_changer(helpers, objective_changer_id)

    result = obj_changer.change_position(pos, control_software.connection, load=False)

    assert result == expected


###############################################################################
#
# Tests for the FocusDrive class
#
###############################################################################


@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    (
        "focus_id, software, max_load_position, "
        "min_work_position, auto_focus_id, obj_changer_id, "
        "prefs_path, action_list, expected"
    ),
    [
        (
            "MotorizedFocus",
            "ZEN Blue Dummy",
            50,
            100,
            "DefiniteFocus2",
            "6xMotorizedNosepiece",
            "data/preferences_ZSD_test.yml",
            ["set_load"],
            "LoadNotDefinedError",
        ),
        (
            "MotorizedFocus",
            "ZEN Blue Dummy",
            500,
            100,
            "DefiniteFocus2",
            "6xMotorizedNosepiece",
            "data/preferences_ZSD_test.yml",
            ["set_load"],
            500,
        ),
        (
            "MotorizedFocus",
            "ZEN Blue Dummy",
            50,
            100,
            "DefiniteFocus2",
            "6xMotorizedNosepiece",
            "data/preferences_ZSD_test.yml",
            ["set_work"],
            500,
        ),
        (
            "MotorizedFocus",
            "ZEN Blue Dummy",
            50,
            1000,
            "DefiniteFocus2",
            "6xMotorizedNosepiece",
            "data/preferences_ZSD_test.yml",
            ["set_work"],
            "WorkNotDefinedError",
        ),
        ("MotorizedFocus", "ZEN Blue Dummy", None, None, None, None, None, [], None),
    ],
)
def test_initialize_focus_drive(
    focus_id,
    software,
    max_load_position,
    min_work_position,
    auto_focus_id,
    obj_changer_id,
    prefs_path,
    action_list,
    expected,
    helpers,
):
    control_software = helpers.setup_local_control_software(software)
    focus_drive = helpers.setup_local_focus_drive(
        helpers,
        focus_id,
        max_load_position,
        min_work_position,
        auto_focus_id,
        obj_changer_id,
    )

    try:
        focus_drive.initialize(
            control_software.connection,
            action_list=action_list,
            verbose=False,
            test=True,
        )
        if "set_work" in action_list:
            result = focus_drive.z_work
        else:
            result = focus_drive.z_load
    except Exception as err:
        result = type(err).__name__

    assert result == expected


@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    (
        "focus_id, software, max_load_position, "
        "min_work_position, auto_focus_id, obj_changer_id, "
        "objectives, prefs_path, action_list, expected"
    ),
    [
        (
            "MotorizedFocus",
            "ZEN Blue Dummy",
            500,
            100,
            "DefiniteFocus2",
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
            "data/preferences_ZSD_test.yml",
            ["set_load"],
            {
                "load_position": 500,
                "work_position": None,
                "absolute": 500,
                "focality_corrected": 500,
                "z_focus_offset": 0,
            },
        ),
        (
            "MotorizedFocus",
            "ZEN Blue Dummy",
            50,
            100,
            "DefiniteFocus2",
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
            "data/preferences_ZSD_test.yml",
            ["set_work"],
            {
                "load_position": None,
                "work_position": 500,
                "absolute": 500,
                "focality_corrected": 500,
                "z_focus_offset": 0,
            },
        ),
        (
            "MotorizedFocus",
            "ZEN Blue Dummy",
            500,
            100,
            "DefiniteFocus2",
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
            "data/preferences_ZSD_test.yml",
            ["set_load", "set_work"],
            {
                "load_position": 500,
                "work_position": 500,
                "absolute": 500,
                "focality_corrected": 500,
                "z_focus_offset": 0,
            },
        ),
        (
            "MotorizedFocus",
            "ZEN Blue Dummy",
            None,
            None,
            None,
            None,
            None,
            None,
            [],
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
def test_get_information_focus_drive(
    focus_id,
    software,
    max_load_position,
    min_work_position,
    auto_focus_id,
    obj_changer_id,
    objectives,
    prefs_path,
    action_list,
    expected,
    helpers,
):
    control_software = helpers.setup_local_control_software(software)
    focus_drive = helpers.setup_local_focus_drive(
        helpers,
        focus_id,
        max_load_position,
        min_work_position,
        auto_focus_id,
        obj_changer_id,
        prefs_path,
    )
    if obj_changer_id:
        obj_changer = helpers.setup_local_obj_changer(
            helpers,
            obj_changer_id,
            objectives=objectives,
            prefs_path=prefs_path,
            auto_focus_id=auto_focus_id,
        )

        focus_drive.microscope_object.add_microscope_object(obj_changer)

    focus_drive.initialize(
        control_software.connection, action_list=action_list, verbose=False, test=True
    )
    result = focus_drive.get_information(control_software.connection)

    assert result == expected


@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    ("focus_id, software, z, expected"),
    [
        ("MotorizedFocus", "ZEN Blue Dummy", 100, 100),
        ("MotorizedFocus", "ZEN Blue Dummy", None, None),
        ("MotorizedFocus", "Slidebook Dummy", None, "HardwareCommandNotDefinedError"),
    ],
)
def test_move_to_position_focus_drive(focus_id, software, z, expected, helpers):
    control_software = helpers.setup_local_control_software(software)
    focus_drive = helpers.setup_local_focus_drive(helpers, focus_id)

    try:
        result = focus_drive.move_to_position(control_software.connection, z)
    except Exception as err:
        result = type(err).__name__

    assert result == expected


@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    (
        "focus_id, software, max_load_position, min_work_position, "
        "prefs_path, action_list, expected"
    ),
    [
        (
            "MotorizedFocus",
            "ZEN Blue Dummy",
            50,
            100,
            "data/preferences_ZSD_test.yml",
            [],
            "LoadNotDefinedError",
        ),
        (
            "MotorizedFocus",
            "ZEN Blue Dummy",
            500,
            100,
            "data/preferences_ZSD_test.yml",
            ["set_load"],
            500,
        ),
        (
            "MotorizedFocus",
            "Slidebook Dummy",
            500,
            100,
            "data/preferences_3i_test.yml",
            [],
            "HardwareCommandNotDefinedError",
        ),
    ],
)
def test_goto_load(
    focus_id,
    software,
    max_load_position,
    min_work_position,
    prefs_path,
    action_list,
    expected,
    helpers,
):
    control_software = helpers.setup_local_control_software(software)
    focus_drive = helpers.setup_local_focus_drive(
        helpers, focus_id, max_load_position, min_work_position, prefs_path=prefs_path
    )

    focus_drive.initialize(
        control_software.connection, action_list=action_list, verbose=False, test=True
    )

    try:
        result = focus_drive.goto_load(control_software.connection)
    except Exception as err:
        result = type(err).__name__

    assert result == expected


@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    (
        "focus_id, software, max_load_position, min_work_position, "
        "prefs_path, action_list, expected"
    ),
    [
        (
            "MotorizedFocus",
            "ZEN Blue Dummy",
            50,
            100,
            "data/preferences_ZSD_test.yml",
            [],
            "WorkNotDefinedError",
        ),
        (
            "MotorizedFocus",
            "ZEN Blue Dummy",
            500,
            100,
            "data/preferences_ZSD_test.yml",
            ["set_work"],
            500,
        ),
        (
            "MotorizedFocus",
            "Slidebook Dummy",
            500,
            100,
            "data/preferences_3i_test.yml",
            [],
            "HardwareCommandNotDefinedError",
        ),
    ],
)
def test_goto_work(
    focus_id,
    software,
    max_load_position,
    min_work_position,
    prefs_path,
    action_list,
    expected,
    helpers,
):
    control_software = helpers.setup_local_control_software(software)
    focus_drive = helpers.setup_local_focus_drive(
        helpers, focus_id, max_load_position, min_work_position, prefs_path=prefs_path
    )

    focus_drive.initialize(
        control_software.connection, action_list=action_list, verbose=False, test=True
    )

    try:
        result = focus_drive.goto_work(control_software.connection)
    except Exception as err:
        result = type(err).__name__

    assert result == expected


###############################################################################
#
# Tests for the AutoFocus class
#
###############################################################################


@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    ("auto_focus_id, software, obj_changer_id, " "positions, objectives, expected"),
    [
        (
            "DefiniteFocus2",
            "ZEN Blue Dummy",
            "6xMotorizedNosepiece",
            6,
            {
                "Dummy Objective": {
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
            "WellTile_10x_true",
        ),
        (
            "DefiniteFocus2",
            "ZEN Blue Dummy",
            "6xMotorizedNosepiece",
            6,
            {
                "Dummy Objective": {
                    "x_offset": -19,
                    "y_offset": 15,
                    "z_offset": 10,
                    "magnification": 10,
                    "immersion": "air",
                    "camera": "Camera1 (back)",
                    "autofocus": "DefiniteFocus2",
                }
            },
            "Not defined",
        ),
    ],
)
def test_get_init_experiment(
    auto_focus_id, software, obj_changer_id, positions, objectives, expected, helpers
):
    control_software = helpers.setup_local_control_software(software)
    obj_changer = helpers.setup_local_obj_changer(
        helpers, obj_changer_id, positions, objectives
    )

    autofocus = helpers.setup_local_autofocus(
        helpers, auto_focus_id, obj_changer=obj_changer
    )

    result = autofocus.get_init_experiment(control_software.connection)

    assert result == expected


@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    (
        "auto_focus_id, software, obj_changer_id, "
        "positions, objectives, prefs_path, "
        "camera_id, pixel_size, pixel_number, pixel_type, "
        "action_list, expected"
    ),
    [
        (
            "DefiniteFocus2",
            "ZEN Blue Dummy",
            "6xMotorizedNosepiece",
            6,
            {
                "Dummy Objective": {
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
            "data/preferences_ZSD_test.yml",
            None,
            None,
            None,
            None,
            [],
            None,
        ),
        (
            "DefiniteFocus2",
            "ZEN Blue Dummy",
            "6xMotorizedNosepiece",
            6,
            {
                "Dummy Objective": {
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
            "data/preferences_ZSD_test.yml",
            None,
            None,
            None,
            None,
            ["find_surface"],
            "HardwareDoesNotExistError",
        ),
        (
            "DefiniteFocus2",
            "ZEN Blue Dummy",
            "6xMotorizedNosepiece",
            6,
            {
                "Dummy Objective": {
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
            "data/preferences_ZSD_test.yml",
            "Camera1 (back)",
            (6.5, 6.5),
            (1024, 1024),
            numpy.int32,
            ["find_surface"],
            None,
        ),
    ],
)
def test_initialize_autofocus(
    auto_focus_id,
    software,
    obj_changer_id,
    positions,
    objectives,
    prefs_path,
    camera_id,
    pixel_size,
    pixel_number,
    pixel_type,
    action_list,
    expected,
    helpers,
):
    control_software = helpers.setup_local_control_software(software)
    obj_changer = helpers.setup_local_obj_changer(
        helpers, obj_changer_id, positions, objectives
    )

    autofocus = helpers.setup_local_autofocus(
        helpers, auto_focus_id, obj_changer=obj_changer, prefs_path=prefs_path
    )

    if camera_id:
        autofocus.default_camera = camera_id
        camera = helpers.setup_local_camera(
            camera_id, pixel_size, pixel_number, pixel_type
        )
        autofocus.microscope_object.add_microscope_object(camera)

    try:
        result = autofocus.initialize(
            control_software.connection, action_list=action_list
        )
    except Exception as err:
        result = type(err).__name__

    assert result == expected


@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    (
        "auto_focus_id, software, obj_changer_id, "
        "positions, objectives, camera_id, expected"
    ),
    [
        (
            "DefiniteFocus2",
            "ZEN Blue Dummy",
            "6xMotorizedNosepiece",
            6,
            None,
            None,
            "TypeError",
        ),
        (
            "DefiniteFocus2",
            "ZEN Blue Dummy",
            "6xMotorizedNosepiece",
            6,
            {
                "Dummy Objective": {
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
            "None",
            {
                "use": False,
                "experiment": "WellTile_10x_true",
                "delta_z": None,
                "reference_object_id": None,
                "camera": None,
                "initial_focus": None,
                "live_mode": True,
            },
        ),
        (
            "DefiniteFocus2",
            "ZEN Blue Dummy",
            "6xMotorizedNosepiece",
            6,
            {
                "Dummy Objective": {
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
            "Camera1 (back)",
            {
                "use": False,
                "experiment": "WellTile_10x_true",
                "delta_z": None,
                "reference_object_id": None,
                "camera": "Camera1 (back)",
                "initial_focus": None,
                "live_mode": True,
            },
        ),
    ],
)
def test_get_information_autofocus(
    auto_focus_id,
    software,
    obj_changer_id,
    positions,
    objectives,
    camera_id,
    expected,
    helpers,
):
    control_software = helpers.setup_local_control_software(software)
    obj_changer = helpers.setup_local_obj_changer(
        helpers, obj_changer_id, positions, objectives
    )

    autofocus = helpers.setup_local_autofocus(
        helpers, auto_focus_id, default_camera=camera_id, obj_changer=obj_changer
    )

    try:
        result = autofocus.get_information(control_software.connection)
    except Exception as err:
        result = type(err).__name__

    assert result == expected


@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    ("auto_focus_id, settings, expected"),
    [
        ("DefiniteFocus2", {}, {"use_auto_focus": False}),
        ("DefiniteFocus2", None, {"use_auto_focus": False}),
        ("DefiniteFocus2", {"use_auto_focus": True}, {"use_auto_focus": True}),
        ("DefiniteFocus2", {"use_auto_focus": False}, {"use_auto_focus": False}),
    ],
)
def test_set_component(auto_focus_id, settings, expected, helpers):
    autofocus = helpers.setup_local_autofocus(helpers, auto_focus_id)

    result = autofocus.set_component(settings)

    assert result == expected


@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    (
        "auto_focus_id, software, obj_changer_id, "
        "positions, objectives, ref_object_id, prefs_path, "
        "use_autofocus, autofocus_ready, df_objective, "
        "obj_name, expected"
    ),
    [
        (
            "DefiniteFocus2",
            "ZEN Blue Dummy",
            "6xMotorizedNosepiece",
            6,
            {
                "Dummy Objective": {
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
            "PlateHolder",
            "data/preferences_ZSD_test.yml",
            False,
            False,
            "",
            "",
            None,
        ),
        (
            "DefiniteFocus2",
            "ZEN Blue Dummy",
            "6xMotorizedNosepiece",
            6,
            {
                "Dummy Objective": {
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
            "PlateHolder",
            "data/preferences_ZSD_test.yml",
            True,
            False,
            "",
            "",
            "AutofocusNotSetError",
        ),
        (
            "DefiniteFocus2",
            "ZEN Blue Dummy",
            "6xMotorizedNosepiece",
            6,
            {
                "Dummy Objective": {
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
            "PlateHolder",
            "data/preferences_ZSD_test.yml",
            True,
            True,
            "",
            "",
            "AutofocusError",
        ),
        (
            "DefiniteFocus2",
            "ZEN Blue Dummy",
            "6xMotorizedNosepiece",
            6,
            {
                "Dummy Objective": {
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
            "PlateHolder",
            "data/preferences_ZSD_test.yml",
            True,
            True,
            "",
            "Dummy Objective",
            "AutofocusObjectiveChangedError",
        ),
        (
            "DefiniteFocus2",
            "ZEN Blue Dummy",
            "6xMotorizedNosepiece",
            6,
            {
                "Dummy Objective": {
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
            "PlateHolder",
            "data/preferences_ZSD_test.yml",
            True,
            True,
            "Dummy Objective",
            "Dummy Objective",
            100,
        ),
    ],
)
def test_recall_focus(
    auto_focus_id,
    obj_changer_id,
    software,
    positions,
    objectives,
    ref_object_id,
    prefs_path,
    use_autofocus,
    autofocus_ready,
    df_objective,
    obj_name,
    expected,
    helpers,
):
    control_software = helpers.setup_local_control_software(software)
    obj_changer = helpers.setup_local_obj_changer(
        helpers,
        obj_changer_id,
        positions,
        objectives,
        prefs_path=prefs_path,
        auto_focus_id=auto_focus_id,
    )

    autofocus = helpers.setup_local_autofocus(
        helpers, auto_focus_id, obj_changer=obj_changer, prefs_path=prefs_path
    )
    autofocus.set_use_autofocus(use_autofocus)

    if autofocus_ready:
        control_software.connection.set_autofocus_ready()

    # TODO: once Samples API is ready add these tests back

    # if prefs_path:
    #     microscope_object = setup_local_microscope(prefs_path)
    # else:
    #     microscope_object = None
    #
    # if ref_object:
    #     if ref_object == "Plate":
    #         ref_object = samples.Plate()
    #     elif ref_object == "PlateHolder":
    #         ref_object = samples.PlateHolder()
    #
    #     ref_object.set_hardware(objective_changer_id=obj_changer_id,
    #                             auto_focus_id=auto_focus_id,
    #                             microscope_object=microscope_object)

    try:
        control_software.connection.Zen.Acquisition._microscope_status.objective_name = (  # noqa
            obj_name
        )
        control_software.connection.DFObjective = df_objective
        result = autofocus.recall_focus(control_software.connection, ref_object_id)
    except Exception as err:
        result = type(err).__name__

    assert result == expected


###############################################################################
#
# Tests for the Pump class
#
###############################################################################


@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    ("pump_id, seconds, port, baudrate, expected"),
    [
        ("BraintreeScientific", 5, "COM1", 19200, ("COM1", 19200)),
        ("BraintreeScientific", None, None, None, (None, None)),
        ("BraintreeScientific", None, 443, "test", (443, "test")),
    ],
)
def test_get_connection(pump_id, seconds, port, baudrate, expected, helpers):
    pump = helpers.setup_local_pump(pump_id, seconds, port, baudrate)

    result = pump.get_connection()

    assert result == expected


@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    ("pump_id, seconds, port, baudrate, expected"),
    [
        ("BraintreeScientific", 5, "COM1", 19200, 5),
        ("BraintreeScientific", 10, None, None, 10),
        ("BraintreeScientific", None, 443, "test", None),
    ],
)
def test_get_time(pump_id, seconds, port, baudrate, expected, helpers):
    pump = helpers.setup_local_pump(pump_id, seconds, port, baudrate)

    result = pump.get_time()

    assert result == expected


@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    ("pump_id, seconds, port, baudrate, software, expected"),
    [("BraintreeScientific", 5, "COM1", 19200, "ZEN Blue Dummy", None)],
)
def test_trigger_pump(pump_id, seconds, port, baudrate, software, expected, helpers):
    pump = helpers.setup_local_pump(pump_id, seconds, port, baudrate)
    control_software = helpers.setup_local_control_software(software)

    result = pump.trigger_pump(control_software.connection)

    assert result == expected
