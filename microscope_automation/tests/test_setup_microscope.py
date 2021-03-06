"""
Test creation of microscope
Created on May 20, 2020

@author: winfriedw
"""

import pytest
from sys import platform
import microscope_automation.settings.preferences as preferences
from microscope_automation.hardware.setup_microscope import setup_microscope
import os

os.chdir(os.path.dirname(__file__))

# set skip_all_tests = True to focus on single test
skip_all_tests = False


@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    "prefs_path, expected_components",
    [
        (
            "data/preferences_ZSD_test.yml",
            [
                "Camera1 (back)",
                "Camera2 (left)",
                "ZSD_01_immersion",
                "ZSD_01_plate",
                "ZSD_01_slide",
                "Marzhauser",
                "6xMotorizedNosepiece",
                "MotorizedFocus",
                "DefiniteFocus2",
                "BraintreeScientific",
            ],
        ),
        (
            "data/preferences_3i_test.yml",
            ["Camera1 (back)", "Camera2 (left)", "Marzhauser", "MotorizedFocus"],
        ),
    ],
)
def test_setup_microscope(prefs_path, expected_components):
    """Test creation of microscope object"""
    prefs = preferences.Preferences(prefs_path)
    microscope_object = setup_microscope(prefs)
    assert (
        list(microscope_object.microscope_components_ordered_dict.keys())
        == expected_components
    )


@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
def test_import_pywin32():
    # if pywin32 isn't installed this will throw ImportError and never assert True
    if platform == "win32" or platform == "cygwin":
        import win32com.client  # noqa

    assert True
