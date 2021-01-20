"""
Test error_handling module
Created on Jan 11, 2021

@author: fletcher.chapin
"""

import os
import pytest
import logging
from microscope_automation.get_path import get_log_file_path
from microscope_automation.preferences import Preferences
from microscope_automation.error_handling import setup_logger

os.chdir(os.path.dirname(__file__))

# set skip_all_tests = True to focus on single test
skip_all_tests = False


@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    "prefs_path, log_level, expected",
    [
        ("data/preferences_ZSD_test.yml", None, True),
        ("data/preferences_ZSD_test.yml", "DEBUG", True),
        ("data/preferences_ZSD_test.yml", "INFO", True),
        ("data/preferences_ZSD_test.yml", "WARNING", False),
        ("data/preferences_ZSD_test.yml", "ERROR", False),
        ("data/preferences_ZSD_test.yml", "CRITICAL", False),
    ],
)
def test_setup_logger(prefs_path, log_level, expected):
    prefs = Preferences(prefs_path)
    log_name = get_log_file_path(prefs)

    setup_logger(prefs, log_level=log_level)
    msg = "Logging test successful for level : " + str(log_level)
    logger = logging.getLogger(__name__)
    logger.debug(msg)

    for handler in logger.handlers:
        print("Entered the loop!")
        print(logging.getLevelName(handler.getEffectiveLevel()))

    logfile = open(log_name, "r+")
    loglist = logfile.readlines()
    logfile.close()
    result = False
    for line in loglist:
        if msg in line:
            result = True
            break

    assert result == expected
