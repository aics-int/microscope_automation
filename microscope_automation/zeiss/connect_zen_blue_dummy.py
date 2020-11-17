"""
Dummy function for ZEN blue conection
Created on Sep 23, 2016

@author: winfriedw
"""
from shutil import copy2

try:
    import pathlib
except ImportError:
    import pathlib2 as pathlib  # noqa
import os

# if True, print out debug messages
test_messages = False


class MicroscopeStatus(object):
    """Create instance of this class to keeps track of microscope status.

    Input:
     none

    Output:
     none
    """

    def __init__(self):
        self._xPos = 60000
        self._yPos = 40000
        self._zPos = 500
        self._objective_position = 0
        self._objective_name = "Dummy Objective"

    @property
    def xPos(self):
        """Get absolute x position for stage"""
        if test_messages:
            print(("MicroscopeStatus returned x as {}".format(self._xPos)))
        return self._xPos

    @xPos.setter
    def xPos(self, x):
        """Set absolute x position for stage"""
        self._xPos = x
        if test_messages:
            print(("MicroscopeStatus set x as {}".format(self._xPos)))

    @property
    def yPos(self):
        """Get absolute y position for stage"""
        if test_messages:
            print(("MicroscopeStatus returned y as {}".format(self._yPos)))
        return self._yPos

    @yPos.setter
    def yPos(self, y):
        """Set absolute y position for stage"""
        self._yPos = y
        if test_messages:
            print(("MicroscopeStatus set y as {}".format(self._yPos)))

    @property
    def zPos(self):
        """Get absolute z position for focus drive"""
        if test_messages:
            print(("MicroscopeStatus returned z as {}".format(self._zPos)))
        return self._zPos

    @zPos.setter
    def zPos(self, z):
        """Set absolute z position for focus drive"""
        self._zPos = z
        if test_messages:
            print(("MicroscopeStatus set z as {}".format(self._zPos)))

    @property
    def objective_position(self):
        """Get position for objective in objective changer"""
        if test_messages:
            print(
                (
                    "MicroscopeStatus returned objective_position as {}".format(
                        self._objective_position
                    )
                )
            )
        return self._objective_position

    @objective_position.setter
    def objective_position(self, objective_position):
        """Set position for objective in objective changer"""
        self._objective_position = objective_position
        if test_messages:
            print(
                (
                    "MicroscopeStatus set objective_position as {}".format(
                        self._objective_position
                    )
                )
            )

    @property
    def objective_name(self):
        """Get name for actual objective"""
        if test_messages:
            print(
                (
                    "MicroscopeStatus returned objective_name as {}".format(
                        self._objective_name
                    )
                )
            )
        return self._objective_name

    @objective_name.setter
    def objective_name(self, objective_name):
        """Set name for actual objective"""
        self._objective_name = objective_name
        if test_messages:
            print(
                (
                    "MicroscopeStatus set objective_name as {}".format(
                        self._objective_name
                    )
                )
            )


class Focus(object):
    def __init__(self, microscope_status):
        """Class in Zeiss.Micro.Scripting.Core namespace that gives access to focus.

        Input:
         none

        Output:
         none
        """
        # Properties of class ZenFocus
        self.TargetPosition = 0
        self._microscope_status = microscope_status

    # Attributes for focus
    @property
    def ActualPosition(self):
        """Get the current z position for focus drive"""
        return self._microscope_status.zPos

    # Methods of class ZenFocus
    def Apply(self):
        """Applies the target parameter values.

        Input:
         none

        Output:
         none
        """
        self._microscope_status.zPos = self.TargetPosition

    def MoveTo(self, z):
        """Moves to the specified focus position.

        Input:
         z: Focus position in um

        Output:
         none
        """
        self._microscope_status.zPos = z
        return None


class ObjectiveChanger(object):
    def __init__(self, microscope_status):
        self.TargetPosition = 1
        self.Magnification = 10
        self._microscope_status = microscope_status

    @property
    def ActualPositionName(self):
        """Get name of actual objectve"""
        return self._microscope_status.objective_name

    @property
    def ActualPosition(self):
        """Get name of actual objective position in ojbective turret"""
        return self._microscope_status.objective_position

    def Apply(self):
        self._microscope_status.objective_position = self.TargetPosition

    def GetMagnificationByPosition(self, position):
        return ""

    def GetNameByPosition(self, position):
        return None


class Stage(object):
    def __init__(self, microscope_status):
        self.TargetPositionY = 0
        self._microscope_status = microscope_status

    @property
    def ActualPositionX(self):
        """Get actual x position for stage"""
        return self._microscope_status.xPos

    @property
    def ActualPositionY(self):
        """Get actual y position for stage"""
        return self._microscope_status.yPos

    def Apply(self):
        self._microscope_status.xPos = self.TargetPositionX
        self._microscope_status.yPos = self.TargetPositionY


class Devices(object):
    """Simulated device objects"""

    def __init__(self, microscope_status):
        """Create Zen devices object"""
        self.Focus = Focus(microscope_status)
        self.ObjectiveChanger = ObjectiveChanger(microscope_status)
        self.Stage = Stage(microscope_status)


######################################################################################
#
# Classes for Acquisition
#
######################################################################################


class Experiments(object):
    def __init__(self, microscope_status):
        self._microscope_status = microscope_status

    def GetByName(self, experiment):
        return experiment

    def ActiveExperiment(self):
        return "Experiment"

    def Contains(self, expClass):
        return True


class Image(object):
    def Save_2(self, fileName):
        if not (os.path.exists(fileName)):
            exampleImage = "../data/testImages/WellEdge_0.czi"
            copy2(exampleImage, fileName)


class Acquisition(object):
    """Simulate image acquisition"""

    def __init__(self, microscope_status):
        self.Experiments = Experiments(microscope_status)
        self.storedAutofocus = 0
        self._microscope_status = microscope_status

    def _set_objective(self, experiment):
        """Sets for debug purposes active objective name based on experiment name."""
        if "10x" in experiment:
            self._microscope_status.objective_name = "Plan-Apochromat 10x/0.45"
            self._microscope_status.objective_position = 1
        if "20x" in experiment:
            self._microscope_status.objective_name = "Plan-Apochromat 20x/0.8 M27"
            self._microscope_status.objective_position = 2
        if "100x" in experiment:
            self._microscope_status.objective_name = (
                "C-Apochromat 100x/1.25 W Korr UV VIS IR"
            )
            self._microscope_status.objective_position = 3

    def Execute(self, experiment):
        self._set_objective(experiment)
        im = Image()
        return im

    def AcquireImage_3(self, expClass):
        self._set_objective(expClass)
        im = Image()
        return im

    def StartLive(self):
        im = Image()
        return im

    def StartLive_2(self, experiment):
        self._set_objective(experiment)
        im = Image()
        return im

    def StopLive_2(self, expClass):
        pass

    def StopLive(self):
        pass

    def FindSurface(self):
        """Finds the surface using definite focus.

        Input:
         none

        Output:
         none
        """
        self._microscope_status.zPos = 9000
        return None

    def StoreFocus(self):
        """Initializes the definite focus on the current position.

        Input:
         none

        Output:
         none
        """
        self.storedAutofocus = self._microscope_status.zPos
        return self.storedAutofocus

    def RecallFocus(self):
        """Finds the surface + offset.

        Input:
         none

        Output
         none
        """
        self._microscope_status.zPos = self.storedAutofocus + 100
        return None

    def FindAutoFocus(self):
        """Use the autofocus of the current experiment to find the sample.

        Input:
         none

        Output:
         none
        """
        self._microscope_status.zPos = self.storedAutofocus
        return None

    def FindAutoFocus_2(self, experiment):
        """Use the autofocus of the current experiment to find the sample.

        Input:
         experiment: String name of experiment in ZEN blue software

        Output:
         none
        """
        self._microscope_status.zPos = self.storedAutofocus
        return None


######################################################################################
#
# Classes for Documents
#
######################################################################################


class Documents(object):
    def RemoveAll(self, remove):
        pass

    def Add(self, image):
        pass


######################################################################################
#
# Classes for Application
#
######################################################################################


class Application(object):
    def __init__(self, microscope_status):
        self.Documents = Documents()
        self.microscope_status = microscope_status

    def Pause(self, message):
        pass

    def RunMacro(self, macro_name):
        print(("Test mode: Running Macro: ", macro_name))

    def RunMacro_2(self, macro_name, macro_params):
        print(
            (
                "Test mode: Running Macro: "
                + macro_name
                + " | Parameter: "
                + macro_params[0]
            )
        )


######################################################################################
#
# Class GetActiveObject
#
######################################################################################


class GetActiveObject(object):
    """Simulation for connection to ZEN blue software."""

    def __init__(self, name):
        """
        Simmulation: Connect to Carl Zeiss ZEN blue Python API
        """
        microscope_status = MicroscopeStatus()
        self.Devices = Devices(microscope_status)
        self.Acquisition = Acquisition(microscope_status)
        self.Application = Application(microscope_status)
