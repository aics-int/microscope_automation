'''
Classes to describe and control hardware. Bridge between automation software and hardware specific implementations.
Created on Jul 7, 2016

@author: winfriedw
'''


import os
import matplotlib
# matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.path import Path as mpl_path
import matplotlib.patches as patches
from matplotlib import cm
import math
import collections
import datetime
import time
# import modules from project MicroscopeAutomation
# modules to connect to microscope hardware are imported in class ControlSoftware
# from .imageAICS import ImageAICS
# from . import automationMessagesFormLayout as message
# from .automationExceptions import AutomationError, HardwareError, CrashDangerError, AutofocusError, AutofocusNotSetError, AutofocusObjectiveChangedError, ObjectiveNotDefinedError, FileExistsError, LoadNotDefinedError
from imageAICS import ImageAICS
import automationMessagesFormLayout as message
from automationExceptions import AutomationError, \
                                 HardwareError, CrashDangerError, \
                                 AutofocusError, AutofocusNotSetError, AutofocusObjectiveChangedError, AutofocusNoReferenceObjectError, \
                                 ObjectiveNotDefinedError, FileExistsError, \
                                 LoadNotDefinedError, \
                                 ExperimentNotExistError,  \
                                 HardwareNotReadyError
import experimentInfo

# setup logging
import logging
import testExperiment
import automationMessagesFormLayout
logger = logging
import inspect
logging.basicConfig(level = logging.WARNING)
logging.debug('Switched on debug level logging in module "{}'.format(__name__))

# keep track of xPos, yPos, and zPos of stage and focus for debugging purposes

def log_method(self, methodName = None):
    '''Log name of module and method if logging level is DEBUG.
    
    Input:
     methodName: string with  name of method
     
    Output:
     none
    '''
    logging.debug('\nlog_method------------------------------')
    logging.debug("Calling '{}' in module '{}'".format(self.__class__.__name__, self.__module__))
    logging.debug('Method: {}'.format(methodName))
    logging.debug('Docstring: {}'.format(inspect.getdoc(self)))

xPos = 0
yPos = 0
zPos = 0

def log_message(message, methodName = None):
    '''Shows message if logging level is INFO.
    
    Input:
     message: string with message
     methodName: string with  name of method
     
    Output:
     none
    '''
    logging.info('\nlog_message------------------------------')
    logging.info("Message from method '{}':\n".format(methodName))
    logging.info(message)

def log_warning(message, methodName = None):
    '''Shows message if logging level is WARNING.
    
    Input:
     message: string with message
     methodName: string with  name of method
     
    Output:
     none
    '''
    logging.warning('\nlog_warning------------------------------')
    logging.warning("Message from method '{}':\n".format(methodName))
    logging.warning(message)


################################################################################################
            
class Microscope(object):
    '''Collection class to describe and operate Microscope
    '''
    def __init__(self, name = None, controlSoftwareObject = None, experiments_path = None, safeties = None, microscope_components = None):
        '''Describe and operate Microscope
        
        Input:         
         name: optional string with microscope name
         controlSoftwareObject: object for software connection to microscope, typically created with class ControlSoftware
         experiments_path: path to folder with microscope software defined experiments. Path does not include experiment.
         safeties: optional list with safety objects
         microscope_components: optional list with component objects
         
        Output:
         none
        '''
        log_method(self, '__init__')

        self.name = name
        
        # add control software object (only one is allowed) to Microscope
        self.add_control_software(controlSoftwareObject)
                
        # add components to microscope
        self.microscope_components_OrderedDict = collections.OrderedDict()
        self.add_microscope_object(safeties) 
        self.add_microscope_object(microscope_components)  
        
        # track last used experiment for test if microscope is ready
        self.experiment_path = experiments_path
        self.last_experiment = None
        # Use objective position because objectives are named differently inside ZEN software and experiment files
        # A call like objRevolver.ActualPositionName returns the objective name.
        # In the experiment files objectives are identified by their order number.
        # Position would allow identical objectives at different positions
        self.last_objective_position = None
        self.objective_ready_dict = {}

    def recover_hardware(self, error):
        '''Execute hardwareFunction and try to recover from failure.
        
        Input:
         autofocusFunction: function that that interacts with microscope autofocus
         args: arguments for autofocusFunction
        
        Output:
         returnValue: return value from autofocusFunction
         
        autofocusFunction has to throw exception AutofocusError in error case
        '''

        if isinstance(error, AutofocusError):
            return_dialog = error.error_dialog()
            if return_dialog == 1:
                # use ['no_find_surface'] for action_list to disable 'find_surface' during auto-focus initialization
                self.initialize_hardware(initialize_components_OrderedDict = {error.error_component.get_id(): ['no_find_surface']}, reference_object = error.focusReferenceObj, verbose = False)
#                 self.reference_position(reference_object = error.focusReferenceObj, find_surface = False, verbose = False)
            return return_dialog
        if isinstance(error, LoadNotDefinedError):
            return_dialog = error.error_dialog()
            if return_dialog == 1:
                self.initialize_hardware(initialize_components_OrderedDict = {error.error_component.get_id(): ['set_load']}, reference_object = None, verbose = False)            
            return return_dialog
        if isinstance(error, CrashDangerError):
            return error.error_dialog('Move stage to save area.')
        if isinstance(error, HardwareError):
            return error.error_dialog()

    def create_experiment_path(self, experiment):
        '''Creates complete path to experiment.
        Input:
         experiment: string with name of experiment (with or w/o extension .czexp)
         
        Output:
         experiment_path: path to experiment
         
        Raises exception if experiment does not exist
        '''
        # For Zen Black implementation, there is no experiment path, hence it is left as "NA"
        if self.experiment_path == 'NA':
            return self.experiment_path
        # check if experiment has proper extension
        extension = os.path.splitext(experiment)[1]
        if extension != '.czexp':
            experiment = experiment + '.czexp'
        experiment_path = os.path.normpath(os.path.join(self.experiment_path, experiment))
        if not os.path.exists(experiment_path):
            raise ExperimentNotExistError('Could not create experiment path {}.'.format(experiment_path), experiment)
        return experiment_path
    
    def set_objective_is_ready(self, objective_info, reference_object = None):
        '''Create list with all objective positions initialized for reference_object.
        
        Input:
         objective_info: information for objective that was initialized
         reference_object: reference object (e.g. well) objective was initialized for
         
        Output:
         none
        '''
        # Each dictionary entry is a set of objective positions
        # create set if dictionary is empty, otherwise add new position, if position is already set, nothing will change
        if self.objective_ready_dict:
            self.objective_ready_dict[reference_object.get_name()].add(objective_info['position'])
        else:
            objective_positions = set()
            objective_positions.add(objective_info['position'])
            self.objective_ready_dict[reference_object.get_name()] = objective_positions
        
    def get_objective_is_ready(self, objective_position, reference_object = None):
        '''Test if objective was initialized.
        
        Input:
         objective_position: position of objective in objective changer
         reference_object: reference object (e.g. well) objective was initialized for
         
        Output:
         objective_is_ready: True, if offset for objective was set
        '''
        try:
            objective_is_ready = objective_position in self.objective_ready_dict[reference_object.get_name()]
            return objective_is_ready
        except:
            return False
        
        
    def change_objective(self, experiment, objective_changer_object, trials = 3):
        '''Switch to objective used in experiment.
        
        Input:
         experiment: string with name of experiment as defined in microscope software
         objective_changer_object: object for objective changer objective is mounted to
         trials: number of times system tries to recover
         
        Output:
         objective_name: name of objective in new position
        '''
        experiment_path = self.create_experiment_path(experiment)
        experiment_object = Experiment(experiment_path, experiment)
        communication_object = self.get_control_software().connection
        
        try:
            experiment_objective_pos = experiment_object.get_objective_position()
        except:
            print('Could not find objective for experiment {}'.format(experiment))
            raise()
        
        trials_count = trials
        success = False
        load = True
        while not success and trials_count >=0:           
            try:
                objective_name = objective_changer_object.change_position(experiment_objective_pos, 
                                                                          communication_object, 
                                                                          load = load)
                success = True
            except LoadNotDefinedError as error:
                if self.recover_hardware(error) == -1:
                    load = False
            except AutomationError as error:                
                self.recover_hardware(error)
            if trials_count == 0:
                raise(error)
            trials_count = trials_count - 1        
        return objective_name

    def _make_ready(self, is_ready, make_ready, component_id, action_list = [], reference_object = None, trials = 3, verbose = True):
        '''Check if component is ready and initialize if requested.
        
        Input:
         is_ready: Flag if component is initialized
         make_ready: if True, initialize component if not ready
         component_id: string id for component to initialize
         action_list: list with component specific instructions for initialization
         reference_object: object used to set parfocality and parcentricity
         trials: maximum number of attempts to initialize hardware. Gives user the option to interact with microscope hardware.
         verbose: if True print debug information (Default = True)
         
        Output:
         is_ready: True if initialization was sucessful
        '''
        if not is_ready and make_ready:
            try:
                initialize_components_OrderedDict = {component_id: action_list}
                self.initialize_hardware(initialize_components_OrderedDict, reference_object, trials, verbose)
                return True
            except:
                return False
        else:
            return True
            
    def _focus_drive_is_ready(self, focus_drive_object, action_list, reference_object = None, trials = 3, make_ready = True, verbose = True):
        '''Test if focus drive is ready and optionally initialize it
        
        Input:
         focus_drive_object: object of class AutoFocus
         action_list: list with component specific instructions for initialization
         reference_object: object used to set parfocality and parcentricity
         trials: maximum number of attempts to initialize hardware. Gives user the option to interact with microscope hardware.
         make_ready: if True, make attempt to initialize auto-focus if necessary (Default: True)
         verbose: if True print debug information (Default = True)
         
        Output:
         is_ready: True if ready
        '''
        # test if object is of class FocusDrive
        if type(focus_drive_object) is not FocusDrive:
            raise TypeError('Object not of type FocusDrive in _focus_is_ready')
        
        focus_drive_id = focus_drive_object.get_id()
        focus_drive_info = self.get_information([focus_drive_id])[focus_drive_id]
        
        is_ready = True
        
        if 'set_load' in action_list:
            is_ready = focus_drive_info['load_position'] is not None
        
        if 'set_work' in action_list:
            is_ready = focus_drive_info['work_position'] is not None and is_ready
               
        # Initialize objective changer
        is_ready = self._make_ready(is_ready, 
                                    make_ready, 
                                    focus_drive_id,
                                    action_list = action_list, 
                                    reference_object = reference_object, 
                                    trials = trials, 
                                    verbose = verbose)
        return is_ready

    def _objective_changer_is_ready(self, objective_changer_object, objective_position, action_list = [], reference_object = None, trials = 3, make_ready = True, verbose = True):
        '''Test if objective changer is ready and optionally initialize it
        
        Input:
         objective_changer_object: object of class ObjectiveChanger
         objective_position: position of objective that will be used for experiment
         action_list: list with item 'set_reference'. If empty no action.
         reference_object: object used to set parfocality and parcentricity
         trials: maximum number of attempts to initialize hardware. Gives user the option to interact with microscope hardware.
         make_ready: if True, make attempt to initialize auto-focus if necessary (Default: True)
         verbose: if True print debug information (Default = True)
         
        Output:
         is_ready: True if ready
        '''
        # test if object is of class ObjectiveChanger
        if type(objective_changer_object) is not ObjectiveChanger:
            raise TypeError('Object not of type ObjectiveChanger in _objective_changer_is_ready')
        
        # test if stage position is in safe area
        objective_changer_object_id = objective_changer_object.get_id()
        
        is_ready = self.get_objective_is_ready(objective_position, reference_object = reference_object)
        
        # Initialize objective changer
        is_ready = self._make_ready(is_ready, 
                                    make_ready, 
                                    objective_changer_object_id,
                                    action_list = action_list, 
                                    reference_object = reference_object, 
                                    trials = trials, 
                                    verbose = verbose)
        return is_ready
    
    def _stage_is_ready(self, stage_object, focus_object, safety_object, reference_object = None, trials = 3, make_ready = True, verbose = True):
        '''Test if stage is ready and optionally initialize it
        
        Input:
         stage_object: object of class Stage
         focus_object: object of class FocusDrive
         safety_object: object of class Safety
         reference_object: object used to set parfocality and parcentricity
         trials: maximum number of attempts to initialize hardware. Gives user the option to interact with microscope hardware.
         make_ready: if True, make attempt to initialize auto-focus if necessary (Default: True)
         verbose: if True print debug information (Default = True)
         
        Output:
         is_ready: True if ready
        '''
        # test if object is of class Stage
        if type(stage_object) is not Stage:
            raise TypeError('Object not of type Stage in _stage_is_ready')
        
        # test if stage position is in safe area
        stage_id = stage_object.get_id()
        focus_id = focus_object.get_id()
        
        x, y = self.get_information([stage_id])[stage_id]['absolute']
        z = self.get_information([focus_id])[focus_id]['absolute']
        is_ready = safety_object.is_save_position(x, y, z, save_area_id = 'Compound')
        
        # Initialize auto-focus
        is_ready = self._make_ready(is_ready, 
                                    make_ready, 
                                    stage_id,
                                    action_list = [], 
                                    reference_object = reference_object, 
                                    trials = trials, 
                                    verbose = verbose)
        return is_ready

    def _auto_focus_is_ready(self, auto_focus_object, experiment_object, action_list, objective_changer_object, reference_object = None, load = True, trials = 3, make_ready = True, verbose = True):
        '''Test if auto-focus is ready and optionally initialize it
        
        Input:
         auto_focus_object: object of class AutoFocus
         experiment_object: object of type experiment to test
         action_list: list with component specific instructions for initialization
         objective_changer_object: object of class ObjectiveChanger
         reference_object: object used to set parfocality and parcentricity
         load: if True, move objective to load position before any stage movement
         trials: maximum number of attempts to initialize hardware. Gives user the option to interact with microscope hardware.
         make_ready: if True, make attempt to initialize auto-focus if necessary (Default: True)
         verbose: if True print debug information (Default = True)
         
        Output:
         is_ready: True if ready
        '''
        is_ready = True
        if action_list:
            # test if object is of class AutoFocus
            if type(auto_focus_object) is not AutoFocus:
                raise TypeError('Object not of type AutoFocus in _auto_focus_is_ready')
            
            # find objective position that will be used for experiment
            try:
                objective_position = experiment_object.get_objective_position()
            except:
                print('Could not find objective for experiment {}'.format(experiment_object.experiment_name))
                raise
    
            # if objective will be changed auto-focus has to be set new
            if objective_position != self.last_objective_position:
                is_ready = False
            
            # check if auto-focus hardware is ready, e.g. autofocus was set
            if not auto_focus_object.get_autofocus_ready(communication_object = self.get_control_software().connection):
                is_ready = False
            
            # Initialize auto-focus
            if not is_ready and make_ready:
                communication_object = self.get_control_software().connection
                if objective_position != self.last_objective_position:
                    try:
                        objective_changer_object.change_position(position = objective_position, 
                                                                 communication_object = communication_object, 
                                                                 load = load)
                    except:
                        return False
                try:
                    initialize_components_OrderedDict = {auto_focus_object.get_id(): action_list}
                    self.initialize_hardware(initialize_components_OrderedDict, reference_object, trials, verbose)
                    is_ready = True
                except:
                    return False
        return is_ready
    
    def microscope_is_ready(self, experiment, component_dict, focus_drive_id, objective_changer_id, safety_object_id, reference_object = None, load = True, make_ready = True, trials = 3, verbose = True):
        '''Check if microscope is ready and setup up for data acquisition.
         
        Input:
         experiment: string with name of experiment as defined in microscope software
         compenent_dict: dictionary with component_id as key and list of potential actions
         focus_drive_id: string id for focus drive
         objective_changer_id: string id for objective changer parfocality and parcentricity has to be calibrated
         safety_object_id: string id for safety area
         reference_object: object used to set parfocality and parcentricity
         load: move objective into load position before moving stage
         make_ready: if True, make attempt to ready microscope, e.g. setup autofocus (Default: True)
         trials: maximum number of attempt to initialize microscope. Will allow user to make adjustments on microscope. (Default: 3)
         verbose: print debug messages (Default: True)
                    
        Output:
         ready: True if microscope is ready for use, False if not 
        '''
        # find objective position that will be used for experiment
        experiment_path = self.create_experiment_path(experiment)
        experiment_object = Experiment(experiment_path, experiment, self)
        
        try:
            objective_position = experiment_object.get_objective_position()
        except:
            print('Could not find objective for experiment {}'.format(experiment))
            raise
        
        # get objects for components that are used for initializations
        focus_object = self.get_microscope_object(focus_drive_id)
        objective_changer_object = self.get_microscope_object(objective_changer_id)
        safety_object = self.get_microscope_object(safety_object_id)
        current_init_experiment_dict = {}
        communication_object = self.get_control_software().connection

        # Set the initialize experiments to the experiment being executed.
        # Reason for doing them in a separate loop - To make sure that all the init _experiments are set
        # before the components are initialized individually. In some cases the components are intialized
        # indirectly through other components (eg. DF can be initialized in objectiveChanger if it fails
        # and goes to recovery). In that case the component should have the correct init_experiment.
        for component_id, action in component_dict.iteritems():
            component = self.get_microscope_object(component_id)
            # Save the original init_experiments and restore them after the specific initialization is done
            current_init_experiment_dict[component_id] = component.get_init_experiment(communication_object)
            self.get_microscope_object(component_id).set_init_experiment(experiment)

        is_ready = {}
        for component_id, action in component_dict.iteritems():
            component = self.get_microscope_object(component_id)

            # use type and not isinstance because we want to exclude subclasses
            if type(component) is Stage:
                if self._stage_is_ready(stage_object = component, 
                                        focus_object = focus_object,
                                        safety_object = safety_object, 
                                        reference_object = reference_object, 
                                        trials = trials, 
                                        make_ready = make_ready, 
                                        verbose = verbose):
                    is_ready[component_id] = True
                else:
                    is_ready[component_id] = False
                    
            if type(component) is ObjectiveChanger:
                if self._objective_changer_is_ready(objective_changer_object = component, 
                                                    objective_position = objective_position,
                                                    action_list = action,
                                                    reference_object = reference_object, 
                                                    trials = trials, 
                                                    make_ready = make_ready, 
                                                    verbose = verbose):
                    is_ready[component_id] = True
                else:
                    is_ready[component_id] = False

            if type(component) is FocusDrive:
                if self._focus_drive_is_ready(focus_drive_object = component, 
                                              action_list = action,
                                              reference_object = reference_object, 
                                              trials = trials, 
                                              make_ready = make_ready, 
                                              verbose = verbose):
                    is_ready[component_id] = True
                else:
                    is_ready[component_id] = False
                    
            if type(component) is AutoFocus:
                if self._auto_focus_is_ready(auto_focus_object = component, 
                                             experiment_object = experiment_object, 
                                             action_list = action,
                                             objective_changer_object = objective_changer_object,
                                             reference_object = reference_object, 
                                             load = load,
                                             trials = trials, 
                                             make_ready = make_ready, 
                                             verbose = verbose):
                    is_ready[component_id] = True
                else:
                    is_ready[component_id] = False

            # set experiment for initializations back to initial experiment
            component.set_init_experiment(current_init_experiment_dict[component_id])
        is_ready['Microscope'] = all(is_ready.values())
        return is_ready
    
    def stop_microscope(self):
        '''Stop Microscope immediately in emergency situation'''
        log_method(self, 'stop_microscope')
        
        self.microscope.stop()
        
        logger.info('Microscope stopped')

    def add_control_software(self, controlSoftwareObject):
        '''add object that connects this code to the  vendor specific microscope control code to Microscope.
         
        Input:
         controlSoftwareObject: single object connecting to vendor software
          
        Output:
         none
        '''
        log_method(self, 'add_control_software')
        self.__control_software = controlSoftwareObject

    def get_control_software(self):
        '''Returns object that connects this code to the  vendor specific microscope control code to Microscope.
         
        Input:
         none
         
        Output:
         controlSoftwareObject: single object connecting to vendor software

        '''
        log_method(self, 'add_control_software')
        return self.__control_software


    def add_microscope_object(self, component_objects):
        '''Add component to microscope.
        
        Input:
         component_objects: object of a component class (e.g. Stage, Camera) or list of component classes
         
        Output:
         none
        '''
        if not isinstance(component_objects, list):
            component_objects = [component_objects]
            
        for component_object in component_objects:
            if isinstance(component_object, MicroscopeComponent):
                self.microscope_components_OrderedDict[component_object.get_id()] = component_object
                # attach microscope to component to let component know to what microscope it belongs
                component_object.microscope = self

    def get_microscope_object(self, component_id):
        '''Get component of microscope.
        
        Input:
         component_id: Unique sting id for microscope component
        Output:
         component_object: object of a component class (e.g. Stage, Camera) or list of component classes
         '''
        return self.microscope_components_OrderedDict[component_id]
        

    def setup_microscope_for_initialization(self, component_object, experiment = None, before_initialization = True):
        '''Setup microscope before initialization of individual components
        
        Input:
         component_object: instance of component class
         experiment: Name of experiment setting in ZEN blue used for microscope initialization (e.g. used for live mode)
         before_initialization: if True setup microscope, if False reset
         
        Output:
         None
         
        Method starts and stops live image mode
        '''
        if component_object.use_live_mode:
            if experiment is None:
                experiment = component_object.get_init_experiment()
            # record status of live mode to keep camera on after initialization if it was on
            if before_initialization:
                self.live_mode_status = self.get_information(components_list = [component_object.default_camera])[component_object.default_camera]['live']

            self.live_mode(camera_id = component_object.default_camera, 
                            experiment = experiment,
                            live = before_initialization or self.live_mode_status)
            self.last_experiment = experiment 
                
                
    def initialize_hardware(self, initialize_components_OrderedDict = None, reference_object = None, trials = 3, verbose = True):
        '''Initialize all hardware components.
        
        Input:
         component_OrderedDict: directory with names of components to initialize and list of initialization steps
                         Default: None = initialize all components in order as assigned to microscope object
         reference_object: Used for setting up of autofocus
         trials: number of trials to initialize component before initialization is aborted
         verbose: if True print debug information (Default = True)
         
        Output:
         none
        '''
        # create directory for default initialization for all components if component_dir is None
        # empty dictionary indicates default initializations
        if initialize_components_OrderedDict is None:
            component_names = self.microscope_components_OrderedDict.keys()
            initialize_components_OrderedDict = collections.OrderedDict((name, []) for name in component_names)
        
        # get communications object as link to microscope hardware
        communicatons_object = self.get_control_software().connection
        # initialize all components
        # if a component has no initialize method, it is handed to default method of super class MicroscopeComponent
        for component_id, action_list in initialize_components_OrderedDict.iteritems():
            component_object = self.get_microscope_object(component_id)
            trials_count = trials
            while trials_count > 0:
                try:
                    trials_count = trials_count - 1
                    component_object.initialize(communicatons_object, action_list, reference_object = reference_object, verbose = verbose)
                except AutofocusNoReferenceObjectError:
                    raise
                except HardwareError as error:
                    if trials_count > 0:
                        result = error.error_dialog()
                        if result == -1:
                            trials_count = 0
                    else:
                        raise HardwareError('Component {} not initialized.'.format(component_id))
                else:
                    trials_count = 0
        
 
                 
    def set_microscope(self, settings_dict = {}):
        '''Set status flags for microscope.
        Input:
         settings_dict: dictionary {component_id: {settings}}   
                         supported flags:
                          autofocus_id: {use_auto_focus: True/False}
        Output:
         new_settings_dict: return all current settings
        '''
        new_settings_dict = {}
        for component_id, settings in settings_dict.iteritems():
            component_object = self.get_microscope_object(component_id)
            settings = component_object.set_component(settings)
            new_settings_dict[component_id] = settings
        return new_settings_dict
    
    def get_information(self, components_list = []):
        '''Get positions for hardware components.
        
        Input:
         components_list: list with names of components to retrieve positions
                         Default: None = get positions for all components
         
        Output:
         positions_dict: dictionary {component_id: positions}. positions are dictionaries if multiple positions can be retrieved
        '''
        # create directory for default initialization for all components if component_dir is None
        # empty list indicates default initializations
        if not len(components_list):
            components_list = self.microscope_components_OrderedDict.keys()
        
        # create list if components_list is only a single string
        if isinstance(components_list, str):
            components_list = [components_list]
        # get communications object as link to microscope hardware
        communicatons_object = self.get_control_software().connection
 
        # create dictionary with positions for all components in components_list
        positions_dict = {}
        for component_id in components_list:
            component_instance = self.get_microscope_object(component_id)
            positions_dict[component_id] = component_instance.get_information(communicatons_object)
        
        return positions_dict
 
    def get_z_position(self, focus_drive_id = None, auto_focus_id = None, force_recall_focus = False, trials = 3, reference_object = None, verbose = True):
        '''Get current position of focus drive. Use autofocus to update.
        
        Input:
         focus_drive_id: string id for focus drive to get the position for
         auto_focus_id: string id for auto focus to use (None: do not use auto-focus)
         force_recall_focus: if True, recall focus, otherwise use old values
                             Default: False
         trials: number of trials to retrieve z position before procedure is aborted
         reference_object: object of type sample (ImagingSystem) used to correct for xyz offset between different objectives
         verbose: if True, print debug messages (Default: False)
         
        Output:
         positions_dict: dictionary {component_id: positions}.
                            positions are dictionaries with 
                                'absolute': absolute position of focus drive as shown in software
                                'z_focus_offset': parfocality offset
                                'focality_corrected': absolute focus position - z_focus_offset
                                'auto_focus_offset': change in autofocus position
                                'focality_drift_corrected': focality_corrected position - auto_focus_offset
                                'load_position': load position of focus drive
                                'work_position': work position of focus drive
                            with focus positions in um
        '''
        # get communications object as link to microscope hardware
        communicatons_object = self.get_control_software().connection
 
        focus_drive_instance = self.get_microscope_object(focus_drive_id)
        auto_focus_instance = self.get_microscope_object(auto_focus_id)

        trials_count = trials
        success = False
        
        # Store status of autofocus and toggle use based on flag force_recall_focus
        auto_focus_status = auto_focus_instance.get_use_autofocus()
        if force_recall_focus:
            auto_focus_instance.set_use_autofocus(True)
        else:
            auto_focus_instance.set_use_autofocus(False)
            
        while not success:
            try:
                z_positions = focus_drive_instance.get_information(communicatons_object)                
                deltaZ = auto_focus_instance.recall_focus(communicatons_object, reference_object, verbose = verbose)
                success = True
            except AutomationError as error:
                self.recover_hardware(error)
                trials_count = trials_count - 1
                if trials_count > 0:
                    result = error.error_dialog()
                    if result == -1:
                        success = True
                else:
                    raise
         
        # Reset auto_focus to previous status
        auto_focus_instance.set_use_autofocus(auto_focus_status)      
        if deltaZ is None:
            z_positions['focality_drift_corrected'] = z_positions['focality_corrected']
        else:
            z_positions['focality_drift_corrected'] = z_positions['focality_corrected'] - deltaZ
        z_positions['auto_focus_offset'] = deltaZ
        return z_positions
   
 
    def _set_reference_position(self, reference_object, find_surface = False, verbose = True):
        '''Set reference position in object coordinates.
        
        Input:
         reference_object: plate, plate holder or other sample object the hardware is initialized for. Used for setting up of autofocus
         find_surface: if True use find surface of definite focus
         verbose: if True print debug information (Default = True)
         
        Output:
         objective_info: information for objective that was used to update offset
        '''
        auto_focus_object = self.get_microscope_object(reference_object.get_auto_focus_id())
        communication_object = self.get_control_software().connection
        
        reference_object.move_to_zero(load = False, 
                                      verbose = verbose)      
        
        if find_surface:
            _z = auto_focus_object.find_surface(communication_object)
            
        message.operate_message(message = 'Please move to and focus on reference position.', returnCode = False)
#         _z_abs = auto_focus_object.store_focus(communication_object, focusReferenceObj = reference_object)

        x_reference, y_reference, z_reference = reference_object.get_pos_from_abs_pos(verbose = verbose)
        # retrieve information for actual objective
        objective_changer_object = self.get_microscope_object(reference_object.get_objective_changer_id())
        objective_info = objective_changer_object.get_information(communication_object)
        
        reference_object.set_reference_position(x_reference, y_reference, z_reference)
        print('Store new reference position in reference object coordinates: {}, {}, {}'.format(x_reference, 
                                                                                                y_reference, 
                                                                                                z_reference))
        return objective_info

    def _update_objective_offset(self, reference_object, find_surface = False, verbose = True):
        '''Find reference position and update offset for objective.
        
        Input:
         communication_object: Object that connects to microscope specific software
         reference_object: plate, plate holder or other sample object the hardware is initialized for. Used for setting up of autofocus
         find_surface: if True use find surface of definite focus
         verbose: if True print debug information (Default = True)
         
        Output:
         objective_info: information for objective that was used to update offset
        '''
        # move to position that was used to define reference positions to calculate par-focality and par-centricity
        # if auto-focus was on, switch off autofocus
        auto_focus_object = self.get_microscope_object(reference_object.get_auto_focus_id())
        objective_changer_object = self.get_microscope_object(reference_object.get_objective_changer_id())
        communication_object = self.get_control_software().connection
        
        auto_focus_status = auto_focus_object.use_autofocus
        auto_focus_object.set_use_autofocus(False)

        x_reference, y_reference, z_reference = reference_object.get_reference_position()
        print('Reference position in reference object coordinates before adjustments: {}, {}, {}'.format(x_reference, y_reference, z_reference))
        
        # when moving to reference position with new objective, Microscope.move_to_abs_pos() takes objective into account
        reference_object.move_to_xyz(x = x_reference, 
                                     y = y_reference, 
                                     z = z_reference, 
                                     load = False, verbose = verbose)
        
        if find_surface:
            _z = self.find_surface(communication_object)
        
        message.operate_message(message = 'Please move to and focus on reference position.', returnCode = False)

        # get new position for reference in object coordinates and check if it changed. This new position is already corrected with current objective offset
        new_x_reference, new_y_reference, new_z_reference = reference_object.get_pos_from_abs_pos(verbose = verbose)
        print('New reference position in reference coordinates: {}, {}, {}'.format(new_x_reference, new_y_reference, new_z_reference))
        
        # retrieve information for actual objective
        objective_info = objective_changer_object.get_information(communication_object)
        
        x_delta = new_x_reference - x_reference
        y_delta = new_y_reference - y_reference
        z_delta = new_z_reference - z_reference

        
        if abs(x_delta) + abs(y_delta) + abs(z_delta) > 0:
            # update offset for objective
            offset = objective_changer_object.get_objective_information(communication_object)
            x_offset = x_delta + offset['x_offset']
            y_offset = y_delta + offset['y_offset']
            z_offset = z_delta + offset['z_offset']
        
            # update objective offset for current objective with new offset
            objective_changer_object.update_objective_offset(communication_object, x_offset, y_offset, z_offset, objective_name = None)
            print('New offset: {}, {}, {}'.format(x_offset, y_offset, z_offset))
        auto_focus_object.set_use_autofocus(auto_focus_status)   
                      
        return objective_info
        
    def reference_position(self, find_surface = False, reference_object = None, verbose = True):
        '''Initialize and update reference position to correct for xyz offset between different objectives.
        
        Input:
         find_surface: if True auto-focus will try to find cover slip before operator refocuses
                     Default: False
         reference_object: plate, plate holder or other sample object the hardware is initialized for. Used for setting up of autofocus
         verbose: if True print debug information (Default = True)
         
        Output:
         none
        '''        
        if reference_object is None:
            raise AutofocusNoReferenceObjectError('Reference object needed to set reference_position')
        
        # make sure that proper objective is in place and all relevant components are initialized
        communication_object = self.get_control_software().connection
        objective_changer_object = self.get_microscope_object(reference_object.get_objective_changer_id())

        # Make sure that objective is in place and not still moving
        experiment = objective_changer_object.get_init_experiment()
        experiment_path = self.create_experiment_path(experiment)
        experiment_object = experimentInfo.ZenExperiment(experiment_path, experiment)
        objective_changer_id = reference_object.get_objective_changer_id()
        objective_changer_object.get_objective_information(communication_object)
        
        counter = 0
        while experiment_object.get_objective_position() != objective_changer_object.get_information(communication_object)['position']:
            # wait one second
            time.sleep(1)
            
            counter = counter + 1
            if counter ==5:                                    
                raise HardwareNotReadyError(message = 'Objective not ready for experiment {}.'.format(objective_changer_object.get_init_experiment()),
                                            error_component = objective_changer_object)
 
        # if reference position is not set, set it, otherwise use stored reference position and correct for offset.
        x ,y, z = reference_object.get_reference_position()
        if x is None or y is None or z is None:
            # reference position was never defined
            objective_info = self._set_reference_position(reference_object, find_surface = find_surface, verbose = verbose)
        else:
            objective_info = self._update_objective_offset(reference_object, find_surface = find_surface, verbose = verbose)
        self.set_objective_is_ready(objective_info, reference_object)
   
    def move_to_abs_pos(self, stage_id = None,
                        focus_drive_id = None,
                        objective_changer_id = None,
                        auto_focus_id = None,
                        safety_id = None,
                        safe_area = 'Compound', 
                        x_target = None, y_target = None, z_target = None,
                        z_focus_preset = None,
                        reference_object = None,
                        load = True,
                        trials = 3,
                        verbose = False):
        '''Move stage and focus drive to position (x, y, z) in absolute system coordinates.
        
        Input:
         stage_id, focus_drive_id: stings to identify stage and focus drive
         objective_changer_id: sting to identify objective changer
         safety_id: string to identify safety object
         save_area: name of safe area withing safety object (default: 'compound' = combine all areas)
         x_target, y_target: coordinates of stage after movement (none = do not move stage)
         z_target: coordinate for focus position after movement (none = do not move focus, but engage auto-focus)
         z_focus_preset: z position for focus before focus recall to make autofocus more reliable (Default: None, do not use feature)
         reference_object: object of type sample (ImagingSystem) used to correct for xyz offset between different objectives
         load: Move focus in load position before move. Default: True
         trials: number of trials to retrieve z position before procedure is aborted
         
        Ouput:
         x_final, y_final, z_final: coordinates after move
        '''
        log_method(self, 'move_to_abs_pos')
        
        # retrieve stage, focus, objective changer, and safety objects
        focus_drive_object = self.get_microscope_object(focus_drive_id)
        objective_changer_object = self.get_microscope_object(objective_changer_id)
        auto_focus_object = self.get_microscope_object(auto_focus_id)
        stage_object = self.get_microscope_object(stage_id)
        safety_object = self.get_microscope_object(safety_id)
        communication_object = self.get_control_software().connection
        
        # retrieve current positions for travel path calculation and in case they will stay the same
        stage_info = stage_object.get_information(communication_object)
        x_current, y_current = stage_info['centricity_corrected']
        focus_drive_info = focus_drive_object.get_information(communication_object)
        z_current = focus_drive_info['focality_corrected'] 
                  
        if x_target is None:
            x_target = x_current
        if y_target is None:
            y_target = y_current            
        if z_target is None:
            z_target = z_current
        
        # set final positions that will be returned to current positions in case stage or focus do not move
        x_final, y_final, z_final = x_current, y_current, z_current
        
        trials_count = trials
        success = False
        while not success:
            # adjust target positions for mechanical offset between different objectives
            # add offset within while loop to use updated offset in case objective was swapped
            offset = objective_changer_object.get_objective_information(communication_object)
            x_target_offset = x_target + offset['x_offset']
            y_target_offset = y_target + offset['y_offset']
            z_target_offset = z_target + offset['z_offset']
            z_target_delta = None
            try:             
                # check if stage and objective can safely move from current position to new target positions
                xy_path = stage_object.move_to_position(communication_object, x_target_offset, y_target_offset, test = True)
                if load:
                    z_max_pos = focus_drive_object.zLoad
                else:
                    z_max_pos = max([focus_drive_info['absolute'], z_target_offset])
                if safety_object.is_safe_move_from_to(safe_area, 
                                                      xy_path, 
                                                      z_max_pos, 
                                                      x_current = stage_info['absolute'][0], 
                                                      y_current = stage_info['absolute'][1], 
                                                      z_current = focus_drive_info['absolute'], 
                                                      x_target = x_target_offset, 
                                                      y_target = y_target_offset, 
                                                      z_target = z_target_offset, 
                                                      verbose = verbose):
                    if load:
                        z_final = focus_drive_object.goto_load(communication_object)
                    x_final, y_final = stage_object.move_to_position(communication_object, x_target_offset, y_target_offset, test = False)
                               
                    # check if autofocus position has changed and update z_target if necessary
                    # move focus close to correct position. This will make autofocus more reliable.
                    if z_focus_preset:
                        focus_drive_object.move_to_position(communication_object, z_focus_preset)
                    else:
                        focus_drive_object.move_to_position(communication_object, z_target_offset)
                    # pre_set_focus = False prevents system to move to last focus position before recalling
                    deltaZ = auto_focus_object.recall_focus(communication_object, reference_object, verbose = verbose, pre_set_focus = False)
                    if deltaZ is not None:
                        z_target_delta = z_target_offset + deltaZ
                    else:
                        z_target_delta = z_target_offset
                    z_final = focus_drive_object.move_to_position(communication_object, z_target_delta)
                else:
                    safety_object.show_save_areas(path = xy_path)
                    raise CrashDangerError('Danger of hardware crash detected when attempting to move stage from ({}, {}, {}) to ({}, {}, {})'.format(stage_info['absolute'][0], stage_info['absolute'][1], focus_drive_info['absolute'], x_target_offset, y_target_offset, z_target_offset))
                success = True
            except AutomationError as error:
                trials_count = trials_count - 1
                if trials_count > 0:

                    result = self.recover_hardware(error)
                    if result == -1:
                        success = True                    
                else:
                    raise           
        return x_final, y_final, z_final

    def run_macro(self, macro_name=None, macro_param=None):
        """
        Function to run a given Macro in the Zen Software
        :param macro_name: Name of the Macro
        :return:
        """
        communication_object = self.get_control_software().connection
        communication_object.run_macro(macro_name, macro_param)

    def execute_experiment(self, experiment = None, file_path = None, z_start = 'C', interactive = False):
        '''Trigger microscope to execute experiment defined within vendor software
        
        Input:
         experiment: string with name of experiment as defined within Microscope software
                      If None use actual experiment.
         file_path: string with path to save image
                    do not save if None (default)
         z_start: define where to start z-stack ('F'= first slice, 'C' = center, 'L' = last slice
                   Default: 'F'
         interactive: if True, allow user to modify file name if file exists
         
        Return:
         image: image of class ImageAICS to hold metadata. Does not contain image data at this moment.
         
        Class ImageAICS is a container for meta and image data. To add image data use method load_image.
        Do not try to recover from exceptions on this level.
        '''
        log_method(self, 'execute_experiment')
        # call execute_experiment method in connectMicroscope instance. This instance will be based on a microscope specific connect module.
        timeStart = datetime.datetime.now()
        
        communication_object = self.get_control_software().connection
        
        # adjust position for z-stack and tile scan
        # ZEN acquires z-stack with center of current positions
        experiment_object = Experiment(self.create_experiment_path(experiment), experiment, self)
        if experiment_object.is_z_stack(self):
            if not testExperiment.test_FocusSetup(experiment_object, verbose = True):
                print('Focus setup not valid')
            z_stack_range = experiment_object.z_stack_range()*1E6
            if z_start == 'F':
                communication_object.z_up_relative(z_stack_range/2)
            if z_start == 'L':
                communication_object.z_down_relative(z_stack_range/2)
        
        if experiment_object.is_tile_scan(self):
            # use current position and set as center of tile_scan
            x, y = communication_object.get_stage_pos()
            z = communication_object.get_focus_pos()
            experiment_object.update_tile_positions(x, y, z)
            # force reload the experiment so that the changes are reflected in Zen Software
            communication_object.close_experiment(experiment)
            
        try:
            communication_object.execute_experiment(experiment)
            self.last_experiment = experiment 
            self.last_objective_position = communication_object.get_objective_position()
        except AutomationError as error:
            self.recover_hardware(error)

        timeEnd = datetime.datetime.now()
                
        image = ImageAICS(meta={'aics_experiment': experiment})
#         image.add_meta(self.settings)
        
        # add meta data about acquisition time
        timeDuration = (timeEnd - timeStart).total_seconds()
        image.add_meta({'aics_dateStartShort': timeStart.strftime('%Y%m%d'),     \
                        'aics_dateEndShort': timeEnd.strftime('%Y%m%d'),         \
                        'aics_dateStart': timeStart.strftime('%m/%d/%Y'),        \
                        'aics_dateEnd': timeEnd.strftime('%m/%d/%Y'),            \
                        'aics_timeStart': timeStart.strftime('%H:%M:%S'),        \
                        'aics_timeEnd': timeEnd.strftime('%H:%M:%S'),            \
                        'aics_timeDuration': timeDuration})
        
        # save image   
        if file_path:                     
            image= self.save_image(file_path, image, interactive = interactive)
 
        return image

    def live_mode(self, camera_id, experiment = None, live = True):
        '''Start/stop live mode of ZEN software.
        
        Input: 
         camera_id: string id for camera
         experiment: name of ZEN experiment (default = None)
         live: switch live mode on (True = default) or off (False)
         
        Output:
         None
        '''

        communication_object = self.get_control_software().connection
        camera_instance = self.get_microscope_object(camera_id)
        
        try:
            if live:
                camera_instance.live_mode_start(communication_object, experiment)
                self.last_experiment = experiment 
                self.last_objective_position = communication_object.get_objective_position()
            else:
                camera_instance.live_mode_stop(communication_object, experiment)
                self.last_objective_position = communication_object.get_objective_position()
        except AutomationError as error:
            self.recover_hardware(error)         
         
    def save_image(self, filePath, image, interactive = False):
        '''Save last Microscope imageAICS taken from within Microscope software.
        
        Input:
         communication_object: Object that connects to microscope specific software
         fileName: filename with path to save imageAICS
         image: image of class ImageAICS
         interactive: if True, allow update of filename if it already exists
         
        Return:
         image: image of class ImageAICS
         
        Methods adds filePath to meta data
        '''
        log_method(self, 'save_image')
        # raise exception if image with name filePath already exists
        
        if interactive:
            for i in range(3):
                if os.path.isfile(filePath):           
                    directory, file_name = os.path.split(filePath)
                    new_file_name = automationMessagesFormLayout.read_string('File exists', 
                                                                             label = 'Modify new filename', 
                                                                             default = file_name, 
                                                                             returnCode = False)                
                    filePath = os.path.normcase(os.path.join(directory, new_file_name))
                else:
                    break
 
        if os.path.isfile(filePath):
            raise FileExistsError('File with path {} already exists.'.format(filePath))
        
        communication_object = self.get_control_software().connection
        communication_object.save_image(filePath)
        image.add_meta({'aics_filePath': filePath})
        
        return image
    
    
    def load_image(self, image, getMeta=False):
        '''Load image and return it as class imageAICS
        
        Input:
         communication_object: Object that connects to microscope specific software
         image: image object of class imageAICS. Holds meta data at this moment, no image data.
         getMeta: if true, retrieve meta data from file. Default is False
         
        Output:
         image: image with data and meta data as imageAICS class
         
        Methods ads image and meta data to image.      
        Methods passes load image to microscope specific load method.
        '''
        log_method(self, 'load_image')
        communication_object = self.get_control_software().connection
        image=communication_object.load_image(image, getMeta)
        return image


    def remove_images(self):
        '''Remove all images from display in microscope software
        
        Input:
         communication_object: Object that connects to microscope specific software
         
        Output:
         none
         
        Methods ads image and meta data to image.      
        Methods passes load image to microscope specific load method.
        '''
        log_method(self, 'remove_images')
        communication_object = self.get_control_software().connection
        communication_object.remove_all()

################################################################################################

class Experiment():
    """
    Class to validate, read and write to experiment files
    They are handled in different ways in Zen Blue and Black.
    Hence this feature was moved to hardware level
    """
    def __init__(self, experiment_path=None, name=None, microscope_object=None):
        """
        :param file_path: File path to the experiment file (in zen black it will be none)
        :param name: Name of the experiment file
        :param microscope_object: microscope object that contains the connection to zen blue/black
        """
        self.experiment_name = name
        self.experiment_path = experiment_path
        self.microscope_object = microscope_object

    def validate_experiment(self):
        """
        Function to check if the experiment is defined and valid
        :return: valid_experiment: bool describing if the experiment is valid or not
        """
        microscope_connection = self.microscope_object.get_control_software().connection
        valid_experiment = microscope_connection.validate_experiment(self.experiment_path, self.experiment_name)
        return valid_experiment

    def is_z_stack(self, microscope_object):
        """
        Function to check if the experiment contains z-stack acquisition
        :return: is_zstack: bool
        """
        microscope_connection = microscope_object.get_control_software().connection
        is_zstack = microscope_connection.is_z_stack(self.experiment_path, self.experiment_name)
        return is_zstack

    def z_stack_range(self):
        """
        Function to calculate the range of the first experiment
        :return: zstack_range: range
        """
        microscope_connection = self.microscope_object.get_control_software().connection
        zstack_range = microscope_connection.z_stack_range(self.experiment_path, self.experiment_name)
        return zstack_range

    def is_tile_scan(self, microscope_object):
        """
        Function to check if the experiment contains a tile scan
        :return: is_tilescan: bool
        """
        microscope_connection = microscope_object.get_control_software().connection
        is_tilescan = microscope_connection.is_tile_scan(self.experiment_path, self.experiment_name)
        return is_tilescan

    def update_tile_positions(self, x_value, y_value, z_value):
        """
        Function to set the tile position
        :param x_value: x coordinate
        :param y_value: y coordinate
        :param z_value: z coordinate
        :return:
        """
        microscope_connection = self.microscope_object.get_control_software().connection
        microscope_connection.update_tile_positions(self.experiment_path, self.experiment_name,
                                                    x_value, y_value, z_value)

    def get_objective_position(self):
        """
        Function to get the position of the objective used in the experiment
        :param experiment_path: path of the experiment file
        :param experiment_name: name of the experiment
        :return: position: the integer position of the objective
        """
        microscope_connection = self.microscope_object.get_control_software().connection
        position = microscope_connection.get_objective_position_from_experiment_file\
            (self.experiment_path, self.experiment_name)
        return position

    def get_focus_settings(self):
        """
        Function to get focus settings to test focus setup in testExperiment.py
        :return: focusSettings
        """
        microscope_connection = self.microscope_object.get_control_software().connection
        focus_settings = microscope_connection.get_focus_settings(self.experiment_path, self.experiment_name)
        return focus_settings

class MicroscopeComponent(object):
    '''Base class for all microscope components.'''
    
    def __init__(self, componentID):
        self.set_id(componentID)
        self.component_type = self.__class__.__name__
        
                # settings during operation
        self.init_experiment = None
        self.default_camera = None
        self.use_live_mode = False

    
    def set_id(self, componentID):
        '''Set unique id for microscope component.
        
        Input: 
         componentID: string with unique component id
         
        Output:
         none
        '''
        self.id = componentID
    
    def get_id(self):
        '''Get unique id for component.
        
        Input:
         none
         
        Output: 
         componentID: string with unique component id
        '''
        return self.id
    
    def set_init_experiment(self, experiment):
        '''Set experiment that will be used for initialization.
        
        Input:
         experiment: string with experiment name as defined within microscope software
         
        Output:
         none
        '''
        self.init_experiment = experiment

    def get_init_experiment(self, communication_object = None):
        '''Get experiment that will be used for initialization.
        
        Input:
         communication_object: not usesd
         
        Output:
         init_experiment: string with experiment name as defined within microscope software       
        '''
        return self.init_experiment
        
    def initialize(self, communication_object, action_list, reference_object = None, verbose = True):
        '''Catch initialization method if not defined in sub class.
        
        Input:
         communication_object: not used: Object that connects to microscope specific software
         action_list: will not be processed
         reference_object: plate the hardware is initialized for. Used for setting up of autofocus
         verbose: if True print debug information (Default = True)
         
        Output:
         none
        '''
        self.communication_object = communication_object
        self.action_list = action_list
        self.plate_object = reference_object

    def set_component(self, settings):
        '''Catch settings method if not defined in sub class.
        
        Input:
         settings: dictionary with flags
        
        Output:
         new_settings: dictionary with updated flags flags
        '''
        return settings
    
    def get_information(self, communication_object):
        '''Catch get_information method if not defined in sup class.
        
        Input:
         communication_object: not used: Object that connects to microscope specific software
         
        Output:
         None
        '''
        return None
    
################################################################################################
                
class ControlSoftware(MicroscopeComponent):
    '''Connect to software that controls specific Microscope. Import correct module based on Microscope software.'''
    
    def __init__(self, software):
        '''Connect to microscope software
        
        Input:
         software: string with software name
         
        Output:
         none
        '''
        #log_method(self, '__init__')
        super(ControlSoftware, self).__init__(software)
        # get name for software that controls Microscope
#         self.software=software
        self.connect_to_microscope_software()

    def connect_to_microscope_software(self):  
        ''' Import connect module based on software name and connect to microscope.
        
        Input:
         none
         
        Output:
         none
        '''
        #log_method(self, 'connect_to_microscope_software')
        if self.get_id() == 'ZEN Blue':
            from connectZenBlue import connectMicroscope
            self.connection = connectMicroscope()
        elif self.get_id() == 'ZEN Black':
            from connectZenBlack import connectMicroscope
            self.connection = connectMicroscope()
        elif self.get_id() == 'ZEN Blue Test':
            from connectZenBlue import connectMicroscope
            self.connection = connectMicroscope(connect_dll=False)

      


        #logger.info('selected software: %s', self.get_id())
    
    
################################################################################################
        
class Safety(MicroscopeComponent):
    '''Class with methods to avoid hardware damage of microscope.
    '''
    
    def __init__(self, safetyID):
        '''Define safe area for stage to travel.
        
        Input:
         safetyID: unique string to describe area
         
        Output:
         none
        '''
        super(Safety, self).__init__(safetyID)
        self.save_areas={}

    
    def add_save_area(self, save_vertices, save_area_id, z_max):
        '''Set save travel area for microscope stage.
        
        Input:
         save_vertices: coordinates in absolute stage positions that define save area in the form [(x_0, y_0), (x_1, y_1),c(x_2, y_2), ...).
         save_area_id: unique string to identify save area
         z_max: maximum z value in focus drive coordinates within save area
         
        Output:
         none
        '''
        save_verts = save_vertices + [save_vertices[0]]
        save_codes = [mpl_path.MOVETO] + [mpl_path.LINETO] * (len(save_verts) - 2) + [mpl_path.CLOSEPOLY]
        save_area = {'path': mpl_path(save_verts, save_codes), 'z_max': z_max}
        self.save_areas[save_area_id] = save_area

    def get_save_area(self, save_area_id = 'Compound'):
        '''Get save travel area for microscope stage. Create compound area if requested.
        
        Input:
         save_area_id: unique string to identify save area
                         Default: 'Compound' = combination of all save areas
         
        Output:
         x_save_min, x_save_max, y_save_min, y_save_max: coordinates in absolute stage positions that define save area.
 
        '''
        if save_area_id in self.save_areas.keys():
            return self.save_areas[save_area_id]
        
        if save_area_id == 'Compound':
        # create compound area out of all existing save areas
            compound_path = None
            for save_area_name, save_area in self.save_areas.iteritems():
                save_path = save_area['path']
                if compound_path is None:
                    compound_path = save_path
                    z_max = save_area['z_max']
                else:
                    compound_path = mpl_path.make_compound_path(compound_path, save_path)
                    z_max = min((z_max, save_area['z_max']))
    
            save_area = {'path': compound_path, 'z_max': z_max}         
            return save_area

        
    def is_save_position(self, x, y, z, save_area_id = 'Compound'):
        '''Test if absolute position is save.
        
        Input:
         x, y: absolute sage position in um to be tested
         z: absolute focus position in um to be tested
         save_area_id: unique string to identify save area
                         Default: 'Compound' = combination of all save areas
         
        Output:
         is_save: True if position is save, otherwise False
        '''
        save_area = self.get_save_area(save_area_id)
        
        is_save = save_area['path'].contains_point([x, y]) and save_area['z_max'] > z
        return is_save


    def is_save_travel_path(self, path, z, save_area_id = 'Compound', verbose = True):
        '''Test if absolute position is save.
        
        Input:
         path: travel path to be tested as matplotlib.Path object
         z: absolute focus position in um to be tested
         save_area_id: unique string to identify save area
                         Default: 'Compound' = combination of all save areas
         verbose: if True, show travel path and safe area (default = True)
         
        Output:
         is_save: True if path is save, otherwise False
        '''
        save_area = self.get_save_area(save_area_id)
        
        # Interpolate path. Path.contains_path appears to test only vertices.
        # Find necessary density for interpolation steps
        # Length of path
        length = 0.0
        is_save = False
        for vert in path.iter_segments():
            if vert[1] == mpl_path.MOVETO:
                start = vert[0]
            if vert[1] == mpl_path.LINETO:
                length = length + math.sqrt((vert[0][0] - start[0])**2 + (vert[0][1] - start[1])**2)
                start = vert[0]
        if int(length) > 0:
            is_save = save_area['path'].contains_path(path.interpolated(int(length))) and save_area['z_max'] > z
        else:
            is_save = True
        
        return is_save

    
    def is_safe_move_from_to (self, save_area_id, xy_path, z_max_pos, x_current, y_current, z_current, x_target, y_target, z_target, verbose = True):
        '''Test if it is save to travel from current to target position.
        
        Input: 
         save_area_id: sting id for save area
         xy_path: matplotlib path object that describes travel path of stage
         z_max_pos: the highest position for z focus during travel
         x_current, y_current, z_current: current x, y, z positions of stage in um
         x_target, y_target, z_target: target x, y, z positions of stage in um
         verbose: if True, show tavel path and safe area (default = True)
         
        Output:
         is_save: True if travel path is save, otherwise False
        '''
        # show safe area and travel path if verbose
        if verbose:
            self.show_save_areas(path = xy_path, point = (x_current, y_current))
        # is start position in safe area?
        if not self.is_save_position(x_current, y_current, z_current, save_area_id):
            return False

        # is target position in safe area?
        if not self.is_save_position(x_target, y_target, z_target, save_area_id):
            return False

        # is path in safe area?
        if not self.is_save_travel_path(xy_path, z_max_pos, save_area_id, verbose = verbose):
            return False
        
        return True

        
    def show_save_areas(self, path = None, point = None):
        '''Show all save areas defined in this class instance.
        
        Input:
         path: travel path to overlay with save areas as matplotlib.Path object
         point: point to overlay with save area as (x, y) tuple
         
        Output:
         none
        '''
        # setup figure
        fig = plt.figure()
        ax = fig.add_subplot(111)
        cmap = cm.get_cmap('Spectral')
        # add all save areas to figure
        compound_path = None
        for i, (save_area_name, save_area) in enumerate(self.save_areas.iteritems()):
            save_path = save_area['path']
            color = cmap(1.0/(i+1))
            patch = patches.PathPatch(save_path, facecolor=color, lw=2)
            ax.add_patch(patch)
            #combine all path objects to one compound path
            if compound_path is None:
                compound_path = save_path
            else:
                compound_path = mpl_path.make_compound_path(compound_path, save_path)
    
        # add point and path information to image
        
        # define size of viewing area
        if point is not None:
            ax.plot(point[0], point[1], 'ro')
        if path is not None:
            path_patch = patches.PathPatch(path, facecolor = 'none', lw=2)
            ax.add_patch(path_patch)
        # get bounding box
        view_box = compound_path.get_extents()
        
        #increase size of bounding box to view_box
        view_box = view_box.expanded(1.1, 1.1)
        ax.set_xlim(view_box.min[0], view_box.max[0])
        ax.set_ylim(view_box.min[1], view_box.max[1])
        plt.show()

        
################################################################################################
        
class Camera(MicroscopeComponent, ImageAICS):
    '''Class to describe and operate microscope camera
    '''
#     def __init__(self, cameraObject, cameraId, prefs, pixelSize = None, pixelNumber=None, pixelType= None, name=None,  detectorType='generic', manufacturer=None, model=None):
#     def __init__(self, cameraId, prefs, pixelSize = None, pixelNumber=None, pixelType= None, name=None,  detectorType='generic', manufacturer=None, model=None):
    def __init__(self, cameraId, pixelSize = (None, None), pixelNumber=(None, None), pixelType= None, name=None,  detectorType='generic', manufacturer=None, model=None):

        '''Describe and operate camera
        
        Input:
         cameraObject: object for software connection to microscope, typically created with class ControlSoftware.
                         often identical to microscopeObject
         cameraId: string with unique camera id
         prefs: dictionary with preferences
         pixelSize: (x, y) pixel size in mum
         pixelNumber: (x, y) pixel number
         pixelType: type of pixels (e.g. int32)
         name: string with brand name of camera, e.g. Flash 4.0
         detectorType: string with camera type, e.g. EMCCD, sCMOS
         manufacturer: sting with name of manufacturere, e.g. Hamamatsu
         
        Output:
         none
        '''
        log_method(self, '__init__')
        super(Camera, self).__init__(cameraId)
        
        # keep track of live mode status
        self.live_mode_on = False
        
        # Specifications for used camera. 
        # Names for keys are based on OME-XML
        # http://www.openmicroscopy.org/Schemas/Documentation/Generated/OME-2015-01/ome.html
        self.settings ={'aics_cameraID': cameraId, 
                        'aics_PixelType': pixelType,                # The variable type used to represent each pixel in the image.
                        'aics_SizeX': pixelNumber[0],               # Dimensional size of pixel data array [units:none].
                        'aics_SizeY': pixelNumber[1],               # Dimensional size of pixel data array [units:none].
                        'aics_PhysicalSizeX': pixelSize[0],         # Physical size of a pixel. Units are set by PhysicalSizeXUnit.
                        'aics_PhysicalSizeY': pixelSize[1],         # Physical size of a pixel. Units are set by PhysicalSizeXUnit.
                        'aics_PhysicalSizeXUnit': 'mum',            # The units of the physical size of a pixel - default:microns[micron].
                        'aics_PhysicalSizeYUnit': 'mum',            # The units of the physical size of a pixel - default:microns[micron].
                        'aics_Manufacturer': manufacturer,          # The manufacturer of the component. [plain text string]
                        'aics_Model': model,                        # The Model of the component. [plain text string]
                        'aics_Type': detectorType}                  # The Type of detector. E.g. CCD, PMT, EMCCD etc.

 

    def get_information(self, communication_object):
        '''get camera status
        
        Input:
         communication_object: Object that connects to microscope specific software
         
        Output:
         camera_dict: dictionary {'live': True/False, 'settings':  dict with settings}
        '''
        
        return {'live': self.live_mode_on, 'settings': self.settings}

    def snap_image(self, communication_object, experiment=None):
        '''Snap image with parameters defined in experiment.
        
        Input:
         communication_object: Object that connects to microscope specific software
         experiment: string with name of experiment as defined within Microscope software
                      If None use actual experiment.
         
        Return:
         image: image of class ImageAICS to hold metadata. Does not contain image data at this moment.
         
        Class ImageAICS is a container for meta and image data. To add image data use method load_image.
        '''
        log_method(self, 'snap_image')
        # call execute_experiment method in connectMicroscope instance. This instance will be based on a microscope specific connect module.
        returnCode = communication_object.snap_image(experiment)                    
        image=ImageAICS(meta={'aics_experiment': experiment})
        image.add_meta(self.settings)
        return image


    def live_mode_start(self, communication_object, experiment = None):
        '''Start live mode of ZEN software.
        
        Input: 
         communication_object: Object that connects to microscope specific software
         experiment: name of ZEN experiment (default = None)
         
        Output:
         None
        '''
        log_method(self, 'live_mode_start')
        communication_object.live_mode_start(experiment)
        self.live_mode_on = True
        
        
    def live_mode_stop(self, communication_object, experiment = None):
        '''Stop live mode of ZEN software.
        
        Input: 
         communication_object: Object that connects to microscope specific software
         experiment: name of ZEN experiment (default = None)
                      If None use actual experiment.
         
        Output:
         none
        '''
        log_method(self, 'live_mode_stop')
        communication_object.live_mode_stop(experiment)
        self.live_mode_on = False
    
    
################################################################################################
                  
class Stage(MicroscopeComponent):
    '''Class to describe and operate microscope stage
    '''
#     def __init__(self, stageObject, id, save_area_object = None):
    def __init__(self, stageId, safe_area = None, safe_position = None, objective_changer = None, microscope_object = None):
        '''Describe and operate microscope stage
        
        Input:
         stageId: string with unique stage id
         safe_area: Name of area to stage can travel safely
         safe_position: Position of stage that is save
         objective_changer: string with unique id for objective changer assoziated with stage
                             required for par-centrizity correction
         microscope_object: microscope component is attached to
        
        Output:
         none
        '''
        log_method(self, '__init__')
        super(Stage, self).__init__(stageId)
        self.safe_area = safe_area
        self.save_position_x = safe_position[0]
        self.save_position_y = safe_position[1]
        self.objective_changer = objective_changer
        self.microscope_object = microscope_object

    def initialize(self, communication_object, 
                   action_list = [],
                   reference_object = None,
                   verbose = True):
        '''Initialize stage.
        
        Input:
         communication_object: Object that connects to microscope specific software
         action_list: not used
         reference_object: plate the hardware is initialized for. Used for setting up of autofocus
         verbose: if True print debug information (Default = True)
         
        Output:
         none
        '''
        # Move stage to save position
        # User prefers no operate message box here. Moved warning to previous dialog box
        # message.operate_message('Stage  "{}" will move to save position.\nMove objective to load position.\nMake sure that travel path is safe'.format(self.get_id()), returnCode = False)
        self.move_to_position(communication_object, 
                              x = self.save_position_x, 
                              y = self.save_position_y, 
                              test = False)
        
        
    def get_information(self, communication_object):
        '''get actual stage position from hardware in mum
        
        Input:
         communication_object: Object that connects to microscope specific software
         
        Output:
         positions_dict: dictionary {'absolute': (x, y), 'centricity_corrected':  (x, y)} with stage position in mum
        '''
        log_method(self, 'get_position')
        x, y = communication_object.get_stage_pos()
        
        # correct par-centricity
        objective_changer_object = self.microscope_object.get_microscope_object(self.objective_changer)
        offset = objective_changer_object.get_objective_information(communication_object)
        x_corrected = x - offset['x_offset']
        y_corrected = y - offset['y_offset']
        return {'absolute': (x, y), 'centricity_corrected':  (x_corrected, y_corrected)}


    def move_to_position(self, communication_object, x ,y, test = False):
        '''set  stage position in mum and move stage
        
        Input:
         communication_object: Object that connects to microscope specific software
         x, y: stage position in mum
         test: if True, do not move stage but return travel path
         
        Output:
         xStage, yStage: position of stage after movement in mum
        '''
        log_method(self, 'set_position')
        if test:
            xy_path = communication_object.move_stage_to(x, y, test = True)
            path_object = mpl_path(xy_path)
            return path_object
        xStage, yStage = communication_object.move_stage_to(x, y)
        return xStage, yStage

################################################################################################
        
class ObjectiveChanger(MicroscopeComponent):
    '''Class to describe and change objectives
    '''
    def __init__(self, objective_changer_specifications):
        '''Describe and change objectives
        
        Input:
         objective_changer_specifications: dictionary with information about objective changer:
             objective_changer_id: string with unique objective changer id
             nPositions:  number of objective positions
             objective_information: dictionary {'objective_name': {'x_offset': x, 'y_offset': y, 'z_offset': z, 'magnification': m, 'immersion': 'type', 'experiment': 'name'}}
         
        Output:
         none
        '''
        log_method(self, '__init__')
 
        super(ObjectiveChanger, self).__init__(objective_changer_specifications.getPref('Name'))
        
        self.set_number_positions(objective_changer_specifications.getPref('Positions'))
        
        # Set dictionary of objectives with self.get_all_objectives(n)
        # Required when using self.change_magnification(magnification)
        self.objectivesDict = {}
        self.objective_information = objective_changer_specifications.getPref('Objectives')
        
        # set experiment for initialization
        self.reference_objective = objective_changer_specifications.getPref('ReferenceObjective')
        init_experiment = self.objective_information[self.reference_objective]['experiment']
        self.set_init_experiment(init_experiment)
        self.default_camera = self.objective_information[self.reference_objective]['camera']
        self.use_live_mode = True
        
    def initialize(self, communication_object, 
                   action_list = [], 
                   reference_object = None, 
                   verbose = True):
        '''Initialize objective changer and set reference positions.
        
        Input:
         communication_object: Object that connects to microscope specific software
         action_list: list with item 'set_reference'. If empty no action.
         reference_object: plate the hardware is initialized for. Used for setting up of autofocus
         verbose: if True print debug information (Default = True)
         
        Output:
         none
        '''
        if 'set_reference' in action_list:
            # setup microscope to initialize ObjectiveChanger
            self.microscope.setup_microscope_for_initialization(component_object = self, 
                                                                 experiment = self.get_init_experiment(), 
                                                                 before_initialization = True)  
                              
            self.microscope.reference_position(find_surface = False,
                                                reference_object = reference_object, 
                                                verbose = verbose)        
            
            # Clean up after initialization
            self.microscope.setup_microscope_for_initialization(component_object = self, 
                                                                experiment = self.get_init_experiment(), 
                                                                before_initialization = False) 

                
    def set_number_positions(self, nPositions):
        '''Sets the number of objective positions.
        
        Input:
         nPositions:  number of objective positions
         
        Output:
         none
        '''
        log_method(self, 'set_number_positions')
        self.numberPositions = nPositions


    def get_number_positions(self):
        '''Get the number of objective positions.
        
        Input:
         none
         
        Output:
         nPositions:  number of objective positions
        '''
        log_method(self, 'get_number_positions')
        return self.numberPositions

        
    def get_all_objectives(self, communication_object):
        '''Retrieve name and magnification of all objectives.
        Warning! Objectives will move!
        
        Input:
         communication_object: Object that connects to microscope specific software
         
        Output:
         objectivesDict: dictionary of all objectives mounted at microscope 
                         in form {'magnification': {'Position': position, 'Name': name}
                         
        Required when using self.change_magnification(magnification)
        '''
        log_method(self, 'get_all_objectives')
        numberObjectives = self.get_number_positions()
        self.objectivesDict = communication_object.get_all_objectives(numberObjectives)
        return self.objectivesDict 

 
    def  get_objectives_dict(self):
        '''Retrieves dictionary with all names and magnifications of objectives.
        
        Input:
         none
         
        Output:
         objectivesDict: dictionary of all objectives mounted at microscope 
                         in form {'magnification': {'Position': position, 'Name': name}
                         
        Requires to run self.get_all_objectives once before usage.'''
        log_method(self, 'get_objectives_dict')  
        return self.objectivesDict


    def get_objective_magnification(self):
        '''Get magnification of actual objective.
         
        Input: 
         none
          
        Output: 
         magnification: magnification of actual objective, objective in imaging position
        '''
        log_method(self, 'get_objective_magnification')
        # get magnification from hardware
        magnification = self.objectiveChanger.get_objective_magnification()
        return magnification

    def get_objective_information(self, communication_object):
        '''Get offset to correct for parfocality and parcentrality for current objective
        
        Input:
         communication_object: Object that connects to microscope specific software
         
        Output:
         objective_information: dictionary {'x_offset': x, 'y_offset': y, 'z_offset': z, 'magnification': m, 'immersion': 'type'} for current objective
        '''
        objective_name = communication_object.get_objective_name()
        if objective_name in self.objective_information:
            objective_information = self.objective_information[objective_name]
        else:
            objective_information = {'x_offset': 0, 'y_offset': 0, 'z_offset': 0, 'magnification': None, 'immersion': None}
            print('Information for objective {} is not defined'.format(objective_name))        
        objective_information['name']=objective_name
        return objective_information

    def update_objective_offset(self, communication_object, x_offset, y_offset, z_offset, objective_name = None):
        '''Update offset to correct for parfocality and parcentrality
        
        Input:
         communication_object: Object that connects to microscope specific software
         objective_name: string with unique name for objective. 
                         If None use current objective
          x_offset, y_offset, z_offset: new offset values in absolute coordinates
         
        Output:
         objective_information: dictionary {'x_offset': x, 'y_offset': y, 'z_offset': z, 'magnification': m, 'immersion': 'type'} for current objective
        '''
        if objective_name is None:
            objective_name = communication_object.get_objective_name()

        # TODO: Should that be
#         try:
#     objective_information = self.objective_information[objective_name]
#     objective_information['x_offset'] = x_offset
#     objective_information['y_offset'] = y_offset
#     objective_information['z_offset'] = z_offset

        # Is this information used somewhere?
        
        try:
            objective_information = self.objective_information[objective_name]['x_offset'] = x_offset
            objective_information = self.objective_information[objective_name]['y_offset'] = y_offset
            objective_information = self.objective_information[objective_name]['z_offset'] = z_offset
        except:
            raise ObjectiveNotDefinedError(message = 'No objective with name {} defined.'.format(objective_name))
        return objective_information
            
    def get_information(self, communication_object):
        '''Get name and magnification of actual objective.
        
        Input: 
         communication_object: Object that connects to microscope specific software
         
        Output: 
         name: name, magnification, and position of actual objective, objective in imaging position
        '''
        log_method(self, 'get_objective_name')
        # get name of objective from hardware
        objective_name = communication_object.get_objective_name()
        objective_magnification = communication_object.get_objective_magnification()
        objective_position = communication_object.get_objective_position()
        init_experiment = self.objective_information[objective_name]['experiment']
        return {'name': objective_name, 
                'magnification': objective_magnification, 
                'position': objective_position,
                'experiment': init_experiment}

    
    def change_magnification(self, magnification, sample_object, use_safe_position = True, verbose = True):
        '''Change to objective with given magnification.
        
        Input:
         magnification: magnification of selected objective as float.
                         not well defined if multiple objectives with identical magnification are present.
         sample_object: object that has save coordinates attached. 
                        If use_safe_position == True than stage and focus drive will move to this position 
                        before magnification is changed to avoid collision between objective and stage.
         use_safe_position: move stage and focus drive to save position before switching magnification to minimize risk of collision
                         Default: True       
         verbose: if True print debug information (Default = True)
         
        Output:
         objectiveName: name of new objective
         
        Requires to run self.get_all_objectives once before usage.
        '''
        log_method(self, 'change_magnification')
        try:
            objectivesDict = self.get_objectives_dict()
            objective = objectivesDict[magnification]
        except KeyError as error:
            raise ObjectiveNotDefinedError('No objective with magnification {}'.format(magnification))
        
        # move to safe position before changing objective
        if use_safe_position:
            sample_object.move_to_save(load = True, verbose = verbose)
        objective_name = self.objectiveChanger.switch_objective(objective['Position'])
        return objective_name

    def change_position(self, position, communication_object, load = True):
        '''Change to objective at given position.
        
        Input:
         position: position of objective
         communication_object: Object that connects to microscope specific software
         load: if True, move objective to load position before switching
                 Default: True
         
        Output:
         objectiveName: name of new objective
         
        Requires to run self.get_all_objectives once before usage.
        '''
        log_method(self, 'change_position')       
        objective_name = communication_object.switch_objective(position, load = load)
        return objective_name

################################################################################################
        
class FocusDrive(MicroscopeComponent):
    '''Class to describe and operate focus drive
    '''
    def __init__(self, focus_drive_id, max_load_position = 0, min_work_position = 10, 
                 auto_focus_id = None, objective_changer = None, microscope_object = None):
        '''Describe and operate focus drive
        
        Input:
         focus_drive_id: string with unique focus drive id
         max_load_position: maximum load position in um (Default = 0)
         min_work_position: minimum work position in um (Default = 10
         auto_focus_id: unique string to identify autofocus used with focus drive
                         (None if no autofocus)
         objective_changer: string with unique id for objective changer assoziated with stage
                             required for par-centrizity correction
         microscope_object: microscope component is attached to
        
        Output:
         none
        '''
        log_method(self, '__init__')
        super(FocusDrive, self).__init__(focus_drive_id)
        
        self.auto_focus_id = auto_focus_id
        
        # define max and min load and work positions
        self.maxLoadPosition = max_load_position
        self.min_work_position = min_work_position
        
        # predefine focus load and work positions as 0 to avoid crashes between objective and stage
        self.zLoad = None
        self.zWork = None
        
        self.objective_changer = objective_changer
        self.microscope_object = microscope_object
        
    def initialize(self, communication_object, 
                   action_list = [], 
                   reference_object = None, 
                   verbose = True):
        '''Initialize focus drive.
        
        Input:
         communication_object: Object that connects to microscope specific software
         action_list: list with items 'set_load' and/or 'set_work'. If empty no action.
         microscope_object: microscope component is attached to
         reference_object: plate the hardware is initialized for. Used for setting up of autofocus
         verbose: if True print debug information (Default = True)
         
        Output:
         none
        '''
        if 'set_load' in action_list:
            message.operate_message('Move focus drive {} to load position.'.format(self.get_id()), returnCode = False)
            loadPos = self.define_load_position(communication_object)
            if loadPos > self.maxLoadPosition:
                message_text = 'Load position {} is higher than allowed maximum {}.'.format(loadPos, self.maxLoadPosition)
                return_code = message.error_message('Please move objective to load position or cancel program.\nError message:\n"{}"'.format(message_text))
                if return_code != -1:
                    raise LoadNotDefinedError('Load position {} is higher than allowed maximum {}.'.format(loadPos, self.maxLoadPosition))                     

        if 'set_work' in action_list:
            message.operate_message('Please move focus drive "{}" to work position.'.format(self.get_id()), returnCode = False)
            workPos = self.define_work_position(communication_object)
                 
    def get_abs_position(self, communication_object):
        '''get absolute focus position from hardware in mum
        
        Input:
         communication_object: Object that connects to microscope specific software
         
        Output:
         z: focus position in mum
        '''
        log_method(self, 'get_abs_position')
        # get current absolute focus position w/o any drift corrections
        absZ = communication_object.get_focus_pos()
        return absZ



    def get_information(self, communication_object):
        '''get absolute and absolute position after drift correction for focus drive.
             
        Input:
         communication_object: Object that connects to microscope specific software
         
        Output:
         positions_dict: dictionary with 'absolute': absolute position of focus drive as shown in software
                                         'z_focus_offset': parfocality offset
                                         'focality_corrected': absolute focus position - z_focus_offset
                                         'load_position': load position of focus drive
                                         'work_position': work position of focus drive
                                     with focus positions in um
        '''

        z = self.get_abs_position(communication_object)

        # correct par-focality
        objective_changer_object = self.microscope_object.get_microscope_object(self.objective_changer)
        offset = objective_changer_object.get_objective_information(communication_object)
        z_corrected = z - offset['z_offset']        
        return {'absolute': z, 'focality_corrected': z_corrected, 'z_focus_offset': offset['z_offset'], 'load_position': self.get_load_position(), 'work_position': self.get_work_position()}

    def move_to_position(self, communication_object, z):
        '''Set focus position in mum and move focus drive
        
        Input:
         communication_object: Object that connects to microscope specific software
         z: focus drive position in mum
         
        Output:
         zFocus: position of focus drive after movement in mum
         
        If use_autofocus is set, correct z value according to new autofocus position.
        '''
        log_method(self, 'move_to_position')
        
        zFocus = communication_object.move_focus_to(z)
        return zFocus


    def goto_load(self, communication_object):
        '''Set focus position to load position.
        
        Input:
         communication_object: Object that connects to microscope specific software
         
        Output:
         zLoad: load position in mum
        '''
        log_method(self, 'goto_load')
        try:
            zLoad = communication_object.move_focus_to_load()
        # check if load was set. If not, ask user to set load
        except LoadNotDefinedError as error:         
            # add focus drive instance to exeption   
            raise LoadNotDefinedError(message = error.message, error_component = self)
#         # move objective to load position and store for future usage
#         # get objectives before setting work position, because changing objectives will delete focus position in Definite Focus
#             message.operate_message("Move objective to load position." +
#                                        '\nObjectives will start moving.' +
#                                        '\nConfirm objective change in software or touch pad if requested')
#     
#             # store current position of focus as load position
#             zLoad = self.define_load_position(communication_object)
#             zLoad = communication_object.move_focus_to_load()
        return zLoad


    def goto_work(self, communication_object):
        '''Set focus position to work position.
        
        Input:
         communication_object: Object that connects to microscope specific software
         
        Output:
         zWork: work position in mum
        '''
        log_method(self, 'goto_work')
        zWork = communication_object.move_focus_to_work()
        return zWork
    
    
    def define_load_position(self, communication_object):
        '''Define current focus position as load position for focus drive
        
        Input:
         communication_object: Object that connects to microscope specific software
         
        Output:
         zLoad: load postion in mum
        '''
        log_method(self, 'define_load_position')
        zLoad = communication_object.set_focus_load_position()
        self.zLoad = zLoad
        return zLoad


    def get_load_position(self):
        '''Get load position for focus drive.
        
        Input:
         none
         
        Output:
         zLoad: load position in mum
        '''
        log_method(self, 'get_load_position')
        return self.zLoad


    def define_work_position(self, communication_object):
        '''Define current focus position as work position for focus drive
        
        Input:
         communication_object: Object that connects to microscope specific software
         
        Output:
         zWork: load postion in mum
        '''
        log_method(self, 'define_work_position')
        zWork = communication_object.set_focus_work_position()
        self.zWork = zWork
        return zWork

    def get_work_position(self):
        '''Get work position for focus drive.
        
        Input:
         none
         
        Output:
         zWork: load position in mum
        '''
        log_method(self, 'get_work_position')
        return self.zWork


################################################################################################
        
class AutoFocus(MicroscopeComponent):
    '''Class to describe and operate hardware autofocus
    '''
    def __init__(self, auto_focus_id, default_camera = None, objective_changer_instance = None, default_reference_position = [[50000, 37000, 6900]]):
        '''Describe and operate hardware autofocus
        
        Input:
         auto_focus_id: string with unique autofocus id
         init_experiment: experiment used for live mode during auto-focus
         default_camera: camera used for live mode during auto-focus
         objective_changer_instance: instance of class ObjectiveChanger connected to this autofocus
         default_reference_position: reference position to set parfocality and parcentricity. Used if no reference object (e.g. well center) is used.
         
        Output:
         none
        '''
        log_method(self, '__init__')
        super(AutoFocus, self).__init__(auto_focus_id)
                
        # enable auto focus
        self.use_autofocus = self.set_use_autofocus(False)
        
        # settings during operation
#         self.set_init_experiment(init_experiment)
        
        if default_camera == 'None': 
            default_camera = None
        self.default_camera = default_camera

        self.use_live_mode = True
        
        # object from class ImagingSystem (module samples.py) that is used as reference (zero plane) for autofocus
        self.focusReferenceObj = None
        self.objective_changer_instance = objective_changer_instance
        self.initialized_objective = None
        self.default_reference_position = default_reference_position
        
        # Save position when autofocus was initialized the first time. 
        # This value is used to correct for focus drift
        self._initial_autofocus_position = None
        # Store difference between _initial_autofocus_position and autofocus position from 'Recall Focus'
        self.last_delta_z = None
 
    def get_init_experiment(self, communication_object):
        '''Get experiment used for initialization based on current objective.
        
        Input:
         communication_object: Object that connects to microscope specific software
         
        Output:
         init_experiment: string with name of experiment used for initialization
        '''
        # connect to associated objective changer and retrieve current objective        
        # retrieve init_experiment for this objective
        init_experiment = self.objective_changer_instance.get_information(communication_object)['experiment']
        return init_experiment
                
        
    def initialize(self, communication_object, 
                   action_list = ['find_surface'], 
                   reference_object = None, 
                   verbose = True):
        '''Initialize auto-focus (default: do nothing if already initialized).
        
        Input:
         communication_object: Object that connects to microscope specific software
         action_list: if list includes 'no_find_surface' auto-focus will not try to find cover slip before operator refocuses
                         no_interaction: no user interaction, no live image
                         force_initialization: initialize even if already initialized
                         if empty no action
         sample_object: plate, plate holder or other sample object the hardware is initialized for. Used for setting up of autofocus
         verbose: if True, print debug messages (Default: True)
         
        Output:
         none
        '''
        if action_list:
            # if auto-focus is already initialized, initialize only if 'force_initialization' is set in action_list
            if not self.get_autofocus_ready(communication_object) or 'force_initialization' in action_list:
                # if auto-focus was on, switch off autofocus
                auto_focus_status = self.use_autofocus
                self.set_use_autofocus(False)
    
                if 'no_interaction' not in action_list:
                    self.microscope.setup_microscope_for_initialization(component_object = self,
                                                                        experiment = self.get_init_experiment(communication_object),
                                                                        before_initialization = True)
    
                    if reference_object:
                        self.microscope.microscope_is_ready(experiment = self.get_init_experiment(communication_object), 
                                                             component_dict = {reference_object.get_objective_changer_id(): []}, 
                                                             focus_drive_id = reference_object.get_focus_id(), 
                                                             objective_changer_id = reference_object.get_objective_changer_id(), 
                                                             safety_object_id = reference_object.get_safety_id(),
                                                             reference_object = reference_object.get_reference_object(),
                                                             load = False, 
                                                             make_ready = True, 
                                                             verbose = verbose)
    
    #                    reference_object.move_to_zero(load = False, verbose = verbose)
    
                    if not 'no_find_surface' in action_list:
                        _z = self.find_surface(communication_object)
                    else:
                        message.operate_message(message = 'Please focus on top of cover slip.', returnCode = False)
                        message.operate_message(message = '1) Bring the objective to focus position using the TFT\n2) Click Find Surface in ZenBlue', returnCode = False)
    
    
                    self.microscope.setup_microscope_for_initialization(component_object = self,
                                                                        experiment = self.get_init_experiment(communication_object),
                                                                        before_initialization = False)
                _z_abs = self.store_focus(communication_object, focusReferenceObj = reference_object)
     
                # Save position when autofocus was initialized the first time.
                # This value is used to correct for focus drift
                self._initial_autofocus_position = _z_abs
                self.set_use_autofocus(auto_focus_status)
        
    def get_information(self, communication_object):
        '''get status of auto-focus.
             
        Input:
         communication_object: Object that connects to microscope specific software
         
        Output:
         positions_dict: dictionary {'absolute': z_abs, 'focality_corrected': z_cor} with focus position in mum
        '''
        autofocus_info = {'initial_focus': self._initial_autofocus_position,
                          'use': self.get_use_autofocus(),
                          'experiment': self.get_init_experiment(communication_object),
                          'camera': self.default_camera,
                          'live_mode': self.use_live_mode,
                          'reference_object': self.get_focus_reference_obj(),
                          'delta_z' : self.last_delta_z}
        return autofocus_info

    def set_component(self, settings):
        '''Switch on/off the use of auto-focus
        
        Input:
         settings: dictionary {use_auto_focus: True/False}. If empty do not change setting
        
        Output:
         new_settings: dictionary with updated status
        '''
        new_settings = {}
        if settings:
            self.set_use_autofocus(settings['use_auto_focus'])
        new_settings['use_auto_focus'] = self.use_autofocus        
        return new_settings


    def set_use_autofocus(self, flag):
        '''Set flag to enable the use of autofocus.
        
        Input:
         flag: if True, use autofocus
         
        Output:
         use_autofocus: status of use_autofocus
         
        If no autofocus position is stored, store current position.
        '''
        log_method(self, 'set_use_autofocus')
        self.use_autofocus = flag
        return self.use_autofocus
 
 
    def get_use_autofocus(self):
        '''Return flag about autofocus usage
        
        Input:
         none
         
        Output:
         use_autofocus: boolean varaible indicating if autofocus should be used
        '''
        log_method(self, 'get_use_autofocus')
        return self.use_autofocus

    def get_autofocus_ready(self, communication_object):
        '''Check if auto-focus is ready
        
        Input:
         communication_object: Object that connects to microscope specific software
         
        Output:
         is_ready: True, if auto-focus is ready
        '''
        log_method(self, 'get_autofocus_ready')
        try:
            is_ready = communication_object.get_autofocus_ready()
        except AutofocusError:
            is_ready = False
        return is_ready


    def find_surface(self, communication_object):
        '''Find cover slip using Definite Focus 2. Does not store found position.
        
        Input:
         communication_object: Object that connects to microscope specific software
         
        Output: 
         z: position of focus drive after find surface
        '''
        log_method(self, 'find_surface')
        z = communication_object.find_surface()
#         self.store_focus()
        return z


    def set_focus_reference_obj(self, focusReferenceObj):
        '''Set object from class ImagingSystem (module samples) used as zero plane for autofocus.
        Input:
         focusReferenceObj: Sample object used as reference for autofocus
        
        Output:
         none
        '''
        self.focusReferenceObj = focusReferenceObj


    def get_focus_reference_obj(self):
        '''Get object from class ImagingSystem (module samples) used as zero plane for autofocus.
        
        Input:
         none
         
        Output:
         focusReferenceObj: Sample object used as reference for autofocus
         '''
        focusReferenceObj = self.focusReferenceObj
        return focusReferenceObj 
        
        
    def store_focus(self, communication_object, focusReferenceObj):
        '''Store actual focus position as offset from coverslip.
        
        Input:
         communication_object: Object that connects to microscope specific software
         focusReferenceObj: Sample object used as reference for autofocus
         
        Output:
         z: position of focus drive after store focus
        '''
        log_method(self, 'store_focus')
        z = communication_object.store_focus()
        self.set_focus_reference_obj(focusReferenceObj)
        self.initialized_objective = self.objective_changer_instance.get_objective_information(communication_object)['name']
        print ('Autofocus position {} stored for {}.'.format(z, self.initialized_objective))
        return z

        
    def recall_focus(self, communication_object, reference_object, verbose = False, pre_set_focus = True):
        '''Find difference between stored focus position and actual autofocus position.
        
        Input:
         communication_object: Object that connects to microscope specific software
         reference_object: object of type sample (ImagingSystem) used to correct for xyz offset between different objectives
         verbose: if True, print debug messages (Default: False)
         pre_set_focus: Move focus to previous auto-focus position. This makes definite focus more robust
         
        Output:
         deltaZ: difference between stored z position of focus drive and position after recall focus
         
        Recall focus will move the focus drive to it's stored position.
        Will try to recover if  autofocus failed
        '''
        log_method(self, 'recall_focus')
        if not self.get_use_autofocus():
            # Get store difference between _initial_autofocus_position and autofocus position from last 'Recall Focus'
            deltaZ = self.last_delta_z
            return deltaZ
        
        try:
            z = communication_object.recall_focus(pre_set_focus = pre_set_focus)
            if verbose:
                print ('From hardware.FocusDrive.recall_focus: recall_focus = {}'.format(z))
        except AutofocusNotSetError as error:
            raise AutofocusNotSetError(message = error.message, error_component = self, focusReferenceObj = reference_object) 

        except AutofocusObjectiveChangedError as error:
            raise AutofocusObjectiveChangedError(message = error.message, error_component = self, focusReferenceObj = reference_object) 

        except AutofocusError as error:
            log_warning(error.message, 'recall_focus')
            z = communication_object.recover_focus()
            if verbose:
                print ('From hardware.FocusDrive.recall_focus: recover_focus = {}'.format(z))
            z = self.store_focus(communication_object, focusReferenceObj = reference_object)
            if verbose:
                print ('From hardware.FocusDrive.recall_focus: store_focus = {}'.format(z))
            log_message('Autofocus recoverd at {}'.format(z), 'recall_focus')
        
        
        # _initial_autofocus_position was saved position when autofocus was initialized the first time. 
        # deltaZ is the difference between the recalled z-position and the saved position amd is identical to focus drift or non-even sample
        deltaZ = z - self._initial_autofocus_position
        
        # Store delta_z as backup if auto focus should not be used
        self.last_delta_z = deltaZ
        if verbose:
            print ('From hardware.FocusDrive.recall_focus: _initial_autofocus_position, = {}, delta = {}'.format(self._initial_autofocus_position, deltaZ))
        log_message(('Autofocus original position in hardware {}'
                     '\nAutofocus new position in hardware {}'
                     '\nAutofocus delta position in hardware {}').format(self._initial_autofocus_position, z, deltaZ),
                        methodName = 'recall_focus')
        return deltaZ

################################################################################################

################################################################################################
        
class Pump(MicroscopeComponent):
    '''Class to describe and operate pump
    '''
    def __init__(self, pump_id, seconds = 1, port='COM1', baudrate=19200):
        '''Describe and operate pump
        
        Input:
         pump_id: string with unique stage id
         seconds: the number of seconds pump is activated
         port: com port, default = 'COM1'
         baudrate: baudrate for connection, can be set on pump, typically = 19200

         
        Output:
         none
        '''
        log_method(self, '__init__')
        super(Pump, self).__init__(pump_id)
#         self.pump=pumpObject.pump
        self.set_connection(port, baudrate)
        self.set_time(seconds)


    def set_connection(self, port, baudrate):
        '''Set communication parameters for pump.
        
        Input:
         port: com port, default = 'COM1'
         baudrate: baudrate for connection, can be set on pump, typically = 19200

        Output:
         none
        '''
        log_method(self, 'set_connection')
        self.port = port
        self.baudrate = baudrate

        
    def get_connection(self):
        '''Get communication parameters for pump.
        
        Input:
         none
         
        Output:
         conPar: dictionary with 
                 port: com port, default = 'COM1'
                 baudrate: baudrate for connection, can be set on pump, typically = 19200

        '''
        log_method(self, 'get_connection')
        return (self.port, self.baudrate)

    
    def set_time(self, seconds):
        '''Set time pump is activated.
        
        Input:
         seconds: time in seconds

        Output:
         none
        '''
        log_method(self, 'set_time')
        self.time = seconds

        
    def get_time(self):
        '''Get communication parameters for pump.
        
        Input:
         none
         
        Output:
         seconds: time in seconds

        '''
        log_method(self, 'get_time')
        return (self.time)
    
        
    def trigger_pump(self, communication_object):
        '''trigger pump
        
        Input:
         communication_object: Object that connects to microscope specific software
         
        Output:
         none
        '''
        log_method(self, 'trigger_pump')
        conPar=self.get_connection()
        seconds=self.get_time()
        communication_object.connection.trigger_pump(seconds=seconds, port=conPar[0], baudrate=conPar[1])


