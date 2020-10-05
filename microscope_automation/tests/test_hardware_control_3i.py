"""
Test control of 3i spinning disk microscope
Created on August 17, 2020

@author: winfriedw
"""

import pytest
import os

os.chdir(os.path.dirname(__file__))

# set skip_all_tests = True to focus on single test
skip_all_tests = False


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
def test_create_experiment_path(prefs_path, experiment, expected_path, helpers):
    """Test creation of experiment path"""
    microscope = helpers.setup_local_microscope(prefs_path)
    experiment_path = microscope.create_experiment_path(experiment)
    assert os.path.abspath(expected_path) == os.path.abspath(experiment_path)


@pytest.mark.skipif(skip_all_tests, reason="Testing disabled")
@pytest.mark.parametrize("prefs_path", [("data/preferences_3i_test.yml")])
def test_execute_experiment(prefs_path, helpers):
    """Test sending experiment info to commands service.
    Slidebook will pull information from this service.
    """
    microscope = helpers.setup_local_microscope(prefs_path)
    image = microscope.execute_experiment()
    # before getting information from Slidebook,
    # there should be no information about microscope on queue
    assert image.get_meta("microscope") == ""

    # setup information about microscope
