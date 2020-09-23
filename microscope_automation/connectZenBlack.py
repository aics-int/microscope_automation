# Communication layer for ZEN BLACK for LSM 880 system

# USE DLL to connect to the ZEN Black API
import win32com.client
import logging
from loadImageCzi import LoadImageCzi
from automationExceptions import HardwareError, AutofocusError, AutofocusObjectiveChangedError, \
    AutofocusNotSetError, LoadNotDefinedError
import os
from imageAICS import ImageAICS
# Create Logger
log = logging.getLogger('ConnectZenBlack')


class connectMicroscope():

    def __init__(self):
        # Connect to the Zen Black API
        self.Zen = win32com.client.Dispatch("Zeiss.Micro.AIM.ApplicationInterface.ApplicationInterface")
        self.zLoad = None
        self.zWork = None
        self.image = ImageAICS()
        # Settings for Definite Focus 2
        # Note: Objective used to set Definite Focus (Definite Focus will lose stored
        # focus position after change of objective)
        self.DFObjective = None
        self.DFStoredFocus = None
        self.lastKnownFocusPosition = None
        self.autofocusReady = False

    ##################################################
    #          Major ZEN Black API calls             #
    ##################################################

    def validate_experiment(self, experiment_path=None, experiment_name=None):
        """
        Function to check that the configurations exists in Zen Black Software
        NOTE - experiment path is not needed. They are added to keep the function signatures same between
        Zen Blue and zen black
        :param experiment_path: path of the experiment file - does not matter for Zen Blue
        :param experiment_name: name of the experiment
        :return: valid_experiment: bool describing if the experiment is valid
        """
        valid_experiment = self.Zen.GUI.Acquisition.Configuration.isValidItem(experiment_name)
        return valid_experiment

    def is_z_stack(self, experiment_path=None, experiment_name=None):
        """
        Function to check if the experiment is a z-stack experiment
        NOTE - experiment path and name are not needed. They are added to keep the function signatures same between
        Zen Blue and zen black
        :param experiment_path: path of the experiment file
        :param experiment_name: name of the experiment
        :return: z_stack_experiment: bool describing if the experiment acquires a z stack
        """
        z_stack_experiment = self.Zen.GUI.Acquisition.EnableZStack.Value
        return z_stack_experiment

    def z_stack_range(self, experiment_path=None, experiment_name=None):
        """
        Function to  get the range of first z-stack in experiment.
        NOTE - The z-stack range is not available directly through the Zen Black API. Hence it is calculated:
        Range = (zstack slices * Interval) - Interval : (by observation)
        NOTE - experiment path and name are not needed. They are added to keep the function signatures same between
        Zen Blue and zen black
        :param experiment_path: path of the experiment file
        :param experiment_name: name of the experiment
        :return: zstack_range: range of the z-stack (in micrometers)
        """
        # TODO Double check with Winfried
        slices = self.Zen.GUI.Acquisition.ZStack.NumberSlices.Value
        interval = self.Zen.GUI.Acquisition.ZStack.Interval.Value
        zrange = (slices * interval) - interval
        return zrange

    def is_tile_scan(self, experiment_path=None, experiment_name=None):
        """
        Function to check if the experiment is a tile scan
        NOTE - experiment path and name are not needed. They are added to keep the function signatures same between
        Zen Blue and zen black
        :param experiment_path: path of the experiment file
        :param experiment_name: name of the experiment
        :return: tile_scan_bool: bool describing if the experiment contains a tile scan
        """
        tile_scan_bool = self.Zen.GUI.Acquisition.EnableTileScan.Value
        return tile_scan_bool

    def update_tile_positions(self,experiment_path, experiment_name, x_value, y_value, z_value):
        """
        Function to define the position of the tile
        :param experiment_path: path of the experiment file
        :param experiment_name: name of the experiment
        :param x_value: float (x - coordinate)
        :param y_value: float (y - coordinate)
        :param z_value: float (z - coordinate)
        :return:
        """
        # Note - Since the stage is already moved to where the tile position is and
        # there is no experiment file that we need to write that position to, this function is not
        # needed and os left blank.

    def get_objective_position_from_experiment_file(self, experiment_path, experiment_name):
        """
        Function to get the position of the objective used in the experiment
        NOTE - experiment path and name are not needed. They are added to keep the function signatures same between
        Zen Blue and zen black
        :param experiment_path: path of the experiment file
        :param experiment_name: name of the experiment
        :return: position: the integer position of the objective
        """
        return self.get_objective_position()

    def get_focus_settings(self, experiment_path, experiment_name):
        """

        :param experiment_path: path of the experiment file
        :param experiment_name: name of the experiment
        :return: focus_settings: All instances of focus settings in experiment file
        """
        # TODO Add API call for this


    def load_experiment(self, experiment=None):
        """
        Function to load acquisition parameters in Zen Black
        :param experiment: Name of the experiment settings
        :return:
        """
        log.info("In function load_experiment.")
        self.Zen.GUI.Acquisition.Activate.Execute()
        self.Zen.GUI.Acquisition.Configuration.Load(experiment)

    def snap_image(self, experiment=None):
        """
        Function to snap an image given acquisition parameters
        :param experiment: Name of the experiment settings
        :return:
        """
        log.info("In function snap_image.")
        current_objective = self.get_objective_name()
        try:
            if experiment is None:
                experiment = self.get_active_experiment()
            self.load_experiment(experiment)
            self.image = self.Zen.GUI.Acquisition.Snap.Execute()
        except:
            raise HardwareError("Error in Snap Image (connectZenBlack.py).")

        # set flag for definite focus if objective was changed
        if current_objective != self.get_objective_name() or self.get_objective_name() == '':
            self.set_autofocus_not_ready()

    def close_experiment(self, experiment_name):
        """
        Function to clear the acquisition parameters
        :param experiment_name: Name of the experiment settings
        :return:
        """
        log.info("In function close_experiment.")

    def get_active_experiment(self):
        """
        Function to get the current active acquisition parameters
        :return: active_experiment = string name of the configurations that were loaded.
        """
        log.info("In function get_active_experiment.")
        active_experiment = self.Zen.GUI.Acquisition.Configuration.CurrentItem
        return active_experiment

    def execute_experiment(self, experiment=None):
        """
        Function to start an experiment
        This is linked to the "Start Experiment" button in the Zen Black GUI
        :param experiment: Name of the experiment settings
        :return:
        """
        log.info("In function execute_experiment.")
        # If method switches objective, the stored position for definite focus will be invalid.
        current_objective = self.get_objective_name()
        # Stop live mode, otherwise the wrong objective might be used
        self.live_mode_stop()
        try:
            self.load_experiment(experiment)
            can_execute = self.Zen.GUI.Acquisition.StartExperiment.CanExecute()
            if can_execute:
                self.Zen.GUI.Acquisition.StartExperiment.Execute()
            else:
                self.snap_image(experiment)
        except:
            raise HardwareError("Error in Execute Experiment(connectZenBlack.py).")
        # Set flag for definite focus if objective was changed
        if current_objective != self.get_objective_name() or self.get_objective_name() == '':
            self.set_autofocus_not_ready()

    def live_mode_start(self, experiment=None):
        """
        Function to start live mode in the Acquisition tab
        :param experiment: Name of the experiment settings
        :return:
        """
        log.info("In function live_mode_start.")
        # If method switches objective, the stored position for definite focus will be invalid.
        current_objective = self.get_objective_name()
        if experiment is None:
            experiment = self.get_active_experiment()
        try:
            self.load_experiment(experiment)
            # Turn the Async Mode on so it doesnt wait on live mode to stop to continue with the software
            self.Zen.GUI.Acquisition.Live.AsyncMode = "True"
            self.Zen.GUI.Acquisition.Live.Execute()
        except:
            raise HardwareError("Error in Starting Live Mode (connectZenBlack.py).")
        # Set flag for definite focus if objective was changed
        if current_objective != self.get_objective_name() or self.get_objective_name() == '':
            self.set_autofocus_not_ready()

    def live_mode_stop(self, experiment=None):
        """
        Function to stop live mode in the Acquisition tab
        :param experiment: Name of the experiment settings
        :return:
        """
        log.info("In function live_mode_stop.")
        if experiment is None:
            experiment = self.get_active_experiment()
        try:
            # Turn the Async Mode on so it doesnt wait on live mode stop to finish to continue with the software
            self.Zen.GUI.Acquisition.Live.AsyncMode = "True"
            self.Zen.SetSelected("Scan.IsFastScanning", False)
        except:
            raise HardwareError("Error in Stopping Live Mode (connectZenBlack.py).")

    def show_image(self):
        """
        Function to display an image in the Zen Black software window
        :return:
        """
        log.info("In function show_image.")

    def remove_all(self):
        """
        Function to remove all images within the Zen Black software window
        :return:
        """
        log.info("In function remove_all (images).")
        try:
            self.Zen.GUI.File.CloseAll.Execute()
        except:
            raise HardwareError("Error in Removing all images (connectZenBlack.py).")

    def get_stage_pos(self):
        """
        Function to return the current position of the stage
        :return: x, y = stage coordinates in micrometers
        """
        log.info("In function get_stage_pos.")
        try:
            x = self.Zen.GUI.Acquisition.Stage.PositionX.Value
            y = self.Zen.GUI.Acquisition.Stage.PositionY.Value
        except:
            raise HardwareError("Error in getting stage position (connectZenBlack.py).")
        return x, y

    def move_stage_to(self, xPos=None, yPos=None, test=False):
        """
        Move the microscope stage to the new position
        :param xPos: x coordinate of the new position in micrometers
        :param yPos: y coordinate of the new position in micrometers
        :return:
        """
        log.info("In function move_stage_to.")
        # Check if the positions are defined
        if xPos is None or yPos is None:
            raise HardwareError("Error in moving stage to x,y position. Positions can't be None."
                                " X = {}, Y = {}".format(xPos, yPos))
        # For testing return the path so it can be tested it is safe to move there
        if test:
            x_current, y_current = self.get_stage_pos()
            xy_path = [(x_current, y_current), (xPos, y_current), (xPos, yPos)]
            return xy_path
        try:
            # Turn the Async Mode on so it comes back to the software after moving and doesnt hang when live mode is on
            # and we want to move the stage
            self.Zen.GUI.Acquisition.Stage.PositionX.AsyncMode = "True"
            self.Zen.GUI.Acquisition.Stage.PositionX.Value = xPos
            self.Zen.GUI.Acquisition.Stage.PositionY.AsyncMode = "True"
            self.Zen.GUI.Acquisition.Stage.PositionY.Value = yPos
        except:
            raise HardwareError("Error in moving stage to position (connectZenBlack.py).")
        return xPos, yPos

    def find_surface(self):
        """
        Function to fins cover slip using Definite Focus 2
        :return: z = Position of focus drive after finding the surface
        """
        log.info("In function find_surface (using DF2).")
        try:
            self.Zen.SetSelected("DefiniteFoc.FindFocus", True)
            z = self.get_focus_pos()
        except:
            raise HardwareError("Error in finding surface using DF2 (connectZenBlack.py).")
        return z

    def find_autofcous(self, experiment=None):
        """
        Function to find focus using Zen Black's autofocus
        :param experiment: Name of the experiment settings
        :return: z = Position of focus drive after autofocus
        """
        log.info("In function find_autofocus.")
        # Don't need for now

    def store_focus(self):
        """
        Function to store actual focus position as offset from cover slip.
        Note (Important)- In Zen Blue: Stored focus position is lost when switching objective,
        even when returning to original objective.
        :return:  z: position of focus drive after store focus
        """
        log.info("In function store_focus.")
        # Check if correct objective was selected
        if self.get_objective_name() == '':
            self.set_autofocus_not_ready()
            raise AutofocusError(message = 'No objective selected to store autofocus position.')
        try:
            # There is no Async mode specifically for the CommandExecute object in Zen Black.
            # hence we turn it on globally and then turn it off right after
            self.Zen.GlobalAsyncMode = True
            self.Zen.CommandExecute("DefiniteFoc.DetermineFocus")
            z = self.get_focus_pos()
        except:
            raise HardwareError("Error in storing focus (connectZenBlack.py).")
        # The reason for turning it off right after is because we don't want to turn it on globally at all times.
        # for some commands, we want them to finish execution before handing the control back to our software
        self.Zen.GlobalAsyncMode = False
        # Get objective used to set Definite Focus
        # (Definite Focus will lose stored focus position after change of objective)
        self.DFObjective = self.get_objective_name()
        self.DFStoredFocus = z
        self.set_autofocus_ready()
        # Track absolute focus position for recovery in case of Definite Focus failure
        self.set_last_known_focus_position(z)
        return z

    def recall_focus(self):
        """
        Function to find stored focus position as offset from cover slip.
        Note (Important)- In Zen Blue: Stored focus position is lost when switching objective,
        even when returning to original objective.
        :return: z: position of focus drive after recall focus
        """
        log.info("In function recall_focus.")
        # If autofocus is not ready, raise exception
        self.get_autofocus_ready()
        # Is z position after RecallFocus the same
        try:
            self.Zen.CommandExecute("DefiniteFoc.Stabilize")
            z = self.get_focus_pos()
        except:
            raise HardwareError('Error in Recalling DF2 (connectZenBlack.py).')
        # Track absolute focus position for recovery in case of Definite Focus failure
        self.set_last_known_focus_position(z)
        return z

    def get_focus_pos(self):
        """
        Function to return the current position of the focus drive
        :return: z: position of the focus drive
        """
        log.info("In function get_focus_pos.")
        try:
            z = self.Zen.GUI.Acquisition.ZStack.FocusPosition.Value
        except:
            raise HardwareError('Error in Getting position of the focus drive (connectZenBlack.py).')
        return z

    def move_focus_to(self, zPos):
        """
        Function to move the focus drive to the new position
        :param zPos: the z position in micrometers
        :return:
        """
        log.info("In function move_focus_to.")
        try:
            # Turn the Async Mode on so it comes back to the software after moving and doesnt hang when live mode is on
            # and we want to move the focus
            self.Zen.GUI.Acquisition.Zstack.FocusPosition.AsyncMode = "True"
            self.Zen.GUI.Acquisition.ZStack.FocusPosition.Value = zPos
            z_focus = self.get_focus_pos()
        except:
            raise HardwareError('Error in Moving focus drive to a specified location (connectZenBlack.py).')
        return z_focus

    def get_objective_changer_object(self):
        """
        Function to get the Zen Black Objective changer object using API call
        This object is used for a lot of helper functions
        :return: objective_changer: the zen object for the objective revolver
        """
        # TODO Test if two clients can operate at the same time
        log.info("In function get_objective_changer.")
        zen_connection = win32com.client.Dispatch('Lsm5Vba.Application')
        objective_changer = zen_connection.Lsm5.Hardware().CpObjectiveRevolver()
        return objective_changer

    def switch_objective(self, targetPosition):
        """
        Function to switch objective to the new target position
        uses self.get_objective_changer_object()
        :param targetPosition:  Position of new objective on objective switcher (0, 1, 2 .. n)
        :return:  objectiveName: name of new objective
        """
        log.info("In function switch_objective.")
        # Move focus drive to load position
        focus = self.get_focus_pos()
        self.move_focus_to_load()
        # Get name of original objective. We have to let autofocus know if we changed the objective
        original_objective_name = self.get_objective_name()
        try:
            self.Zen.GUI.Acquisition.AcquisitionMode.Objective.ByIndex = targetPosition
            # get name of new objective
            objective_name = self.get_objective_name()
        except:
            raise HardwareError('Error in Switching Objectives (connectZenBlack.py).')

        # Move focus drive back to original position
        self.move_focus_to(focus)

        # check if objective was really changed
        if objective_name != original_objective_name:
            # Because objectives where changed the stored focus position for definite focus is no longer available
            self.set_autofocus_not_ready()
        return objective_name

    def trigger_pump(self, seconds, port='COM1', baudrate=19200):
        """
        Function to trigger pump
        Use BraintTree library to connect to the pump
        :param seconds: the number of seconds pump is activated
        :param port: com port, default = 'COM1'
        :param baudrate: baudrate for connection, can be set on pump, typically = 19200
        :return:
        """
        log.info("In function trigger_pump.")

    def get_microscope_name(self):
        """
        function to retrieve the name of the microscope
        :return: name: name of the microscope
        """
        log.info("In function get_microscope_name.")
        # Could not figure it out

    def stop(self):
        """
        Function to stop the microscope
        :return:
        """
        log.info("In function stop (microscope).")
        # Could not figure it out

    ##################################################################
    #     Helper Functions (do not include ZEN Black API calls)      #
    ##################################################################

    def save_image(self, fileName):
        """
        Function to save current image at a specified file path
        :param fileName: file path (including the file name) as a string
        :return:
        """
        try:
            # Get the current image
            image = self.Zen.GUI.Document.DsRecordingDoc
            # 14 here is the enumeration value for the export type of Lsm5
            # TODO instead of hard coding the enum value, find a way to access the enum object using the com object
            image.Export(14, fileName, False, False, 0, 0, False, 0, 1, 2)
            log.info('Saved image to path: {}. '.format(fileName))
        except Exception as err:
            log.exception(err)
            raise HardwareError('Error in saving image to path: {} in connectZenBlack.py.'.format(fileName))

    def load_image(self, image, getMeta=False):
        """
        Function to load image using internal library aicsimage
        :param image: Object of class imageAICS meta data (including file path)
        :param getMeta: if True, retrieve additional meta data
        :return: image: image with data and meta data as an object of imageAICS class
        """
        reader = LoadImageCzi()
        image = reader.load_image(image, get_meta_data=True)
        log.info('Loaded file using aicsimage. File path: {}.'.format(image.get_meta('aics_filePath')))
        return image

    def wait_for_experiment(self, experiment):
        """
        Function to wait till the given experiment is loaded and is active
        For this we will use the function get_active_experiment and compare it to the param experiment
        :param experiment:  Name of the experiment settings
        :return:
        """
        # if experiment name contains extension (.czexp), remove it
        target_experiment = os.path.splitext(experiment)[0]
        while True:
            active_experiment = self.get_active_experiment()
            log.info('Active experiment = {}'.format(active_experiment))
            if target_experiment == active_experiment:
                break

    def set_autofocus_ready(self):
        """
        Function to update autofocusReady flag to True
        Meaning auto focus position for DF2 was stores and recall_focus should work
        :return:
        """
        self.autofocusReady = True

    def set_autofocus_not_ready(self):
        """
        Function to update autofocusReady flag to False
        Meaning auto focus for DF2 is not ready and recall_focus won't work
        :return:
        """
        self.autofocusReady = False

    def get_autofocus_ready(self):
        """
        Function to check if auto focus position for DF2 was stored & if recall_focus should work
        :return: bool value: True, if DF2 was initialized and recall_focus should work
        Otherwise, throw an exception
        """
        if not self.autofocusReady:
            raise AutofocusNotSetError(message='Definite Focus is not ready.')

        # Additional Tests to check if auto focus should work.
        # Test 1 - Validity of the objective selected
        if self.get_objective_name() == '' or self.DFObjective is None:
            self.set_autofocus_not_ready()
            raise AutofocusObjectiveChangedError(message='No objective selected.')
        # Test 2 - Was the objective changed since storing the focus
        if self.DFObjective != self.get_objective_name():
            self.set_autofocus_not_ready()
            raise AutofocusObjectiveChangedError(message='Different objective was used to set focus position.')
        return True

    def set_last_known_focus_position(self, focusPosition):
        """
        Function to store focus position for recovery if auto focus fails
        :param focusPosition: position of the focus drive in micrometers
        :return:
        """
        self.lastKnownFocusPosition = focusPosition

    def get_last_known_focus_position(self):
        """
        Function to retrieve last focus position if auto focus fails
        :return: lastKnownFocusPosition: position in micrometers
        """
        if self.lastKnownFocusPosition is None:
            raise AutofocusNotSetError(message='Autofocus position not defined.')
        return self.lastKnownFocusPosition

    def recover_focus(self):
        """
        Function to recover focus from auto focus failure
        Moves the focus to last know focus position
        :return:
        """
        # Test the validity of the Objective
        if self.get_objective_name() == '':
            self.set_autofocus_not_ready()
            raise AutofocusError(message='No objective is selected.')

        # Move focus to last know position
        self.move_focus_to(self.get_last_known_focus_position())
        self.store_focus()

    def z_relative_move(self, delta):
        """
        Function to move focus relative to the current position
        It finds current focus position using API call, calculates new position by adding delta to the old one,
        and moves focus to the new position using another Zen API call
        :param delta: distance in micrometers
        :return: z: Updated position of focus drive
        """
        try:
            zStart = self.get_focus_pos()
            zEndCalc = zStart + delta
            self.move_focus_to(zEndCalc)
            z = self.get_focus_pos()
        except:
            raise HardwareError('Error in Relative movement of focus in the z direction (connectZenBlack.py).')
        return z

    def z_down_relative(self, delta):
        """
        Function to move the focus relative to the current position away from the sample
        :param delta: absolute distance in micrometers
        :return: z: New position of the focus drive in micrometers
        """
        z = self.z_relative_move(-delta)
        return z

    def z_up_relative(self, delta):
        """
        Function to move focus relative to the current position towards the smaple
        :param delta: absolute distance in micrometers
        :return: z: new position of the focus drive
        """
        z = self.z_relative_move(delta)
        return z

    def set_focus_work_position(self):
        """
        Function to retrieve current focus position and update the z_work position
        :return: zWork: current focus position in micrometers
        """
        self.zWork = self.get_focus_pos()
        log.info('Stored current focus position as work position', str(self.zWork))
        return self.zWork

    def set_focus_load_position(self):
        """
        Function to retrieve current focus position and update the z_load position
        :return: zLoad: current focus position in micrometers
        """
        self.zLoad = self.get_focus_pos()
        log.info('Stored current focus position as load position: %s', str(self.zLoad))
        return self.zLoad

    def move_focus_to_load(self):
        """
        Function to move focus to load position if load position is defined
        :return: zFocus: updated position of the focus in micrometers
        """
        # check if load position is defined
        if self.zLoad is None:
            log.error('Load position is not defined.')
            raise LoadNotDefinedError('Tried to move focus drive to load position, but load position was not defined.')
        elif self.zLoad > 1000:
            log.error('Load position too high.')
            raise LoadNotDefinedError('Tried to move focus drive to load position, but load position was too high.')

        # Move to load position if defined
        zFocus = self.move_focus_to(self.zLoad)
        log.info('Moved focus to load position: %s.', str(zFocus))
        return zFocus

    def move_focus_to_work(self):
        """
        Function to move focus to work position if work position is defined
        :return: zFocus: updated position of the focus in micrometers
        """
        if self.zWork is None:
            log.error('Work position is not defined.')
            return None

        # Move to work position if defined
        zFocus = self.move_focus_to(self.zWork)
        log.info('moved focus to load position: %s.', str(zFocus))
        return zFocus

    def wait_for_objective(self, target_objective):
        """
        Function to wait till the correct objective is in place
        :param target_objective: Name of the objective (string)
        :return:
        """
        while True:
            current_objective = self.get_objective_name()
            if current_objective == target_objective:
                break

    def get_all_objectives(self, nPositions):
        """
        Function to retrieve the name and magnification of all objectives
        uses self.get_objective_changer_object()
        WARNING: The objectives will move
        :param nPositions: Number of objective positions
        :return: objectives_dict = {'magnification': {'Position': position, 'name': name}}
        """
        try:
            # Get the objective changer object
            objective_changer = self.get_objective_changer_object()
            objectives_dict = {}
            for position in range(1, nPositions + 1):
                magnification = objective_changer.Magnification(position)
                name = objective_changer.Name(position)
                objectives_dict[magnification] = {'Position': position, 'Name': name}
                objinfo = ''
                objinfo = objinfo + ' ' + format(position)
                objinfo = objinfo + '\t' + format(magnification)
                objinfo = objinfo + '\t' + name
                print objinfo
        except:
            raise HardwareError('Error in get_all_objectives.')
        return objectives_dict

    def get_objective_magnification(self):
        """
        Function to get the magnification of the current objective
        uses self.get_objective_changer_object()
        :return: magnification: magnification of actual objective, objective in imaging position
        """
        objective_changer = self.get_objective_changer_object()
        current_objective_mag = objective_changer.RevolverPositionMagnification
        return current_objective_mag

    def get_objective_name(self):
        """
        Function to get the name of the objective in the imaging position
        uses self.get_objective_changer_object()
        :return: current_objective_name: name of actual objective, objective in imaging position
        """
        objective_changer = self.get_objective_changer_object()
        current_objective_name = objective_changer.RevolverPositionName
        return current_objective_name

    def get_objective_position(self):
        """
        Function to get the position of the imagine objective
        :return: position: position of actual objective, objective in imaging position
        """
        try:
            # Retrieve ZEN ObjectiveChanger object
            objective_changer = self.get_objective_changer_object()
            # Get position of objective
            position = objective_changer.RevolverPosition
        except:
            raise HardwareError('Error in get_objective_name.')
        return position