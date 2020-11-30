"""
Test get_path module, which returns path for settings, logfile, and data
based on preferences file
Created on Nov 17, 2020

@author: fletcher.chapin
"""
import os
import pytest
import time
import re
import datetime
from pathlib import Path
from microscope_automation.preferences import Preferences
from microscope_automation import get_path

os.chdir(os.path.dirname(__file__))


# set skip_all_tests = True to focus on single test
skip_all_tests = False

today = datetime.date.today()
DATE_STR = str(today.year) + "_" + str(today.month) + "_" + str(today.day)
time_stamp = time.time()
TIME_STAMP = datetime.datetime.fromtimestamp(time_stamp).strftime("%Y-%m-%d_%H-")


@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    "file_path, suffix, expected",
    [
        ("test_file", "1", "test_file_1"),
        ("test_image.czsh", "2", "test_image_2.czsh"),
        ("test_data.csv", "123;lkas", "test_data_123;lkas.csv"),
    ],
)
def test_add_suffix(file_path, suffix, expected):
    result = get_path.add_suffix(file_path, suffix)
    assert result == expected


@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    "prefs_path, key, search_dir, validate, expected",
    [
        (
            "data/preferences_3i_test.yml",
            "PathExperiments",
            True,
            True,
            "data" + os.path.sep + "SlideBook 6.0" + os.path.sep,
        ),
        (
            "data/preferences_ZSD_test.yml",
            "PathExperiments",
            True,
            True,
            "data" + os.path.sep + "Experiment Setup" + os.path.sep,
        ),
        (
            "data/preferences_ZSD_test.yml",
            "PathExperiments",
            False,
            True,
            "AssertionError",
        ),
        (
            "data/preferences_ZSD_test.yml",
            "InvalidKey",
            True,
            False,
            "ValueError",
        ),
    ],
)
def test_get_valid_path_from_prefs(prefs_path, key, search_dir, validate, expected):
    prefs = Preferences(prefs_path)

    try:
        result = get_path.get_valid_path_from_prefs(prefs, key, search_dir, validate)
    except Exception as err:
        result = type(err).__name__
    assert result == expected


@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    "parent_folder_path, subfolder, expected",
    [
        ("data", "1234", ["data" + os.path.sep + "1234"]),
        (
            "data",
            ["1234", "new_folder"],
            ["data" + os.path.sep + "1234", "data" + os.path.sep + "new_folder"],
        ),
    ],
)
def test_set_up_subfolders(parent_folder_path, subfolder, expected):
    result = get_path.set_up_subfolders(parent_folder_path, subfolder)
    assert result == expected


@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    "prefs_path, barcode, expected",
    [
        ("data/preferences_3i_test.yml", None, os.path.join(DATE_STR, "3iW1-0")),
        ("data/preferences_ZSD_test.yml", None, os.path.join(DATE_STR, "Zeiss SD 1")),
        (
            "data/preferences_ZSD_test.yml",
            "test_code",
            os.path.join("test_code", "Zeiss SD 1"),
        ),
    ],
)
def test_get_daily_folder(prefs_path, barcode, expected):
    prefs = Preferences(prefs_path)
    result = get_path.get_daily_folder(prefs, barcode)
    assert result == expected


@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    "prefs_path, pref_name, barcode, expected",
    [
        (
            "data/preferences_3i_test.yml",
            "SegmentWells",
            None,
            (
                Path(os.path.join(DATE_STR, "3iW1-0", "positions.csv")),
                Path(os.path.join(DATE_STR, "3iW1-0", "positions_wellid.csv")),
                Path(os.path.join(DATE_STR, "3iW1-0", "failed_wells.csv")),
            ),
        ),
        (
            "data/preferences_ZSD_test.yml",
            "SegmentWells",
            None,
            (
                Path(os.path.join(DATE_STR, "Zeiss SD 1", "positions.csv")),
                Path(os.path.join(DATE_STR, "Zeiss SD 1", "positions_wellid.csv")),
                Path(os.path.join(DATE_STR, "Zeiss SD 1", "failed_wells.csv")),
            ),
        ),
        (
            "data/preferences_ZSD_test.yml",
            "SegmentWells",
            "test_code",
            (
                Path(os.path.join("test_code", "Zeiss SD 1", "positions.csv")),
                Path(os.path.join("test_code", "Zeiss SD 1", "positions_wellid.csv")),
                Path(os.path.join("test_code", "Zeiss SD 1", "failed_wells.csv")),
            ),
        ),
    ],
)
def test_get_position_csv_path(prefs_path, pref_name, barcode, expected):
    prefs = Preferences(prefs_path).get_pref_as_meta(pref_name)
    result = get_path.get_position_csv_path(prefs, barcode)
    assert result == expected


@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    "prefs_path, expected",
    [
        (
            "data/preferences_3i_test.yml",
            os.path.join("data", "Production", "LogFiles", DATE_STR + ".log"),
        ),
        (
            "data/preferences_ZSD_test.yml",
            os.path.join("data", "Production", "LogFiles", DATE_STR + ".log"),
        ),
    ],
)
def test_get_log_file_path(prefs_path, expected):
    prefs = Preferences(prefs_path)
    result = get_path.get_log_file_path(prefs)
    assert result == expected


@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    "prefs_path, barcode, expected",
    [
        (
            "data/preferences_3i_test.yml",
            None,
            os.path.join(DATE_STR, "3iW1-0", "MetaData.csv"),
        ),
        (
            "data/preferences_ZSD_test.yml",
            None,
            os.path.join(DATE_STR, "Zeiss SD 1", "MetaData.csv"),
        ),
        (
            "data/preferences_ZSD_test.yml",
            "test_code",
            os.path.join("test_code", "Zeiss SD 1", "MetaData.csv"),
        ),
    ],
)
def test_get_meta_data_path(prefs_path, barcode, expected):
    prefs = Preferences(prefs_path)
    result = get_path.get_meta_data_path(prefs, barcode)
    assert result == expected


@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    "prefs_path, pref_name, dir, expected",
    [
        (
            "data/preferences_3i_test.yml",
            None,
            False,
            "TypeError",
        ),
        (
            "data/preferences_3i_test.yml",
            "ScanPlate",
            False,
            os.path.join("data", "SlideBook 6.0", "test_communication.exp.prefs"),
        ),
        (
            "data/preferences_3i_test.yml",
            None,
            True,
            os.path.join("data", "SlideBook 6.0"),
        ),
        (
            "data/preferences_ZSD_test.yml",
            None,
            False,
            os.path.join("data", "Experiment Setup", "WellTile_10x_true.czexp"),
        ),
    ],
)
def test_get_experiment_path(prefs_path, pref_name, dir, expected):
    if pref_name:
        prefs = Preferences(prefs_path).get_pref_as_meta(pref_name)
    else:
        prefs = Preferences(prefs_path)

    try:
        result = get_path.get_experiment_path(prefs, dir)
    except Exception as err:
        result = type(err).__name__
    assert result == expected


@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    "prefs_path, expected",
    [
        (
            "data/preferences_3i_test.yml",
            os.path.join("data", "Production", "GeneralSettings", "RecoverySettings"),
        ),
        (
            "data/preferences_ZSD_test.yml",
            os.path.join("data", "Production", "GeneralSettings", "RecoverySettings"),
        ),
    ],
)
def test_get_recovery_settings_path(prefs_path, expected):
    prefs = Preferences(prefs_path)
    result = get_path.get_recovery_settings_path(prefs)
    path0, path1 = os.path.split(result)
    assert path0 == expected
    # had to match regex so that seconds and minutes were ignored
    expression = "Plate_" + TIME_STAMP + "[0-9][0-9]-[0-9][0-9]" + ".pickle"
    print(expression)
    assert re.match(expression, path1)


@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    "prefs_path, barcode, expected",
    [
        (
            "data/preferences_3i_test.yml",
            None,
            os.path.join(DATE_STR, "3iW1-0", "CeligoColonyData"),
        ),
        (
            "data/preferences_ZSD_test.yml",
            None,
            os.path.join(DATE_STR, "Zeiss SD 1", "CeligoColonyData"),
        ),
        (
            "data/preferences_ZSD_test.yml",
            "test_code",
            os.path.join("test_code", "Zeiss SD 1", "CeligoColonyData"),
        ),
    ],
)
def test_get_colony_dir_path(prefs_path, barcode, expected):
    prefs = Preferences(prefs_path)
    result = get_path.get_colony_dir_path(prefs, barcode)
    assert result == expected


@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    "prefs_path, pref_name, expected",
    [
        (
            "data/preferences_3i_test.yml",
            "InitializeMicroscope",
            "data/PlateSpecifications",
        ),
        (
            "data/preferences_ZSD_test.yml",
            "InitializeMicroscope",
            "data/PlateSpecifications",
        ),
    ],
)
def test_get_colony_remote_dir_path(prefs_path, pref_name, expected):
    prefs = Preferences(prefs_path).get_pref_as_meta(pref_name)
    result = get_path.get_colony_remote_dir_path(prefs)
    assert result == expected


@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    "prefs_path, colony_file, barcode, expected",
    [
        (
            "data/preferences_3i_test.yml",
            "test.csv",
            None,
            os.path.join(DATE_STR, "3iW1-0", "CeligoColonyData", "test.csv"),
        ),
        (
            "data/preferences_ZSD_test.yml",
            "test.csv",
            None,
            os.path.join(DATE_STR, "Zeiss SD 1", "CeligoColonyData", "test.csv"),
        ),
        (
            "data/preferences_ZSD_test.yml",
            "test.csv",
            "test_code",
            os.path.join("test_code", "Zeiss SD 1", "CeligoColonyData", "test.csv"),
        ),
        (
            "data/preferences_ZSD_test.yml",
            None,
            "test_code",
            "TypeError",
        ),
    ],
)
def test_get_colony_file_path(prefs_path, barcode, colony_file, expected):
    prefs = Preferences(prefs_path)
    try:
        result = get_path.get_colony_file_path(prefs, colony_file, barcode)
    except Exception as err:
        result = type(err).__name__
    assert result == expected


@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    "prefs_path, expected",
    [
        (
            "data/preferences_3i_test.yml",
            os.path.join("data", "microscopeSpecifications_3iW1-1_dummy.yml"),
        ),
        (
            "data/preferences_ZSD_test.yml",
            os.path.join("data", "microscopeSpecifications_ZSD1_dummy.yml"),
        ),
    ],
)
def test_get_hardware_settings_path(prefs_path, expected):
    prefs = Preferences(prefs_path)
    result = get_path.get_hardware_settings_path(prefs)
    assert result == expected


@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    "prefs_path, barcode, expected",
    [
        (
            "data/preferences_3i_test.yml",
            None,
            os.path.join(DATE_STR, "3iW1-0", "References"),
        ),
        (
            "data/preferences_ZSD_test.yml",
            None,
            os.path.join(DATE_STR, "Zeiss SD 1", "References"),
        ),
        (
            "data/preferences_ZSD_test.yml",
            "test_code",
            os.path.join("test_code", "Zeiss SD 1", "References"),
        ),
    ],
)
def test_get_references_path(prefs_path, barcode, expected):
    prefs = Preferences(prefs_path)
    result = get_path.get_references_path(prefs, barcode)
    assert result == expected


@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    "prefs_path, sub_dir, barcode, expected",
    [
        (
            "data/preferences_3i_test.yml",
            None,
            None,
            os.path.join(DATE_STR, "3iW1-0"),
        ),
        (
            "data/preferences_3i_test.yml",
            "test_sub_dir",
            None,
            os.path.join(DATE_STR, "3iW1-0", "test_sub_dir"),
        ),
        (
            "data/preferences_ZSD_test.yml",
            None,
            None,
            os.path.join(DATE_STR, "Zeiss SD 1"),
        ),
        (
            "data/preferences_ZSD_test.yml",
            None,
            "test_code",
            os.path.join("test_code", "Zeiss SD 1"),
        ),
    ],
)
def test_get_images_path(prefs_path, sub_dir, barcode, expected):
    prefs = Preferences(prefs_path)
    result = get_path.get_images_path(prefs, sub_dir, barcode)
    assert result == expected


@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    "prefs_path, expected",
    [
        (
            "data/preferences_3i_test.yml",
            os.path.join("data", "Production", "GeneralSettings", "Calibration", ""),
        ),
        (
            "data/preferences_ZSD_test.yml",
            os.path.join("data", "Production", "GeneralSettings", "Calibration", ""),
        ),
    ],
)
def test_get_calibration_path(prefs_path, expected):
    prefs = Preferences(prefs_path)
    result = get_path.get_calibration_path(prefs)
    assert result == expected


@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    "prefs_path, barcode, expected",
    [
        (
            "data/preferences_3i_test.yml",
            None,
            os.path.join(DATE_STR, "3iW1-0", "WellEdge"),
        ),
        (
            "data/preferences_ZSD_test.yml",
            None,
            os.path.join(DATE_STR, "Zeiss SD 1", "WellEdge"),
        ),
        (
            "data/preferences_ZSD_test.yml",
            "test_code",
            os.path.join("test_code", "Zeiss SD 1", "WellEdge"),
        ),
    ],
)
def test_get_well_edge_path(prefs_path, barcode, expected):
    prefs = Preferences(prefs_path)
    result = get_path.get_well_edge_path(prefs, barcode)
    assert result == expected
