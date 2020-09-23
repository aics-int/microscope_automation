'''
Export position list for ZEN blue tiles experiment (.czsh)
Created on Jul 26, 2019

authors: Brian Kim, Calysta Yan, winfriedw
'''

import xml.etree.ElementTree as ET
import os
import pandas as pd

class save_position_list(object):
    '''
    Converts positions to stage coordinates, saves positions to .czsh file
    Requirements:
        1) Ensure the dummy_tile_positions.czsh path is specified in preferences under key "PathDummy"

    '''


    def __init__(self, zsd, plate, production_path, testing_mode=False):
        """
        Initialization

        Inputs:
         zsd:             String or integer Id of ZSD used for acquisition
         plate:           String of integer Id of plate
         production_path  Path of the prouduction folder
        Return:
         None
        """
        # Check Inputs
        if production_path is None:
            raise ValueError("Production path not specified")
        if type(plate) is not str:
            if type(plate) is int:
                plate = str(plate)
            else:
                raise ValueError("specified plate number is not a number or a string")
        if type(zsd) is not str:
            if type(zsd) is int:
                zsd = str(zsd)
            else:
                raise ValueError("specified ZSD id is not a number or a string")
        if isinstance(production_path, list):
            production_path = production_path[0]

        self.plate = plate
        self.path = os.path.join(production_path, plate, zsd)
        if not os.path.exists(self.path):
            raise OSError("Please check zsd, plate, and production path info given to save_position_list")
        self.zsd = zsd

    def convert_to_stage_coords(self, offset_x=0, offset_y=0, positions_list=[]):
        """
        Converts the distance of points from center of image to x-y coordinates in
        stage with 10 to 100x objective offsets.

        Inputs:
         offset_x:        x_offset to account for in stage coordinate conversion
         offset_y:        y_offset to accoutn for in stage coordinate conversion
         positions_list:  center of well positions to convert to stage coordinates
        Return:
         converted_list:  stage coordinates of positions converted from center of well positions
        """

        # Check to ensure there are positions to convert
        if len(positions_list) <= 1:
            raise AssertionError("positions list from automation software needs to contain coordinates")

        converted_list = []
        obj_offset = [offset_x, offset_y]
        for i in range(1, len(positions_list)):
            # positions_list[i][0] is name of position from automation software
            this_position = dict()
            this_position["name"] = positions_list[i][0]
            this_position["actual_x"] = positions_list[i][1] + obj_offset[0] #coordinate X + offset for X
            this_position["actual_y"] = positions_list[i][2] + obj_offset[1] #coordinate Y + offset Y
            this_position["actual_z"] = positions_list[i][3]                 #coordinate Z (no offset here)
            converted_list.append(this_position)

        return converted_list




    def write(self, converted=[], dummy='', name_czsh='positions_output.czsh'):
        """
        Writes coordinates to a dummy.czsh file, and saves it

        Inputs:
         converted:       positions to write to the czsh file
         dummy:           empty (no coordinates) .czsh file to use for writing
         name_czsh:       name to save written .czsh file as
        Return:
         None
        """

        # Theres no data here, or the file was mistakenly rewritten
        if len(converted) == 0:
            raise AssertionError("Need positions to write, Did you call convert_to_stage_coords()?")
        # Get empty file
        tree = ET.parse(os.path.abspath(dummy))
        root = tree.getroot()
        for single_tiles in root.iter("SingleTileRegions"):

            for n in converted:
                # Assign Values for writing
                tile = ET.SubElement(single_tiles, "SingleTileRegion")
                tile.set('Name', n["name"])
                # Need str for tree.write()
                ET.SubElement(tile, "X").text = str(n["actual_x"])
                ET.SubElement(tile, "Y").text = str(n["actual_y"])
                ET.SubElement(tile, "Z").text = str(n["actual_z"])
                ET.SubElement(tile, "IsUsedForAcquisition").text = 'true'

        # Write Values
        tree.write(os.path.join(self.path, name_czsh))


