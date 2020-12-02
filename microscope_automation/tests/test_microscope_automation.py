"""
Test microscope automation's main module, which orchestrates workflows.
Created on December 1, 2020

@author: fletcher.chapin
"""

import pytest
import os
from mock import patch
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
