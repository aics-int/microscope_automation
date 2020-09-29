"""
Test control of 3i spinning disk microscope
Created on August 17, 2020

@author: winfriedw
"""

import pytest
import microscope_automation.hardware.setup_microscope as setup_microscope
import microscope_automation.preferences as preferences
import os

os.chdir(os.path.dirname(__file__))

# set skip_all_tests = True to focus on single test
skip_all_tests = False


def setup_local_microscope(prefs_path):
    """Create microscope object"""
    prefs = preferences.Preferences(prefs_path)
    microscope_object = setup_microscope.setup_microscope(prefs)
    return microscope_object


@pytest.mark.skipif(skip_all_tests, reason="Testing disabled")
@pytest.mark.parametrize(
    "prefs_path, experiment, expected_path",
    [
        (
            "data/preferences_3i_test.yml",
            "test_communication.exp.prefs",
            "data/SlideBook 6.0/test_communication.exp.prefs",
        )
    ],
)
def test_create_experiment_path(prefs_path, experiment, expected_path):
    """Test creation of experiment path"""
    microscope = setup_local_microscope(prefs_path)
    experiment_path = microscope.create_experiment_path(experiment)
    assert os.path.abspath(expected_path) == os.path.abspath(experiment_path)


@pytest.mark.skipif(skip_all_tests, reason="Testing disabled")
@pytest.mark.parametrize("prefs_path", [("data/preferences_3i_test.yml")])
def test_execute_experiment(prefs_path):
    """Test sending experiment info to commands service.
    Slidebook will pull information from this service.
    """
    microscope = setup_local_microscope(prefs_path)
    image = microscope.execute_experiment()
    # before getting information from Slidebook,
    # there should be no information about microscope on queue
    assert image.get_meta("microscope") == ""

    # setup information about microscope
