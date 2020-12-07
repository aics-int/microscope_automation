"""
Test microscope automation's main module, which orchestrates workflows.
Created on December 1, 2020

@author: fletcher.chapin
"""

import pytest
import os
from mock import patch
from microscope_automation.preferences import Preferences
from microscope_automation.samples import samples
from microscope_automation import microscope_automation

os.chdir(os.path.dirname(__file__))

# set skip_all_tests = True to focus on single test
skip_all_tests = False


@patch("microscope_automation.automation_messages_form_layout.information_message")
@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    ("text, allow_continue, expected"),
    [
        (None, False, "SystemExit"),
        (None, True, None),
    ],
)
def test_stop_script(mock_message, text, allow_continue, expected):
    try:
        result = microscope_automation.stop_script(
            message_text=text, allow_continue=allow_continue
        )
    except SystemExit as err:
        result = type(err).__name__
    assert result == expected


@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    ("prefs_path, plate_holder_name, plate_name, well"),
    [
        ("data/preferences_ZSD_test.yml", "Plateholder", "96-well", "A1"),
    ],
)
def test_get_well_object(prefs_path, plate_holder_name, plate_name,
                         well, helpers):
    mic_auto = helpers.setup_local_microscope_automation(prefs_path)
    well_object = helpers.setup_local_well(helpers, name=well, plate_name=plate_name)
    plate_holder_object = helpers.setup_local_plate_holder(helpers, plate_holder_name)
    plate_object = well_object.container
    plate_object.set_container(plate_holder_object)
    plate_object.add_wells({well: well_object})
    plate_holder_object.add_plates({plate_name: plate_object})

    result = mic_auto.get_well_object(plate_holder_object, plate_name, well)

    assert result.name == well
    assert result.__class__ == samples.Well


@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    ("prefs_path, well_name, barcode_name"),
    [
        ("data/preferences_ZSD_test.yml", "A1", "1234"),
    ],
)
def test_get_barcode_object(prefs_path, well_name, barcode_name, helpers):
    mic_auto = helpers.setup_local_microscope_automation(prefs_path)
    well_object = helpers.setup_local_well(helpers, name=well_name)
    barcode_object = samples.Barcode(name=barcode_name)
    well_object.add_barcode({barcode_name: barcode_object})

    result = mic_auto.get_barcode_object(well_object, barcode_name)

    assert result.name == barcode_name
    assert result.__class__ == samples.Barcode


@patch(
    "microscope_automation.samples.samples.PlateHolder.execute_experiment"
)
@patch("microscope_automation.automation_messages_form_layout.operate_message")
@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    ("prefs_path, pref_name, plate_holder_name, plate_name, "
     "well_name, barcode_name, expected"),
    [
        ("data/preferences_ZSD_2_test.yml", "ImageBarcode", "Plateholder",
         "96-well", "A1", "1234", "Not implemented"),
        ("data/preferences_ZSD_2_test.yml", "ImageBarcode", "Plateholder",
         "96-well", None, None, "AttributeError"),
    ],
)
def test_read_barcode(mock_message, mock_execute, prefs_path, pref_name,
                      plate_holder_name, plate_name, well_name, barcode_name,
                      expected, helpers):
    mic_auto = helpers.setup_local_microscope_automation(prefs_path)
    well_object = helpers.setup_local_well(helpers, name=well_name,
                                           plate_name=plate_name)
    plate_holder_object = helpers.setup_local_plate_holder(
        helpers,
        name=plate_holder_name,
        prefs_path=prefs_path
    )
    plate_object = well_object.container
    plate_object.set_container(plate_holder_object)
    plate_object.add_wells({well_name: well_object})
    plate_holder_object.add_plates({plate_name: plate_object})
    barcode_object = samples.Barcode(name=barcode_name)
    barcode_object.set_container(well_object)
    well_object.add_barcode({barcode_name: barcode_object})

    try:
        result = mic_auto.read_barcode(
            Preferences(prefs_path).get_pref_as_meta(pref_name),
            plate_holder_object,
            plate_name,
            well_name,
            barcode_name
        )
    except Exception as err:
        result = type(err).__name__

    assert result == expected


@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    ("prefs_path, pref_name, plate_holder_name, plate_name, "
     "well_names, well_diameter, experiment, expected"),
    [
        ("data/preferences_ZSD_2_test.yml", "CalibrateWellDistance", "Plateholder",
         "96-well", ["B2", "B11", "G11"], None, "ImageBarcode.czexp",
         "TypeError"),
        ("data/preferences_ZSD_2_test.yml", "CalibrateWellDistance", "Plateholder",
         "96-well", ["B2", "B11", "G11"], 6134, "ImageBarcode.czexp",
         None),
        ("data/preferences_ZSD_2_test.yml", "ImageBarcode", "Plateholder",
         "96-well", [], None, None, "AttributeError"),
    ],
)
def test_calculate_all_wells_correction(prefs_path, pref_name,
                                        plate_holder_name, plate_name, well_names,
                                        well_diameter, experiment, expected, helpers):
    mic_auto = helpers.setup_local_microscope_automation(prefs_path)
    plate_object = helpers.setup_local_plate(helpers, name=plate_name)
    plate_holder_object = helpers.setup_local_plate_holder(
        helpers,
        name=plate_holder_name,
        prefs_path=prefs_path
    )
    plate_object.set_container(plate_holder_object)
    plate_holder_object.add_plates({plate_name: plate_object})
    for name in well_names:
        well = helpers.setup_local_well(helpers, name=name)
        well.set_measured_diameter(well_diameter)
        well.container = plate_object
        plate_object.add_wells({name: well})

    try:
        result = mic_auto.calculate_all_wells_correction(
            Preferences(prefs_path).get_pref_as_meta(pref_name),
            plate_holder_object,
            experiment
        )
    except Exception as err:
        result = type(err).__name__

    assert result == expected
