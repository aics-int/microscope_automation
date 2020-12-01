"""
Test microscope automation's main module, which orchestrates workflows.
Created on December 1, 2020

@author: fletcher.chapin
"""

import pytest
import os
from microscope_automation import microscope_automation

os.chdir(os.path.dirname(__file__))

# set skip_all_tests = True to focus on single test
skip_all_tests = True


@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    ("text, allow_continue, expected"),
    [
        (None, False, "SystemExit"),
    ],
)
def test_stop_script(text, allow_continue, expected):
    result = microscope_automation.stop_script(
        message_text=text, allow_continue=allow_continue
    )
    assert result == expected
