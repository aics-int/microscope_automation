"""
Communication layer for 3i Slidebook
This layer sends http commands to a command and data servers.
Slidebook calls a MatLab library that pulls the commands from the server queue

Date Created: January 26, 2020
"""

import time
import os.path
import logging
import requests
import numpy as np
import matplotlib.pyplot as plt

# import modules from project MicroscopeAutomation
from ..automation_exceptions import (
    HardwareError,
    LoadNotDefinedError,
    WorkNotDefinedError,
    HardwareCommandNotDefinedError,
    ExperimentNotExistError,
)
from .slidebook_experiment_info import SlidebookExperiment
from ..image_AICS import ImageAICS

try:
    from ..hardware.RS232 import Braintree
except ImportError:
    from ..hardware.RS232_dummy import Braintree

# Create Logger
log = logging.getLogger("microscopeAutomation connect_slidebook")


def show_image(image, meta_data):
    """Show image"""
    plt.imshow(image)
    plt.title(meta_data["time_stamp"])
    plt.show()


class ConnectMicroscope:
    """"""

    def __init__(
        self,
        cmd_url="http://127.0.0.1:5000",
        data_url="http://127.0.0.1:5100",
        microscope="3iW1-0",
        dummy=False,
    ):
        """Connect to command and data services that function as bridge
        to the MatLab macro that controls 3i Slidebook

        Input:
            cmd_url: url for command server. Typical localhost at port 5000

            data_url: url for data (image) server. Typical localhost at port 51000

            microscope: microscope that should have connected to command and data server

        Output:
         none
        """
        self.cmd_url = cmd_url + "/cmd"
        self.data_url = data_url + "/data"
        self.microscope = microscope
        self.dummy = dummy

        if self.dummy:
            self.default_experiment = {
                "experiment_id": "",
                "microscope": self.microscope,
                "number_positions": 1,
                "stage_locations": [(0, 0, 0)],
                "stage_locations_filter": [True],
                "capture_settings": ["No_experiment"],
                "centers_of_interest": [(0, 0, 0)],
                "objective": "Apo_10x",
                "time_stamp": "",
                "microscope_action": "exit",
                "id_counter": 0,
                "status": "none",
            }
            self.zLoad = 500
            self.zWork = 500
            print("Running in Test Mode - Connecting to Simulated hardware")
            return

        # test connections and get information about servers

        # Test commands server. This server send commands to the microscope.
        # The commands are stored in a queue and worked on in the order they were posted
        try:
            cmd_response = requests.get(self.cmd_url + "/about")
            # Raise if bad status code
            cmd_response.raise_for_status()
            self.cmd_server_info = cmd_response.json()
        except requests.exceptions.RequestException as e:
            # catastrophic error. bail.
            raise SystemExit(e)

        # Test data server.
        # This server will receive images form microscope and store them in a queue.
        data_response = requests.get(self.data_url + "/about")
        # Raise if bad status code
        data_response.raise_for_status()
        self.data_server_info = data_response.json()

        self.microscope = microscope
        self.default_experiment = {
            "experiment_id": "",
            "microscope": self.microscope,
            "number_positions": 1,
            "stage_locations": [(0, 0, 0)],
            "stage_locations_filter": [True],
            "capture_settings": ["No_experiment"],
            "centers_of_interest": [(0, 0, 0)],
            "objective": "Apo_10x",
            "time_stamp": "",
            "microscope_action": "exit",
            "id_counter": 0,
            "status": "none",
        }

    def not_implemented(self, method_name):
        """Raise exception if method is not implemented.

        Input:
         method_name: method that calls this method

        Output:
         none
        """
        raise HardwareCommandNotDefinedError(
            method_name + " is not supported for Slidebook microscope"
        )

    ############################################################################
    #
    # Methods to handle Capture Settings
    #
    ############################################################################

    def create_experiment_path(self, experiment, experiment_folder):
        """Creates complete path to capture settings.
        Raises exception if experiment does not exist.

        Input:
         experiment: string with name of capture settings
         (with or w/o extension .exp.prefs)

         experiment_folder: folder for capture settings

        Output:
         experiment_path: path to experiment
        """
        # make sure that experiment has proper extension
        name_1, extension_prefs = os.path.splitext(experiment)
        name, extension_exp = os.path.splitext(name_1)
        # experiment_corrected = name + '.exp.prefs'
        experiment_path = os.path.normpath(os.path.join(experiment_folder, experiment))
        if not os.path.exists(experiment_path):
            raise ExperimentNotExistError(
                "Could not create experiment path {}.".format(experiment_path),
                experiment,
            )
        return experiment_path

    ############################################################################
    #
    # Methods to get information about command and data services
    #
    ############################################################################

    def get_about_command_service(self):
        """Retrieve information about command service"""

        about_response = requests.get(self.cmd_url + "/about")
        # Raise if bad status code
        about_response.raise_for_status()
        return about_response.json()

    def get_about_data_service(self):
        """Retrieve information about data service"""

        about_response = requests.get(self.data_url + "/about")
        # Raise if bad status code
        about_response.raise_for_status()
        return about_response.json()

    ############################################################################
    #
    # Methods to save and load images and meta data
    #
    ############################################################################

    def save_image(self, fileName):
        """Save last acquired ImageAICS in original file format
        using microscope software

        Raises HardwareCommandNotDefinedError

        Input:
         file: file name and path for ImageAICS save

        Output:
         none
        """
        self.not_implemented("save_image")

    def load_image(self, image, get_meta_data=False):
        """Load most recent image from data service and return it a class ImageAICS

        Input:
         image: image object of class ImageAICS.

         get_meta: if true, retrieve meta data from file. Default is False

        Output:
         image: image with data and meta data as ImageAICS class
        """
        # Retrieve most recent meta data from data queue
        meta_response = requests.get(self.data_url + "/last")
        # Raise if bad status code
        meta_response.raise_for_status()

        if meta_response.status_code == 200:
            # get meta data
            meta_data = meta_response.json()

            # get image and decode
            response = requests.get(self.data_url + "/binary/" + meta_data["data_id"])
            image_data = np.frombuffer(
                response.content, dtype=meta_data["format"]
            ).reshape(meta_data["image_dimensions"])
        else:
            image_data = None
            meta_data = None
        # show_image(image_data, meta_data)
        if image is None:
            image = ImageAICS(data=image_data)
        else:
            image.add_data(image_data)

        if get_meta_data and meta_data is not None:
            # add additional meta data
            if get_meta_data:
                meta = {}
                physical_size = meta_data["xy_pixel_size"]
                # Slidebook returns pixel size in  micrometers
                meta["PhysicalSizeX"] = physical_size
                meta["PhysicalSizeXUnit"] = "mum"
                meta["PhysicalSizeY"] = physical_size
                meta["PhysicalSizeYUnit"] = "mum"
                meta["PhysicalSizeZ"] = meta_data["z_spacing"]
                meta["PhysicalSizeZUnit"] = "mum"
                # TODO: Handle multi channel image
                channel_size = 1
                # Test the channel stuff
                for c in range(channel_size):
                    meta["Channel_" + str(c)] = "Channel_" + str(c)
                meta["Type"] = meta_data["format"]
                meta["Microscope"] = meta_data["microscope"]
                meta["StageLocationX"] = meta_data["stage_location"][0]
                meta["StageLocationY"] = meta_data["stage_location"][1]
                meta["StageLocationZ"] = meta_data["stage_location"][2]
                meta["TimeStamp"] = meta_data["time_stamp"]
                meta["StageDirectionX"] = meta_data["x_stage_direction"]
                meta["StageDirectionY"] = meta_data["y_stage_direction"]
                meta["StageDirectionZ"] = meta_data["z_stage_direction"]
                meta["IdCounter"] = meta_data["id_counter"]
                meta["DataId"] = meta_data["data_id"]
                meta["TmpPath"] = meta_data["tmp_path"]
                image.add_meta(meta)
        return image

    def remove_all(self):
        """Remove all images from queue at data service.

        Input:
         none

        Output:
         none
        """
        response = requests.delete(self.data_url + "/clear")
        # Raise if bad status code
        response.raise_for_status()

    ############################################################################
    #
    # Methods to manipulate commands queue
    #
    ############################################################################
    def clear_experiments(self):
        """Clear experiments queue"""
        experiments_response = requests.delete(self.cmd_url + "/experiments/clear")
        # Raise if bad status code
        experiments_response.raise_for_status()

    def count_experiments(self):
        """Return number of experiments inqueue"""
        experiments_response = requests.get(self.cmd_url + "/experiments/count")
        # Raise if bad status code
        experiments_response.raise_for_status()
        return experiments_response.json()

    def post_experiment(self, experiment):
        """Post experiment as last entry on queue and return updated experiment"""
        experiments_response = requests.post(
            self.cmd_url + "/experiments", json=experiment
        )
        # Raise if bad status code
        experiments_response.raise_for_status()
        return experiments_response.json()

    def get_next_experiment(self):
        """Return next (oldest) experiments in queue"""
        experiments_response = requests.get(self.cmd_url + "/experiments/next")
        # Raise if bad status code
        experiments_response.raise_for_status()
        if experiments_response.status_code == 204:
            return None
        else:
            return experiments_response.json()

    def get_experiment(self, experiment_id):
        """Return experiment by id"""
        experiments_response = requests.get(
            self.cmd_url + "/experiments/" + experiment_id
        )
        # Raise if bad status code
        experiments_response.raise_for_status()
        return experiments_response.json()

    def delete_experiment(self, experiment_id):
        """Delete experiment by id"""
        experiments_response = requests.delete(
            self.cmd_url + "/experiments/" + experiment_id
        )
        # Raise if bad status code
        experiments_response.raise_for_status()
        return experiments_response.json()

    def get_experiment_dict(self):
        """Retrieve dictionary with all experiments on queue"""
        experiments_response = requests.get(self.cmd_url + "/experiments")
        # Raise if bad status code
        experiments_response.raise_for_status()
        return experiments_response.json()

    ############################################################################
    #
    # Methods to acquire images
    #
    ############################################################################

    def snap_image(self, capture_settings, objective=""):
        """Snap image with parameters defined in experiment at current location.
        Raise exception if request was not successful

        Input:
         capture_settings: string with name of capture_settings as defined
         within Microscope software

         objective: objective used to acquire image. If none keep objective.

        Return:
         response: Return dictionary with response from commands microservice
        """
        experiment = self.default_experiment
        experiment["objective"] = objective
        experiment["microscope_action"] = "snap"

        if self.dummy:
            return {"microscope": ""}

        response = requests.post(self.cmd_url + "/experiments", json=experiment)
        # raise exception if request was not successful
        response.raise_for_status()
        return response.json()

    def execute_experiment(self, capture_settings, locations, objective=""):
        """Execute experiments with parameters defined in experiment
        on multiple positions.

        Input:
         capture_settings: string with name of experiment as defined within
         Microscope software

         objective: objective used to acquire image. If none keep objective.

         locations: list with (x,y,z) stage locations
        Output:
         success: True when experiment was successfully posted on command server
        """
        experiment = self.default_experiment
        experiment["stage_locations"] = locations
        experiment["capture_settings"] = [capture_settings] * len(locations)
        experiment["centers_of_interest"] = locations
        experiment["objective"] = objective
        experiment["microscope_action"] = "move_snap"

        response = requests.post(self.cmd_url + "/experiments", json=experiment)
        success = response.status_code == requests.codes.ok
        return success

    def live_mode_start(self, experiment):
        """Start live mode.
        Included for parity between Microscope connections.

        Raises HardwareCommandNotDefinedError.

        Input:
         experiment: name of experiment

        Output:
         none
        """
        self.not_implemented("live_mode_start")

    def live_mode_stop(self, experiment):
        """Stop live mode.
        Included for parity between Microscope connections.

        Raises HardwareCommandNotDefinedError.

        Input:
         experiment: name of experiment

        Output:
         none
        """
        self.not_implemented("live_mode_stop")

    ############################################################################
    #
    # Methods to control motorized xy stage
    #
    ############################################################################

    def get_stage_pos(self, repetitions=5, wait=1):
        """Return most recent position of Microscope stage.

        Input:
         repetitions: number of times to try to get a response

         wait: wait time per repetition in sec

        Output:
         xPos, yPos, zPos: x and y position of stage in micrometer
        """
        for i in range(repetitions):
            response = requests.get(self.cmd_url + "/recent_position")
            # Raise if bad status code
            response.raise_for_status()
            if len(response.json()) > 0:
                return response.json()["stage_location"]
            time.sleep(wait)
        raise requests.exceptions.Timeout()

    def move_stage_to(self, xPos, yPos, zPos, capture_settings=None, test=False):
        """Move stage to new position.

        Input:
         xPos, yPos, zPos: new stage and objective position in micrometers.

         capture_settings: capture settings in Slidebook Capture dialog to move stage

         test: not used but included for consistency with ZEN Blue API

        Output:
         xPos, yPos, zPos: new stage and objective position in micrometers
        """
        if xPos is None or yPos is None or zPos is None:
            raise HardwareError("Position not defined in move_stage_to.")

        if test:
            raise HardwareCommandNotDefinedError(
                "move_stage_to method does not support testing with Slidebook microscope"  # noqa
            )

        xPos, yPos, zPos = int(round(xPos)), int(round(yPos)), int(round(zPos))
        experiment = self.default_experiment
        if capture_settings is not None:
            experiment["capture_settings"] = capture_settings
        experiment["stage_locations"] = [(xPos, yPos, zPos)]
        experiment["microscope_action"] = "move"
        experiment["capture_settings"] = []

        requests.post(self.cmd_url + "/experiments", json=experiment)
        return [xPos, yPos, zPos]

    ############################################################################
    #
    # Methods to control focus
    #
    ############################################################################
    def get_focus_pos(self):
        """Return current position of focus drive.

        Input:
         none

        Output:
         zPos: position of focus drive in micrometer
        """
        positions = self.get_stage_pos()
        if len(positions) == 0:
            return None
        return positions[2]

    def move_focus_to(self, zPos):
        """Move focus to new position.
        Included for parity between Microscope connections.

        Raises HardwareCommandNotDefinedError.

        Input:
         zPos, yPos: new focus position in micrometers.

        Output:
         zFocus: new position of focus drive
        """
        self.not_implemented("move_focus_to")

    def z_relative_move(self, delta):
        """Move focus relative to current position.
        Included for parity between Microscope connections.

        Raises HardwareCommandNotDefinedError.

        Input:
         delta: distance in mum

        Output:
         z: new position of focus drive
        """
        self.not_implemented("z_relative_move")

    def z_down_relative(self, delta):
        """Move focus relative to current position away from sample.
        Included for parity between Microscope connections.

        Raises HardwareCommandNotDefinedError.

        Input:
         delta: absolute distance in mum

        Output:
         z: new position of focus drive
        """
        z = self.z_relative_move(-delta)
        return z

    def z_up_relative(self, delta):
        """Move focus relative to current position towards sample.
        Included for parity between Microscope connections.

        Raises HardwareCommandNotDefinedError.

        Input:
         delta: absolute distance in mum

        Output:
         z: new position of focus drive
        """
        z = self.z_relative_move(delta)
        return z

    def set_focus_work_position(self):
        """Retrieve current position and set as work position.

        Input:
         none

        Output:
         z_work: current focus position in mum
        """
        z_work = self.get_focus_pos()
        self.zWork = z_work

        log.info("Stored current focus position as work position", str(z_work))

        return z_work

    def set_focus_load_position(self):
        """Retrieve current position and set as load position.

        Input:
         none

        Output:
         zLoad: current focus position in mum
        """
        zLoad = self.get_focus_pos()
        self.zLoad = zLoad

        log.info("Stored current focus position as load position: %s", str(zLoad))

        return zLoad

    def move_focus_to_load(self):
        """Move focus to load position if defined.

        Input:
         zPos, yPos: new focus position in micrometers.

        Output:
         zFocus: new position of focus drive
        """
        # check if load position is defined
        if self.zLoad is None:
            log.error("Load position not defined")
            raise LoadNotDefinedError(
                "Tried to move focus drive to load position, but load position was not defined."  # noqa
            )

        if self.zLoad > 1000:
            log.error("Load position too high")
            raise LoadNotDefinedError(
                "Tried to move focus drive to load position, but load position was too high."  # noqa
            )

        # move to load position if defined
        zFocus = self.move_focus_to(self.zLoad)

        log.info("moved focus to load position: %s", str(zFocus))

        return zFocus

    def move_focus_to_work(self):
        """Move focus to work position if defined.

        Input:
         zPos, yPos: new focus position in micrometers.

        Output:
         zFocus: new position of focus drive
        """
        # check if load position is defined
        if self.zWork is None:
            log.error("Work position not defined")
            raise WorkNotDefinedError(
                "Tried to move focus drive to work position, but work position was not defined."  # noqa
            )

        # move to load position if defined
        zFocus = self.move_focus_to(self.zWork)

        log.info("moved focus to load position: %s", str(zFocus))

        return zFocus

    ############################################################################
    #
    # Methods to control immersion water delivery
    #
    ############################################################################

    def trigger_pump(self, seconds, port="COM1", baudrate=19200):
        """Trigger pump

        Input:
         seconds: the number of seconds pump is activated

         port: com port, default = 'COM1'

         baudrate: baudrate for connection, can be set on pump, typically = 19200

        Output:
         none
        """
        try:
            # connect to pump through RS232
            pump = Braintree(port="COM1", baudrate=19200)

            # activate pump
            pump.start_pump()

            # continue pumping for seconds
            time.sleep(seconds)

            # stop pump and close connection
            pump.close_connection()
        except Exception:
            raise HardwareError("Error in trigger_pump.")

        log.debug("Pump activated for : %s sec", seconds)

    ############################################################################
    #
    # Methods to collect information about microscope
    #
    ############################################################################

    def get_microscope_name(self):
        """Returns name of the microscope from hardware that is controlled by this class

        Input:
         none

        Output:
         Microscope: name of Microscope
        """

        name = "get_microscope_name not implemented"
        log.info("This class controls the microscope: %s", name)
        return name

    def stop(self):
        """Stop Microscope immediately"""
        log.info("Microscope operation aborted")

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
        slidebook_experiment = SlidebookExperiment(experiment_path, experiment_name)
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
        self.not_implemented("get_focus_settings")

    def get_objective_position_from_experiment_file(
        self, experiment_path=None, experiment_name=None
    ):
        """Function to get the position of the objective used in the experiment
        Included for parity between Microscope connections.

        Raises HardwareCommandNotDefinedError.

        Input:
         experiment_path: path of the experiment file

         experiment_name: name of the experiment

        Output:
         none
        """
        self.not_implemented("get_objective_position_from_experiment_file")

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
        self.not_implemented("is_z_stack")

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
        self.not_implemented("z_stack_range")

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
        self.not_implemented("is_tile_scan")

    def update_tile_positions(
        self, experiment_path, experiment_name, x_value, y_value, z_value
    ):
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
        self.not_implemented("update_tile_positions")
