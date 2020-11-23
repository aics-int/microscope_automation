"""
Test creation of sample objects
Created on Nov 16, 2020

@author: fletcher.chapin
"""

import pytest
from microscope_automation.preferences import Preferences
from microscope_automation.samples import samples
import microscope_automation.samples.setup_samples as setup
import os

os.chdir(os.path.dirname(__file__))

# set skip_all_tests = True to focus on single test
skip_all_tests = False


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
