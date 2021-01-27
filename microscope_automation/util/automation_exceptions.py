"""
Classes for exceptions
Do not name module exceptions. It will conflict with system exceptions.
Created on Jun 7, 2017

@author: winfriedw
"""

from .automation_messages_form_layout import error_message

# global variable to control blocking behavior of error messages
blocking = True


################################################################################
#
# Helper functions
#
################################################################################


def set_error_blocking(block):
    """Set blocking behavior of error dialogs.

    Input:
     block: if True use modal dialog for error reporting, otherwise print message

    Output:
     None
    """
    global blocking
    blocking = block


def get_error_blocking():
    """Retrieve blocking behavior of error dialogs.

    Input:
     none
    Output:
     blocking: if True use modal dialog for error reporting, otherwise print message

    Output:
     None
    """
    return blocking


################################################################################
#
# Base exception
#
################################################################################


class AutomationError(Exception):
    """Base exception for all errors in package microscopeautomation"""

    def __init__(self, message=None, error_component=None):
        """Initialize automation exceptions.

        Input:
         message: error message

         error_component: instance of hardware instance that caused exception.
         Default: None

        Output:
         none
        """
        self.message = message
        self.error_component = error_component

    def __str__(self):
        return repr(self.message)


################################################################################
#
# Hardware exceptions
#
################################################################################
class HardwareError(AutomationError):
    """Exception for failures in hardware."""

    def error_dialog(self):
        """Show error message to user.

        Input:
         none

        Output:
         none
        """
        return error_message(
            (
                "Hardware Error."
                "\nPlease check for problems with hardware\n"
                " e.g. laser safety not engaged"
            ),
            return_code=False,
            blocking=get_error_blocking(),
        )


class HardwareDoesNotExistError(HardwareError):
    """Exception if hardware was not defined."""

    def error_dialog(self, advice=""):
        """Show error message to user.

        Input:
         none

        Output:
         none
        """
        return error_message(
            ("Hardware Does Not Exist Error:" "\n'{}'' does not exist.\n'{}'").format(
                self.error_component, advice
            ),
            return_code=False,
            blocking=get_error_blocking(),
        )


class CrashDangerError(AutomationError):
    """Exception if danger for hardware was detected."""

    def error_dialog(self, advice=""):
        """Show error message to user.

        Input:
         advice: str with advice to user of how to avoid crash.

        Output:
         none
        """
        return error_message(
            'Crash Danger Error:\n"{}"\n{}'.format(self.message, advice),
            return_code=False,
            blocking=get_error_blocking(),
        )


class HardwareNotReadyError(AutomationError):
    """Exception if hardware is not ready for experiment."""

    def error_dialog(self, advice=""):
        """Show error message to user.

        Input:
         advice: str with advice to user of how to avoid crash.

        Output:
         none
        """
        return error_message(
            'Hardware is not ready for experiment:\n"{}"\n{}'.format(
                self.message, self.error_component
            ),
            return_code=False,
            blocking=get_error_blocking(),
        )


class HardwareCommandNotDefinedError(AutomationError):
    """Exception if experiment is not defined for this microscope."""

    def error_dialog(self, advice=""):
        """Show error message to user.

        Input:
         advice: str with advice to user of how to avoid crash.

        Output:
         none
        """
        return error_message(
            'Action not supported by hardware:\n"{}"\n{}'.format(
                self.message, self.error_component
            ),
            return_code=False,
            blocking=get_error_blocking(),
        )


################################################################################
#
# Autofocus exceptions
#
################################################################################
class AutofocusError(HardwareError):
    """Exception if autofocus failed."""

    def __init__(self, message=None, error_component=None, focus_reference_obj_id=None):
        """Raise autofocus exception.

        Input:
         message: error message

         error_component: instance of hardware instance that caused exception
         Default: None

         focus_reference_obj_id: Sample object used as reference for autofocus

         message: Test to display as error message

        Output:
         none
        """
        self.message = message
        self.error_component = error_component
        self.set_focus_reference_obj_id(focus_reference_obj_id)

    def __str__(self):
        return repr(self.message)

    def error_dialog(self):
        """Show error message to user.

        Input:
         none

        Output:
         none
        """
        return error_message(
            (
                "Autofocus did not work.\n"
                "Please fix the following issue:\n{}\n"
                "You will be prompted to refocus."
            ).format(self.message),
            blocking=get_error_blocking(),
        )

    def set_focus_reference_obj_id(self, focus_reference_obj_id):
        """Set object (typcially plate) that is used as reference for autofocus offset.

        Input:
         focus_reference_obj_id: Sample object used as reference for autofocus

        Output:
         None
        """
        self.focus_reference_obj_id = focus_reference_obj_id

    def get_focus_reference_obj_id(self):
        """Retrieve object (typcially plate) that is used as reference for autofocus
         offset.

        Input:
         none

        Output:
         focus_reference_obj_id: Sample object used as reference for autofocus
        """
        if self.focus_reference_obj_id is None:
            raise AutofocusNoReferenceObjectError(
                message="Could not retrieve focus reference."
            )
        return self.focus_reference_obj_id


class AutofocusObjectiveChangedError(AutofocusError):
    """Exception if objective was changed since autofocus was initialized

    Input:
     focus_reference_obj_id: Sample object used as reference for autofocus

     message: Test to display as error message

    Output:
     none
    """

    def error_dialog(self):
        """Show error message to user.

        Input:
         none

        Output:
         none
        """
        return error_message(
            (
                "Objective changed since last use of autofocus.\n"
                "Error message:\n'{}'"
            ).format(self.message),
            blocking=get_error_blocking(),
        )


class AutofocusNotSetError(AutofocusError):
    """Exception if objective was changed since autofocus was initialized

    Input:
     focus_reference_obj_id: Sample object used as reference for autofocus

     message: Test to display as error message
    """

    def error_dialog(self):
        """Show error message to user.

        Input:
         none

        Output:
         none
        """
        return error_message(
            'Autofocus position not set.\nError message:\n"{}"'.format(self.message),
            blocking=get_error_blocking(),
        )


class AutofocusNoReferenceObjectError(AutofocusError):
    """Exception if no reference object was selected for autofocus

    Input:
     focus_reference_obj_id: Sample object used as reference for autofocus

     message: Test to display as error message
    """

    def error_dialog(self):
        """Show error message to user.

        Input:
         none

        Output:
         none
        """
        return error_message(
            'No autofocus reference.\nError message:\n"{}"'.format(self.message),
            blocking=get_error_blocking(),
        )


################################################################################
#
# Focus Drive exceptions
#
################################################################################
class LoadNotDefinedError(HardwareError):
    """Exception if load position for focus drive is not defined."""

    def error_dialog(self):
        """Show error message to user.

        Input:
         none

        Output:
         none
        """
        return error_message(
            (
                "Please move objective to load position or cancel"
                " program.\nError message:\n'{}'"
            ).format(self.message),
            return_code=False,
            blocking=get_error_blocking(),
        )


class WorkNotDefinedError(HardwareError):
    """Exception if work position for focus drive is not defined."""

    def error_dialog(self):
        """Show error message to user.

        Input:
         none

        Output:
         none
        """
        return error_message(
            (
                "Please move objective to work position or cancel"
                " program.\nError message:\n'{}'"
            ).format(self.message),
            return_code=False,
            blocking=get_error_blocking(),
        )


################################################################################
#
# Objective exceptions
#
################################################################################
class ObjectiveNotDefinedError(HardwareError):
    """Exception if selected objective was not defined."""

    def error_dialog(self):
        """Show error message to user.

        Input:
         none

        Output:
         none
        """
        return error_message(
            'Objective not defined.\nError message:\n"{}"'.format(self.message),
            return_code=False,
            blocking=get_error_blocking(),
        )


################################################################################
#
# Acquisition exceptions
#
################################################################################
class ExperimentError(HardwareError):
    """Exception for failures experiment execution."""

    def error_dialog(self):
        """Show error message to user.

        Input:
         none

        Output:
         none
        """
        return error_message(
            (
                "Cannot execute experiment."
                "\nPlease check for problems with hardware\n"
                " e.g. laser safety not engaged"
            ),
            return_code=False,
            blocking=get_error_blocking(),
        )


class ExperimentNotExistError(ExperimentError):
    """Exception for failures experiment execution."""

    def error_dialog(self):
        """Show error message to user.

        Input:
         none

        Output:
         none
        """
        return error_message(
            'Experiment "{}" does not exist.'.format(self.error_component),
            return_code=False,
            blocking=get_error_blocking(),
        )


################################################################################
#
# I/O exceptions
#
################################################################################
class IOError(AutomationError):
    """Exception for I/O errors."""

    def error_dialog(self):
        """Show error message to user.

        Input:
         none

        Output:
         none
        """
        return error_message(
            'I/O Error.\nError:\n"{}"'.format(self.message),
            return_code=False,
            blocking=get_error_blocking(),
        )


class FileExistsError(AutomationError):
    """Exception if file exists to prevent overriding it."""

    def error_dialog(self):
        """Show error message to user.

        Input:
         none

        Output:
         none
        """
        return error_message(
            ("A file with this name already exists.\n" "Error:\n'{}'").format(
                self.message
            ),
            return_code=False,
            blocking=get_error_blocking(),
        )


class MetaDataNotSavedError(AutomationError):
    """Exception if data could not be saved to meta data file."""

    def error_dialog(self):
        """Show error message to user.

        Input:
         none

        Output:
         none
        """
        return error_message(
            ("Could not save meta data to file.\n" "Error:\n'{}'").format(self.message),
            return_code=False,
            blocking=get_error_blocking(),
        )


################################################################################
#
# Program flow exceptions
#
################################################################################
class StopCollectingError(AutomationError):
    """Stop collecting sample positions."""

    def error_dialog(self):
        """Show error message to user.

        Input:
         none

        Output:
         none
        """
        return error_message(
            ("User stopped collecting image positions.\n" "Message:\n'{}'").format(
                self.message
            ),
            return_code=False,
            blocking=get_error_blocking(),
        )
