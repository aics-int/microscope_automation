'''
Dummy function for generic microscope connection. Used to test hardware functions.
Created on Sep 9, 2020

@author: fletcher.chapin
'''
from shutil import copy2
from lxml import etree
import time
import os.path
import logging

try:
    from pathlib import Path
except ImportError:
    from pathlib2 import Path
import os

from .load_image_czi import LoadImageCzi
from .RS232_dummy import Braintree
from .automation_exceptions import HardwareError, AutofocusError, \
    AutofocusObjectiveChangedError, AutofocusNotSetError, LoadNotDefinedError,  \
    WorkNotDefinedError, ExperimentError, ExperimentNotExistError, \
    HardwareDoesNotExistError, HardwareCommandNotDefinedError

# if True, print out debug messages
test_messages = False


def connection_selector(software_simulated):
    if software_simulated == "ZEN Blue":
        return ConnectZenBlueDummy()
    elif software_simulated == "Slidebook":
        return ConnectSlidebookDummy()
    else:
        raise HardwareDoesNotExistError("Software " + software_simulated
                                        + " not supported by microscope_automation")


class ConnectZenBlueDummy():

    def __init__(self):
        # create logger
        self.log = logging.getLogger('microscopeAutomation connect_zen_blue')

        # predefine internal settings
        self.zLoad = None
        self.zWork = None
        self.image = None

        self.Zen = GetActiveObject("Zeiss.Micro.Scripting.ZenWrapperLM")

        # Save stored position. We will use this position to move the objective to this position before recalling this position.
        # If the stored position is close to the find_surface position, Definite Focus works much faster.
        self.DFObjective = None
        self.DFStoredFocus = None
        self.lastKnownFocusPosition = None
        self.set_autofocus_not_ready()

        self.log.info('Connected to ZEN')

    ##################################################################################################################
    #
    # Methods to acquire images
    #
    ##################################################################################################################

    def snap_image(self, experiment=None):
        """Snap image with parameters defined in experiment.
        Image object is stored in self.image.
        Acquires single image from experiment (e.g. single slice of stack).

        Input:
         experiment: string with name of experiment as defined within Microscope software
         If None use active experiment.

        Output:
         none
        """
        self.log.info('snap image using experiment ', experiment)

        # if method switches objective the stored position for definite focus will be invalid.
        currentObjective = self.get_objective_name()

        try:
            # call ZEN API to set experiment
            if experiment is None:
                # use active experiment in software. Will fail if no experiment is set.
                try:
                    exp_class = self.Zen.Acquisition.Experiments.ActiveExperiment
                except Exception:
                    raise ExperimentError('No active experiment is defined.')
            else:
                exp_class = self.Zen.Acquisition.Experiments.GetByName(experiment)
            # check if experiment exists
            if exp_class is not None and self.Zen.Acquisition.Experiments.Contains(exp_class):
                self.image = self.Zen.Acquisition.AcquireImage_3(exp_class)
            else:
                ExperimentNotExistError(experiment)
        except (ExperimentNotExistError, ExperimentError) as err:
            raise err
        except Exception:
            raise HardwareError('Error in snap_image.')

        # set flag for definite focus if objective was changed
        if currentObjective != self.get_objective_name() or self.get_objective_name() == '':
            self.set_autofocus_not_ready()

    def live_mode_start(self, experiment=None):
        '''Start live mode of ZEN software.

        Input:
         experiment: name of ZEN experiment (default = None)

        Output:
         imgLive: image of type ZenImage
        '''
        # if method switches objective the stored position for definite focus will be invalid.
        currentObjective = self.get_objective_name()

        try:
            if experiment:
                # get experiment as type ZenExperiment by name
                exp_class = self.Zen.Acquisition.Experiments.GetByName(experiment)
                if exp_class is None or not self.Zen.Acquisition.Experiments.Contains(exp_class):
                    raise ExperimentNotExistError(experiment)
                # Reason for the duplicate try except block: One specific experiment - WellTile_10x
                # fails to enter live mode the first time the execution function is called. Hence, it needs
                # a second call if the first one fails, and that seems to fix the bug.
                # Note - This is a temporary fix. There is something messed up with the oommunication object.
                # We will be looking into it further.
                try:
                    imgLive = self.Zen.Acquisition.StartLive_2(exp_class)
                except Exception:
                    imgLive = self.Zen.Acquisition.StartLive_2(exp_class)
            else:
                try:
                    exp_class = self.Zen.Acquisition.Experiments.ActiveExperiment
                except Exception:
                    raise ExperimentError('No active experiment is defined.')
                imgLive = self.Zen.Acquisition.StartLive_2(exp_class)
        except (ExperimentNotExistError, ExperimentError) as err:
            raise err
        except Exception:
            raise HardwareError('Error in live_mode_start.')

        # set flag for definite focus if objective was changed
        if currentObjective != self.get_objective_name() or self.get_objective_name() == '':
            self.set_autofocus_not_ready()

        return imgLive

    def live_mode_stop(self, experiment=None):
        '''Stop live mode of ZEN software.

        Input:
         experiment: name of ZEN experiment (default = None)

        Output:
         none
        '''
        try:
            if experiment:
                exp_class = self.Zen.Acquisition.Experiments.GetByName(experiment)
                if exp_class is None or not self.Zen.Acquisition.Experiments.Contains(exp_class):
                    raise ExperimentNotExistError(experiment)
                self.Zen.Acquisition.StopLive_2(exp_class)
            else:
                self.Zen.Acquisition.StopLive()
        except ExperimentNotExistError as err:
            raise err
        except Exception:
            raise HardwareError('Error in live_mode_stop.')

################################################################################
#
# Methods to control motorized xy stage
#
################################################################################

    def get_stage_pos(self):
        '''Return current position of Microscope stage.

        Input:
         none

        Output:
         xPos, yPos: x and y position of stage in micrometer
        '''
        # Get current stage position
        try:
            xPos = self.Zen.Devices.Stage.ActualPositionX
            yPos = self.Zen.Devices.Stage.ActualPositionY
        except Exception:
            raise HardwareError('Error in get_stage_pos.')
        return xPos, yPos

    def move_stage_to(self, xPos, yPos, zPos=None, experiment=None, test=False):

        '''Move stage to new position.

        Input:
         xPos, yPos: new stage position in micrometers.

         zPos, experiment: not used but included for consistency with Slidebook API

         test: if True return travel path and do not move stage

        Output:
         xPos, yPos: x and y position of stage in micrometer after stage movement (if test = False)

         x_path, y_path: projected travel path (if test = True)
        '''
        if xPos is None or yPos is None:
            raise HardwareError('Position not defined in move_stage_to.')

        if test:
            x_current = self.Zen.Devices.Stage.ActualPositionX
            y_current = self.Zen.Devices.Stage.ActualPositionY
            xy_path = [(x_current, y_current), (xPos, y_current), (xPos, yPos)]
            return xy_path

        try:
            self.Zen.Devices.Stage.TargetPositionX = xPos
            self.Zen.Devices.Stage.Apply()
            self.Zen.Devices.Stage.TargetPositionY = yPos
            self.Zen.Devices.Stage.Apply()
            # check new position
            xStage = self.Zen.Devices.Stage.ActualPositionX
            yStage = self.Zen.Devices.Stage.ActualPositionY
        except Exception:
            raise HardwareError('Error in move_stage_to.')
        return [xStage, yStage]

################################################################################
#
# Methods to control focus including soft- and hardware autofocus
#
################################################################################
    def set_autofocus_ready(self):
        '''Set flag that auto focus position for DF2 was stored and recall_focus should work.

        Input:
         none

        Output:
         none
        '''
        self.autofocusReady = True

    def set_autofocus_not_ready(self):
        '''Set flag that auto focus position for DF2 is not ready and recall_focus will not work.

        Input:
         none

        Output:
         none
        '''
        self.autofocusReady = False

    def get_autofocus_ready(self):
        '''Check if auto focus position for DF2 was stored and recall_focus should work.

        Raises AutofocusNotSetError if not ready.
        Raises AutofocusObjectiveChangedError if there is an issue with objective_name

        Input:
         none

        Output:
         ready: True if DF2 was initialized and recall_focus should work.
        '''
        objective_name = self.get_objective_name()
        if not self.autofocusReady:
            raise AutofocusNotSetError(message='Definite Focus is not ready.',
                                       error_component=objective_name)

        # do additional test to check if autofocus should work
        # a valid objective selected?
        if objective_name == '' or self.DFObjective is None:
            self.set_autofocus_not_ready()
            raise AutofocusError(message='No objective selected.',
                                 error_component=objective_name)
        # was objective changed since focus was stored?
        if self.DFObjective != objective_name:
            self.set_autofocus_not_ready()
            raise AutofocusObjectiveChangedError(message='Different objective was used to set focus position.',
                                                 error_component=objective_name)
        return True

    def set_last_known_focus_position(self, focusPostion):
        '''Stores focus position used for recovery if autofocus fails.

        Input:
         focusPostion: position in um to be used for autofocus recovery

        Output:
         none.
        '''
        self.lastKnownFocusPosition = focusPostion

    def recover_focus(self):
        '''Try to recover from autofocus failure.

        Input:
         none

        Output:
         none
        '''
        # Make sure valid objective is selected
        if self.get_objective_name() == '':
            self.set_autofocus_not_ready()
            raise AutofocusError(message='No objective selected.')

        # move focus to last know position
        self.move_focus_to(self.get_last_known_focus_position())
        self.store_focus()

    def find_surface(self):
        '''Find cover slip using Definite Focus 2.

        Input:
         none

        Output:
         z: position of focus drive after find surface
        '''
        # FindSurface always returns None
        # exception does not work
        try:
            self.Zen.Acquisition.FindSurface()
            z = self.Zen.Devices.Focus.ActualPosition
        except Exception:
            raise HardwareError('Error in find_surface.')

        # Track absolute focus position for recovery in case of Definite Focus failure
        self.set_last_known_focus_position(z)
        return z

    def store_focus(self):
        '''Store actual focus position as offset from coverslip.
        Stored focus position is lost when switching objective, even when returning to original objective.

        Input:
         none

        Output:
         z: position of focus drive after store focus
        '''
        # check if correct objective was selected
        if self.get_objective_name() == '':
            self.set_autofocus_not_ready()
            raise AutofocusError(message='No objective selected to store autofocus position.')
        try:
            self.Zen.Acquisition.StoreFocus()
            z = self.Zen.Devices.Focus.ActualPosition
        except Exception:
            raise HardwareError('Error in store_focus.')
        # Get objective used to set Definite Focus (Definite Focus will lose stored focus position after change of objective)
        self.DFObjective = self.get_objective_name()

        # Save stored position. We will use this position to move the objective to this position before recalling this positions
        # If the stored position is close to the find_surface position, Definite Focus works much faster.
        self.DFStoredFocus = z
        self.set_autofocus_ready()

        # track absolute focus position for recovery in case of Definite Focus failure
        self.set_last_known_focus_position(z)

        return z

    def recall_focus(self, pre_set_focus=True):
        '''Find stored focus position as offset from coverslip.
        Stored focus position is lost when switching objective, even when returning to original objective.

        Input:
         pre_set_focus: Move focus to previous auto-focus position. This makes definite focus more robust

        Output:
         z: position of focus drive after recall focus
        '''
        # Zen.Acquisition.RecallFocus will fail if Zen cannot find a stored position.
        # This can happen if the objective was switched.
        # After each objective switch a new focus position has to be stored within Zen.
        # We do not know a way to catch a failure directly (tired exception and time out)
        # Therefore we try to catch common indicators that RecallFocus will fail/failed

        # If autofocus is not ready raise exception
        self.get_autofocus_ready()
        # Is z position after RecallFocus the same
        try:
            # Move the objective to the stored focus position before recalling this positions
            # If the stored position is close to the find_surface position, Definite Focus works much faster.
            if pre_set_focus:
                self.move_focus_to(self.DFStoredFocus)
            self.Zen.Acquisition.RecallFocus()

            # Store position, that will keep definite focus in optimal operational range
            z = self.store_focus()
        except Exception:
            raise HardwareError('Error in recall_focus.')
        # track absolute focus position for recovery in case of Definite Focus failure

        self.set_last_known_focus_position(z)
        return z

    def get_focus_pos(self):
        '''Return current position of focus drive.

        Input:
         none

        Output:
         zPos: position of focus drive in micrometer
        '''
        # Get current stage position
        try:
            zPos = self.Zen.Devices.Focus.ActualPosition
            print(('Focus position is {}'.format(zPos)))
        except Exception:
            raise HardwareError('Error in get_focus_pos.')
        return zPos

    def move_focus_to(self, zPos):
        '''Move focus to new position.

        Input:
         zPos, yPos: new focus position in micrometers.
        '''

        # an alternative to set the position
        try:
            self.Zen.Devices.Focus.TargetPosition = zPos
#             print ('2.1: ID for self.Zen.Devices.Focus.ActualPosition: {}'.format(id(self.Zen.Devices.Focus.ActualPosition)))
            self.Zen.Devices.Focus.Apply()
#             print ('2.2: ID for self.Zen.Devices.Focus.ActualPosition: {}'.format(id(self.Zen.Devices.Focus.ActualPosition)))
            # check new position
            zFocus = self.Zen.Devices.Focus.ActualPosition
#             print ('2.3 ID for self.Zen.Devices.Focus.ActualPosition: {}'.format(id(self.Zen.Devices.Focus.ActualPosition)))
        except Exception:
            raise HardwareError('Error in move_focus_to.')
        # gives type error

        return zFocus

    def set_focus_work_position(self):
        '''retrieve current position and set as work position.

        Input:
         none

        Output:
         z_work: current focus position in mum
        '''
        zWork = self.get_focus_pos()
        self.zWork = zWork

        self.log.info('Stored current focus position as work position', str(zWork))

        return zWork

    def set_focus_load_position(self):
        '''retrieve current position and set as load position.

        Input:
         none

        Output:
         zLoad: current focus position in mum
        '''
        zLoad = self.get_focus_pos()
        self.zLoad = zLoad

        self.log.info('Stored current focus position as load position: %s', str(zLoad))

        return zLoad

    def move_focus_to_load(self):
        '''Move focus to load position if defined.

        Input:
         zPos, yPos: new focus position in micrometers.
        '''
        # check if load position is defined
        if self.zLoad is None:
            self.log.error('Load position not defined')
            raise LoadNotDefinedError('Tried to move focus drive to load position, but load position was not defined.')

        if self.zLoad > 1000:
            self.log.error('Load position too high')
            raise LoadNotDefinedError('Tried to move focus drive to load position, but load position was too high.')

        # move to load position if defined
        zFocus = self.move_focus_to(self.zLoad)

        self.log.info('moved focus to load position: %s', str(zFocus))

        return zFocus

    def move_focus_to_work(self):
        '''Move focus to work position if defined.

        Input:
         zPos, yPos: new focus position in micrometers.

        Output:
         none
        '''
        # check if load position is defined
        if self.zWork is None:
            self.log.error('Work position not defined')
            raise WorkNotDefinedError('Tried to move focus drive to work position, but work position was not defined.')

        # move to load position if defined
        zFocus = self.move_focus_to(self.zWork)

        self.log.info('moved focus to load position: %s', str(zFocus))

        return zFocus

################################################################################
#
# Methods to interact with objectives and objective turret
#
################################################################################

    def get_all_objectives(self, n_positions):
        '''Retrieve name and magnification of all objectives.
        Warning! The objectives will move.

        Input:
         n_positions:  number of objective positions

        Output:
         objectives_dict: dictionary of all objectives mounted at microscope
         in form {'magnification': {'Position': position, 'Name': name}
        '''

        try:
            # retrieve ZEN ObjectiveChanger object
            objective_changer = self.Zen.Devices.ObjectiveChanger
            objectives_dict = {}

            for position in range(1, n_positions + 1):
                magnification = objective_changer.GetMagnificationByPosition(position)
                name = objective_changer.GetNameByPosition(position)
                if not name:
                    name = ''
                objectives_dict[magnification] = {'Position': position, 'Name': name}
                objinfo = ''
                objinfo = objinfo + ' ' + format(position)
                objinfo = objinfo + '\t' + format(magnification)
                objinfo = objinfo + '\t' + name
                print(objinfo)
        except Exception:
            raise HardwareError('Error in get_all_objectives.')
        return objectives_dict

    def switch_objective(self, targetPosition, load=True):
        '''Switches objective.

        Input:
         targetPosition: Position of new objective on objective switcher

         load: if True, move objective to load position before switching. Default: True

        Output:
         objectiveName: name of new objective
        '''
        # move focus drive to load position
        focus = self.get_focus_pos()
        if load:
            self.move_focus_to_load()

        # get name of original objective. We have to let autofocus know if we really changed the objective
        originalObjectiveName = self.get_objective_name()

        try:
            # retrieve ZEN ObjectiveChanger object
            objRevolver = self.Zen.Devices.ObjectiveChanger

            # switch objective
            objRevolver.TargetPosition = targetPosition
            objRevolver.Apply()

            # get name of new objective
            objectiveName = self.get_objective_name()
        except Exception:
            raise HardwareError('Error in switch_objective.')

        # move focus drive back to original position
        self.move_focus_to(focus)

        # check if objective was really changed
        if objectiveName != originalObjectiveName:
            # because objectives where changed the stored focus position for definite focus is no longer available
            self.set_autofocus_not_ready()

        return objectiveName

    def get_objective_magnification(self):
        '''Get magnification of actual objective.

        Input:
         none

        Output:
         magnification: magnification of actual objective, objective in imaging position
        '''
        try:
            # retrieve ZEN ObjectiveChanger object
            objRevolver = self.Zen.Devices.ObjectiveChanger

            # get magnification
            magnification = objRevolver.Magnification
        except Exception:
            raise HardwareError('Error in get_objective_magnification.')
        return magnification

    def get_objective_name(self):
        '''Get name of actual objective.

        Input:
         none

        Output:
         name: name of actual objective, objective in imaging position
        '''
        try:
            # retrieve ZEN ObjectiveChanger object
            objRevolver = self.Zen.Devices.ObjectiveChanger

            # if name == None, automation software will stop later on, using empty string instead
            # This is a temp fix. See jira
            name = objRevolver.ActualPositionName
            if name is None:
                name = ''
        except Exception:
            raise HardwareError('Error in get_objective_name.')
        return name

    def get_objective_position(self):
        '''Get position of actual objective.

        Input:
         none

        Output:
         position: position of actual objective, objective in imaging position
        '''
        try:
            # retrieve ZEN ObjectiveChanger object
            objRevolver = self.Zen.Devices.ObjectiveChanger

            # get name of objective
            position = objRevolver.ActualPosition
        except Exception:
            raise HardwareError('Error in get_objective_name.')
        return position

################################################################################
#
# Methods to control immersion water delivery
#
################################################################################

    def trigger_pump(self, seconds, port='COM1', baudrate=19200):
        '''Trigger pump

        Input:
         seconds: the number of seconds pump is activated

         port: com port, default = 'COM1'

         baudrate: baudrate for connection, can be set on pump, typically = 19200

        Output:
         none
        '''
        try:
            # connect to pump through RS232
            pump = Braintree(port='COM1', baudrate=19200)

            # activate pump
            pump.start_pump()

            # continue pumping for seconds
            time.sleep(seconds)

            # stop pump and close connection
            pump.close_connection()
        except Exception:
            raise HardwareError('Error in trigger_pump.')

        self.log.debug('Pump activated for : %s sec', seconds)

################################################################################
#
# Methods to collect information about experiments
#
################################################################################

    def validate_experiment(self, experiment_path=None, experiment_name=None):
        """Function to check if the experiment is defined in the Zen blue software

        Input:
         experiment_path: path of the experiment file

         experiment_name: name of the experiment

        Output:
         valid_experiment: bool describing if the experiment is valid
        """
        zen_experiment = ZenExperimentDummy(experiment_path, experiment_name)
        valid_experiment = zen_experiment.experiment_exists()
        return valid_experiment

    def is_z_stack(self, experiment_path=None, experiment_name=None):
        """Function to check if the experiment is a z-stack experiment

        Input:
         experiment_path: path of the experiment file

         experiment_name: name of the experiment

        Output:
         z_stack_experiment: bool describing if the experiment acquires a z stack
        """
        zen_experiment = ZenExperimentDummy(experiment_path, experiment_name)
        z_stack_experiment = zen_experiment.is_z_stack()
        return z_stack_experiment

    def z_stack_range(self, experiment_path=None, experiment_name=None):
        """Function to  get the range of first z-stack in experiment.

        Input:
         experiment_path: path of the experiment file

         experiment_name: name of the experiment

        Output:
         zstack_range: range of the z-stack
        """
        zen_experiment = ZenExperimentDummy(experiment_path, experiment_name)
        zstack_range = zen_experiment.z_stack_range()
        return zstack_range

    def is_tile_scan(self, experiment_path=None, experiment_name=None):
        """Function to check if the experiment is a tile scan

        Input:
         experiment_path: path of the experiment file

         experiment_name: name of the experiment

        Output:
         tile_scan_bool: bool describing if the experiment contains a tile scan
        """
        zen_experiment = ZenExperimentDummy(experiment_path, experiment_name)
        tile_scan_bool = zen_experiment.is_tile_scan()
        return tile_scan_bool

    def update_tile_positions(self, experiment_path, experiment_name,
                              x_value, y_value, z_value):
        """Function to define the position of the tile

        Input:
         experiment_path: path of the experiment file

         experiment_name: name of the experiment

         x_value: float (x - coordinate)

         y_value: float (y - coordinate)

         z_value: float (z - coordinate)

        Output:
         none
        """
        zen_experiment = ZenExperimentDummy(experiment_path, experiment_name)
        zen_experiment.update_tile_positions(x_value, y_value, z_value)

    def get_objective_position_from_experiment_file(self, experiment_path,
                                                    experiment_name):
        """Function to get the position of the objective used in the experiment

        Input:
         experiment_path: path of the experiment file

         experiment_name: name of the experiment

        Output:
         position: the integer position of the objective
        """
        zen_experiment = ZenExperimentDummy(experiment_path, experiment_name)
        position = zen_experiment.get_objective_position()
        return position

    def get_focus_settings(self, experiment_path, experiment_name):
        """Function to get the focus settings used in the experiment

        Input:
         experiment_path: path of the experiment file

         experiment_name: name of the experiment

        Output:
         focus_settings: All instances of focus settings in experiment file
        """
        zen_experiment = ZenExperimentDummy(experiment_path, experiment_name)
        focus_settings = zen_experiment.get_focus_settings()
        return focus_settings


class ZenExperimentDummy():

    TAG_PATH_TILE_CENTER_XY = '/HardwareExperiment/ExperimentBlocks/AcquisitionBlock' \
        '/SubDimensionSetups/RegionsSetup/SampleHolder/TileRegions/TileRegion/CenterPosition'
    TAG_PATH_TILE_CENTER_Z = '/HardwareExperiment/ExperimentBlocks/AcquisitionBlock' \
        '/SubDimensionSetups/RegionsSetup/SampleHolder/TileRegions/TileRegion/Z'

    def __init__(self, experiment_path, experiment_name):
        """Initializing the experiment class

        Input:
         experiment_name: Name of the experiment as defined in the Zen software & preference file

        Output:
         prefs: the preference file for the workflow
        """
        self.experiment_path = experiment_path
        self.experiment_name = experiment_name
        if self.experiment_exists():
            self.tree = etree.parse(self.experiment_path)
        else:
            self.tree = None

    def experiment_exists(self):
        """Function to check if the experiment name provided in the preference file exists in the Zen software

        Input:
         none

        Output:
         a boolean indicating if the experiment exists or not
        """
        # log.debug("Experiment path: {}".format(self.experiment_path))
        experiment_exists = Path(self.experiment_path).exists()
        # print('Experiment {} exists: {}'.format(self.experiment_path, experiment_exists))
        return experiment_exists

    def update_tag_value(self, tag_path, new_value):
        """Function to update the value of a tag in the experiment xml file.

        Input:
         tag_path: Path where the tag is loacted in the xml tree

         new_value: The value that needs to be assigned to the tag (string)

        Output:
         none
        """
        root = self.tree.getroot()
        try:
            tag = root.xpath(tag_path)
            tag[0].text = new_value
            self.tree.write(self.experiment_path)
        except Exception as err:
            raise ValueError("Updating tag '{}' for experiment {} raised the error: {}".format(tag_path, self.experiment_path, err.strerror))

    def is_tile_scan(self):
        '''Test if experiment is tile scan.

        Input:
         none

        Output:
         is_tile_scan: True if experiment contains z-stack
        '''
        root = self.tree.getroot()
        # retrieve all z-stack setups, use only fist
        RegionsSetup = root.findall(".//RegionsSetup")[0]
        is_tile_scan = RegionsSetup.attrib['IsActivated'] == 'true'
        return is_tile_scan

    def update_tile_positions(self, x_value, y_value, z_value):
        """In the tile function, correct the hard coded values of the tile region using the values from
        the automation software

        Input:
         x_value: float (x - coordinate)
         y_value: float (y - coordinate)
         z_value: float (z - coordinate)

        Output:
         none
        """

        xy_value = str(x_value) + ',' + str(y_value)
        self.update_tag_value(self.TAG_PATH_TILE_CENTER_XY, xy_value)
        self.update_tag_value(self.TAG_PATH_TILE_CENTER_Z, str(z_value))

    def get_focus_settings(self):
        """Function to get all the instances of focus settings in the experiment file

        Input:
         none

        Output:
         focus_settings: All instances of focus settings in experiment file
        """
        root = self.tree.getroot()
        # retrieve all focus setups
        focus_settings = root.findall(".//FocusSetup")
        return focus_settings

    def get_objective_position(self):
        ''' Return position of objective used in experiment.
        Method assumes that only one objective is used in experiment.

        Input:
         None

        Output:
         position: integer with position of objective used in experiment
        '''
        root = self.tree.getroot()
        # retrieve all objective changers. Use only first
        objective_changer = root.findall(".//ParameterCollection[@Id = 'MTBObjectiveChanger']")[0]
        position = int(objective_changer.find('Position').text)
        return position

    def is_z_stack(self):
        '''Test if experiment is z-stack.

        Input:
         none

        Output:
         is_z_stack: True if experiment contains z-stack
        '''
        root = self.tree.getroot()
        # retrieve all z-stack setups, use only first
        ZStackSetup = root.findall(".//ZStackSetup")[0]
        is_z_stack = ZStackSetup.attrib['IsActivated'] == 'true'
        return is_z_stack

    def z_stack_range(self):
        '''Return range of first z-stack in experiment.
        Returns 0 if z-stack is not activated.

        Input:
         none

        Output:
         z_stack_range: True if experiment contains z-stack
        '''
        if not self.is_z_stack():
            return 0
        else:
            root = self.tree.getroot()
            # retrieve all z-stack setups, use only fist
            ZStackSetup = root.findall(".//ZStackSetup")[0]
            first_postion = float(ZStackSetup.find('First/Distance/Value').text)
            last_postion = float(ZStackSetup.find('Last/Distance/Value').text)
            z_stack_range = abs(last_postion - first_postion)
            return z_stack_range


class ConnectSlidebookDummy():
    def __init__(self, cmd_url='http://127.0.0.1:5000',
                 data_url='http://127.0.0.1:5100',
                 microscope='3iW1-0'):
        # Create Logger
        self.log = logging.getLogger('microscopeAutomation connect_slidebook')

        self.cmd_url = cmd_url + '/cmd'
        self.data_url = data_url + '/data'
        self.microscope = microscope

        self.default_experiment = {'experiment_id': '',
                                   'microscope': self.microscope,
                                   'number_positions': 1,
                                   'stage_locations': [(0, 0, 0)],
                                   'stage_locations_filter': [True],
                                   'capture_settings': ['No_experiment'],
                                   'centers_of_interest': [(0, 0, 0)],
                                   'objective': 'Apo_10x',
                                   'time_stamp': '',
                                   'microscope_action': 'exit',
                                   'id_counter': 0,
                                   'status': 'none'
                                   }
        self.zLoad = 500
        self.zWork = 500

    def not_implemented(self, method_name):
        '''Raise exception if method is not implemented.

        Input:
         method_name: method that calls this method

        Output:
         none
        '''
        raise HardwareCommandNotDefinedError(method_name + ' is not supported'
                                             + ' for Slidebook microscope')

    ############################################################################
    #
    # Methods to handle Capture Settings
    #
    ############################################################################

    def snap_image(self, capture_settings, objective=''):
        """Snap image with parameters defined in experiment at current location.

        Input:
         capture_settings: string with name of capture_settings as defined
         within Microscope software

         objective: objective used to acquire image. If none keep objective.

        Return:
         success: True when experiment was successfully posted on command server
        """
        experiment = self.default_experiment
        experiment['objective'] = objective
        experiment['microscope_action'] = 'snap'

        return True

    def live_mode_start(self, experiment):
        '''Start live mode.
        Included for parity between Microscope connections.

        Raises HardwareCommandNotDefinedError.

        Input:
         experiment: name of experiment

        Output:
         none
        '''
        self.not_implemented('live_mode_start')

    def live_mode_stop(self, experiment):
        '''Stop live mode.
        Included for parity between Microscope connections.

        Raises HardwareCommandNotDefinedError.

        Input:
         experiment: name of experiment

        Output:
         none
        '''
        self.not_implemented('live_mode_stop')

    def move_focus_to(self, zPos):
        '''Move focus to new position.
        Included for parity between Microscope connections.

        Raises HardwareCommandNotDefinedError.

        Input:
         zPos, yPos: new focus position in micrometers.

        Output:
         zFocus: new position of focus drive
        '''
        self.not_implemented('move_focus_to')

    def move_focus_to_load(self):
        '''Move focus to load position if defined.

        Input:
         zPos, yPos: new focus position in micrometers.

        Output:
         zFocus: new position of focus drive
        '''
        # check if load position is defined
        if self.zLoad is None:
            self.log.error('Load position not defined')
            raise LoadNotDefinedError("Tried to move focus drive to load position,"
                                      " but load position was not defined.")

        if self.zLoad > 1000:
            self.log.error('Load position too high')
            raise LoadNotDefinedError("Tried to move focus drive to load position,"
                                      " but load position was too high.")

        # move to load position if defined
        zFocus = self.move_focus_to(self.zLoad)

        self.log.info('moved focus to load position: %s', str(zFocus))

        return zFocus

    def move_focus_to_work(self):
        '''Move focus to work position if defined.

        Input:
         zPos, yPos: new focus position in micrometers.

        Output:
         zFocus: new position of focus drive
        '''
        # check if load position is defined
        if self.zWork is None:
            self.log.error('Work position not defined')
            raise WorkNotDefinedError("Tried to move focus drive to load position,"
                                      " but work position was not defined.")

        # move to load position if defined
        zFocus = self.move_focus_to(self.zWork)

        self.log.info('moved focus to load position: %s', str(zFocus))

        return zFocus

    ############################################################################
    #
    # Methods to collect information about experiments
    #
    ############################################################################

    def validate_experiment(self, experiment_path=None, experiment_name=None):
        """Function to check if the experiment is defined in the Slidebook software

        Input:
         experiment_path: path of the experiment file - does not matter for Zen Black

         experiment_name: name of the experiment

        Output:
         valid_experiment: bool describing if the experiment is valid
        """
        slidebook_experiment = SlidebookExperimentDummy(experiment_path, experiment_name)
        valid_experiment = slidebook_experiment.experiment_exists()
        return valid_experiment

    def get_focus_settings(self, experiment_path=None, experiment_name=None):
        """Get focus settings.
        Included for parity between Microscope connections.

        Raises HardwareCommandNotDefinedError.

        Input:
         experiment_path: path of the experiment file

         experiment_name: name of the experiment

        Output:
         none
        """
        self.not_implemented('get_focus_settings')

    def get_objective_position_from_experiment_file(self, experiment_path=None,
                                                    experiment_name=None):
        """Function to get the position of the objective used in the experiment
        Included for parity between Microscope connections.

        Raises HardwareCommandNotDefinedError.

        Input:
         experiment_path: path of the experiment file

         experiment_name: name of the experiment

        Output:
         none
        """
        self.not_implemented('get_objective_position_from_experiment_file')

    def is_z_stack(self, experiment_path=None, experiment_name=None):
        """Function to check if the experiment contains z-stack acquisition.
        Included for parity between Microscope connections.

        Raises HardwareCommandNotDefinedError.

        Input:
         experiment_path: path of the experiment file

         experiment_name: name of the experiment

        Output:
         none
        """
        self.not_implemented('is_z_stack')

    def z_stack_range(self, experiment_path=None, experiment_name=None):
        """Function to  get the range of first z-stack in experiment.
        Included for parity between Microscope connections.

        Raises HardwareCommandNotDefinedError.

        Input:
         experiment_path: path of the experiment file

         experiment_name: name of the experiment

        Output:
         none
        """
        self.not_implemented('z_stack_range')

    def is_tile_scan(self, experiment_path=None, experiment_name=None):
        """Function to check if the experiment is a tile scan.
        Included for parity between Microscope connections.

        Raises HardwareCommandNotDefinedError.

        Input:
         experiment_path: path of the experiment file

         experiment_name: name of the experiment

        Output:
         none
        """
        self.not_implemented('is_tile_scan')

    def update_tile_positions(self, experiment_path, experiment_name,
                              x_value, y_value, z_value):
        """Function to define the position of the tile.
        Included for parity between Microscope connections.

        Raises HardwareCommandNotDefinedError.

        Input:
         experiment_path: path of the experiment file

         experiment_name: name of the experiment

         x_value: float (x - coordinate)

         y_value: float (y - coordinate)

         z_value: float (z - coordinate)

        Output:
         none
        """
        self.not_implemented('update_tile_positions')


class SlidebookExperimentDummy():
    def __init__(self, experiment_path, experiment_name):
        """
        Initializing the experiment class

        Input:
         experiment_name: Name of the experiment as defined in the Zen software
         & preference file

         prefs: the preference file for the workflow

        Output:
         none
        """
        self.experiment_path = experiment_path
        self.experiment_name = experiment_name

    def experiment_exists(self):
        """Function to check if the experiment name provided in the preference
        file exists in the Slidebook software

        Input:
         none

        Output:
         a boolean indicating if the experiment exists or not
        """
        # log.debug("Experiment path: {}".format(self.experiment_path))
        experiment_exists = Path(self.experiment_path).exists()
        return experiment_exists


class MicroscopeStatus(object):
    '''Create instance of this class to keeps track of microscope status.

    Input:
     none

    Output:
     none
    '''
    def __init__(self):
        self._xPos = 60000
        self._yPos = 40000
        self._zPos = 500
        self._objective_position = 0
        self._objective_name = 'Dummy Objective'

    @property
    def xPos(self):
        '''Get absolute x position for stage'''
        if test_messages:
            print(('MicroscopeStatus returned x as {}'.format(self._xPos)))
        return self._xPos

    @xPos.setter
    def xPos(self, x):
        '''Set absolute x position for stage'''
        self._xPos = x
        if test_messages:
            print(('MicroscopeStatus set x as {}'.format(self._xPos)))

    @property
    def yPos(self):
        '''Get absolute y position for stage'''
        if test_messages:
            print(('MicroscopeStatus returned y as {}'.format(self._yPos)))
        return self._yPos

    @yPos.setter
    def yPos(self, y):
        '''Set absolute y position for stage'''
        self._yPos = y
        if test_messages:
            print(('MicroscopeStatus set y as {}'.format(self._yPos)))

    @property
    def zPos(self):
        '''Get absolute z position for focus drive'''
        if test_messages:
            print(('MicroscopeStatus returned z as {}'.format(self._zPos)))
        return self._zPos

    @zPos.setter
    def zPos(self, z):
        '''Set absolute z position for focus drive'''
        self._zPos = z
        if test_messages:
            print(('MicroscopeStatus set z as {}'.format(self._zPos)))

    @property
    def objective_position(self):
        '''Get position for objective in objective changer'''
        if test_messages:
            print(('MicroscopeStatus returned objective_position as {}'.format(self._objective_position)))
        return self._objective_position

    @objective_position.setter
    def objective_position(self, objective_position):
        '''Set position for objective in objective changer'''
        self._objective_position = objective_position
        if test_messages:
            print(('MicroscopeStatus set objective_position as {}'.format(self._objective_position)))

    @property
    def objective_name(self):
        '''Get name for actual objective'''
        if test_messages:
            print(('MicroscopeStatus returned objective_name as {}'.format(self._objective_name)))
        return self._objective_name

    @objective_name.setter
    def objective_name(self, objective_name):
        '''Set name for actual objective'''
        self._objective_name = objective_name
        if test_messages:
            print(('MicroscopeStatus set objective_name as {}'.format(self._objective_name)))


class Focus(object):
    def __init__(self, microscope_status):
        '''Class in Zeiss.Micro.Scripting.Core namespace that gives access to focus.

        Input:
         none

        Output:
         none
        '''
        # Properties of class ZenFocus
        self.TargetPosition = 0
        self._microscope_status = microscope_status

    # Attributes for focus
    @property
    def ActualPosition(self):
        '''Get the current z position for focus drive'''
        return self._microscope_status.zPos

    # Methods of class ZenFocus
    def Apply(self):
        '''Applies the target parameter values.

        Input:
         none

        Output:
         none
        '''
        self._microscope_status.zPos = self.TargetPosition

    def MoveTo(self, z):
        '''Moves to the specified focus position.

        Input:
         z: Focus position in um

        Output:
         none
        '''
        self._microscope_status.zPos = z
        return None


class ObjectiveChanger(object):
    def __init__(self, microscope_status):
        self.TargetPosition = 1
        self.Magnification = 10
        self._microscope_status = microscope_status

    @property
    def ActualPositionName(self):
        '''Get name of actual objectve'''
        return self._microscope_status.objective_name

    @property
    def ActualPosition(self):
        '''Get name of actual objective position in ojbective turret'''
        return self._microscope_status.objective_position

    def Apply(self):
        self._microscope_status.objective_position = self.TargetPosition

    def GetMagnificationByPosition(self, position):
        return ''

    def GetNameByPosition(self, position):
        return None


class Stage(object):
    def __init__(self, microscope_status):
        self.TargetPositionY = 0
        self._microscope_status = microscope_status

    @property
    def ActualPositionX(self):
        '''Get actual x position for stage'''
        return self._microscope_status.xPos

    @property
    def ActualPositionY(self):
        '''Get actual y position for stage'''
        return self._microscope_status.yPos

    def Apply(self):
        self._microscope_status.xPos = self.TargetPositionX
        self._microscope_status.yPos = self.TargetPositionY


class Devices(object):
    '''Simulated device objects'''

    def __init__(self, microscope_status):
        '''Create Zen devices object'''
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
        return 'Experiment'

    def Contains(self, expClass):
        return True


class Image(object):
    def Save_2(self, fileName):
        if not (os.path.exists(fileName)):
            exampleImage = '../data/testImages/WellEdge_0.czi'
            copy2(exampleImage, fileName)


class Acquisition(object):
    '''Simulate image acquisition'''
    def __init__(self, microscope_status):
        self.Experiments = Experiments(microscope_status)
        self.storedAutofocus = 0
        self._microscope_status = microscope_status

    def _set_objective(self, experiment):
        '''Sets for debug purposes active objective name based on experiment name.
        '''
        if '10x' in experiment:
            self._microscope_status.objective_name = 'Plan-Apochromat 10x/0.45'
            self._microscope_status.objective_position = 1
        if '20x' in experiment:
            self._microscope_status.objective_name = 'Plan-Apochromat 20x/0.8 M27'
            self._microscope_status.objective_position = 2
        if '100x' in experiment:
            self._microscope_status.objective_name = 'C-Apochromat 100x/1.25 W Korr UV VIS IR'
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
        '''Finds the surface using definite focus.

        Input:
         none

        Output:
         none
        '''
        self._microscope_status.zPos = 9000
        return None

    def StoreFocus(self):
        '''Initializes the definite focus on the current position.

        Input:
         none

        Output:
         none
        '''
        self.storedAutofocus = self._microscope_status.zPos
        return self.storedAutofocus

    def RecallFocus(self):
        '''Finds the surface + offset.

        Input:
         none

        Output
         none
        '''
        self._microscope_status.zPos = self.storedAutofocus + 100
        return None

    def FindAutoFocus(self):
        '''Use the autofocus of the current experiment to find the sample.

        Input:
         none

        Output:
         none
        '''
        self._microscope_status.zPos = self.storedAutofocus
        return None

    def FindAutoFocus_2(self, experiment):
        '''Use the autofocus of the current experiment to find the sample.

        Input:
         experiment: String name of experiment in ZEN blue software

        Output:
         none
        '''
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
        print(("Test mode: Running Macro: " + macro_name + " | Parameter: " + macro_params[0]))


######################################################################################
#
# Class GetActiveObject
#
######################################################################################

class GetActiveObject(object):
    '''Simulation for connection to ZEN blue software.
    '''

    def __init__(self, name):
        '''
        Simmulation: Connect to Carl Zeiss ZEN blue Python API
        '''
        microscope_status = MicroscopeStatus()
        self.Devices = Devices(microscope_status)
        self.Acquisition = Acquisition(microscope_status)
        self.Application = Application(microscope_status)
