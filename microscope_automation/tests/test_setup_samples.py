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
def add_colonies_result():
    df = pandas.read_csv("data/PlateSpecifications/AddColoniesResult.csv")
    result = df.astype({'CloneID': 'str'})
    return result


@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    "prefs_path, expected_plate",
    [
        ("data/preferences_ZSD_test.yml", "96-well"),
        ("data/preferences_3i_test.yml", "96-well"),
    ],
)
def test_setup_plate(prefs_path, expected_plate):
    prefs = Preferences(prefs_path)
    plate_holder = setup.setup_plate(prefs, barcode="test_barcode")
    assert plate_holder.__class__ == samples.PlateHolder
    plate = list(plate_holder.plates.values())[0]
    assert plate.__class__ == samples.Plate
    assert plate.get_name() == expected_plate
    assert list(plate_holder.plates.keys()) == ["test_barcode"]


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


@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@patch("microscope_automation.automation_messages_form_layout.pull_down_select_dialog")
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
                         expected, helpers, add_colonies_result):
    mock_pull_down.return_value = "3500000938"
    prefs = Preferences(prefs_path).get_pref_as_meta(pref_name)
    try:
        colonies = setup.get_colony_data(prefs, colony_file)
        for col_label in colonies:
            pandas.testing.assert_series_equal(colonies[col_label],
                                               add_colonies_result[col_label])
    except Exception as err:
        result = type(err).__name__
        assert expected == result
