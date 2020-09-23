'''
Created on Sep 10, 2018

Functions to test module samples using calibration slide
@author: winfriedw
'''
from samples import *
import setupAutomation

import argparse

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
    images = sample_object.acquire_images(experiment = test_settings['experiment_standard'], 
                                          cameraID = test_settings['camera_id'],
                                          filePath = None, 
                                          verbose = test_settings['verbose'])
    
    sample_object.move_delta_xyz(x = test_settings['image_pos_increment'][0], 
                                 y = 0, 
                                 z = 0, 
                                 load = False, 
                                 verbose = test_settings['verbose'])
    images = sample_object.acquire_images(experiment = test_settings['experiment_standard'], 
                                          cameraID = test_settings['camera_id'],
                                          filePath = None, 
                                          verbose = test_settings['verbose'])
    
    sample_object.move_delta_xyz(x = 0, 
                                 y = test_settings['image_pos_increment'][1], 
                                 z = 0, 
                                 load = False, 
                                 verbose = test_settings['verbose'])
    images = sample_object.acquire_images(experiment = test_settings['experiment_standard'], 
                                          cameraID = test_settings['camera_id'],
                                          filePath = None, 
                                          verbose = test_settings['verbose'])
    
    sample_object.move_delta_xyz(x = - test_settings['image_pos_increment'][0], 
                                 y = test_settings['image_pos_increment'][1], 
                                 z = 0, 
                                 load = False, 
                                 verbose = test_settings['verbose'])
    images = sample_object.acquire_images(experiment = test_settings['experiment_standard'], 
                                          cameraID = test_settings['camera_id'],
                                          filePath = None, 
                                          verbose = test_settings['verbose'])
    return True   

def test_definite_focus(sample_object, test_settings):  
    '''Test definite focus.
    
    Input:
     sample_object: object based on class ImagingSystem in module samples.py
                     sample_object has microscope object attached
     prefs: preferences as class preferences
     
    Output:
     success: True, if all tests where run
    '''            
    # get autofocus status
    print('Use auto-focus:{}'.format(sample_object.get_use_autofocus()))   
                                                         
    # switch autofocus on
    sample_object.live_mode_start(cameraID = test_settings['camera_id'], 
                                  experiment = test_settings['experiment_standard'])
    sample_object.set_use_autofocus(True)

    # find sample surface using definite focus
    sample_object.find_surface(trials = 3, 
                               verbose = test_settings['verbose'])
    
    # find focus position 
    sample_object.move_to_zero(load = False, 
                               verbose = test_settings['verbose'])
    raw_input('Please focus')
    sample_object.set_zero(x=None, y=None, z=None, 
                           verbose = test_settings['verbose'])
    sample_object.store_focus(trials = 3, 
                              verbose = test_settings['verbose'])
    sample_object.live_mode_stop(cameraID = test_settings['camera_id'], 
                                 experiment = test_settings['experiment_standard'])   
  
    test_move_sample(sample_object, test_settings) 
    
    print('Use auto-focus:{}'.format(sample_object.get_use_autofocus()))                                                   
    return True   

def test_samples(test, prefs, test_settings):
    '''Different test cases for module hardware.
    
    Input:
     test: tests to perform
             test options: 'test_move_sample', 'test_definet_focus', 'test_parfocality'
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
    
    
    # setup slide
    plate_holder_object = setupAutomation.setup_slide(prefs, microscopeObject = microscope_object)
    # get slide object, we will need object coordinates in order reference correction to work
    slide_object = plate_holder_object.get_slide()
    
    initializePrefs = prefs.getPrefAsMeta('InitializeMicroscope')
    initialization_experiment = initializePrefs.getPref('Experiment')
    microscope_object.initialize_hardware(initialize_components_OrderedDict = None, 
                                          reference_object = slide_object.get_reference_object(), 
                                          trials = 3,
                                          verbose = test_settings['verbose'])

    # select test options    
    if test == 'test_move_sample':
        return test_move_sample(sample_object = slide_object,
                                test_settings = test_settings)

    if test == 'test_definite_focus':
        return test_definite_focus(sample_object = slide_object,
                                   test_settings = test_settings)
      
if __name__ == '__main__':
    # settings for tests
    #     test_list=['test_move_sample', 'test_definite_focus', 'test_parfocality']
    test_list=['test_definite_focus']

    test_settings = {'camera_id': 'Camera1 (back)',
                     'safety_id': 'ZSD_03_slide',
                     'stage_id': 'Marzhauser',
                     'focus_drive_id': 'MotorizedFocus',
                     'auto_focus_id': 'DefiniteFocus2', 
                     'objective_changer_id': '6xMotorizedNosepiece',
                     'pump_id': 'BraintreeScientific',
                     'verbose': False,
                     'experiment_standard': 'Setup_10x',
                     'image_pos_1': (48600, 35500, 7498),
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
        if test_samples(test = test, prefs = prefs, test_settings = test_settings):
            print ('Hardware successfully tested for {}'.format(test))
        else:
            print ('Error in test hardware for {}'.format(test))
