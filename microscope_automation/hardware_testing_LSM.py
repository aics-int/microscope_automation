'''
Functions to test module hardware.py on spinning disk microscope ZSD_3
Created on Sep 7, 2018

@author: winfriedw
'''

from hardware import *
import setupAutomation

import argparse
from samples_testing import test_definite_focus
from collections import OrderedDict
                

def test_microscope(sample_object, test_settings):  
    '''Test of basic microscope functionality.
    
    Input:
     sample_object: object based on class ImagingSystem in module samples.py
                     sample_object has microscope object attached
     prefs: preferences as class preferences
     
    Output:
     success: True, if all tests where run
    '''            
    # all hardware functionality should only be accessed through object of class Microscope
    microscope_object = sample_object.get_microscope()
        
    print ('Switch on live mode')
    microscope_object.live_mode(camera_id = test_settings['camera_id'], 
                                experiment = test_settings['experiment_standard'], 
                                live = True)
    
    x, y, z = test_settings['image_pos_1']
    print ('Move to stage position ({}, {}, {}).'.format(x, y, z))
    microscope_object.move_to_abs_pos(stage_id = test_settings['stage_id'],
                                           focus_drive_id = test_settings['focus_drive_id'],
                                           objective_changer_id = test_settings['objective_changer_id'],
                                           auto_focus_id = test_settings['auto_focus_id'],
                                           safety_id = test_settings['safety_id'],
                                           safe_area = 'Compound', 
                                           x_target = x, y_target = y, z_target = z,
                                           reference_object = sample_object.get_reference_object(),
                                           load = True,
                                           trials = 3,
                                           verbose = test_settings['verbose'])

    print ('Switch off live mode')
    microscope_object.live_mode(camera_id = test_settings['camera_id'], 
                                experiment = test_settings['experiment_standard'], 
                                live = False)
    
    print ('Execute experiment and save image')
    image = microscope_object.execute_experiment(experiment = test_settings['experiment_standard'], 
                                         file_path = test_settings['file_path'], 
                                         z_start = 'F',
                                         interactive = True)

##############################
# Test fails in aicsImage    
#     print ('Load image data')
#     image_w_data = microscope_object.load_image(image, getMeta = True)

    
    print ('Remove all images in ZEN software')
    microscope_object.remove_images() 
    
    return(True)

def test_move_sample(sample_object, test_settings, z_pos = None):  
    '''Test definite focus.
    
    Input:
     sample_object: object based on class ImagingSystem in module samples.py
                     sample_object has microscope object attached
     test_settings: settings for testing as defined in __main__
     z_pos: override z position in test_settings
     
    Output:
     success: True, if all tests where run
    '''  
    microscope_object = sample_object.get_microscope()
    
    x, y, z = test_settings['image_pos_1']  
    if z_pos: 
        z = z_pos    
    sample_object.move_to_abs_position(x, y, z,
                                       load = False, 
                                       verbose = test_settings['verbose'])
    image = microscope_object.execute_experiment(experiment = test_settings['experiment_standard'], 
                                         file_path = None, 
                                         z_start = 'F',
                                         interactive = True)
    
    sample_object.move_delta_xyz(x = test_settings['image_pos_increment'][0], 
                                 y = 0, 
                                 z = 0, 
                                 load = False, 
                                 verbose = test_settings['verbose'])
    image = microscope_object.execute_experiment(experiment = test_settings['experiment_standard'], 
                                         file_path = None, 
                                         z_start = 'F',
                                         interactive = True)
    
    sample_object.move_delta_xyz(x = 0, 
                                 y = test_settings['image_pos_increment'][1], 
                                 z = 0, 
                                 load = False, 
                                 verbose = test_settings['verbose'])
    image = microscope_object.execute_experiment(experiment = test_settings['experiment_standard'], 
                                         file_path = None, 
                                         z_start = 'F',
                                         interactive = True)
    
    sample_object.move_delta_xyz(x = - test_settings['image_pos_increment'][0], 
                                 y = test_settings['image_pos_increment'][1], 
                                 z = 0, 
                                 load = False, 
                                 verbose = test_settings['verbose'])
    image = microscope_object.execute_experiment(experiment = test_settings['experiment_standard'], 
                                         file_path = None, 
                                         z_start = 'F',
                                         interactive = True)
    
    microscope_object.live_mode(camera_id = test_settings['camera_id'], 
                                experiment = test_settings['experiment_standard'], 
                                live = False)
    return True   

def test_definite_focus(sample_object, test_settings, experiment = 'experiment_standard'):  
    '''Test definite focus.
    
    Input:
     sample_object: object based on class ImagingSystem in module samples.py
                     sample_object has microscope object attached
     test_settings: preferences as class preferences
     experiment: label for experiment in test_settings
     
    Output:
     success: True, if all tests where run
    '''            
    # all hardware functionality should only be accessed through object of class Microscope
    microscope_object = sample_object.get_microscope()
        
    # get autofocus status
    autofocus_id = test_settings['auto_focus_id']
    autofocus_satus = microscope_object.get_information([autofocus_id])
    print('Information about auto-focus:\n{}'.format(autofocus_satus))   
                                                     
    # test with autofocus switched off
    microscope_object.set_microscope({autofocus_id: {'use_auto_focus': False}})
    # find focus position
    microscope_object.live_mode(camera_id = test_settings['camera_id'], 
                                experiment = test_settings['experiment_standard'], 
                                live = True)
    print('Please focus')
    focus_drive_id = test_settings['focus_drive_id']
    focus_info = microscope_object.get_information([focus_drive_id])[focus_drive_id]
    z_pos = focus_info['focality_corrected'] 
    microscope_object.live_mode(camera_id = test_settings['camera_id'], 
                                experiment = test_settings['experiment_standard'], 
                                live = False)   
    test_move_sample(sample_object, test_settings, z_pos)
    
    # test with autofocus switched on
    microscope_object.live_mode(camera_id = test_settings['camera_id'], 
                                experiment = test_settings['experiment_standard'], 
                                live = True)
    microscope_object.set_microscope({autofocus_id: {'use_auto_focus': True}})
    # find focus position 
    sample_object.move_to_abs_position(*test_settings['image_pos_1'],
                                       load = False, 
                                       verbose = test_settings['verbose'])
    print('Please focus')
    focus_info = microscope_object.get_information([focus_drive_id])[focus_drive_id]
    z_pos = focus_info['focality_corrected'] 
    microscope_object.live_mode(camera_id = test_settings['camera_id'], 
                                experiment = test_settings['experiment_standard'], 
                                live = False)   
  
    test_move_sample(sample_object, test_settings, z_pos)                                                 
    return True   

def test_parfocality(sample_object, test_settings):  
    '''Test definite focus and parfocality.
    
    Input:
     sample_object: object based on class ImagingSystem in module samples.py
                     sample_object has microscope object attached
     test_settings: preferences as class preferences
     
    Output:
     success: True, if all tests where run
    '''            
    print ('==============================================\nStart testing parfocality\n')
    # all hardware functionality should only be accessed through object of class Microscope
    microscope_object = sample_object.get_microscope()

    # Switch between different objectives
    for experiment_label in test_settings['magnification_experiments']:
    # check if microscope is ready and initialize if necessary
        test_ready_dict = OrderedDict([(test_settings['stage_id'], []),
                                       (test_settings['focus_drive_id'], ['set_load']),
                                       (test_settings['objective_changer_id'], []),
                                       (test_settings['auto_focus_id'], ['no_find_surface'])])
        success = microscope_object.microscope_is_ready(experiment = test_settings[experiment_label], 
                                                        component_dict = test_ready_dict, 
                                                        focus_drive_id = test_settings['focus_drive_id'], 
                                                        objective_changer_id = test_settings['objective_changer_id'], 
                                                        safety_object_id = test_settings['safety_id'],
                                                        reference_object = sample_object.get_reference_object(),
                                                        load = True, 
                                                        make_ready = True, 
                                                        verbose = test_settings['verbose'])
                                                                                                                                                                     

    return success

def test_hardware(test, prefs, test_settings):
    '''Different test cases for module hardware.
    
    Input:
     test: tests to perform
             test options: 'test_microscope', 'test_move_sample', 'test_definet_focus', 'test_parfocality'
     prefs: preferences as class preferences
     test_settings: dictionary with test specific settings
     
    Output:
     success: True, if all tests where run
    '''

    # setup microscope
    microscope_object = setupAutomation.setup_microscope(prefs)

    print('Microscope {} with the following components created:\n'.format(microscope_object.name))
    print('{}'.format(microscope_object.microscope_components_OrderedDict))
    print('Information about components:\n{}'.format(microscope_object.get_information()))
    
    test_ready_dict = OrderedDict([(test_settings['stage_id'], []),
                                   (test_settings['focus_drive_id'], ['set_load']),
                                   (test_settings['objective_changer_id'], []),
                                   (test_settings['auto_focus_id'], ['no_find_surface'])])
    print('The following components are ready for experiment {}:\n{}'.format(test_settings['experiment_standard'],
                                                                            microscope_object.microscope_is_ready(experiment = test_settings['experiment_standard'], 
                                                                                                                  component_dict = test_ready_dict, 
                                                                                                                  focus_drive_id = test_settings['focus_drive_id'],
                                                                                                                  objective_changer_id = test_settings['objective_changer_id'], 
                                                                                                                  safety_object_id = test_settings['safety_id'],
                                                                                                                  reference_object = None,
                                                                                                                  load = True, 
                                                                                                                  make_ready = False, 
                                                                                                                  verbose = test_settings['verbose'])))
   
    # setup slide
    plate_holder_object = setupAutomation.setup_slide(prefs, microscopeObject = microscope_object)
    # get slide object, we will need object coordinates in order reference correction to work
    slide_object = plate_holder_object.get_slide()
     
    initializePrefs = prefs.getPrefAsMeta('InitializeMicroscope')
    initialization_dict = OrderedDict([(test_settings['focus_drive_id'], ['set_load']),
                                       (test_settings['stage_id'], []),
                                       (test_settings['objective_changer_id'], []),
                                       (test_settings['auto_focus_id'], ['no_find_surface'])])
    microscope_object.initialize_hardware(initialize_components_OrderedDict = initialization_dict, 
                                          reference_object = slide_object.get_reference_object(), 
                                          trials = 3,
                                          verbose = test_settings['verbose'])
 
    print('The following components are ready for experiment {} after microscope initialization:\n{}'.format(test_settings['experiment_standard'],
                                                                                                                microscope_object.microscope_is_ready(experiment = test_settings['experiment_standard'], 
                                                                                                                                                      component_dict = test_ready_dict, 
                                                                                                                                                      focus_drive_id = test_settings['focus_drive_id'],
                                                                                                                                                      objective_changer_id = test_settings['objective_changer_id'], 
                                                                                                                                                      safety_object_id = test_settings['safety_id'],
                                                                                                                                                      reference_object = slide_object.get_reference_object(),
                                                                                                                                                      load = True, 
                                                                                                                                                      make_ready = True, 
                                                                                                                                                      verbose = test_settings['verbose'])))

    # select test options
    if test == 'test_hardware':
        return True
    
    if test == 'test_microscope':
        return (test_microscope(sample_object = slide_object,
                                test_settings = test_settings))
    
    if test == 'test_move_sample':
        return test_move_sample(sample_object = slide_object,
                                test_settings = test_settings)
    
    if test == 'test_definite_focus':
        return (test_definite_focus(sample_object = slide_object,
                                    test_settings = test_settings))
    
    if test == 'test_parfocality':
        return (test_parfocality(sample_object = slide_object,
                                 test_settings = test_settings))
      
if __name__ == '__main__':
    # settings for tests
#     test_list=['test_hardware', 'test_microscope', 'test_move_sample', 'test_definite_focus', 'test_parfocality']
    test_list=['test_definite_focus']

    test_settings = {'camera_id': 'T-PMT',
                     'safety_id': 'LSM880_2_slide',
                     'stage_id': 'Marzhauser',
                     'focus_drive_id': 'MotorizedFocus',
                     'auto_focus_id': 'DefiniteFocus2', 
                     'objective_changer_id': '6xMotorizedNosepiece',
                     'pump_id': 'BraintreeScientific',
                     'verbose': False,
                     'experiment_standard': 'Setup_10x',
                     'experiment_10x': 'ScanWell_10x',
                     'experiment_20x': 'ScanCell_20x',
                     'experiment_100x': 'CellStack_100x',
                     'magnification_experiments': ['experiment_20x', 'experiment_10x', 'experiment_100x'],
                     'image_pos_1': (-7938, 7034, -243),
                     'image_pos_increment': (500, 500, 0),
                     'file_path': 'D:\\Winfried\\Production\\testing\\test_image.czi'}

    
    # Regularized argument parsing
    from getPath import *
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument('-p', '--preferences', help="path to the preferences file")
    args = arg_parser.parse_args()
    if args.preferences is not None:
        set_pref_file(args.preferences)


    prefs = Preferences(get_prefs_path())


    for test in test_list:
        print ('Start test of hardware for {}'.format(test))
        if test_hardware(test = test, prefs = prefs, test_settings = test_settings):
            print ('Hardware successfully tested for {}'.format(test))
        else:
            print ('Error in test hardware for {}'.format(test))
