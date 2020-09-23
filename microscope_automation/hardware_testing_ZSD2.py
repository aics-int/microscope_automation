'''
Functions to test module hardware.py on spinning disk microscope ZSD_3
Created on Sep 7, 2018

@author: winfriedw
'''

from hardware import *
import setupAutomation
from findPositions import create_output_objects_from_parent_object

import argparse
from samples_testing import test_definite_focus
from collections import OrderedDict
from pyqtgraph.Qt import QtGui
import pyqtgraph
                

def test_microscope(sample_object, test_settings):  
    '''Test of basic microscope functionality.
    
    Input:
     sample_object: object based on class ImagingSystem in module samples.py
                     sample_object has microscope object attached
     prefs: preferences as class preferences
     
    Output:
     success: True, if all tests where run
    '''            
    print('\n===================================================\nStart test_microscope\n')
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

    print ('Acquire image with and without positions list')
    image = sample_object.acquire_images(experiment = test_settings['experiment_standard'], 
                                         cameraID  = test_settings['camera_id'], 
                                         reference_object = sample_object.get_reference_object(), 
                                         filePath=None, 
                                         posList = [test_settings['image_pos_1']], 
                                         load = False, 
                                         metaDict = {}, 
                                         verbose = test_settings['verbose'])
    image = sample_object.acquire_images(experiment = test_settings['experiment_standard'], 
                                         cameraID  = test_settings['camera_id'], 
                                         reference_object = sample_object.get_reference_object(), 
                                         filePath = None, 
                                         posList = None, 
                                         load = False, 
                                         metaDict = {}, 
                                         verbose = test_settings['verbose'])
    print ('Remove all images in ZEN software')
    microscope_object.remove_images() 
    
    return(True)

def set_objective_offset(sample_object, test_settings):
    '''Set parfocality and parcentricity for objectives used in experiments.
    
    Input:
     offsetPrefs: dictionary with preferences based on preferences.yml
     plate_holder_object: plateHolderObject: object that contains all plates and all wells with sample information.
     _experiment: dictionary with keys 'Experiment', Repetitions', 'Input', 'Output'] (not used, for compatibility only)
                     from workflow with information about specific experiment
     
    Output:
     none
    '''
    microscope_object = sample_object.get_microscope()
        
    # retrieve list with experiments used to find objective offset and iterate through them
    experiments_list = test_settings['set_offset_experiments']
         
     # iterate through all experiments, each experiment should contain a different objective
    for experiment in experiments_list:        
        objective_changer_id = test_settings['objective_changer_id']
        objective_changer = microscope_object.get_microscope_object(objective_changer_id)
        objective_changer.set_init_experiment(experiment)   
        
        microscope_object.initialize_hardware(initialize_components_OrderedDict = {objective_changer_id: {'no_find_surface'}}, 
                                     reference_object = sample_object.get_reference_object(), 
                                     trials = 3,
                                     verbose = test_settings['verbose'])       
    return True

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
    print('\n===================================================\nStart test_move_sample\n')
    microscope_object = sample_object.get_microscope()
    
    x, y, z = test_settings['image_pos_1']  
    if z_pos: 
        z = z_pos    
    
    # use experiments with different objectives
    test_ready_dict = OrderedDict([(test_settings['stage_id'], []),
                                       (test_settings['focus_drive_id'], ['set_load']),
                                       (test_settings['objective_changer_id'], []),
                                       (test_settings['auto_focus_id'], ['no_find_surface'])])
    
    for experiment_type in ['experiment_10x', 'experiment_20x']:  
        microscope_object.microscope_is_ready(experiment = test_settings[experiment_type], 
                                                        component_dict = test_ready_dict, 
                                                        focus_drive_id = test_settings['focus_drive_id'], 
                                                        objective_changer_id = test_settings['objective_changer_id'], 
                                                        safety_object_id = test_settings['safety_id'],
                                                        reference_object = sample_object.get_reference_object(),
                                                        load = False, 
                                                        make_ready = True, 
                                                        verbose = test_settings['verbose']) 
        print ('Move sample to ({}, {}, {}).'.format(x, y, z))
        sample_object.move_to_abs_position(x, y, z,
                                           load = False, 
                                           verbose = test_settings['verbose'])
        image = microscope_object.execute_experiment(experiment = test_settings[experiment_type], 
                                             file_path = None, 
                                             z_start = 'F',
                                             interactive = True)
        
        print ('get_abs_position returns: {}'.format(sample_object.get_abs_position(stage_id = test_settings['stage_id'], 
                                                                                    focus_id = test_settings['focus_drive_id'])))
        print ('get_pos_from_abs_pos returns: {}'.format(sample_object.get_pos_from_abs_pos(verbose = test_settings['verbose'])))
    
        
        print ('\nMove sample {} um in x.'.format(test_settings['image_pos_increment'][0]))
        sample_object.move_delta_xyz(x = test_settings['image_pos_increment'][0], 
                                     y = 0, 
                                     z = 0, 
                                     load = False, 
                                     verbose = test_settings['verbose'])
        image = microscope_object.execute_experiment(experiment = test_settings[experiment_type], 
                                             file_path = None, 
                                             z_start = 'F',
                                             interactive = True)
        print ('get_abs_position returns: {}'.format(sample_object.get_abs_position(stage_id = test_settings['stage_id'], 
                                                                                    focus_id = test_settings['focus_drive_id'])))
        print ('get_pos_from_abs_pos returns: {}'.format(sample_object.get_pos_from_abs_pos(verbose = test_settings['verbose'])))
    
        
        print ('\nMove sample {} um in y.'.format(test_settings['image_pos_increment'][1]))
        sample_object.move_delta_xyz(x = 0, 
                                     y = test_settings['image_pos_increment'][1], 
                                     z = 0, 
                                     load = False, 
                                     verbose = test_settings['verbose'])
        image = microscope_object.execute_experiment(experiment = test_settings[experiment_type], 
                                             file_path = None, 
                                             z_start = 'F',
                                             interactive = True)
        print ('get_abs_position returns: {}'.format(sample_object.get_abs_position(stage_id = test_settings['stage_id'], 
                                                                                    focus_id = test_settings['focus_drive_id'])))
        print ('get_pos_from_abs_pos returns: {}'.format(sample_object.get_pos_from_abs_pos(verbose = test_settings['verbose'])))
    
        
        print ('\nMove sample {} um in x and {} um in y.'.format(test_settings['image_pos_increment'][0], test_settings['image_pos_increment'][1]))
        sample_object.move_delta_xyz(x = - test_settings['image_pos_increment'][0], 
                                     y = test_settings['image_pos_increment'][1], 
                                     z = 0, 
                                     load = False, 
                                     verbose = test_settings['verbose'])
        image = microscope_object.execute_experiment(experiment = test_settings[experiment_type], 
                                             file_path = None, 
                                             z_start = 'F',
                                             interactive = True)
        
        microscope_object.live_mode(camera_id = test_settings['camera_id'], 
                                    experiment = test_settings['experiment_standard'], 
                                    live = False)
        print ('get_abs_position returns: {}'.format(sample_object.get_abs_position(stage_id = test_settings['stage_id'], 
                                                                                    focus_id = test_settings['focus_drive_id'])))
        print ('get_pos_from_abs_pos returns: {}'.format(sample_object.get_pos_from_abs_pos(verbose = test_settings['verbose'])))

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
    print('\n===================================================\nStart test_definite_focus\n')
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
    raw_input('Please focus')
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
    raw_input('Please focus')
    focus_info = microscope_object.get_information([focus_drive_id])[focus_drive_id]
    z_pos = focus_info['focality_corrected'] 
    microscope_object.live_mode(camera_id = test_settings['camera_id'], 
                                experiment = test_settings['experiment_standard'], 
                                live = False)   
  
    for i in range(3):
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
    print('\n===================================================\nStart test_parfocality\n')
    success = True
    # all hardware functionality should only be accessed through object of class Microscope
    microscope_object = sample_object.get_microscope()
    # test with autofocus switched on
    microscope_object.set_microscope({test_settings['auto_focus_id']: {'use_auto_focus': True}})

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
        print('Microscope is ready for experiment {}'.format(experiment_label))                                                                                                                                                            

    # mark positions with different magnifications and image postions
    for experiment_label in test_settings['magnification_experiments']:
        # create several positions
        pos_list = []
        for pos_number in range(2):
            microscope_object.live_mode(camera_id = test_settings['camera_id'], 
                                        experiment = test_settings[experiment_label], 
                                        live = True)
            raw_input('Please move to position {}'.format(pos_number))
            pos_list.append(sample_object.get_pos_from_abs_pos(verbose = test_settings['verbose']))
            
        # image all marked positions with all magnification experiments
        for pos_number, pos in enumerate(pos_list):
            for experiment_label in test_settings['magnification_experiments']:
                if sample_object.microscope_is_ready(experiment = test_settings[experiment_label], 
                                                     reference_object = sample_object.get_reference_object(),
                                                     load = False, 
                                                     make_ready = True, 
                                                     trials = 3, 
                                                     verbose = test_settings['verbose']):
                    sample_object.move_to_xyz(*pos,
                                              verbose = test_settings['verbose'])
                else:
                    success = False
                
                images = sample_object.acquire_images(experiment = test_settings[experiment_label], 
                                                     cameraID = test_settings['camera_id'],
                                                     reference_object = None,
                                                     filePath = test_settings['file_path'], 
                                                     posList = None,
                                                     load = False, 
                                                     metaDict = None, 
                                                     verbose = test_settings['verbose'])
                raw_input('Was position {} with coordinates {} imaged correct with experiment {}?'.format(pos_number, pos, experiment_label))
    return success

def test_set_zero(sample_object, test_settings, image_settings):  
    '''Test moving to multiple positions and switching objective.
       Use offsets for objectives from preferences file.
    
    Input:
     sample_object: object based on class ImagingSystem in module samples.py
                     sample_object has microscope object attached
     test_settings: settings for testing as defined in __main__
     image_settings: settings from preferences file
     
    Output:
     success: True, if all tests where run
    '''  
    print('\n===================================================\nStart test_set_zero\n')
    # test with autofocus switched on/off    
    microscope_object = sample_object.get_microscope()
    microscope_object.set_microscope({test_settings['auto_focus_id']: {'use_auto_focus': False}})
    
    # create several cell objects
    microscope_object.live_mode(camera_id = test_settings['camera_id'], 
                                experiment = test_settings['tile_experiment'], 
                                live = True)
    
    # set zero position for slide
    # get actual z-position for slide and set as new z_zero position for slide
    sample_object.microscope_is_ready(experiment = test_settings['tile_experiment'], 
                                                     reference_object = sample_object.get_reference_object(),
                                                     load = False, 
                                                     make_ready = True, 
                                                     trials = 3, 
                                                     verbose = test_settings['verbose'])
    
    raw_input('Please focus to set z-zero for slide')
    _x, _y, z_new = sample_object.get_container().get_pos_from_abs_pos(verbose = test_settings['verbose'])
    sample_object.update_zero(z = z_new, 
                              verbose = test_settings['verbose'])
    print('z-zero for slide: {}'.format(sample_object.get_zero()))
    
    # We have to call app = QtGui.QApplication([]) and than pass app to the function call
    # If we call QtGui.QApplication([]) in the function call, formlayout forms later will disappear
    app = QtGui.QApplication([])
    samples_list = []
    
    # collect image positions at multiple locations.
    # That simulates multi-well imaging to define cells
    for pos in range(2):
        microscope_object.live_mode(camera_id = test_settings['camera_id'], 
                                experiment = test_settings['tile_experiment'], 
                                live = True)
        
        sample_object.move_to_zero()
        sample_object.microscope_is_ready(experiment = test_settings['tile_experiment'], 
                                                 reference_object = sample_object.get_reference_object(),
                                                 load = False, 
                                                 make_ready = True, 
                                                 trials = 3, 
                                                 verbose = test_settings['verbose'])
        print('\nZero position of slide: {}'.format(sample_object.get_zero()))
        raw_input('Please select center of tile scan')
        tile_image = sample_object.acquire_images(experiment = test_settings['tile_experiment'], 
                                                 cameraID = test_settings['camera_id'],
                                                 reference_object = None,
                                                 filePath = test_settings['file_path'], 
                                                 posList = None,
                                                 load = False, 
                                                 metaDict = None, 
                                                 verbose = test_settings['verbose'])
        
        print('aics_imageAbsPosZ(focality_corrected): {}'.format(tile_image[0].get_meta('aics_imageAbsPosZ(focality_corrected)')))
        print('aics_imageAbsPosZ(auto_focus_offset): {}'.format(tile_image[0].get_meta('aics_imageAbsPosZ(auto_focus_offset)')))
        print('aics_imageObjectPosZ: {}'.format(tile_image[0].get_meta('aics_imageObjectPosZ')))
        print('aics_imageAbsPosZ(z_focus_offset): {}'.format(tile_image[0].get_meta('aics_imageAbsPosZ(z_focus_offset)')))
        print('aics_cellInColonyPosZ: {}'.format(tile_image[0].get_meta('aics_cellInColonyPosZ')))
        print('aics_imageAbsPosZ(focality_drift_corrected): {}'.format(tile_image[0].get_meta('aics_imageAbsPosZ(focality_drift_corrected)')))
        print('aics_imageAbsPosZ: {}'.format(tile_image[0].get_meta('aics_imageAbsPosZ')))
        
        print('\naics_imageObjectPos*: ({}, {})'.format(tile_image[0].get_meta('aics_imageObjectPosX'), tile_image[0].get_meta('aics_imageObjectPosY')))
        print('aics_imageAbsPos*(centricity_corrected): ({}, {})'.format(tile_image[0].get_meta('aics_imageAbsPosX(centricity_corrected)'), tile_image[0].get_meta('aics_imageAbsPosY(centricity_corrected)')))
        print('aics_cellInColonyPos*: ({}, {})'.format(tile_image[0].get_meta('aics_cellInColonyPosX'), tile_image[0].get_meta('aics_cellInColonyPosY')))
        print('aics_imageAbsPos*: ({}, {})'.format(tile_image[0].get_meta('aics_imageAbsPosX'), tile_image[0].get_meta('aics_imageAbsPosY')))
            
        tile_image = sample_object.get_microscope().load_image(tile_image[0], getMeta=True)  # loads the image & metadata
        
        # We have to call app = QtGui.QApplication([]) and than pass app to the function call
        # If we call QtGui.QApplication([]) in the fuction call, formlayout forms later will disappear
        sample_list_for_locaton = create_output_objects_from_parent_object(find_type = 'Interactive',
                                                                           sample_object = sample_object,
                                                                           imaging_settings = None,
                                                                           image = tile_image,
                                                                           output_class = 'Cell', 
                                                                           app = app,
                                                                           offset = (0, 0, 0))
        samples_list.extend(sample_list_for_locaton[0])
         
    # use experiments with different objectives
    for experiment_type in test_settings['magnification_experiments']:
        experiment = test_settings[experiment_type]
    
        # switch on live mode, that will switch objective   
        microscope_object.live_mode(camera_id = test_settings['camera_id'], 
                                experiment = experiment, 
                                live = True)
   
        sample_object.microscope_is_ready(experiment = test_settings[experiment_type], 
                                                     reference_object = sample_object.get_reference_object(),
                                                     load = False, 
                                                     make_ready = True, 
                                                     trials = 3, 
                                                     verbose = test_settings['verbose'])

        # set zero position for slide
        raw_input('Please focus on slide surface')
        
        # get actual z-position for slide and set as new z_zero position for slide
        _x, _y, z_new = sample_object.get_container().get_pos_from_abs_pos(verbose = test_settings['verbose'])
        sample_object.update_zero(z = z_new, 
                                  verbose = test_settings['verbose'])
        print('z-zero for slide: {}'.format(sample_object.get_zero()))
        
        # step through all samples and image them
        for cell_object in samples_list:
            microscope_object.live_mode(camera_id = test_settings['camera_id'], 
                                experiment = experiment, 
                                live = True)
            posList = cell_object.get_tile_positions_list(image_settings, 
                                                            tile_type = 'NoTiling', 
                                                            verbose = test_settings['verbose'])
            print('\nImaging postion in object coordinates: {}'.format(cell_object.get_zero()))
            print('Imaging position in abs coordinates: {}'.format(posList))
            images = cell_object.acquire_images(experiment = experiment, 
                                                 cameraID = test_settings['camera_id'],
                                                 reference_object = None,
                                                 filePath = test_settings['file_path'], 
                                                 posList = posList,
                                                 load = False, 
                                                 metaDict = None, 
                                                 verbose = test_settings['verbose'])
            
            print('\naics_imageAbsPosZ(focality_corrected): {}'.format(images[0].get_meta('aics_imageAbsPosZ(focality_corrected)')))
            print('aics_imageAbsPosZ(auto_focus_offset): {}'.format(images[0].get_meta('aics_imageAbsPosZ(auto_focus_offset)')))
            print('aics_imageObjectPosZ: {}'.format(images[0].get_meta('aics_imageObjectPosZ')))
            print('aics_imageAbsPosZ(z_focus_offset): {}'.format(images[0].get_meta('aics_imageAbsPosZ(z_focus_offset)')))
            print('aics_cellInColonyPosZ: {}'.format(images[0].get_meta('aics_cellInColonyPosZ')))
            print('aics_imageAbsPosZ(focality_drift_corrected): {}'.format(images[0].get_meta('aics_imageAbsPosZ(focality_drift_corrected)')))
            print('aics_imageAbsPosZ: {}'.format(images[0].get_meta('aics_imageAbsPosZ')))
            print('aics_cellInColonyPosZ: {}'.format(images[0].get_meta('aics_cellInColonyPosZ')))
            
            print('\naics_imageObjectPos*: ({}, {})'.format(images[0].get_meta('aics_imageObjectPosX'), images[0].get_meta('aics_imageObjectPosY')))
            print('aics_imageAbsPos*(centricity_corrected): ({}, {})'.format(images[0].get_meta('aics_imageAbsPosX(centricity_corrected)'), images[0].get_meta('aics_imageAbsPosY(centricity_corrected)')))
            print('aics_cellInColonyPos*: ({}, {})'.format(images[0].get_meta('aics_cellInColonyPosX'), images[0].get_meta('aics_cellInColonyPosY')))
            print('aics_imageAbsPos*: ({}, {})'.format(images[0].get_meta('aics_imageAbsPosX'), images[0].get_meta('aics_imageAbsPosY')))

            print('\nFocus position after imaging: {}'.format(microscope_object.get_information(components_list = ['MotorizedFocus'])))
            print('Stage position after imaging: {}'.format(microscope_object.get_information(components_list = ['Marzhauser'])))
    return True

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
    print('\n===================================================\nStart test_hardware\n')
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
    
    if test == 'set_objective_offset':
        return(set_objective_offset(sample_object = slide_object,
                                    test_settings = test_settings))
                                    
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

    if test == 'test_set_zero':
        image_settings = prefs.getPrefAsMeta('ScanCells')
        return (test_set_zero(sample_object = slide_object,
                                 test_settings = test_settings,
                                 image_settings = image_settings))      
if __name__ == '__main__':
    # settings for tests
#     test_list=['test_hardware', 'set_objective_offset', 'test_microscope', 'test_move_sample', 'test_definite_focus', 'test_parfocality', 'test_set_zero']
    test_list=['test_set_zero']

    test_settings = {'camera_id': 'Camera2 (Back)',
                     'safety_id': 'ZSD_02_slide',
                     'stage_id': 'Marzhauser',
                     'focus_drive_id': 'MotorizedFocus',
                     'auto_focus_id': 'DefiniteFocus2', 
                     'objective_changer_id': '6xMotorizedNosepiece',
                     'pump_id': 'BraintreeScientific',
                     'verbose': False,
                     'experiment_standard': 'Setup_10x',
                     'experiment_10x': 'Setup_10x',
                     'experiment_20x': 'ScanCell_20x',
                     'experiment_100x': 'CellStack_100x',
                     'tile_experiment': 'ScanWell_10x',
                     'set_offset_experiments': ['Setup_10x'],
#                      'magnification_experiments': ['experiment_20x', 'experiment_10x', 'experiment_100x'],
                     'magnification_experiments': ['experiment_10x'],
                     'image_pos_1': (50286, 37280, 6931),
                     'image_pos_increment': (50, 50, 0),
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
