"""
Test creation of Preferences objects
Created on Nov 24, 2020

@author: fletcher.chapin
"""

import pytest
from mock import patch
from microscope_automation.settings.preferences import Preferences
import os

os.chdir(os.path.dirname(__file__))

# set skip_all_tests = True to focus on single test
skip_all_tests = False


@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    "prefs_path, expected",
    [("data/preferences_ZSD_test.yml", None), ("data/preferences_3i_test.yml", None)],
)
def test_print_prefs(prefs_path, expected):
    prefs = Preferences(prefs_path)
    result = prefs.print_prefs()

    assert result == expected


@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    "prefs_path, parent_prefs_path",
    [
        (
            "data/microscopeSpecifications_ZSD1_dummy.yml",
            "data/preferences_ZSD_test.yml",
        ),
        (
            "data/microscopeSpecifications_3iW1-1_dummy.yml",
            "data/preferences_3i_test.yml",
        ),
    ],
)
def test_get_parent_prefs(prefs_path, parent_prefs_path):
    parent_prefs = Preferences(parent_prefs_path)
    prefs = Preferences(prefs_path, parent_prefs=parent_prefs)
    result = prefs.get_parent_prefs()

    assert result == parent_prefs


@patch(
    "microscope_automation.util.automation_messages_form_layout.pull_down_select_dialog"
)
@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    "prefs_path, name, valid_values, expected",
    [
        ("data/preferences_ZSD_test.yml", "InvalidPref", None, None),
        ("data/preferences_ZSD_test.yml", "MetaDataPath", None, "MetaData.csv"),
        (
            "data/preferences_ZSD_test.yml",
            "MetaDataPath",
            ["MetaData.pdf", "MetaData.txt"],
            "MetaData.txt",
        ),
        (
            "data/preferences_ZSD_test.yml",
            "LogFilePath",
            ["data\\Production\\LogFiles", "data/Production/LogFiles"],
            "data/Production/LogFiles",
        ),
        (
            "data/preferences_ZSD_test.yml",
            "MetaDataPath",
            ["MetaData.pdf", "MetaData.txt", "MetaData.csv"],
            "MetaData.csv",
        ),
    ],
)
def test_get_prefs(mock_pull_down, prefs_path, name, valid_values, expected):
    mock_pull_down.return_value = expected
    prefs = Preferences(prefs_path)
    result = prefs.get_pref(name, valid_values)
    if isinstance(result, list):
        result = result[0]

    assert result == expected


@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    "prefs_path, name, expected",
    [
        ("data/preferences_ZSD_test.yml", "InvalidPref", type(None)),
        ("data/preferences_ZSD_test.yml", "AddColonies", Preferences),
        ("data/preferences_3i_test.yml", "AddColonies", Preferences),
    ],
)
def test_get_pref_as_meta(prefs_path, name, expected):
    prefs = Preferences(prefs_path)
    result = prefs.get_pref_as_meta(name)
    result = result.__class__

    assert result == expected


@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    "prefs_path, default, name, val_to_set",
    [
        ("data/preferences_ZSD_test.yml", None, "NewPref", "New Value"),
        ("data/preferences_ZSD_test.yml", "csv", "MetaDataFormat", "pdf"),
    ],
)
def test_set_pref(prefs_path, default, name, val_to_set):
    prefs = Preferences(prefs_path)
    assert prefs.get_pref(name) == default

    prefs.set_pref(name, val_to_set)
    print()
    assert prefs.get_pref(name) == val_to_set
