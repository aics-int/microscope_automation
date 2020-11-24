"""
Test creation of sample objects
Created on Nov 16, 2020

@author: fletcher.chapin
"""

import pytest
from mock import patch
from microscope_automation.preferences import Preferences
from microscope_automation.samples import samples
import microscope_automation.samples.setup_samples as setup
import pandas
import os

os.chdir(os.path.dirname(__file__))

# set skip_all_tests = True to focus on single test
skip_all_tests = False


@pytest.fixture
def get_colony_data_result():
    df = pandas.read_csv("data/PlateSpecifications/GetColonyDataResult.csv")
    result = df.astype({'CloneID': 'str'})
    return result


@pytest.fixture
def filter_colonies_result():
    df = pandas.read_csv("data/PlateSpecifications/FilterColoniesResult.csv")
    result = df.astype({'CloneID': 'str'}).set_index('index').sort_index()
    return result


@pytest.fixture
def add_colonies_input():
    df = pandas.read_csv("data/PlateSpecifications/AddColoniesInput.csv")
    result = df.astype({'CloneID': 'str'})
    return result


@patch("microscope_automation.automation_messages_form_layout.pull_down_select_dialog")
@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    "prefs_path, colony_file, expected_plate, expected_name",
    [
        ("data/preferences_ZSD_test.yml", None, "96-well", ["test_barcode"]),
        ("data/preferences_ZSD_special_colony_path.yml",
         "PipelineData_Celigo.csv", "96-well", [3500000938]),
        ("data/preferences_3i_test.yml", None, "96-well", ["test_barcode"]),
    ],
)
def test_setup_plate(mock_pull_down, prefs_path, colony_file,
                     expected_plate, expected_name):
    mock_pull_down.return_value = "3500000938"
    prefs = Preferences(prefs_path)
    plate_holder = setup.setup_plate(prefs, colony_file=colony_file,
                                     barcode="test_barcode")
    assert plate_holder.__class__ == samples.PlateHolder
    plate = list(plate_holder.plates.values())[0]
    assert plate.__class__ == samples.Plate
    assert plate.get_name() == expected_plate
    assert list(plate_holder.plates.keys()) == expected_name


@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    "prefs_path, expected_slide",
    [
        ("data/preferences_ZSD_test.yml", "CalibrationSlide"),
        ("data/preferences_3i_test.yml", "CalibrationSlide"),
    ],
)
def test_setup_slide(prefs_path, expected_slide):
    prefs = Preferences(prefs_path)
    plate_holder = setup.setup_slide(prefs)
    assert plate_holder.__class__ == samples.PlateHolder
    slide = list(plate_holder.slides.values())[0]
    assert slide.__class__ == samples.Slide
    assert slide.get_name() == expected_slide


@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    "name, layout_path",
    [
        ("test_barcode", "data/PlateSpecifications/PlateLayout.yml"),
    ],
)
def test_add_barcode(name, layout_path, helpers):
    layout = Preferences(layout_path)
    well = helpers.create_sample_object("well")
    setup.add_barcode(name, well, layout)
    barcode = list(well.samples.values())[0]
    assert barcode.__class__ == samples.Barcode
    assert barcode.get_name() == name


@patch("microscope_automation.automation_messages_form_layout.pull_down_select_dialog")
@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    "prefs_path, pref_name, colony_file, expected",
    [
        ("data/preferences_ZSD_test.yml", "InitializeMicroscope",
         "data/PlateSpecifications/PipelineData_Celigo.csv", "AttributeError"),
        ("data/preferences_ZSD_test.yml", "AddColonies",
         "data/PlateSpecifications/PipelineData_Celigo.csv", None),
        ("data/preferences_3i_test.yml", "AddColonies",
         "data/PlateSpecifications/PipelineData_Celigo.csv", None),
    ],
)
def test_get_colony_data(mock_pull_down, prefs_path, pref_name, colony_file,
                         expected, helpers, get_colony_data_result):
    mock_pull_down.return_value = "3500000938"
    prefs = Preferences(prefs_path).get_pref_as_meta(pref_name)
    try:
        colonies = setup.get_colony_data(prefs, colony_file)
        for col_label in colonies:
            pandas.testing.assert_series_equal(colonies[col_label],
                                               get_colony_data_result[col_label])
    except Exception as err:
        result = type(err).__name__
        assert expected == result


@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    "prefs_path, pref_name, well_dict, expected",
    [
        ("data/preferences_ZSD_test.yml", "AddColonies",
         {'A1': ''}, "TypeError"),
        ("data/preferences_ZSD_test.yml", "AddColonies",
         {'C4': 70}, None),
        ("data/preferences_ZSD_test.yml", "AddColonies",
         {'C4': 71}, "ValueError"),
        ("data/preferences_3i_test.yml", "AddColonies",
         {'C4': 70}, None),
    ],
)
def test_filter_colonies(prefs_path, pref_name, well_dict,
                         expected, helpers, get_colony_data_result,
                         filter_colonies_result):
    prefs = Preferences(prefs_path).get_pref_as_meta(pref_name)
    try:
        colonies = setup.filter_colonies(prefs, get_colony_data_result, well_dict)
        colonies = colonies.sort_index()
        colonies.index.rename('index', inplace=True)

        for col_label in colonies:
            print(col_label)
            pandas.testing.assert_series_equal(
                colonies[col_label],
                filter_colonies_result[col_label],
                check_exact=False,
                rtol=1e-10,
                atol=1e-10
            )
    except Exception as err:
        result = type(err).__name__
        assert expected == result


@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    "prefs_path, well_name, expected",
    [
        ("data/microscopeSpecifications_ZSD1_dummy.yml", "A1", []),
        ("data/microscopeSpecifications_ZSD1_dummy.yml", "C4", ['C4_26.0', 'C4_06.0']),
    ],
)
def test_add_colonies(prefs_path, well_name, expected, helpers, add_colonies_input):
    hardware_settings = Preferences(prefs_path)
    well = helpers.setup_local_well(helpers, name=well_name)
    result = setup.add_colonies(well, add_colonies_input, hardware_settings)

    assert [colony.get_name() for colony in result] == expected
    assert all([colony.__class__ == samples.Colony for colony in result])
