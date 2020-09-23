"""
Test creation of  sample objects
Created on May 21, 2020

@author: winfriedw
"""

import pytest
from microscope_automation.setup_samples import setup_plate
import microscope_automation.preferences as preferences
from microscope_automation.setup_microscope import setup_microscope
import os
os.chdir(os.path.dirname(__file__))

# Set to True if you want to skip all tests, e.g. when developing a new function
skip_all_functions = False


@pytest.mark.skipif(skip_all_functions, reason='Test disabled with skip_all_functions')
@pytest.mark.parametrize('prefs_path, use_microscope_object, expected_components',
                         [('test_data/preferences_ZSD_test.yml',
                           True,
                           {'auto_focus_id': 'DefiniteFocus2',
                            'focus_id': 'MotorizedFocus',
                            'name': 'Plateholder',
                            'objective_changer_id': '6xMotorizedNosepiece',
                            'reference_object': None,
                            'reference_objective': None,
                            'safety_id': 'ZSD_01_plate',
                            'stage_id': 'Marzhauser'}),
                          ('test_data/preferences_3i_test.yml',
                           True,
                           {'auto_focus_id': 'DefiniteFocus2',
                            'focus_id': 'MotorizedFocus',
                            'name': 'Plateholder',
                            'objective_changer_id': '6xMotorizedNosepiece',
                            'reference_object': None,
                            'reference_objective': None,
                            'safety_id': 'ZSD_01_plate',
                            'stage_id': 'Marzhauser'})])
def test_setup_plate(prefs_path, use_microscope_object, expected_components):
    """Test creation of plate object"""
    prefs = preferences.Preferences(prefs_path)
    if use_microscope_object:
        microscope_object = setup_microscope(prefs)
    else:
        microscope_object = None
    plate_object = setup_plate(prefs, microscope_object=microscope_object, barcode='123')
    for key, component in list(expected_components.items()):
        assert component == getattr(plate_object, key)
