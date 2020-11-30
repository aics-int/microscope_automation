from lxml import etree
import logging

try:
    from pathlib import Path
except ImportError:
    from pathlib2 import Path


log = logging.getLogger(__name__)


class ZenExperiment(object):

    TAG_PATH_TILE_CENTER_XY = (
        "/HardwareExperiment/ExperimentBlocks/AcquisitionBlock/SubDimensionSetups/"
        "RegionsSetup/SampleHolder/TileRegions/TileRegion/CenterPosition"
    )
    TAG_PATH_TILE_CENTER_Z = (
        "/HardwareExperiment/ExperimentBlocks/AcquisitionBlock/SubDimensionSetups"
        "/RegionsSetup/SampleHolder/TileRegions/TileRegion/Z"
    )

    def __init__(self, experiment_path, experiment_name):
        """Initializing the experiment class

        Input:
         experiment_name: Name of the experiment as defined in the Zen software
         and preference file

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
        """Function to check if the experiment name provided
        in the preference file exists in the Zen software

        Input:
         none

        Output:
         a boolean indicating if the experiment exists or not
        """
        # log.debug("Experiment path: {}".format(self.experiment_path))
        experiment_exists = Path(self.experiment_path).exists()
        return experiment_exists

    def get_tag_value(self, tag_path):
        """Function to find the value of a tag in the Zen Experiment file.

        Input:
         experiment_name: Name of the experiment file

        Output:
         tag_value: string value of the tag
        """
        root = self.tree.getroot()
        try:
            tag = root.xpath(tag_path)
            tag_value = tag[0].text
            return tag_value
        except Exception as err:
            log.exception(err)
            raise ValueError("Tag path '{}' is not valid".format(tag_path))

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
            log.exception(err)
            raise ValueError(
                "Updating tag '{}' for experiment {} raised the error: {}".format(
                    tag_path, self.experiment_path, err.strerror
                )
            )

    def is_tile_scan(self):
        """Test if experiment is tile scan.

        Input:
         none

        Output:
         is_tile_scan: True if experiment contains z-stack
        """
        root = self.tree.getroot()
        # retrieve all z-stack setups, use only fist
        RegionsSetup = root.findall(".//RegionsSetup")[0]
        is_tile_scan = RegionsSetup.attrib["IsActivated"] == "true"
        return is_tile_scan

    def update_tile_positions(self, x_value, y_value, z_value):
        """In the tile function, correct the hard coded values of the tile
        region using the values from the automation software

        Input:
         x_value: float (x - coordinate)

         y_value: float (y - coordinate)

         z_value: float (z - coordinate)

        Output:
         none
        """

        xy_value = str(x_value) + "," + str(y_value)
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
        """Return position of objective used in experiment.
        Method assumes that only one objective is used in experiment.

        Input:
         None

        Output:
         position: integer with position of objective used in experiment
        """
        root = self.tree.getroot()
        # retrieve all objective changers. Use only first
        objective_changer = root.findall(
            ".//ParameterCollection[@Id = 'MTBObjectiveChanger']"
        )[0]
        position = int(objective_changer.find("Position").text)
        return position

    def is_z_stack(self):
        """Test if experiment is z-stack.

        Input:
         none

        Output:
         is_z_stack: True if experiment contains z-stack
        """
        root = self.tree.getroot()
        # retrieve all z-stack setups, use only first
        # TODO:
        # I would separate this out into two steps -
        # one where you do the findall and another to access the first item.
        # That way, you can actually check if the file has any MTBObjectiveChanger
        # entries in it and throw an appropriate error if they are non, rather
        # than have the findall return an empty list and
        # then the [0] access throw an undescriptive IndexError.
        # It may be helpful to write a common function for this that
        # will take the result of a findall, ensure that there is
        # at least one element in it and if not throw a more appropriate exception.
        ZStackSetup = root.findall(".//ZStackSetup")[0]
        is_z_stack = ZStackSetup.attrib["IsActivated"] == "true"
        return is_z_stack

    def z_stack_range(self):
        """Return range of first z-stack in experiment.
        Returns 0 if z-stack is not activated.

        Input:
         none

        Output:
         z_stack_range: True if experiment contains z-stack
        """
        if not self.is_z_stack():
            return 0
        else:
            root = self.tree.getroot()
            # retrieve all z-stack setups, use only fist
            ZStackSetup = root.findall(".//ZStackSetup")[0]
            first_postion = float(ZStackSetup.find("First/Distance/Value").text)
            last_postion = float(ZStackSetup.find("Last/Distance/Value").text)
            z_stack_range = abs(last_postion - first_postion)
            return z_stack_range
