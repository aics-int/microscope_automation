"""
Test samples Classes
Created on October 5, 2020

@author: fletcher.chapin
"""

import pytest
import os

os.chdir(os.path.dirname(__file__))

# set skip_all_tests = True to focus on single test
skip_all_tests = False

###############################################################################
#
# Tests for the ImagingSystem class
#
###############################################################################


@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    ("stage_id_init, stage_id_change"),
    [(None, ""), ("stage_init", "stage_final")]
)
def test_set_hardware(stage_id_init, stage_id_change, helpers):
    img_sys = helpers.setup_local_imaging_system(helpers, stage_id=stage_id_init)
    assert img_sys.stage_id == stage_id_init

    img_sys.set_hardware(stage_id=stage_id_change)
    assert img_sys.stage_id == stage_id_change


@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    ("name_get, name_set"),
    [(None, ""), ("test_name", "new_test_name")]
)
def test_get_set_name(name_get, name_set, helpers):
    img_sys = helpers.setup_local_imaging_system(helpers, name=name_get)
    assert img_sys.get_name() == name_get

    img_sys.set_name(name_set)
    assert img_sys.get_name() == name_set
