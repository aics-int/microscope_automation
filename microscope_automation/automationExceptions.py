'''
Classes for exceptions
Do not name module exceptions. It will conflict with system exceptions.
Created on Jun 7, 2017

@author: winfriedw
'''

# global variable to control blocking behavior of error messages
blocking = True

# from .automationMessagesFormLayout import error_message
from automationMessagesFormLayout import error_message

############################################################################################
#
# Helper functions
#
############################################################################################

def set_error_bocking(block):
    '''Set blocking behavior of error dialogs.
    
    Input:
     block: if True use modal dialog for error reporting, otherwise print message
     
    Output:
     None
    '''
    global blocking
    blocking = block
    
def get_error_bocking():
    '''Retrieve blocking behavior of error dialogs.
    
    Input:
     none
    Output:
     blocking: if True use modal dialog for error reporting, otherwise print message
     
    Output:
     None
    '''
    return blocking
    
############################################################################################
#
# Base exception
#
############################################################################################

class AutomationError(Exception):
    '''Base exception for all errors in package microscopeautomation
    ''' 
    def __init__(self, message = None, error_component = None):
        '''Initialize automation exceptions.
        
        Input:
         message: error message
         error_component: instance of hardware instance that caused exception
                             Default: None
        
        Output:
         None
        '''
        self.message = message
        self.error_component = error_component 

    def __str__(self):
        return repr(self.message)

############################################################################################
#
# Hardware exceptions
#
############################################################################################
class HardwareError(AutomationError):
    '''Exception for failures in hardware.
    '''
    def error_dialog(self):
        '''Show error message to user.
        
        Input:
         none
         
        Output:
         none
        '''
        return error_message('Hardware Error:\n"{}"\nPlease check for problems with hardware\n e.g. laser safety not engaged'.format(self.message), returnCode=False, blocking = get_error_bocking())

class CrashDangerError(AutomationError):
    '''Exception if danger for hardware was detected.
    '''
    def error_dialog(self, advice=''):
        '''Show error message to user.
        
        Input:
         advice: str with advice to user of how to avoid crash.
         
        Output:
         none
        '''
        return error_message('Crash Danger Error:\n"{}"\n{}'.format(self.message, advice), returnCode=False, blocking = get_error_bocking())

class HardwareNotReadyError(AutomationError):
    '''Exception if hardware is not ready for experiment.
    '''
    def error_dialog(self, advice=''):
        '''Show error message to user.
        
        Input:
         advice: str with advice to user of how to avoid crash.
         
        Output:
         none
        '''
        return error_message('Hardware is not ready for experiment:\n"{}"\n{}'.format(self.message, self.error_component), returnCode=False, blocking = get_error_bocking())

############################################################################################
#
# Autofocus exceptions
#
############################################################################################
class AutofocusError(HardwareError):
    '''Exception if autofocus failed
    '''
    def __init__(self,  message = None, error_component = None, focusReferenceObj = None):
        '''Raise autofocus exception.
        
        Input:
         message: error message
         error_component: instance of hardware instance that caused exception
                             Default: None
         focusReferenceObj: Sample object used as reference for autofocus
         message: Test to display as error message
        '''
        self.message = message
        self.error_component = error_component
        self.set_focus_reference_obj(focusReferenceObj)
               
    def __str__(self):
        return repr(self.message)
    
    def error_dialog(self):
        '''Show error message to user.
        
        Input:
         none
         
        Output:
         none
        '''
        return error_message('Autofocus did not work.\nPlease fix the following issue:\n{}\nYou will be prompted to refocus.'.format(self.message), blocking = get_error_bocking())
        
    def set_focus_reference_obj(self, focusReferenceObj):
        '''Set object (typcially plate) that is used as reference for autofocus offset.

        Input:
         focusReferenceObj: Sample object used as reference for autofocus
         
        Output:
         None
        '''
        self.focusReferenceObj = focusReferenceObj

    def get_focus_reference_obj(self):
        '''Retrieve object (typcially plate) that is used as reference for autofocus offset.

        Input:
         None
         
        Output:
         focusReferenceObj: Sample object used as reference for autofocus
        '''
        if self.focusReferenceObj is None:
            raise AutofocusNoReferenceObjectError(message='Could not retrieve focus reference.')
        return self.focusReferenceObj

class AutofocusObjectiveChangedError(AutofocusError):
    '''Exception if objective was changed since autofocus was initialized

    Input:
     focusReferenceObj: Sample object used as reference for autofocus
     message: Test to display as error message
    '''
     
    def error_dialog(self):
        '''Show error message to user.
        
        Input:
         none
         
        Output:
         none
        '''
        return error_message('Objective changed since last use of autofocus.\nError message:\n"{}"'.format(self.message), blocking = get_error_bocking())

class AutofocusNotSetError(AutofocusError):
    '''Exception if objective was changed since autofocus was initialized

    Input:
     focusReferenceObj: Sample object used as reference for autofocus
     message: Test to display as error message
    '''
     
    def error_dialog(self):
        '''Show error message to user.
        
        Input:
         none
         
        Output:
         none
        '''
        return error_message('Autofocus position not set.\nError message:\n"{}"'.format(self.message), blocking = get_error_bocking())
        
class AutofocusNoReferenceObjectError(AutofocusError):
    '''Exception if no reference object was selected for autofocus

    Input:
     focusReferenceObj: Sample object used as reference for autofocus
     message: Test to display as error message
    '''
     
    def error_dialog(self):
        '''Show error message to user.
        
        Input:
         none
         
        Output:
         none
        '''
        return error_message('No autofocus reference.\nError message:\n"{}"'.format(self.message), blocking = get_error_bocking())

############################################################################################
#
# Focus Drive exceptions
#
############################################################################################
class LoadNotDefinedError(HardwareError):
    '''Exception if load position for focus drive is not defined.
    '''
    def error_dialog(self):
        '''Show error message to user.
        
        Input:
         none
         
        Output:
         none
        '''
        return error_message('Please move objective to load position or cancel program.\nError message:\n"{}"'.format(self.message), returnCode = False, blocking = get_error_bocking())

############################################################################################
#
# Objective exceptions
#
############################################################################################
class ObjectiveNotDefinedError(HardwareError):
    '''Exception if selected objective was not defined.
    '''
    def error_dialog(self):
        '''Show error message to user.
        
        Input:
         none
         
        Output:
         none
        '''
        return error_message('Objective not defined.\nError message:\n"{}"'.format(self.message), returnCode = False, blocking = get_error_bocking())



############################################################################################
#
# Acquisition exceptions
#
############################################################################################
class ExperimentError(HardwareError):
    '''Exception for failures experiment execution.
    '''
    def error_dialog(self):
        '''Show error message to user.
        
        Input:
         none
         
        Output:
         none
        '''
        return error_message('Cannot execute experiment.\nPlease check for problems with hardware\n e.g. laser safety not engaged', returnCode=False, blocking = get_error_bocking())

class ExperimentNotExistError(ExperimentError):
    '''Exception for failures experiment execution.
    '''
    def error_dialog(self):
        '''Show error message to user.
        
        Input:
         none
         
        Output:
         none
        '''
        return error_message('Experiment "{}" does not exist.'.format(self.error_component), returnCode=False, blocking = get_error_bocking())

############################################################################################
#
# I/O exceptions
#
############################################################################################
class IOError(AutomationError):
    '''Exception for I/O errors.
    '''
    def error_dialog(self):
        '''Show error message to user.
        
        Input:
         none
         
        Output:
         none
        '''
        return error_message('I/O Error.\nError:\n"{}"'.format(self.message), returnCode=False, blocking = get_error_bocking())
        
class FileExistsError(AutomationError):
    '''Exception if file exists to prevent overriding it.
    '''
    def error_dialog(self):
        '''Show error message to user.
        
        Input:
         none
         
        Output:
         none
        '''
        return error_message('A file with this name already exists.\nError:\n"{}"'.format(self.message), returnCode=False, blocking = get_error_bocking())

class MetaDataNotSavedError(AutomationError):
    '''Exception if data could not be saved to meta data file.
    '''
    def error_dialog(self):
        '''Show error message to user.
        
        Input:
         none
         
        Output:
         none
        '''
        return error_message('Could not save meta data to file.\nError:\n"{}"'.format(self.message), returnCode=False, blocking = get_error_bocking())

############################################################################################
#
# Program flow exceptions
#
############################################################################################
class StopCollectingError(AutomationError):
    '''Stop collecting sample positions.
    '''
    def error_dialog(self):
        '''Show error message to user.
        
        Input:
         none
         
        Output:
         none
        '''
        return error_message('User stopped collecting image positions.\nMessage:\n"{}"'.format(self.message), returnCode=False, blocking = get_error_bocking())
        
