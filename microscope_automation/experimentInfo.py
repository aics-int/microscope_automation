# module to extract and update information from the zen software experiment files (.czexp)

from lxml import etree
import os
try:
    from pathlib import Path
except ImportError:
    from pathlib2 import Path

try:
    from . import preferences
except:
    import preferences

import logging


log = logging.getLogger(__name__)


class ZenExperiment(object):

    TAG_PATH_TILE_CENTER_XY = '/HardwareExperiment/ExperimentBlocks/AcquisitionBlock/SubDimensionSetups/' \
            'RegionsSetup/SampleHolder/TileRegions/TileRegion/CenterPosition'
    TAG_PATH_TILE_CENTER_Z = '/HardwareExperiment/ExperimentBlocks/AcquisitionBlock/SubDimensionSetups' \
            '/RegionsSetup/SampleHolder/TileRegions/TileRegion/Z'

    def __init__(self, experiment_path, experiment_name):
        """
        Initializing the experiment class
        :param experiment_name: Name of the experiment as defined in the Zen software & preference file
        :param prefs: the preference file for the workflow
        """
        self.experiment_path = experiment_path
        self.experiment_name = experiment_name
        if self.experiment_exists():
            self.tree = etree.parse(self.experiment_path)
        else:
            self.tree = None

    def experiment_exists(self):
        """
        Function to check if the experiment name provided in the preference file exists in the Zen software

        :return: a boolean indicating if the experiment exists or not
        """
        #log.debug("Experiment path: {}".format(self.experiment_path))
        experiment_exists = Path(self.experiment_path).exists()
#         print('Experiment {} exists: {}'.format(self.experiment_path, experiment_exists))
        return experiment_exists

    def get_tag_value(self, tag_path):
        """
        Function to find the value of a tag in the Zen Experiment file
        :param experiment_name: Name of the experiment file
        :return: String value of the tag
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
        """
        Function to update the value of a tag in the experiment xml file
        :param tag_path: Path where the tag is loacted in the xml tree
        :param new_value: The value that needs to be assigned to the tag (string)
        :return: Nothing
        """
        root = self.tree.getroot()
        try:
            tag = root.xpath(tag_path)
            tag[0].text = new_value
            self.tree.write(self.experiment_path)
        except Exception as err:
            log.exception(err)
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
        """
        In the tile function, correct the hard coded values of the tile region using the values from
         the automation software
        :param x_value: float (x - coordinate)
        :param y_value: float (y - coordinate)
        :param z_value: float (z - coordinate)
        :return:
        """

        xy_value = str(x_value) + ',' + str(y_value)
        self.update_tag_value(self.TAG_PATH_TILE_CENTER_XY, xy_value)
        self.update_tag_value(self.TAG_PATH_TILE_CENTER_Z, str(z_value))

    def get_focus_settings(self):
        """
        Function to get all th instances of focus settings in the experiment file
        :return:
        """
        root = self.tree.getroot()
        # retrieve all focus setups
        focus_settings = root.findall(".//FocusSetup")
        return focus_settings

    def get_objective_position(self):
        ''' Return position of objective used in experiment.
        
        Input:
         None
         
        Output:
         position: integer with position of objective used in experiment
         
        
        Method assumes that only one objective is used in experiment
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
        # retrieve all z-stack setups, use only fist
        # TODO:
        # I would separate this out into two steps - one where you do the findall and another to access the first item. 
        # That way, you can actually check if the file has any MTBObjectiveChanger entries in it and throw an appropriate error if they are non, rather than have the findall return an empty list and then the [0] access throw an undescriptive IndexError.
        # It may be helpful to write a common function for this that will take the result of a findall, ensure that there is at least one element in it and if not throw a more appropriate exception.
        ZStackSetup = root.findall(".//ZStackSetup")[0]
        is_z_stack = ZStackSetup.attrib['IsActivated'] == 'true'
        return is_z_stack        

    def z_stack_range(self):
        '''Return range of first z-stack in experiment.
        
        Input:
         none
         
        Output:
         z_stack_range: True if experiment contains z-stack
         
        Returns 0 if z-stack is not activated
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
        
if __name__ == '__main__':

    # Initializing the object
    prefs = preferences.Preferences('../GeneralSettings/preferences_ZSD1_Shailja.yml')
    experiment_directory = prefs.getPref('PathExperiments')
    experiment_name = 'ScanWell_10x.czexp'
#     experiment_path = os.path.normpath(os.path.join(prefs.getPref('PathExperiments'),
#                                                     experiment_name))
    experiment_path = 'D:\Users\winfriedw\Documents\Carl Zeiss\ZEN\Documents\Experiment Setups/ScanWell_10x.czexp'
    test_object = ZenExperiment(experiment_path, experiment_name)

    # Test 1 - Experiment exists
    #result_test1 = test_object.experiment_exists()
    #print(result_test1)

    # Test 2 - Get Tag Value
    #tag_value = test_object.get_tag_value('/HardwareExperiment/ExperimentBlocks/AcquisitionBlock/SubDimensionSetups'
                                          #'/RegionsSetup/SampleHolder/TileRegions/TileRegion/CenterPosition')
    # Test 3 - Update Tag Value
    print('Experiment acquires tile scan: {}'.format(test_object.is_tile_scan()))
    test_object.update_tag_value('/HardwareExperiment/ExperimentBlocks/AcquisitionBlock/SubDimensionSetups'
                                 '/RegionsSetup/SampleHolder/TileRegions/TileRegion/CenterPosition', '5000,7800')

    # Test 4 - Update Tile Positions
    #test_object.update_tile_positions(3600, 7600, 4)

    # Test 5: Get objective name
    print('Objective position used in experiment: {}'.format(test_object.get_objective_position()))
    
    # Test 6: Return z-stack information
    print('Experiment acquires z-stack: {}'.format(test_object.is_z_stack()))
    print('Range for z-stack: {}'.format(test_object.z_stack_range()))
    