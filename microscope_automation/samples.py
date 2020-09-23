'''
Classes to describe and manipulate samples
Created on Jul 11, 2016

@author: winfriedw
'''

import logging
import math
import string
import pandas
from os import path
import warnings
from collections import OrderedDict
# import modules from project MicroscopeAutomation
# from . import preferences
# from .getPath import *
# from .drawPlate import drawPlate
# from . import automationMessagesFormLayout as message
# from . import findWellCenter
# from .getPath import add_suffix
# import numpy
# from . import correctBackground
# # requires module aicsimagetools
# from . import tileImages
# from .loadImageCzi import LoadImageCzi
# # from readBarcode import read_barcode
# from .metaDataFile import meta_data_file
# from .positions_list import CreateTilePositions
# from .automationExceptions import AutofocusError, AutofocusObjectiveChangedError, AutofocusNotSetError, LoadNotDefinedError, HardwareError, ObjectiveNotDefinedError, FileExistsError,\
#     CrashDangerError
# # we need module hardware only for testing
# from . import hardware
# from .interactive_location_picker_pyqtgraph import ImageLocationPicker
import preferences
from getPath import *
from drawPlate import drawPlate
import automationMessagesFormLayout as message
import findWellCenter
from getPath import add_suffix
import numpy
import correctBackground
# requires module aicsimagetools
import tileImages
from loadImageCzi import LoadImageCzi
# from readBarcode import read_barcode
from metaDataFile import meta_data_file
from positions_list import CreateTilePositions
from automationExceptions import AutofocusError, AutofocusObjectiveChangedError, AutofocusNotSetError, LoadNotDefinedError, HardwareError, ObjectiveNotDefinedError, FileExistsError,\
    MetaDataNotSavedError, CrashDangerError
# we need module hardware only for testing
import hardware
from interactive_location_picker_pyqtgraph import ImageLocationPicker
from __builtin__ import True

# create logger
logger = logging.getLogger('microscopeAutomation')
################################################################################
#
# constants with valid preferences values
#
################################################################################
VALID_FUNCTIONNAME = ['initialize_microscope',
                      'set_up_objectives',
                      'update_plate_well_zZero',
                      'calculate_plate_correction',
                      'calculate_all_wells_correction',
                      'setup_immersion_system',
                      'scan_samples']
VALID_SETUPFILES =[True, False]
VALID_FINDLOAD = [True, False]
VALID_LASERSAFETY = [True, False]
VALID_KOEHLER = [True, False]
VALID_VERBOSE = [True, False]
VALID_USEAUTOFOCUS = [True, False]
VALID_MANUELREFOCUS = [True, False]
VALID_SNAPIMAGE = [True, False]
VALID_WAIT = [True, False]
VALID_LOAD = [True, False]
VALID_LOADBETWEENWELLS = [True, False]
VALID_ADDIMERSIONWATER = [True, False]
VALID_USEPUMP = [True, False]
VALID_TILE = ['NoTiling', 'Fixed', 'Size']
VALID_FINDOBJECTS = ['None', 'Cells', 'Colonies']
VALID_TYPEFINDCELLS = ['False', 'CenterMassCellProfiler', 'TwofoldDistanceMap']
#######################################################################################
#
# Support functions
#
#######################################################################################
def create_plate(plateFormat):
    '''Set up coordinates for different plate layouts for standard plates to be used with class Plate.
    
    Input:
     plateFormat: sting for format of plate ('12', '24', '96')
     
    Output: 
     plateLayout: dictionary to describe plate with entries 
            name: name of plate
            wellDiameter: diameter of well in mum
            wellNames in format 'A1': (x,y) coordinates of well center in plate coordinates in mum. The center of well A1 = (0,0)
    '''
    if plateFormat=='12':
        nrow=3
        ncol=4
        pitch=26000
        diameter=22050
        zCenterWell = 104 
    elif plateFormat=='24':
        nrow=4
        ncol=6
        pitch=19300
        diameter=15540 
        zCenterWell = 104
    elif plateFormat=='96':
        nrow=8
        ncol=12
        pitch=9000
        diameter=6134
        zCenterWell = 104
        
    # calculate name and position of wells
    # Center of well A1 is considered the origin
    plateLayout={'name': plateFormat, 'wellDiameter': diameter}
    for x in range(ncol):
        xName=str(x+1)
        xCoord=x*pitch
        for y in range(nrow):          
            yName=string.ascii_uppercase[y]            
            yCoord=y*pitch
            plateLayout[yName+xName]=(xCoord, yCoord, zCenterWell)
    return plateLayout

#######################################################################################

def create_rect_tile(nCol, nRow, xPitch, yPitch, zPos = 0):
    '''Create coordinates for rectangular tile scan.
    
    Input: 
     nCol, nRow: number of tiles in x and y
     xPitch, yPitch: distance between tile centers in x and y
     zPos: offset in z in mum
     
    Output:
     posList: list with tuples (x,y) for tile centers.
     
    The tiles will be centered around the current stage position.
    '''
    posList=[]
    nCol_int=int(math.ceil(nCol))
    nRow_int=int(math.ceil(nRow))
    for i in [n-(nCol_int-1)/2.0 for n in range(nCol_int)]:
        for j in [k-(nRow_int-1)/2.0 for k in range(nRow_int)]:
            posList.append((i*xPitch, j*yPitch, zPos))
    return posList

#######################################################################################
#
# Classes for sample hierarchy
#
#######################################################################################

class ImagingSystem(object):

    def __init__(self, container=None, name = '',
                 image = True,
                 xZero=0, yZero=0, zZero=0,
                 xFlip=1, yFlip=1, zFlip=1,
                 xCorrection=0, yCorrection=0, zCorrection=0,
                 zCorrectionXSlope=0,
                 zCorrectionYSlope=0,
                 zCorrectionZSlope=0,
                 xSavePosition=None, ySavePosition=None, zSavePosition=None,
                 reference_object = None,
                 x_reference = None, y_reference = None, z_reference = None,
                 prefs = None,
                 microscope_object = None,
                 stage_id = None,
                 focus_id = None,
                 auto_focus_id = None,
                 objective_changer_id = None,
                 safety_id = None):
        '''This is the superclass for all sample related classes (e.g. well, colony, etc).
        
        Input:
         container: class that contains object (e.g. Plate is container for Well)
         name: sting name of object
         image: include in list of samples that will be imaged
         xZero, yZero, zZero: position of object center in container coordinates in mum
         xFlip, yFlip, zFlip: -1 if coordinate system is flipped compared to container, otherwise 1
                         e.g. PlateHolder has origin in lower left corner, 
                         while Zeiss SD stage has origin in upper left corner, 
                         thus xFlip =1 and yFlip=-1
         xCorrection, yCorrection, zCorrection: correction factor for coordinate system relative to container coordinates,
                                     e.g. if 1 mum in well coordinates is not exactly 1 mum in plate coordinates.
         xSavePosition, ySavePosition, zSavePosition: position to start any movements without danger of objective or other collisions
         reference_object: any object of type sample used as reference to correct for xyz offset between different objectives.
                             Use only reference object or reference positions
         x_reference, y_reference, z_reference: positions used as reference to correct for xyz offset between different objectives.
                             Use only reference object or reference positions
                             
        Output:
         None
        '''
        self.images=[]
        self.set_name(name)
        
        # object self is part of, is contained in
        self.set_container(container)
        
        # We can attach images to objects
        # E.g. images for background correction
        self.imageDict = {}
        
        # Decide weather sample should be imaged
        self.set_image(image)

        # positions of object center in container coordinates
        self.set_zero(xZero, yZero, zZero)
        
        # set save position for start of any movement
        self.set_save(xSavePosition, ySavePosition, zSavePosition)

        # flip of coordinate system compared to enclosing container
        # e.g. typically we assume a cartesian coordinate system with origin in the lower left corner
        # the Zeiss SD stage coordinates have their origin in the upper left corner, 
        # thus the y axis of the PlateHolder is flipped by -1
        self.set_flip(xFlip, yFlip, zFlip)

        # correction for calibration.
        # E.g. these values can be used when well diameter or distance between wells are used for calibration.
        self.set_correction(xCorrection, yCorrection, zCorrection,\
                             zCorrectionXSlope, zCorrectionYSlope, zCorrectionZSlope)
        

        # attach additional meta data
        self.metaDict = None
        
        # Directory with list of objects to be imaged
        self.image_dirs = {}
        
        self.set_hardware(microscope_object = microscope_object,
                         stage_id = stage_id,
                         focus_id = focus_id,
                         auto_focus_id = auto_focus_id,
                         objective_changer_id = objective_changer_id,
                         safety_id = safety_id)

        # reference positions for auto-focus
        # when switching objective user focuses on identical object at this position.
        # the difference between the stored and the new position is used to calculate par-centricity and par-focuality
        self.set_reference_object(reference_object)
        self.set_reference_position(x_reference, y_reference, z_reference)
        self.reference_objective = None
        self.reference_objective_changer = None
        
        # Position used to define zero position for plate z
        self.update_z_zero_pos = None


    def __repr__(self):
        return "<class {}: '{}'>".format(self.__class__.__name__, self.get_name())

    def set_hardware(self, microscope_object = None,
                     stage_id = None,
                     focus_id = None,
                     auto_focus_id = None,
                     objective_changer_id = None,
                     safety_id = None):
        '''Store object that describes connection to hardware.
        
        Input:
         microscope_object: object of class Microscope from module hardware
         stage_id: id string for stage. 
         focus_id: id string with name for focus drive
         auto_focus_id: id string with name for auto-focus
         objective_changer_id: id string with name for objective changer
         safety_id: id string for safety area that prevents objective damage during stage movement
         
        Output:
         none
        '''
        self.microscope=microscope_object
        self.stage_id = stage_id
        self.focus_id = focus_id
        self.auto_focus_id = auto_focus_id
        self.objective_changer_id = objective_changer_id
        self.safety_id = safety_id

    def set_name(self, name=''):
        '''Set name of object
        
         Input:
          name: string with name of object
         Output:
          none
        '''
        self.name=name

    def get_name(self):
        '''Return name of object.
        
        Input:
         none
         
        Output:
         name: string name of object
        '''
        return self.name

#################################################################
# Begin
# Methods to find positions in image
#
#################################################################

    def set_interactive_positions(self, tileImageData, location_list=[], app = None):
        """ Opens up the interactive mode and lets user select colonies and return the list of coordinates selected

        Input:
        tileImageData: The pixel data of the image of the well - numpy array
        location_list: The list of coordinates to be pre plotted on the image.
        app: pyqt application object initialized in microscopeAutomation.py

        Output:
        location_list: Returns the list of colonies selected by the user
        """
        # Using pyqtgraph module
        interactive_plot = ImageLocationPicker(tileImageData, location_list, app)
        interactive_plot.plot_points("Well Overview Image")
        return interactive_plot.location_list

#################################################################
# 
# Methods to find positions in image
# End
#################################################################

#################################################################
# Begin
# Methods to handle reference used to correct for xyz offset between different objectives.
#
#################################################################

    def set_reference_object(self, reference_object):
        '''Set reference object to correct for xyz offset between different objectives.
        
        Input:
         reference_object: any object of type sample
         
        Output:
         none
        
        Avoid setting reference positions and connect reference object to the same sample.
        '''
        self.reference_object = reference_object

    def get_reference_object(self):
        '''Get reference object to correct for xyz offset between different objectives.
        
        Input:
         none
         
        Output:
         reference_object: any object of type sample
        
        Searches through all containers until id is found
        '''
        try:
            reference_object = self.reference_object
            if reference_object is None:
                reference_object = self.get_container().get_reference_object()
        except:
            reference_object = None
        return reference_object 
       
    def set_reference_position(self, x, y, z):
        '''Set position used as reference to correct for xyz offset between different objectives.
        Input:
         x, y, z: position of reference structure in object coordinates
         
         Output:
          none
          
        Avoid setting reference positions and connect reference object to the same sample.
        x, y, z can be none
        '''
        if self.get_reference_object() and self.get_reference_object() is not self:
            warnings.warn('''The object {} has already the reference object {} attached. 
                            One should avoid to use reference positions and objects at the same time'''.format(self.get_name(), self.get_reference_object().get_name()))

# We have to allow to set reference positions to none during initialization
#         if x is None and y is None and z is None:
#             return
        self.x_reference = x
        self.y_reference = y
        self.z_reference = z

    def get_reference_position(self):
        '''Return position used as reference to correct for xyz offset between different objectives.
        Input:
         none
         
        Output:
         x, y, z: position of reference structure in object coordinates

          
        Get position from reference object if available.
        If none is available use zero postion
        '''
        if self.get_reference_object() and self.get_reference_object() is not self:
            if self.x_reference or self.y_reference or self.z_reference:
                warnings.warn('''The object {} has reference positions and the reference object {} attached. 
                                Reference positions from reference object will be used.'''.format(self.get_name(), self.get_reference_object().get_name()))
            x, y, z = self.get_reference_object().get_reference_position()    
        else:
            if self.x_reference is not None and self.y_reference is not None and self.z_reference is not None:
                x = self.x_reference
                y = self.y_reference
                z = self.z_reference
            else: 
                # reference position was not defined
                x, y, z = (None, None, None)
        return x, y, z

#################################################################
# 
# Methods to handle reference used to correct for xyz offset between different objectives.
# End
#################################################################        

    def add_samples(self, sampleObjectsDict):
        '''Adds colonies to well.

        Input:
         colonyObjectsDict: dictionary of form {'name': colonyObject}

        Output:
         none
        '''
        self.samples.update(sampleObjectsDict)


    def get_well_object(self):
        '''Get well object for subclass.
        
        Input:
         none
         
        Output:
         wellObject: object for well
        '''
        wellObject = self.container.get_well_object()
        return wellObject

    def set_image(self, image = True):
        '''Define if sample should be included in imaging.
        
        Input:
         image: if True, include in imaging
         
        Output:
         none
        '''
        self.image = image
        
    def get_image(self):
        '''Return image property that defines if sample is included in imaging.
        
        Input:
         none
         
        Output:
         image: if True, include in imaging
        '''
        image = self.image
        return image

    def add_to_image_dir(self, listName, sampleObject = None, position = None):
        '''Add sample object to list with name listName of objects to be imaged.
        
        Input:
         listName: string with name of list (e.g. 'ColoniesPreScan'
         sampleObject: object to be imaged. Can be list. List will always added at end
         position: position of object in list. Position will determine order of imaging.
                    Default: None = Append to end. Has no effect if object is list.
                    
        Output:
         none
        '''
        if listName not in self.image_dirs.keys():
            self.image_dirs[listName] = []
        if isinstance(sampleObject, list):
            self.image_dirs[listName].extend(sampleObject)
        else:
            if position is None:
                self.image_dirs[listName].append(sampleObject)
            else:
                self.image_dirs[listName].insert(sampleObject, position)

    def get_from_image_dir(self, listName):
        '''Get list with name listName of objects to be imaged.
        
        Input:
         listName: string with name of list (e.g. 'ColoniesPreScan'
                    
        Output:
         sampleObjects: list of name listName with objects to be imaged
        '''
        sampleObjects = None
        for key in self.image_dirs.keys():
            if listName in self.image_dirs.keys():
                sampleObjects = self.image_dirs[listName]
        return sampleObjects
                    
    def set_barcode(self, barcode):
        '''Set barcode for plate.
        
        Input:
         barcode: string with barcode
         
        Output:
         none
        '''
        self.barcode = self.container.set_barcode(barcode)

    def get_barcode(self):
        '''Get barcode for plate.
        
        Input:
         none
        Output:
         barcode: string with barcode         
        '''
        try:
            barcode = self.container.get_barcode()
        except:
            barcode = None
        return barcode
        

    def set_container(self, container=None):
        '''Object is part of container object (e.g. Plate is container for Well).
        
         Input:
          container: object for container
         Output:
          none
        '''
        self.container=container

    def get_container(self):
        '''Return container object that encloses object.
        
        Input:
         none
         
        Output:
         container: container object
        '''
        return self.container

    def get_sample_type(self):
        '''Return sample type.
        
        Input:
         none
         
        Output:
         sampleType: string with name of object type
        '''
        sampleType = type(self).__name__
        return sampleType
    
    def set_zero(self, x=None, y=None, z=None, verbose = True):
        '''Set center position of object in container coordinates.
        Input:
         x, y, z: position of object center in mum in coordinate system of inclosing container.
                if not set, use current position
         verbose: if True print debug information (Default = True)
         
        Output:
         xZero, yZero, zZero: new center position in container coordinates
        '''
        if (x is None) or (y is None) or (z is None):
            if self.container==None:
                xZero, yZero, zZero = self.get_corrected_stage_position(verbose = verbose)
            else:
                xZero, yZero, zZero = self.container.get_pos_from_abs_pos(verbose = verbose)
        if x is None:
            x= xZero
        if y is None:
            y=yZero
        if z is None:
            z=zZero
        self.xZero=x
        self.yZero=y
        self.zZero=z
        return self.xZero, self.yZero, self.zZero

    def update_zero(self, x=None, y=None, z=None, verbose = True):
        '''Update center position of object in container coordinates.
        Input:
         x, y, z: position of object center in mum in coordinate system of inclosing container.
                if None, keep old values
         verbose: if True print debug information (Default = True)
        Output:
         xZero, yZero, zZero: new center position in container coordinates
        '''
        if x is not None:
            self.xZero=x
        if y is not None:
            self.yZero=y
        if z is not None:
            self.zZero=z
        return self.xZero, self.yZero, self.zZero

    def get_zero(self):
        '''Return center of object in container coordinates.
        
        Input:
         none
        
        Output:
         xZero, yZero, zZero: center of object in mum in container coordinates
        '''
        return (self.xZero, self.yZero, self.zZero)

    def get_abs_zero(self, verbose = True):
        '''Return center of object in stage coordinates.
        
        Input:
         verbose: if True print debug information (Default = True)
        
        Output:
         xZero, yZero, zZero: center of object in mum in stage coordinates
        '''
        xStageZero, yStageZero, zStageZero = self.get_abs_pos_from_obj_pos(0, 0, 0, verbose = verbose)
        return (xStageZero, yStageZero, zStageZero)

    def set_save(self, x, y, z):
        '''Set save stage position to start any movement without danger of collision in sample coordinates.
        
        Input: 
         x, y, z: save position in sample coordinates.
         
        Output: 
         x, y, z: save position in sample coordinates.
        '''
        # check if input is a number or None
        try:
            if x is None:
                self.xSave = None
            else:
                self.xSave = float(x)
            
            if y is None:
                self.ySave = None
            else:
                self.ySave = float(y)
            if z is None or z == 'None':
                "save z position in load position"
                self.zSave = None
            else:
                self.zSave = float(z)
        except:
            print ('{}, {}, {} should all be numbers or None'.format(x, y, z))
            raise
        return self.xSave, self.ySave, self.zSave

    def get_save(self):
        '''get save stage position to start any movement without danger of collision in sample coordinates.
        
        Input: 
         None
         
        Output: 
         x, y, z: save position in sample coordinates.
        '''
        x = self.xSave
        y = self.ySave
        z = self.zSave
        if (x is None) or (y is None):
            x, y, z = self.get_container().get_save()
        return x ,y, z
       
    def set_flip(self, xFlip=1, yFlip=1, zFlip=1):
        '''Set if object coordinate system is flipped relative to container coordinate system.
        
        Input:
         xFlip, yFlip, zFlip: 1 if system is not flipped, otherwise -1
         
        Output:
         none
        '''
        self.xFlip=xFlip
        self.yFlip=yFlip
        self.zFlip=zFlip
 
    def update_flip(self, xFlip=1, yFlip=1, zFlip=1):
        '''Set if object coordinate system should be flippedcompared to current settings.
        
        Input:
         xFlip, yFlip, zFlip: 1 if coordinate system flip should stay the same, otherwise -1
         
        Output:
         xFlip, yFlip, zFlip: updated parameters
        '''
        self.xFlip=self.xFlip*xFlip
        self.yFlip=self.yFlip*yFlip
        self.zFlip=self.zFlip*zFlip

    def get_flip(self):
        '''Return if object coordinate system is flipped relative to container coordinate system.
        
        Input:
         none
         
        Output:
         xFlip, yFlip: 1 if system is not flipped, otherwise -1
        '''
        return self.xFlip, self.yFlip, self.zFlip

    def set_correction(self, xCorrection=1, yCorrection=1, zCorrection=1,\
                             zCorrectionXSlope=0,\
                             zCorrectionYSlope=0,\
                             zCorrectionZSlope=0,\
                             zCorrectionOffset=0):
        '''Set correction term if scaling for object coordinate system is slightly off relative to container coordinate system.
        
        Input:
         xCorrection, yCorrection, zCorrection: Correction terms
         
        Output:
         none
        '''
        self.xCorrection=xCorrection
        self.yCorrection=yCorrection
        self.zCorrection=zCorrection
        self.zCorrectionXSlope=zCorrectionXSlope
        self.zCorrectionYSlope=zCorrectionYSlope
        self.zCorrectionZSlope=zCorrectionZSlope
        self.zCorrectionOffset=zCorrectionOffset
 
    def update_correction(self, xCorrection=1, yCorrection=1, zCorrection=1,\
                             zCorrectionXSlope=0,\
                             zCorrectionYSlope=0,\
                             xyzCorrectionXZero=0,\
                             xyzCorrectionYZero=0):
        '''Multiply existing correction terms if scaling for object coordinate system is slightly off 
        relative to container coordinate system with additional correction term.
        
        Input:
         xCorrection, yCorrection, zCorrection: Additional multiplicative correction terms
         
        Output:
         xCorrection, yCorrection, zCorrection: updated parameters
        '''
        self.xCorrection=self.xCorrection*xCorrection
        self.yCorrection=self.yCorrection*yCorrection
        self.zCorrection=self.zCorrection*zCorrection
#         self.zCorrectionOffset=self.zCorrectionOffset*zCorrectionOffset
        self.zCorrectionXSlope=self.zCorrectionXSlope*zCorrectionXSlope
        self.zCorrectionYSlope=self.zCorrectionYSlope*zCorrectionYSlope
        self.xyzCorrectionXZero=xyzCorrectionXZero
        self.xyzCorrectionYZero=xyzCorrectionYZero
        
        return self.xCorrection, self.yCorrection, self.zCorrection

    def get_correction(self):
        '''Get correction term if scaling for object coordinate system is slightly off relative to container coordinate system.
       
        Input:
         none
         
        Output:
         xCorrection, yCorrection, zCorrection: Correction terms
        '''
        return {'xCorrection': self.xCorrection,\
                'yCorrection': self.yCorrection,\
                'zCorrection': self.zCorrection,\
                'zCorrectionXSlope': self.zCorrectionXSlope,\
                'zCorrectionYSlope': self.zCorrectionYSlope,\
                'zCorrectionZSlope': self.zCorrectionZSlope,\
                'zCorrectionOffset': self.zCorrectionOffset,\
                }

       
###################################################################################################################
#
# Methods to move stage and focus
#
###################################################################################################################

    def microscope_is_ready(self, experiment, reference_object = None, load = True, use_reference = True, use_auto_focus = True, make_ready = True, trials = 3, verbose = True):
        '''Check if microscope is ready and setup up for data acquisition.
         
        Input:
         experiment: string with name of experiment as defined in microscope software
         reference_object: object used to set parfocality and parcentricity
         load: move objective into load position before moving stage
         use_reference: initialize reference position if not set
         make_ready: if True, make attempt to ready microscope, e.g. setup autofocus (Default: True)
         trials: maximum number of attempt to initialize microscope. Will allow user to make adjustments on microscope. (Default: 3)
         verbose: print debug messages (Default: True)
                    
        Output:
         ready: True if microscope is ready for use, False if not 
        '''
        stage_id = self.get_stage_id()
        focus_drive_id = self.get_focus_id() 
        auto_focus_id = self.get_auto_focus_id()
        objective_changer_id = self.get_objective_changer_id()
        safety_object_id = self.get_safety_id()
        microscope_object = self.get_microscope()
    
        test_ready_dict = OrderedDict([(stage_id, []),
                                       (focus_drive_id, ['set_load'] if load else []),
                                       (objective_changer_id, ['set_reference'] if use_reference else []),
                                       (auto_focus_id, ['no_find_surface'] if use_auto_focus else [])])
        is_ready = microscope_object.microscope_is_ready(experiment = experiment, 
                                                         component_dict = test_ready_dict,
                                                         focus_drive_id = focus_drive_id,
                                                         objective_changer_id = objective_changer_id,
                                                         safety_object_id = safety_object_id,
                                                         reference_object = reference_object,
                                                         load = load,
                                                         make_ready = make_ready,
                                                         trials = trials,
                                                         verbose = verbose)
    
        return is_ready['Microscope']

    def move_to_abs_position(self, x = None, y = None, z = None, 
                             reference_object = None,
                             load = True, 
                             verbose = True):
        '''Move stage to position x, y, z.
        
        Input:
         x, y: Position stage should move to in stage coordinates in mum. If None, stage will not move
         z: Focus position in mum. If not provided focus will not be changed, but autofocus might engage
         reference_object: object of type sample (ImagingSystem) used to correct for xyz offset between different objectives
         load: Move focus in load position before move. Default: True
         verbose: if True print debug information (Default = True)
         
        Output:
         x, y: New stage position
         
        If use_autofocus is set, correct z value according to new autofocus position.
        '''
        if self.get_container() == None:
            return self.set_stage_position(x, y, z, 
                                           reference_object = reference_object,
                                           load = load, 
                                           verbose = verbose)
        else:
            return(self.container.move_to_abs_position(x, y, z, 
                                                       reference_object = reference_object,
                                                       load = load, 
                                                       verbose = verbose))

    
    def move_to_zero(self, load = True, verbose = True):
        '''Move to center of object.
        
        Input: 
         load: Move focus in load position before move. Default: True
         verbose: if True print debug information (Default = True)
         
        Output: 
         x, y, z: new position in stage coordinates in mum
        '''        
        return(self.move_to_xyz(x=0, y=0, z=0, load = load, verbose = verbose))

    def move_to_save(self, load = True, verbose = True):
        '''Move to save position for object.
        
        Input: 
         load: Move focus in load position before move. Default: True
         verbose: if True print debug information (Default = True)
         
        Output: 
         x, y, z: new position in stage coordinates in mum
        '''    
        
        x, y, z = self.get_save() 
        if z is None:
            focusDriveObject = self.get_focus()
            z = focusDriveObject.get_load_position()
               
        return(self.move_to_abs_position(x, y, z, load = load, verbose = verbose))
        
    def move_to_xyz(self, x, y, z=None, 
                    reference_object = None,
                    load = True, 
                    verbose = True):
        '''Move to position in object coordinates in mum.
        Input:
         x, y, z; Position in object coordinates in mum.
                 If z == None do not change z position
         reference_object: object of type sample (ImagingSystem) used to correct for xyz offset between different objectives
         load: Move focus in load position before move. Default: True
         verbose: if True print debug information (Default = True)
         
        Output:
         xAbs, yAbs, zAbs: new position in absolute stage coordinates in mum
         
        If use_autofocus is set, correct z value according to new autofocus position.
        '''
        xAbs, yAbs, zAbs = self.get_abs_pos_from_obj_pos(x, y, z, verbose = verbose)
        return(self.move_to_abs_position(xAbs, yAbs, zAbs, 
                                         reference_object = reference_object,
                                         load = load, 
                                         verbose = verbose))

    def move_to_r_phi(self, r, phi, load = True, verbose = True):
        '''moves to position r [mum], phi [degree] in radial coordinates. 
        (0,0) is the center of unit (e.g. well). 0 degrees is in direction of x axis.
        
        Input:
         r: radius in mum for radial coordinates (center = 0)
         phi: angle in degree for radial coordinates (right = 0 degree)
         load: Move focus in load position before move. Default: True
         verbose: if True print debug information (Default = True)
         
        Output:
         xStage, yStage: x, y position on stage in mum
        '''
        phi_r=math.radians(phi)
        x=r * math.sin(phi_r)
        y=r * math.cos(phi_r)
        xStage, yStage, zStage = self.move_to_xyz(x, y, z=None, load = load, verbose = verbose)
        return xStage, yStage, zStage

    def move_delta_xyz(self, x, y, z=0, load = True, verbose = True):
        '''Move in direction x,y,z in micrometers from current position. 
        
        Input:
         x, y, z: step size in micrometers
         load: Move focus in load position before move. Default: True
         verbose: if True print debug information (Default = True)
         
        Output:
         xStage, yStage: x, y position on stage in mum
        '''
        # get current stage position in absolute stage coordinates
        xStage, yStage, zStage= self.get_abs_position()
        xNew=xStage+x
        yNew=yStage+y
        zNew=zStage+z
        
        xNewStage, yNewStage, zNewStage = self.move_to_abs_position(xNew, yNew, zNew, load = load, verbose = verbose)
        return xNewStage, yNewStage, zNewStage

    def get_abs_position(self, stage_id = None, focus_id = None):
        '''Return current stage position.
        Input:
         stage_id, focus_id: string ids to identify stage and focus drive information is collected from
         
        Output:
         absPos: absolute (x, y, z) position of stage in mum
         
        Positions are corrected for centricity and parfocality
        '''
        # use stage_id and focus_id from most top level object (e.g. use from well if available, not from plate)
        if stage_id is None:
            stage_id = self.stage_id
        if focus_id is None:
            focus_id = self.focus_id

        if self.get_container() == None:
            return self.get_abs_stage_position(stage_id, focus_id)
        else:
            absPos = self.get_container().get_abs_position(stage_id, focus_id)
        return absPos
        
#####################################################################################
#
# Transformations from container coordinates to object coordinates
#  Correction factors for this transformation are attached to the object
#
#####################################################################################
    def calculate_slope_correction(self, x, y, verbose = True):
        '''Calculate offset in z because of tilted sample.
        
        Input:
        x, y: x and y positions in object coordinates in um the correction is to be calculated
         verbose: if True print debug information (Default = True)
         
        Output:
         zSlopeCorrection: offset in z in um
        '''
        if self.zCorrectionZSlope == 0:
            zSlopeCorrection = 0
        else:
            zSlopeCorrection = (self.zCorrectionOffset - (x * self.zCorrectionXSlope) - (y * self.zCorrectionYSlope)) / self.zCorrectionZSlope
            
        if verbose:
            print '\ncalculate_slope_correction in module samples.py for object ', self.get_name()
            print ' Calculate correction for position (in object coordinates): ', x, y
            print ' zCorrectionXSlope: ', self.zCorrectionXSlope
            print ' zCorrectionYSlope: ', self.zCorrectionYSlope
            print ' zCorrectionZSlope: ', self.zCorrectionZSlope
            print ' zCorrectionOffset: ', self.zCorrectionOffset
            print ' Calculated slope correction offset: ', zSlopeCorrection
            
        return zSlopeCorrection
        
 
    def get_obj_pos_from_container_pos(self, xContainer, yContainer, zContainer, verbose = True):
        '''Calculate object coordinates from container coordinates.
        
        Input:
         xContainer, yContainer, zContainer: container coordinates in mum
         verbose: if True print debug information (Default = True)
         
        Output:
         xObject, yObject, zObject: object coordinates in mum for container coordinates
        '''
        # calculate translation
        # the origin of the object coordinate system in container coordinates is give by (self.xZero, self.yZero, self.zZero)
        xOffsetContainer = xContainer - self.xZero
        yOffsetContainer = yContainer - self.yZero
        zOffsetContainer = zContainer - self.zZero
        
        # The coordinate system of the object might be stretched and flipped compared to the container
        if self.yFlip == -1:
            pass

        xObject = xOffsetContainer * self.xFlip * self.xCorrection
        yObject = yOffsetContainer * self.yFlip * self.yCorrection
        zObject = zOffsetContainer * self.zFlip * self.zCorrection - self.calculate_slope_correction(xObject, yObject, verbose = verbose)

        # Output for debugging
        if verbose:
            if self.get_container() is None:
                containerName = 'Stage Position'
            else: 
                containerName = self.get_container().get_name() 
            print '\nResults from method get_obj_pos_from_container_pos(xContainer, yContainer, zContainer)'
            print ' ' + self.get_name() + ' coordinates calculated from ' + containerName + ' coordinates'
            print ' Container coordinates: ', xContainer, yContainer, zContainer
            print ' Object coordinates: ', xObject, yObject, zObject
            print ' ObjectObject.zero in container coordinates (flip not applied): ', self.xZero, self.yZero, self.zZero
            print ' Object flip relative to container: ', self.xFlip, self.yFlip, self.zFlip
                
        return xObject, yObject, zObject
          
    def get_pos_from_abs_pos(self, x=None, y=None, z=None, verbose = True):
        '''Return current position in object coordinates in mum.
        or transforms (x,y,z) from stage coordinates into object coordinates.
        
        Input:
         x, y, z: Absolute stage coordinates in mum.
                  If not given or None retrieve current stage position and express in object coordinates.
         verbose: if True print debug information (Default = True)
                  
        Output:
         xPos, yPos, zPos: current or position passed in stage coordinate returned in object coordinates
    
        This method is based on focus coordinates after drift correction.
        '''
        if self.get_container()==None:
            if (x==None) or (y==None) or (z==None):
                xStage, yStage, zStage = self.get_corrected_stage_position()
            if x==None:
                x=xStage
            if y==None:
                y=yStage
            if z==None:
                z=zStage
            xPos = x -self.xZero
            yPos = y -self.yZero
            zPos = z -self.zZero
        else:
            xContainer, yContainer, zContainer = self.get_container().get_pos_from_abs_pos(x, y, z, verbose = verbose)
            xPos, yPos, zPos = self.get_obj_pos_from_container_pos(xContainer, yContainer, zContainer, verbose = verbose)
        return (xPos, yPos, zPos)

#####################################################################################
#
# Transformations from object coordinates to container coordinates
#  Correction factors for this transformation are attached to the object
#
#####################################################################################
    def get_container_pos_from_obj_pos(self, xObject, yObject, zObject, verbose = True):
        '''Calculate container coordinates for given object coordinates.
        
        Input:
         xObject, yObject, zObject: Object coordinates in mum
         verbose: if True print debug information (Default = True)
         
        Output:
         xContainer, yContainer, zContainer: Container coordinates in mum for object coordinates
        '''
        
        # The coordinate system of the container might be stretched and fliped compared to the object
        xContainerOffset = xObject / self.xCorrection * self.xFlip
        yContainerOffset = yObject / self.yCorrection * self.yFlip
        if zObject == None:
            zContainer = None
        else:
            zContainerOffset = zObject / self.zCorrection * self.zFlip

        # calculate translation
        # the origin of the object coordinate system in container coordinates is give by (self.xZero, self.yZero, self.zZero)
        xContainer = (xContainerOffset + self.xZero)
        yContainer = (yContainerOffset + self.yZero)
        if zObject != None:
            zContainer = (zContainerOffset + self.zZero) + self.calculate_slope_correction(xContainer, yContainer, verbose = verbose)
        
        # Output for debugging
        if verbose:
            if self.get_container() is None:
                containerName = 'Stage Position'
            else: 
                containerName = self.get_container().get_name() 
            print '\nResults from method get_container_pos_from_obj_pos(xObject, yObject, zObject)'
            print ' ' + containerName + ' coordinates calculated from ' + self.get_name() + ' coordinates'
            print ' Object coordinates: ', xObject, yObject, zObject
            print ' Container coordinates: ', xContainer, yContainer, zContainer
            print ' Object.zero in container coordinates (flip not applied): ', self.xZero, self.yZero, self.zZero
            print ' Object flip relative to container: ', self.xFlip, self.yFlip, self.zFlip

            
        return xContainer, yContainer, zContainer


    def get_abs_pos_from_obj_pos(self, xObject, yObject, zObject=None, verbose = True):
        '''Convert object coordinates into stage coordinates.
        
        Input: 
         xObject, yObject, zObject: object coordinates relative to object center in mum
         verbose: if True print debug information (Default = True)
         
        Output:
         x, y, z: coordinates in absolute stage coordinates in mum
        '''
        xContainer, yContainer, zContainer = self.get_container_pos_from_obj_pos(xObject, yObject, zObject, verbose)
        if self.get_container()==None:
            return xContainer, yContainer, zContainer
        else:
            xObject = xContainer 
            yObject = yContainer 
            zObject = zContainer 
            xContainer, yContainer, zContainer = self.get_container().get_abs_pos_from_obj_pos(xObject, yObject, zObject, verbose)
            return xContainer, yContainer, zContainer

    ###############################################################
    #
    # Methods to control autofocus
    #
    ###############################################################

#     def recover_hardware(self, hardwareFunction, *args, **kwargs):
#         '''Execute hardwareFunction and try to recover from failure.
#         
#         Input:
#          autofocusFunction: function that that interacts with microscope autofocus
#          args: arguments for autofocusFunction
#         
#         Output:
#          returnValue: return value from autofocusFunction
#          
#         autofocusFunction has to throw exception AutofocusError in error case
#         '''
#         return self.container.recover_hardware(hardwareFunction, *args, **kwargs)
#     
    def set_use_autofocus(self, flag):
        '''Set flag to enable the use of autofocus.
        
        Input:
         flag: if true, use autofocus
         
        Output:
         use_autofocus: status of use_autofocus
        '''
        return self.container.set_use_autofocus(flag)

    def get_use_autofocus(self):
        '''Return flag about autofocus usage
        
        Input:
         none
         
        Output:
         use_autofocus: boolean varaible indicating if autofocus should be used
        '''
        return self.container.get_use_autofocus()

    def find_surface(self, trials = 3, verbose = True):
        '''Find cover slip using Definite Focus 2.
        
        Input:
         trials: number of trials to initialize component before initialization is aborted
         verbose: if True, print debug messages (Default: True)

         
        Output: 
         z: position of focus drive after find surface
        '''
        return self.container.find_surface(reference_object = self.get_reference_object(),
                                           trials = trials, 
                                           verbose = verbose)

    def store_focus(self, focusReferenceObj = None, trials = 3, verbose = True):
        '''Store actual focus position as offset from coverslip.
        
        Input:
         focusReferenceObj: Sample object used as reference for autofocus
         trials: number of trials to initialize component before initialization is aborted
         verbose: if True, print debug messages (Default: True)
         
        Output:
         z: position of focus drive after store focus
        '''
        if focusReferenceObj is None:
            focusReferenceObj = self
        return self.container.store_focus(focusReferenceObj, trials = trials, verbose = verbose)
    
    def recall_focus(self, cameraID, experiment):
        '''Find stored focus position as offset from coverslip.
        
        Input:
         cameraID: sting with camera ID for experiment
         experiment: string with experiment name as defined in microscope software.

         
        Output:
         z: position of focus drive after recall focus
        '''
        return self.container.recall_focus(cameraID, experiment)
 
    def live_mode_start(self, cameraID, experiment):
        '''Start live mode in microscope software.
        
        Input:
         cameraID: string with unique camera ID
         experiment: string with experiment name as defined within microscope software
                      If None use actual experiment.
         
        Output:
          None
       
        Methods calls method of container instance until container has method implemented 
        that actually performs action.
        '''
        self.container.live_mode_start(cameraID, experiment)

    def live_mode_stop(self, cameraID, experiment=None, ):
        '''Stop live mode in microscope software.
        
        Input:
         cameraID: string with unique camera ID
         experiment: string with experiment name as defined within microscope software
                      If None use actual experiment.
         
        Output:
          None
       
        Methods calls method of container instance until container has method implemented 
        that actually performs action.
        '''
        self.container.live_mode_stop(cameraID, experiment)

    def execute_experiment(self, experiment, cameraID, reference_object = None, filePath=None,  metaDict = {}, verbose = True):
        '''acquire single image using settings defined in microscope software and optionally save.
        
        Input:
         experiment: string with experiment name as defined within microscope software
         cameraID: string with unique camera ID
         reference_object: object of type sample (ImagingSystem) used to correct for xyz offset between different objectives
         filePath: filename with path to save image in original format. Default=None: no saving
         metaDict: directory with additional meta data, e.g. {'aics_well':, 'A1'}
         focus: use autofocus (default = False)
         verbose: if True print debug information (Default = True)
         
        Output:
         image: imageAICS object. At this moment they do not include the pixel data. Get pixel data with load_image.
         
        Methods calls method of container instance until container has method implemented 
        that actually performs action.
        '''
        # add name and type of object to meta data
        className = self.__class__.__name__
        if metaDict is None:
            metaDict = {}
        metaDict.update({'aics_objectContainerName': self.get_container().get_name(), \
                        'aics_type': className,                                   \
                        'aics_containerType': self.get_container().__class__.__name__,          \
                        'aics_barcode': self.get_barcode()})
        
        # add relative positions to meta data
        posX, posY, posZ = self.get_zero()
        metaDict.update({'aics_cellInColonyPosX': posX,             \
                        'aics_cellInColonyPosY': posY,             \
                        'aics_cellInColonyPosZ': posZ})

        # add correction terms to meta data
        corrections = self.get_correction()

        metaDict.update({'aics_xCorrection': corrections['xCorrection'],
                        'aics_yCorrection': corrections['yCorrection'],
                        'aics_zCorrection': corrections['zCorrection'],
                        'aics_zCorrectionXSlope': corrections['zCorrectionXSlope'],
                        'aics_zCorrectionYSlope': corrections['zCorrectionYSlope'],
                        'aics_zCorrectionZSlope': corrections['zCorrectionZSlope'],
                        'aics_zCorrectionOffset': corrections['zCorrectionOffset']})
        flip = self.get_flip()
        metaDict.update({'aics_xFlip': flip[0], \
                        'aics_yFlip': flip[1], \
                        'aics_zFlip': flip[2]})

        image=self.container.execute_experiment(experiment, 
                                                cameraID, 
                                                reference_object = reference_object,
                                                filePath = filePath, 
                                                metaDict = metaDict, 
                                                verbose = verbose)
        
        # use x, y, z values corrected for objective offset to calculate object positions, otherwise they would be different for different objectives
        xAbs = image.get_meta('aics_imageAbsPosX(centricity_corrected)')
        yAbs = image.get_meta('aics_imageAbsPosY(centricity_corrected)')
        zAbs = image.get_meta('aics_imageAbsPosZ(focality_drift_corrected)')
        posX, posY, posZ = self.get_pos_from_abs_pos(xAbs, yAbs, zAbs, verbose = verbose)
        image.add_meta({'aics_imageObjectPosX': posX, 'aics_imageObjectPosY': posY, 'aics_imageObjectPosZ': posZ})
        return image
       
    def acquire_images(self, experiment, cameraID, reference_object = None, filePath=None, posList=None, load = True, use_reference = True, use_auto_focus = False, metaDict = {}, verbose = True):
        '''Acquire image or set of images using settings defined in microscope software and optionally save.
        
        Input:
         experiment: string with experiment name as defined within microscope software
         cameraID: string with unique camera ID
         reference_object: object used to set parfocality and parcentricity, typically a well in plate
         filePath: string for filename with path to save image in original format 
                    or tuple with string to directory and list with template for file name.
                    Default=None: no saving
         posList: coordinates if multiple images (e.g. tile) should be acquired. 
                     The coordinates are absolute stage positions in mum not corrected for objective offset.
         load: Move focus in load position before move. Default: True
         metaDict: directory with additional meta data, e.g. {'aics_well':, 'A1'}
         use_autofocus: use autofocus (default = False)
         use_reference: use reference object (default = True)
         verbose: if True print debug information (Default = True)
         
        Output:
         images: list with imageAICS objects. At this moment they do not include the pixel data. Get pixel data with load_image.
         
        Methods calls method of container instance until container has method implemented 
        that actually performs action.
        '''
        if posList==None:
            images=[self.execute_experiment(experiment, 
                                            cameraID, 
                                            reference_object = reference_object,
                                            filePath = filePath, 
                                            metaDict = metaDict, 
                                            verbose = verbose)]
        else:
#             xCurrent, yCurrent, zCurrent = self.get_abs_position()
            images=[]
            for x, y, z in posList:
                # check if microscope is ready and initialize if necessary
                self.get_microscope().microscope_is_ready(experiment = experiment, 
                                                         component_dict = {self.get_objective_changer_id(): []}, 
                                                         focus_drive_id = self.get_focus_id(), 
                                                         objective_changer_id = self.get_objective_changer_id(), 
                                                         safety_object_id = self.get_safety_id(),
                                                         reference_object = self.get_reference_object(),
                                                         load = load, 
                                                         use_reference = use_reference,
                                                         use_auto_focus = use_auto_focus,
                                                         make_ready = True, 
                                                         verbose = verbose)
                self.move_to_abs_position(x, y, z, 
                                          reference_object = reference_object,
                                          load = load, 
                                          verbose = verbose)
                newPath = filePath
               # Currently not needed - might be needed later for metadata extraction
                # if filePath != None:
                #     if isinstance(filePath, tuple):
                #         # filePath is tuple containing path to directory and template for file name
                #         # use list() to make sure that newTemplate has a copy of filePath[1] and not only a reference
                #         newTemplate = list(filePath[1])
                #         newTemplate.insert(-1, '_x'+ str(x) + '_y' + str(y) + '_z' + str(z))
                #         newPath = (filePath[0], newTemplate)
                #     else:
                #         # filePath is single string with directory and filename
                #         splitPath=path.splitext(filePath)
                #         newPath=splitPath[0]+'_x'+ str(x) + '_y' + str(y) + '_z' + str(z) + splitPath[1]
                # else:
                #     newPath=None
                if metaDict != None:
##################################################
#
# ToDo: add relative pixel positions for stitching to meta data
#
##################################################
#                     metaDict.update({'aics_objectName': self.get_name()'aics_xTile': xTileName, 'aics_yTile': yTileName})
                    metaDict.update({'aics_objectName': self.get_name()})
                    try:
                        metaDict.update({'aics_positionNumber': self.position_number})
                    except:
                        pass
                image=self.execute_experiment(experiment, cameraID, reference_object, newPath, metaDict = metaDict, verbose = verbose)
                images.append(image)            
        return images

    def _get_tile_params(self, prefs, tile_object = 'None', verbose = True):
        '''Retrieve settings to define tiles from preferences.
        
        Input:
         prefs: dictionary with preferences for tiling
         verbose: print logging comments
        Output:
         tile_params: directory with parameters to calculate tile positions
        ''' 
        # retrieve center of sample object. This will be the center of all tiles.
        center = self.get_abs_zero(verbose)        
        
        # tile_object describes the object (e.g. colony, well) that should be covered with tiles
        # this has to be translated into tile_type. tile_type describes how the arrangement of tiles is calculated
        # different subclasses might allow additional options
        if tile_object == 'NoTiling':
            tile_type = 'none'
            tile_number = (1,1)
            tile_size = (None, None)
            degrees = None
            percentage = 100
        elif tile_object == 'Fixed':
            tile_type ='rectangle'
            tile_number = (prefs.getPref('nColTile'), prefs.getPref('nRowTile'))
            tile_size = (prefs.getPref('xPitchTile'), prefs.getPref('yPitchTile'))
            degrees = (prefs.getPref('RotationTile'))
            percentage = 100
        elif tile_object == 'Well':
            tile_type = 'ellipse'
            percentage = prefs.getPref('PercentageWell')
            well_diameter = self.get_diameter() * math.sqrt(percentage/100.0)
            tile_size = (prefs.getPref('xPitchTile'), prefs.getPref('yPitchTile'))
            tile_number = (math.ceil(well_diameter/tile_size[0]), math.ceil(well_diameter/tile_size[1]))            
            degrees = (prefs.getPref('RotationTile'))            
        elif tile_object == 'ColonySize':
            tile_type ='ellipse'
            tile_number = (None, None)
            tile_size = (prefs.getPref('xPitchTile'), prefs.getPref('yPitchTile'))
            degrees = None
            percentage = 100
        else:
            # Tile object is not implemented
            raise ValueError, 'Tiling object not implemented'
  
        tile_params = {'center': center, 'tile_type': tile_type, 'tile_number': tile_number, 'tile_size': tile_size, 'degrees': degrees, 'percentage': percentage}
        return tile_params
        
    def _compute_tile_positions_list(self, tile_params):
        '''Get positions for tiles in absolute coordinates. Private method that is called from get_tile_positions_list().
        
        Input: 
         tile_params: directory with parameters to calculate tile positions
        
        Output:
         tile_position_list: list with absolute positions for tiling
        '''
        
        tileObject = CreateTilePositions(tile_type = tile_params['tile_type'], 
                                         tile_number = tile_params['tile_number'], 
                                         tile_size = tile_params['tile_size'], 
                                         degrees = tile_params['degrees'])
        tile_positions_list = tileObject.get_pos_list(tile_params['center'])
        return tile_positions_list

    def get_tile_positions_list(self, prefs, tile_type = 'NoTiling', verbose = True):
        '''Get positions for tiles in absolute coordinates.
        
        Input: 
         prefs: dictionary with preferences for tiling
         tile_type: type of tiling.  Possible options:
                     - 'NoTiling': do not tile
                     - 'rectangle': calculate tiling to image a rectangular area
                     - 'ellipse': cover ellipse (e.g. well) with tiles
         verbose: print debugging information
         
        Output:
         tile_position_list: list with absolute positions for tiling
         
         Subclasses have additional tile_objects (e.g. ColonySize, Well)
        '''
        tile_params = self._get_tile_params(prefs, tile_type, verbose = verbose)
        tile_positions_list = self._compute_tile_positions_list(tile_params)
        return tile_positions_list
        
    def load_image(self, image, getMeta):
        '''Load image and meta data in object of type imageAICS
        
        Input:
         image: image object of class imageAICS. Holds meta data at this moment, no image data.
         getMeta: if true, retrieve meta data from file.
         
        Output:
         image: image with data and meta data as imageAICS class

        Methods calls method of container instance until container has method implemented 
        that actually performs action.
        '''
        if image.get_data() == None:
            image = self.container.load_image(image, getMeta) 
        return image

    def get_images(self, load=True, getMeta=False):
        '''Retrieve dictionary with images.
        
        Input:
         load: if true, will load image data before returning dictionary
         getMeta: if true, load meta data
         
        Output:
         imageDir: directory with images.
        '''
        for imageName, imageObject in self.images:
            if imageObject.data == None:
                self.load_image(imageObject, getMeta=getMeta)
        return self.images

    def background_correction(self, uncorrected_image, settings):
        '''Correct background using background images attached to object or one of it's superclasses.
        
        Input:
         image: object of class ImageAICS
         
        Output:
         corrected: object of class ImageAICS after background correction.
        '''
        image = self.load_image(uncorrected_image, getMeta = True)
        image_data = uncorrected_image.get_data()
        if len(image_data.shape) == 2:
            image_data = image_data[:,:, numpy.newaxis]
        n_channels = image_data.shape[2]
        prefs = settings.getPref('ChannelDefinitions')
        
        # iterate through channels and apply appropriate background correction
        for ch, channelPref in enumerate(prefs):
            if ch >= n_channels:
                continue
            background_name = channelPref.get('BackgroundCorrection')
            black_reference_name = channelPref.get('BlackReference')
            background = self.get_attached_image(background_name)
            black_reference = self.get_attached_image(black_reference_name)
            if black_reference is None or background is None:
                continue
            background_data = background.get_data()
            black_reference_data = black_reference.get_data()
            channel_data = image_data[:, :, ch]
            corrected_data = correctBackground.IlluminationCorrection(channel_data, black_reference_data, background_data)
            # corrected_data = channel_data
            image_data[:, :, ch] = corrected_data

        image.add_data(image_data)
        return image

    def tile_images(self, images, settings):
        '''Create tile of all images associated with object.
        
        Input:
         images: list with image objects of class ImageAICS
         
        Output:
         tile: ImageAICS object with tile
        '''
        # Information about tiling should be int he image meta data (e.g. image positions)
#         if not settings.getPref('Tile', validValues = VALID_TILE):
#             return images[(len(images)-1)/2] # return the x-0, y-0 image

        corrected_images = []
        # apply background correction

        ######################################################################
        #
        # ToDo: Catch if background image does not exist
        #
        ######################################################################
        for i, image in enumerate(images):
            if settings.getPref('CorrectBackground'):
                # TODO: figure out if it's okay for this to be a float with negative values
                corrected_images.append(self.background_correction(image, settings))
            else:
                corrected_images.append(self.load_image(image, getMeta=True))
 
        print("Done with Background correction")
        # create path and filename for tiled image
        folder_path = get_images_path(settings, subDir=settings.getPref('TileFolder'))
        file_name_pattern = settings.getPref('TileFileName')
        file_name = images[int(len(images)/2)].create_file_name(file_name_pattern)
        image_output_path=os.path.normpath(os.path.join(folder_path, file_name))
        # use tiling method 'anyShape' for arbitrary shaped tile regions, use 'stack' if tile region is a rectangle.
        # return _ list = [return_image, x_pos_list, y_pos_list]
        tiled_image, x_border_list, y_border_list = tileImages.tile_images(corrected_images, method="anyShape", output_image=True, image_output_path=image_output_path)
        return [tiled_image, x_border_list, y_border_list]
        #return tiled_image

    def add_attached_image(self, key, image):
        '''Attach image to sample object.
        
        Input:
         key:  string with name of image (e.g. 'backgroundGreen_10x')
         image: image object of class ImageAICS
         
        Output:
         none
        '''
        self.imageDict.update({key: image})

    def get_attached_image(self, key):
        '''Retrieve attached image.
        
        Input:
         key:  string with name of image (e.g. 'backgroundGreen_10x')
         
        Output:
         image: image object of class ImageAICS
        '''
        image = self.imageDict.get(key)
        if not (image):
            if self.container is not None:
                image = self.container.get_attached_image(key)
            else:
                # need to get a default image here
                print("Default Image")

        return image
              
    def remove_images(self, image):
        '''Remove all images from microscope software display.
        
        Input:
         image: image taken with same camera as images to be removed
         
        Output:
         none
        '''
        image=self.container.remove_images(image)
        return image

####################################################################################################
#
# Get hardware ids and microscope object used to image sample
#
####################################################################################################

    def get_microscope(self):
        '''Return object that describes connection to hardware.
        
        Input:
         none
         
        Output:
         microscope_object: object of class Microscope from module hardware
        '''
        try:
            microscope_object = self.container.get_microscope()
        except:
            microscope_object = None
        return microscope_object
 
    def get_stage_id(self):
        '''Return id for stage used with this sample.
        
        Input:
         none
         
        Output:
         stage_id: id for stage used with this sample
         
        Searches through all containers until id is found
        '''
        try:
            stage_id = self.stage_id
            if stage_id is None:
                stage_id = self.get_container().get_stage_id()
        except:
            stage_id = None
        return stage_id


    def get_focus_id(self):
        '''Return id for focus used with this sample.
        
        Input:
         none
         
        Output:
         focus_id: id for focus used with this sample
         
        Searches through all containers until id is found
        '''
        try:
            focus_id = self.focus_id
            if focus_id is None:
                focus_id = self.get_container().get_focus_id()
        except:
            focus_id = None
        return focus_id


    def get_auto_focus_id(self):
        '''Return id for auto-focus used with this sample.
        
        Input:
         none
         
        Output:
         auto_focus_id: id for auto-focus used with this sample
         
        Searches through all containers until id is found
        '''
        try:
            auto_focus_id = self.auto_focus_id
            if auto_focus_id is None:
                auto_focus_id = self.get_container().get_auto_focus_id()
        except:
            auto_focus_id = None
        return auto_focus_id


    def get_objective_changer_id(self):
        '''Return id for objective changer used with this sample.
        
        Input:
         none
         
        Output:
         objective_changer_id: id for objective changer used with this sample
         
        Searches through all containers until id is found
        '''
        try:
            objective_changer_id = self.objective_changer_id
            if objective_changer_id is None:
                objective_changer_id = self.get_container().get_objective_changer_id()
        except:
            objective_changer_id = None
        return objective_changer_id

    def get_safety_id(self):
        '''Return id for safety object. Safety object describes travel save areas for stage and objectives.
        
        Input:
         none
         
        Output:
         saftey_id: id for safety object used with this sample
         
        Searches through all containers until id is found
        '''
        try:
            safety_id = self.safety_id
            if safety_id is None:
                safety_id = self.get_container().get_safety_id()
        except:
            safety_id = None
        return safety_id


    def get_cameras_ids(self):
        '''Return ids for cameras used with this sample.
        
        Input:
         none
         
        Output:
         cameras_ids: list with ids for cameras used with this sample
         
        Searches through all containers until id is found
        '''
        #########################################
        # TODO: camera_ids not implemented
        #############################################
        try:
            cameras_ids = self.cameras_ids
            if cameras_ids is None:
                cameras_ids = self.get_container().get_cameras_ids()
        except:
            cameras_ids = None
        return cameras_ids

    def get_immersionDeliverySystems(self):
        '''Return dictionary with objects that describes immersion water delivery system.
         
        Input:
         none
          
        Output:
         immersion_delivery_systems: object of class Pump from module hardware
        '''
        try:
            immersion_delivery_systems = self.container.get_immersionDeliverySystems()
        except:
            immersion_delivery_systems = None
        return immersion_delivery_systems

    def get_immersionDeliverySystem(self, name):
        '''Return dictionary with objects that describes immersion water delivery system.
         
        Input:
         name: string id for immersion water delivery system
          
        Output:
         immersion_delivery_system: object of class ImmersionDelivery         
        '''
        try:
            immersion_delivery_system = self.container.get_immersionDeliverySystem(name)
        except:
            immersion_delivery_system = None
        return immersion_delivery_system

####################################################################################################
#
# Handle meta data
#
####################################################################################################

     
    def add_meta(self, metaDict):
        '''Update dictionary with meta data.
        
        Input:
         metaDict: dictionary with meta data
         
        Output:
         updatedMetaDict: dictionary with additional meta data   
        '''
        if self.metaDict is None:
            self.metaDict = metaDict
        else:
            self.metaDict.update(metaDict)
        return self.metaDict
    
    def get_meta(self):
        '''Return dictionary with meta data.
        
        Input:
         none
         
        Output:
         meta_dict: dictionary with meta data
        '''
        try:
            meta_dict = self.metaDict
        except:
            meta_dict = None
        return meta_dict

    def add_meta_data_file(self, metaDataFileObject):
        '''Add object that handles saving of meta data to disk.
        
        Input:
         metaDataFileObject: object of type meta_data_file
         
        Output:
         None
        '''
        self.metaDataFile = metaDataFileObject
        
    def get_meta_data_file(self):
        '''Return object that handles saving of meta data to disk.
        
        Input:
         None
         
        Output:
         meta_data_file_object: object of type meta_data_file. None if no meta data file exists
        '''
        try:
            meta_data_file_object = self.metaDataFile
        except:
            meta_data_file_object = None
        return meta_data_file_object


class Background(ImagingSystem):
    """
    Class for the background object associated with each plate. It will be used to do background correction.
    """

    def __init__(self, name='Background', center=[0, 0, 0], wellObject=None, image=True, ellipse=[0, 0, 0], meta=None, \
                 xFlip=1, yFlip=-1, zFlip=1, \
                 xCorrection=1, yCorrection=1, zCorrection=1, \
                 zCorrectionXSlope=0, zCorrectionYSlope=0):
        '''Initialize class Background.

        Input:
         name: id for background
         image: True, if background should be imaged
         center: (x, y, z) center of background relative to well center in mum
         ellipse: (long axis, short axis, orientation) for ellipse around the background
         meta: additional meta data for background
         wellObject: object of type Well the background is associated with
         xFlip, yFlip, zFlip: -1 if coordinate system of plate holder is flipped in respect to stage
         xCorrection1, yCorrection, zCorrection: correction factor if there is a discrepancy between the stage and the plate holder calibration

        Output:
         None
        '''
        super(Background, self).__init__(container=wellObject, name=name, \
                                     image=True, \
                                     xZero=center[0], yZero=center[1], zZero=center[2], \
                                     xFlip=xFlip, yFlip=yFlip, zFlip=zFlip, \
                                     xCorrection=xCorrection, yCorrection=yCorrection, zCorrection=zCorrection, \
                                     zCorrectionXSlope=zCorrectionXSlope, zCorrectionYSlope=zCorrectionYSlope)

class PlateHolder(ImagingSystem):
    '''Class to describe and navigate Stage.
    
    A Stage is the superclass for everything that can be imaged on a microscope (e.g. plates, wells, colonies, cells).
    A Stage has it's own coordinate system measured in mum and nows it's position in stage coordinates.
    A Stage can be moved to a position and acquire images. It will take track of the last image. To keep the image
    the user has to save it.
    '''
    def __init__(self, name = 'PlateHolder',
                 microscope_object = None,
                 stage_id = None,
                 focus_id = None,
                 auto_focus_id = None,
                 objective_changer_id = None,
                 safety_id = None,
                 immersionDelivery = None,
                 cameraIdList = [],
                 center = [0,0,0], xFlip = 1, yFlip = 1, zFlip = 1,
                 xCorrection = 1 , yCorrection = 1, zCorrection = 1,
                 zCorrectionXSlope = 0, zCorrectionYSlope = 0,
                 xSavePosition = 55600,
                 ySavePosition = 31800,
                 zSavePosition = 0):
        '''Send all commands to microscope hardware
        
        Input:
         name: string with unique name for plate holder
         microscope_object: object of class Microscope from module hardware
         stage_id: id string for stage. 
         focus_id: id string with name for focus drive
         auto_focus_id: id string with name for auto-focus
         objective_changer_id: id string with name for objective changer
         safety_id: id string for safety area that prevents objective damage during stage movement
         immersionDelivery: instance of class ImmersionDelivery
         center: [x,y,z] zero position of plate holder in respect to stage
         xFlip, yFlip, zFlip: -1 if coordinate system of plate holder is flipped in respect to stage
         xCorrection1, yCorrection, zCorrection: correction factor if there is a discrepancy between the stage and the plate holder calibration
         xSavePosition, ySavePosition, zSavePosition: position to start any movements without danger of objective or other collisions

        Output:
         None
        '''
        self.immersionDeliverySystem = immersionDelivery
        self.plates={}                                   # will hold plate objects
        super(PlateHolder, self).__init__(container=None, name=name,\
                                    xZero=center[0], yZero=center[1], zZero=center[2],\
                                    xFlip=xFlip, yFlip=yFlip, zFlip=zFlip,\
                                    xCorrection=xCorrection, yCorrection=yCorrection, zCorrection=zCorrection,\
                                    zCorrectionXSlope=zCorrectionXSlope, zCorrectionYSlope=zCorrectionYSlope,\
                                    xSavePosition=xSavePosition, ySavePosition=ySavePosition, zSavePosition=zSavePosition,\
                                    microscope_object = microscope_object,
                                    stage_id = stage_id,
                                    focus_id = focus_id,
                                    auto_focus_id = auto_focus_id,
                                    objective_changer_id = objective_changer_id,
                                    safety_id = safety_id)
    
   
    def get_microscope(self):
        '''Return object that describes connection to hardware.
         
        Input:
         none
          
        Output:
         microscope_object: object of class Microscope from module hardware
        '''
        try:
            microscope_object = self.microscope
        except:
            microscope_object = None
        return microscope_object
  
    def get_stage(self):
        '''Return object that describes connection to microscope stage.
         
        Input:
         none
          
        Output:
         stage_object: object of class Stage from module hardware
        '''
        try:
            stage_object = self.stage
        except:
            stage_object = None
        return stage_object
 
    def get_focus(self):
        '''Return object that describes connection to microscope focus drive.
         
        Input:
         none
          
        Output:
         focusDrive: object of class focusDrive from module hardware
        '''
        return self.focusDrive
 
    def get_objectiveChanger(self):
        '''Return object that describes objective changer and information about objectives.
         
        Input:
         none
          
        Output:
         objectiveChanger: object of class ObjectiveChanger from module hardware
        '''
        return self.objectiveChanger
  
    def get_cameras(self):
        '''Return objects that describes connection to cameras.
         
        Input:
         none
          
        Output:
         cameraObjects: object of class Camera from module hardware
        '''
        return self.cameras
  
    def get_immersionDeliverySystems(self):
        '''Return dictionary with objects that describes immersion water delivery system.
          
        Input:
         none
           
        Output:
         pumpDict: dictionary of objects of class Pump from module hardware
        '''
        return self.immersionDeliverySystems
   
    def get_immersionDeliverySystem(self, name):
        '''Return object that describes immersion water delivery system.
          
        Input:
         name: string id for immersion water delivery system
           
        Output:
         immersionObject: object of class ImmersionDelivery
        '''
        immersionDict = self.get_immersionDeliverySystems()
        immersionObject = immersionDict[name]
        return immersionObject
               
    def add_plates(self, plateObjectDict):
        '''Adds Plate to Stage.
        
        Input:
         name: string with unique name of plate
         
        Output:
         none
        '''
        self.plates.update(plateObjectDict)

    def get_plates(self):
        '''Return list will all plateObjects associated with plateholder.
        
        Input:
         none
         
        Output:
         plate_objects: list with plate objects
        '''
        try:
            plate_objects=self.plates
        except:
            plate_objects = []
        return plate_objects

    def add_slide(self, slide_object):
        '''Adds Slide to PlateHolder.
        
        Input:
         slide_object: object of class slide
         
        Output:
         none
        '''
        self.slide = slide_object 

    def get_slide(self):
        '''Return Slide object attached to PlateHolder
        
        Input:
         none
         
        Output:
         slide_object: Slide object
        '''
        try:
            slide_object = self.slide
        except:
            slide_object = []
        return slide_object

    def set_plate_holder_pos_to_zero(self, x=None, y=None, z=None):
        '''Set current stage position as zero position for Stage in stage coordinates.
        
        Input:
         x, y, z: optional position in stage coordinates to set as zero position for Stage. If omitted, actual stage position will be used.
         
        Output:
         x, y, z: new zero position in stage coordinates
         
        Superclass for all sample related classes. Handles connection to microscope hardware through Microscope class in module hardware.
        '''
        if (x is None) or (y is None) or (z is None) :
            xStage, yStage, zStage = self.get_corrected_stage_position()
        if x is None:
            x= xStage
        if y is None:
            y=yStage
        if z is None:
            z=zStage

        self.set_zero(xZero=x, yZero=y, zZero=z)
        return x, y, z

    def get_corrected_stage_position(self, verbose=False):
        '''Get current position in stage coordinates and focus position in mum.
        
        Input:
         none
         
        Output:
         none
         
        Stage position after centricity correction
        Focus position after drift corrections (as if no drift occurred)
        '''
        # get position in x and y from stage and z focus drive
        positions_dict = self.get_microscope().get_information([self.stage_id])

        x, y = positions_dict[self.stage_id]['centricity_corrected']
        z_positions = self.get_microscope().get_z_position(self.focus_id, self.auto_focus_id)
        z = z_positions['focality_drift_corrected']
        return x, y, z

    def get_abs_stage_position(self, stage_id = None, focus_drive_id = None):
        '''Get current position in stage coordinates and focus position in mum corrected for parcentricity.
        
        Input:
         stage_id, focus_drive_id: string ids to identify stage and focus drive information is collected from
         
        Output:
         none
         
        Real focus position not corrected for drift.
        '''
        if stage_id is None:
            stage_id = self.stage_id
        if focus_drive_id is None:
            focus_drive_id = self.focus_id
            
        # get position in x and y from stage and z focus drive
        positions_dict = self.get_microscope().get_information([stage_id, focus_drive_id])
        x, y = positions_dict[self.stage_id]['centricity_corrected']
        z_positions = self.get_microscope().get_z_position(focus_drive_id, self.auto_focus_id)
        z = z_positions['focality_corrected']
        return x, y, z

    def set_stage_position(self, xStage, yStage, zStage = None, 
                           reference_object = None, 
                           load = True, 
                           verbose = True):
        '''Move stage to position in stage coordinates in mum.
        
        Input:
         xStage, yStage, zStage: stage position in mum
         reference_object: object of type sample (ImagingSystem) used to correct for xyz offset between different objectives
         load: Move focus in load position before move. Default: True
         verbose: if True print debug information (Default = True)
         
        Output:
         x, y, z: actual stage position
         
        If use_autofocus is set, correct z value according to new autofocus position.
        '''
        x, y, z =self.microscope.move_to_abs_pos(stage_id = self.stage_id,
                                                   focus_drive_id = self.focus_id,
                                                   objective_changer_id = self.objective_changer_id,
                                                   auto_focus_id = self.auto_focus_id,
                                                   safety_id = self.safety_id,
                                                   x_target = xStage,
                                                   y_target = yStage,
                                                   z_target = zStage,
                                                   reference_object = reference_object,
                                                   load = load,
                                                   verbose = verbose)

        return x, y, z
    
    ###############################################################
    #
    # Methods to control autofocus
    #
    ###############################################################

#     def recover_autofocus(self):
#         '''Execute autofocusFunction and try to recover from failure.
#         
#         Input:
#          autofocusFunction: function that that interacts with microscope autofocus
#          args: arguments for autofocusFunction
#         
#         Output:
#          returnValue: return value from autofocusFunction
#          
#         autofocusFunction has to throw exception AutofocusError in error case
#         '''
# #         success = False
# #         while not success:
#         try:
#             raise
#         except (AutofocusObjectiveChangedError, AutofocusNotSetError)  as error:
#             # show error dialog from exception
#             error.error_dialog()
#             
#             # retrieve focus reference object (typcially plate)
#             referenceObj = error.get_focus_reference_obj()
#             # try to find coverslip           
#             message.operate_message('Press ok and wait until autofocus found coverslip.\nThan focus on {} to set autofocus reference.'.format(referenceObj.get_name()))
#             # start with autofocus to find coverslip.
#             focusDriveObject = self.get_focus()
#             if isinstance(error, AutofocusObjectiveChangedError):
#                 z = focusDriveObject.focusDrive.recover_focus()
#             referenceObj.find_surface()
#             message.operate_message('Is focus ok?')
#             referenceObj.store_focus(referenceObj)
#             # update z_zero position for plate
#             xPlate, yPlate, zPlate = referenceObj.get_pos_from_abs_pos(verbose = False)
#             xZero, yZero, zZero = referenceObj.get_zero()
#             newZZeroPlate = zZero + zPlate
#             xPlate, yPlate, zZeroPlate = referenceObj.update_zero(z = newZZeroPlate)
# 
#         except AutofocusError as error:
#             focusReferenceObj = error.focusReferenceObj
#             message.operate_message(
#                 'Autofocus returned with error:\n"{}"\nPlease focus on {}\nor cancel program.'.format(error.message, focusReferenceObj.get_name()), 
#                 returnCode = False)
#             focusReferenceObj.set_use_autofocus(False)
#     
#             # update z_zero position for reference object
#             xPlate, yPlate, zPlate = self.recover_hardware(focusReferenceObj.get_pos_from_abs_pos, verbose = False)
#             xZero, yZero, zZero = self.recover_hardware(focusReferenceObj.get_zero)
#                 xPlate, yPlate, zPlate = self.recover_hardware(focusReferenceObj.get_pos_from_abs_pos, verbose = False)
#             xZero, yZero, zZero = self.recover_hardware(focusReferenceObj.get_zero)
# 
#             newZZeroPlate = zZero + zPlate
#             xPlate, yPlate, zZeroPlate = focusReferenceObj.update_zero(z = newZZeroPlate)
    
    def set_use_autofocus(self, flag):
        '''Set flag to enable the use of autofocus.
        
        Input:
         flag: if true, use autofocus
         
        Output:
         use_autofocus: status of use_autofocus
        '''
        microscope_object = self.get_microscope()
        microscope_object.set_microscope({self.get_auto_focus_id(): {'use_auto_focus': flag}})
#         self.recover_hardware(self.focusDrive.set_use_autofocus, flag)
        return self.get_use_autofocus()

    def get_use_autofocus(self):
        '''Return flag about autofocus usage
        
        Input:
         none
         
        Output:
         use_autofocus: boolean variable indicating if autofocus should be used
        '''
        microscope_object = self.get_microscope()
        use_autofocus = microscope_object.get_information([self.get_auto_focus_id()])[self.get_auto_focus_id()]['use']
#         use_autofocus = self.recover_hardware(self.focusDrive.get_use_autofocus)
        return use_autofocus        
 
    def find_surface(self, reference_object = None, trials = 3, verbose = True):
        '''Find cover slip using Definite Focus 2 and store position in focusDrive object
        
        Input:
         reference_object: Used for setting up of autofocus
         trials: number of trials to initialize component before initialization is aborted
         verbose: if True, print debug messages (Default: True)
         
        Output: 
         positions_dict: dictionary {'absolute': z_abs, 'focality_corrected': z_cor} with focus position in mum
        '''
#         communication_object = self.get_microscope().get_control_software().connection
#         z = self.recover_hardware(self.focusDrive.find_surface, communication_object)
        microscope_object = self.get_microscope()
        microscope_object.initialize_hardware(initialize_components_OrderedDict = {self.get_auto_focus_id():['find_surface']}, 
                                              reference_object = reference_object, 
                                              trials = trials, 
                                              verbose = verbose)
        positions_dict = microscope_object.get_information(components_list = [self.get_auto_focus_id()])
        return positions_dict

    def store_focus(self, focusReferenceObj = None, trials = 3, verbose = True):
        '''Store actual focus position as offset from coverslip.
        
        Input:
         focusReferenceObj: Sample object used as reference for autofocus
         trials: number of trials to initialize component before initialization is aborted
         verbose: if True, print debug messages (Default: True)
         
        Output: 
         positions_dict: dictionary {'absolute': z_abs, 'focality_corrected': z_cor} with focus position in mum
        '''
        microscope_object = self.get_microscope()
        microscope_object.initialize_hardware(initialize_components_OrderedDict = {self.get_auto_focus_id():['no_find_surface', 'no_interaction']}, 
                                              reference_object = focusReferenceObj, 
                                              trials = trials, 
                                              verbose = verbose)
        positions_dict = microscope_object.get_information(components_list = [self.get_auto_focus_id()])
        return positions_dict


    def execute_experiment(self, experiment, 
                           cameraID, 
                           reference_object = None,
                           filePath = None,
                           metaDict = {'aics_well': '', 'aics_barcode': '', 'aics_xTile': '', 'aics_yTile': ''},
                           verbose = True):
        '''acquire image using settings defined in microscope software and optionally save.
        
        Input:
         experiment: string with experiment name as defined within microscope software
         cameraID: string with unique camera ID
         reference_object: object of type sample (ImagingSystem) used to correct for xyz offset between different objectives
         filePath: filename with path to save image in original format. Default=None: no saving
         metaDict: directory with additional meta data, e.g. {'aics_well':, 'A1'}
         verbose: if True print debug information (Default = True)
         
        Output:
          image: image of class ImageAICS
          
        Method adds cameraID to image.
        '''
        # Use an instance of Microscope from module hardware.
        # The method execute_experiment will send a command to the microscope software to acquire an image.
        # experiment is the name of the settings used by the microscope software to acquire the image.
        # The method does not return the image, nor does it save it.
        # use PlateHolder.save_image to trigger the microscope software to safe the image.    
        microscope_instance = self.get_microscope()   
        image = microscope_instance.execute_experiment(experiment)
        
        # retrieve information about camera and add to meta data
        image.add_meta({'aics_cameraID': cameraID})
        
        # retrieve information hardware status
        informations_dict = microscope_instance.get_information()
        stage_z_corrected = microscope_instance.get_z_position(focus_drive_id = self.focus_id, 
                                                               auto_focus_id = self.auto_focus_id, 
                                                               reference_object = reference_object, 
                                                               verbose = verbose)
        
        image.add_meta({'aics_imageAbsPosX': informations_dict[self.stage_id]['absolute'][0]})
        image.add_meta({'aics_imageAbsPosY': informations_dict[self.stage_id]['absolute'][1]})
        image.add_meta({'aics_imageAbsPosX(centricity_corrected)': informations_dict[self.stage_id]['centricity_corrected'][0]})
        image.add_meta({'aics_imageAbsPosY(centricity_corrected)': informations_dict[self.stage_id]['centricity_corrected'][1]})

        # stage_z_corrected is dictionary with 
#                                 'absolute': absolute position of focus drive as shown in software
#                                 'z_focus_offset': parfocality offset
#                                 'focality_corrected': absolute focus position - z_focus_offset
#                                 'auto_focus_offset': change in autofocus position
#                                 'focality_drift_corrected': focality_corrected position - auto_focus_offset
#                                 'load_position': load position of focus drive
#                                 'work_position': work position of focus drive
#                             with focus positions in um
                            
        image.add_meta({'aics_imageAbsPosZ': stage_z_corrected['absolute']})
        image.add_meta({'aics_imageAbsPosZ(focality_corrected)': stage_z_corrected['focality_corrected']})
        image.add_meta({'aics_imageAbsPosZ(z_focus_offset)': stage_z_corrected['z_focus_offset']})
        image.add_meta({'aics_imageAbsPosZ(focality_drift_corrected)': stage_z_corrected['focality_drift_corrected']})
        image.add_meta({'aics_imageAbsPosZ(auto_focus_offset)': stage_z_corrected['auto_focus_offset']})
        image.add_meta({'aics_imageAbsPosZ(load_position)': stage_z_corrected['load_position']})
        image.add_meta({'aics_imageAbsPosZ(work_position)': stage_z_corrected['work_position']})
        
        image.add_meta({'aics_objectiveMagnification': int(informations_dict[self.objective_changer_id]['magnification']),
                        'aics_objectiveName': informations_dict[self.objective_changer_id]['name']})
        

        # add meta data imported into method
        image.add_meta(metaDict)
        
        if filePath != None:
            image=self.save_image(filePath, cameraID, image)
        return image

    def live_mode_start(self, camera_id, experiment = None):
        '''Start live mode in microscope software.
        
        Input:
         camera_id: string with unique camera ID
         experiment: string with experiment name as defined within microscope software
                      If None use actual experiment.
         
        Output:
          None
        '''
        # Use an instance of a Camera from module hardware.
        # The method starts live mode for adjustments in the software. It does not acquire an image
        # experiment is the name of the settings used by the microscope software to acquire the image.
               
#         self.recover_hardware(self.microscope.live_mode, camera_id, experiment, live = True)
        self.microscope.live_mode(camera_id, experiment, live = True)

    def live_mode_stop(self, camera_id, experiment=None, ):
        '''Start live mode in microscopy software.
        
        Input:
         camera_id: string with unique camera ID
         experiment: string with experiment name as defined within microscope software
                      If None use actual experiment.
                  
        Output:
          None
        '''
        # Use an instance of a Camera from module hardware.
        # The method stops live mode for adjustments in the software. It does not acquire an image
        # experiment is the name of the settings used by the microscope software to acquire the image.
               
#         self.recover_hardware(self.microscope.live_mode, camera_id, experiment, live = False)
        self.microscope.live_mode(camera_id, experiment, live = False)
    
    def save_image(self, filePath, cameraID, image):
        '''save original image acquired with given camera using microscope software
        
        Input:
         filePath: string with filename with path for saved image in original format
                    or tuple with path to directory and template for file name
         cameraID: name of camera used for data acquisition
         image: image of class ImageAICS
         
        Output:
         image: image of class ImageAICS
         
        '''
        # if filePath is a string use this string
        # if filePath is a list create file name including meta data defined in list        
        filePathUpdated = image.create_file_name(filePath)
        # create new filename if filename already exists
        splitExt = os.path.splitext(filePathUpdated)
        success = False
        counter = 0
        while not success:
            try:
                # Do Not need the filePath counter - Better for uploading it to FMS
                # filePathCounter = splitExt[0] + '_{}'.format(counter) + splitExt[1]
#                 image=self.cameras[cameraID].save_image(filePathCounter, image)
                image = self.get_microscope().save_image(filePathUpdated, image)
            except FileExistsError as error:
                # We need to update the filepath, other wise we end up in an infinite loop
                counter = counter + 1
                filePathUpdated = splitExt[0] + '_{}'.format(counter) + splitExt[1]
            else:
                success = True
                
        metaData = image.get_meta()
        try:
            self.get_meta_data_file().write_meta(metaData)
        except:
            MetaDataNotSavedError('Sample object {} has not meta data file path.'.format(self.get_name()))
            

        return image
 
    def load_image(self, image, getMeta):
        '''load image and meta data in object of type imageAICS
        
        Input:
         image: meta data as imageAICS object. No image data loaded so far (if image data exists, it will be replaced)
         
        Output:
         image: image and meta data as imageAICS object
        '''
        image=self.get_microscope().load_image(image, getMeta)
        return image
       
    def remove_images(self, image):
        '''Remove all images from microscope software display.
        
        Input:
         image: image taken with same camera as images to be removed
         
        Output:
         none
        '''
        self.get_microscope().remove_images()



#######################################################

class ImmersionDelivery(ImagingSystem):
    '''Class for pump and tubing to deliver immersion water to objective.
    '''
    def __init__(self, 
                 name = None,
                 plateHolderObject = None,
                 safety_id = None,
                 center = [0,0,0],
                 xFlip = 1, yFlip = 1, zFlip = 1,
                 xCorrection = 1 , yCorrection = 1, zCorrection = 1,
                 zCorrectionXSlope = 0, zCorrectionYSlope = 0):
        '''Initialize immersion water delivery system.
        
        Input:
         name: name of immersion delivery system (string)
         plateHolderObject: objet for plateHolder the system is attached to
         safety_id: id string for safety area that prevents objective damage during stage movement
         center: position of the water outlet in plateholder coordinates in mum
         xFlip, yFlip, zFlip: -1 if coordinate system of plate holder is flipped in respect to stage
         xCorrection1, yCorrection, zCorrection: correction factor if there is a discrepancy between the stage and the plate holder calibration

        Output:
         None
        '''
        super(ImmersionDelivery, self).__init__(container=plateHolderObject, name=name,\
                                    xZero=center[0], yZero=center[1], zZero=center[2],
                                    xCorrection=xCorrection, yCorrection=yCorrection, zCorrection=zCorrection,\
                                    zCorrectionXSlope=zCorrectionXSlope, zCorrectionYSlope=zCorrectionYSlope)
        self.id = name
        self.safety_id = safety_id
#         self.add_pump(pumpObject)
        # counter will be incremented by self.add_counter
        self.count = 0
        # Set magnification of lens used with immersion delivery system
        self.magnification = None
        
#     def add_pump(self, pumpObject):
#         '''Add object for pump that delivers water to immersion delivery system
#         
#         Input:
#          pumpObject: object of type pump from module hardware 
#                      (only one pump per immersion delivery system)
#          
#         Output:
#          none
#         '''
#         self.pump = pumpObject
#  
#     def get_pump(self):
#         '''Get object for pump that delivers water to immersion delivery system
#         
#         Input:
#          none
#          
#         Output:
#          pumpObject: object of type pump from module hardware 
#                      (only one pump per immersion delivery system)
#         '''
#         return self.pump

#     def set_magnification(self, magnification):
#         '''Set magnification of lens used with immersion delivery system
#         
#         Input:
#          magnification: magnification of objective used with immersion delivery system
#          
#         Output:
#          none
#         '''
#         self.magnification = float(magnification)
#  
#     def get_magnification(self):
#         '''Get magnification of lens used with immersion delivery system
#         
#         Input:
#          none
#          
#         Output:
#          magnification: magnification of objective used with immersion delivery system as float
#         '''
#         return self.magnification
        
    def trigger_pump(self):
        '''Trigger pump to deliver immersion water.
        
        Input:
         pumpID: string with name for pump to be used
         
        Output:
         none
        '''
        self.recover_hardware(self.pump.trigger_pump)
            
    def get_water(self, objectiveMagnification = None, verbose = True, automatic = False):
        '''Move objective to water outlet and add drop of water to objective.
        
        Input:    
         objectiveMagnification: add water to specific objective with given magnification as float number 
                                   Keep current objective if set to None.
         verbose: if True print debug information (Default = True)
         automatic: if True, trigger pump, else show dialog
        Output:
         none
        '''
        # get autofocus status and switch off autofocus
        autofocusUse = self.get_use_autofocus()
        self.set_use_autofocus(flag = False)
        
        # Get original position of stage and focus
        xPos, yPos, zPos = self.get_abs_position()
        # Move objective in load positionss
        focusObject=self.get_focus()
        self.recover_hardware(focusObject.goto_load)
        
        # Change objective
        if objectiveMagnification != None:
            objectiveChangerObject = self.get_objectiveChanger()
            try:
                objectiveName = objectiveChangerObject.change_magnification(objectiveMagnification, self, use_safe_position = True, verbose = verbose)
            except ObjectiveNotDefinedError as error:
                message.error_message('Please switch objective manually.\nError:\n"{}"'.format(error.message), returnCode = False)
        # Move objective below water outlet, do not use autofocus
        storeAutofocusFlag = self.get_use_autofocus()
        self.set_use_autofocus(False)
        self.move_to_zero(load = True, verbose = verbose)
        self.set_use_autofocus(storeAutofocusFlag)
        # trigger pump
        if automatic:
            self.trigger_pump()
        else:
            message.operate_message('Please add immersion water to objective.', returnCode = False)
        
        # Return to original position
        self.move_to_abs_position(xPos, yPos, zPos, 
                                  reference_object = self.get_reference_object(),
                                  load = True, 
                                  verbose = verbose)
        
        # Switch autofocus back on if it was switch on when starting get_water
        self.set_use_autofocus(flag = autofocusUse)
         
    def add_counter(self, increment = 1):
        '''Increment counter.
        
        Input:
         increment: integer to increment counter value.
                     default = 1
                     
        Output:
         count: counter setting after increment
        '''
        self.count += increment
        return self.count
 
    def get_counter(self):
        '''Get current counter value.
        
        Input:
         none
                     
        Output:
         count: current counter value
        '''
        try:
            count = self.count
        except:
            count = None
        return count

    def reset_counter(self):
        '''Reset counter value to 0.
        
        Input:
         none
                     
        Output:
         count: current counter value
        '''
        self.count = 0
        return self.count

    def set_counter_stop_value(self, counterStopValue):
        '''Set value to stop counter and trigger pumping of immersion water.
        
        Input:
         none
                     
        Output:
         counterStopValue: current counter stop value
        '''
        self.counterStopValue = counterStopValue
        return self.counterStopValue

    def get_counter_stop_value(self):
        '''Get value for counter to stop.
        
        Input:
         none
                     
        Output:
         counter_stop_value: value for counter to stop
        '''
        try:
            counter_stop_value = self.counterStopValue
        except:
            counter_stop_value = None
        return counter_stop_value

       
    def count_and_get_water(self, objectiveMagnification = None, increment = 1, verbose = True, automatic = False):
        '''Move objective to water outlet and add drop of water to objective.
        
        Input:    
         objectiveMagnification: add water to specific objective with given magnification as float number 
                     Keep current objective if set to None.
         increment: integer to increment counter value.
                     default = 1
         verbose: if True print debug information (Default = True)
         automatic: if True, trigger pump, else show dialog (Default = False)
         
        Output:
         counter: counter value after increment
        '''
        # increase counter and compare to stop value
        counter = self.add_counter(increment = increment)
        
        if counter >= self.get_counter_stop_value():
            self.recover_hardware(self.get_water, objectiveMagnification = objectiveMagnification, verbose = verbose)
            
        return counter
        

#######################################################
        
class Plate(ImagingSystem):
    '''Class to describe and navigate Plate.
    '''
    def __init__(self,name='Plate', plateHolderObject=None,center = [0,0,0],
                 xFlip=1, yFlip=1, zFlip=1,
                 xCorrection=1 , yCorrection=1, zCorrection=1,
                 zCorrectionXSlope=0, zCorrectionYSlope=0,
#                  reference_well = None
                 ):
        '''Initialize microwell plate
        
        Input:
         microscopeObject: object of class Microscope from module hardware
         name: name of plate, typically barcode
         stageID: id string for stage. Stage can only be on one stage
         xFlip, yFlip, zFlip: -1 if coordinate system of plate holder is flipped in respect to stage
         xCorrection1, yCorrection, zCorrection: correction factor if there is a discrepancy between the stage and the plate holder calibration
         reference_well: name of reference well to get initial coordinates for reference position to correct parfocality

        Output:
         None
        '''
        super(Plate, self).__init__(container=plateHolderObject, name=name,\
                                    xZero=center[0], yZero=center[1], zZero=center[2],\
                                    xFlip=xFlip, yFlip=yFlip, zFlip=zFlip,\
                                    xCorrection=xCorrection, yCorrection=yCorrection, zCorrection=zCorrection,\
                                    zCorrectionXSlope=zCorrectionXSlope, zCorrectionYSlope=zCorrectionYSlope)
#         self.name=name
        self.container=plateHolderObject
        self.wells={}
        # reference well to get initial coordinates for reference position to correct parfocality
#         self.reference_well = reference_well

    def set_barcode(self, barcode):
        '''Set barcode for plate.
        
        Input:
         barcode: string with barcode
         
        Output:
         none
        '''
        self.barcode = barcode

    def get_barcode(self):
        '''Get barcode for plate.
        
        Input:
         none
        Output:
         barcode: string with barcode         
        '''
        try:
            barcode = self.barcode
        except:
            barcode = None
        return barcode
    
    def add_wells(self, wellObjectsDict):
        '''Adds well to plate.
        
        Input:
         wellObjectsDict: dictionary of form {'name': wellObject}
         
        Output:
         none
        '''
        self.wells.update(wellObjectsDict)

    def get_wells(self):
        '''Return list with all wellObjects associated with plate.
        
        Input:
         none
         
        Output:
         well_objects: dict with well objects
        '''
        try:
            well_objects = self.wells
        except:
            well_objects = None
        return well_objects

    def get_wells_by_type(self, sample_type):
        '''Return list with all wellObjects associated with plate that contain samples of given type.
        
        Input:
         sampleType: string or set with sample type(s) (e.g. {'Sample', 'Colony', 'Barcode'})
         
        Output:
         well_objects_of_type: dict with well objects
        '''
        try:
        # create set of sampleTypes if only one same type was given as string
            if isinstance(sample_type, str):
                sample_type = {sample_type}
            # retrieve list of all well objects for plate
            wellObjects = self.get_wells()
            well_objects_of_type = {wellName: wellObject for wellName, wellObject in wellObjects.iteritems() if len(wellObject.get_samples(sampleType=sample_type))>0}            
        except:
            well_objects_of_type = {}
        return well_objects_of_type
    
    def get_well(self, well_name):
        '''Return wellOjbect for well with name wellName.
        
        Input:
         well_name: name of well in form 'A1'
         
        Output:
         well_object: object for one well with name wellName
                      None if no wellObject with wellName exists
        '''
        try:
            well_object = self.wells.get(well_name)
        except:
            well_object = None
        return well_object
    
#     def get_well_center(self, well):
#         '''retrieves center of well in stage coordinates
#         
#         Input:
#          well: name of well in format 'A1'
#          
#         Output:
#          x, y: stage coordinates for center of well in mum
#         '''
#         wellX, wellY, wellZ = self.layout[well]
#         x=wellX+Plate.xZero
#         y=wellY+Plate.yZero
#         z=wellZ+Plate.zZero
#         return x, y, z

    def move_to_well(self, well):
        '''moves stage to center of well
        
        Input:
         well: name of well in format 'A1'
         
        Output:
         xStage, yStage: x, y position on Stage in mum
        '''
        wellX, wellY, wellZ = self.layout[well]
        xStage, yStage, zStage=self.set_plate_position(wellX, wellY, wellZ)
        return xStage, yStage, zStage
        
    def show(self, nCol=4, nRow=3, pitch=26, diameter=22.05):
        '''show imageAICS of plate layout
        
        Input:
         nCol: number of columns, labeled from 1 to nCol
         nRow: number of rows, labeled alphabetically
         pitch: distance between individual wells in mm
         diameter: diameter of Well in mm
         
        Output:
         none
        '''
        drawPlate(nCol, nRow, pitch, diameter)
        

class Slide(ImagingSystem):
    '''Class to describe and navigate slide.
    '''
    def __init__(self,
                 name='Slide', 
                 plate_holder_object = None,
                 center = [0,0,0],
                 xFlip = 1, yFlip = 1, zFlip = 1,
                 xCorrection = 1 , yCorrection = 1, zCorrection = 1,
                 zCorrectionXSlope = 0, zCorrectionYSlope = 0
                 ):
        '''Initialize slide
        
        Input:
         plate_holder_object: object of class PlateHolder
         name: name of slide
         xFlip, yFlip, zFlip: -1 if coordinate system of plate holder is flipped in respect to stage
         xCorrection1, yCorrection, zCorrection: correction factor if there is a discrepancy between the stage and the plate holder calibration

        Output:
         None
        '''
        super(Slide, self).__init__(container = plate_holder_object,
                                    name = name,
                                    xZero = center[0], yZero = center[1], zZero = center[2],
                                    xFlip = xFlip, yFlip = yFlip, zFlip = zFlip,
                                    xCorrection = xCorrection, yCorrection = yCorrection, zCorrection = zCorrection,
                                    zCorrectionXSlope = zCorrectionXSlope, zCorrectionYSlope = zCorrectionYSlope)

        self.container=plate_holder_object

class Well(ImagingSystem):
    '''Class to describe and navigate single Well
    '''
    def __init__(self,name='Well', center=[0,0,0], diameter=1, plateObject=None,\
                 wellPositionNumeric = (1,1), wellPositionString = ('A','1'),\
                 xFlip=1, yFlip=1, zFlip=1,\
                 xCorrection=1 , yCorrection=1, zCorrection=1,\
                 zCorrectionXSlope=0, zCorrectionYSlope=0):
        '''Initialize class Well
        
        Input:
         name: string with well name in format 'A1'
         center: center position of well in plate coordinates in mum
         diameter: diameter of well in mum
         plateObject: object of type Plate the well is associated with
         wellPositionNumeric: (column, row) as integer tuple (e.g. (0,0) for well A1)
         wellPositionString: (row, column) as string tuple (e.g. ('A','1'))
         xFlip, yFlip, zFlip: -1 if coordinate system of plate holder is flipped in respect to stage
         xCorrection1, yCorrection, zCorrection: correction factor if there is a discrepancy between the stage and the plate holder calibration

        Output:
         None
        '''
        super(Well, self).__init__(container=plateObject, name=name,\
                                    xZero=center[0], yZero=center[1], zZero=center[2],\
                                    xFlip=xFlip, yFlip=yFlip, zFlip=zFlip,\
                                    xCorrection=xCorrection, yCorrection=yCorrection, zCorrection=zCorrection,\
                                    zCorrectionXSlope=zCorrectionXSlope, zCorrectionYSlope=zCorrectionYSlope)

        self.samples={}
        self.set_setDiameter(setDiameter= diameter)
        # As long as only a set diameter from specifications exists, use this value for all calculation.
        # Replace this value with a measured value as soon as possible
        self.set_diameter(diameter)
        self.set_plate_position_numeric(position = wellPositionNumeric)
        self._failed_image = False;

    def get_name(self):
        return self.name

    def failed_image(self):
        return self._failed_image

    def set_interactive_positions(self, tileImageData, location_list = None, app = None):
        """ Opens up the interactive mode and lets user select colonies and return the list of coordinates selected

        Input:
        tileImageData: The pixel data of the image of the well - numpy array
        location_list: The list of coordinates to be pre plotted on the image.
        app: pyqt application object initialized in microscopeAutomation.py

        Output:
        location_list: Returns the list of colonies selected by the user
        """
        if location_list is None:
            location_list = []
        # Using pyqtgraph module
        interactive_plot = ImageLocationPicker(tileImageData, location_list, app)
        title = "Well Overview Image - Well " + self.name
        interactive_plot.plot_points(title)
        self._failed_image = interactive_plot.failed_image()
        if self._failed_image:
            # A failed image has no locations
            return []
        return interactive_plot.location_list

    def find_colonies(self, location_list):
        """Find locations of colonies to be imaged in well and add them to well.

        Input:
        location_list: list of the colony locations relative to the center of the well

        Output:
        colony_list: List of Colony Objects
        """
        number = 1
        colony_dict = {}
        colony_list = []
        for location in location_list:
            colony_name = self.name + "_00" + str(number)
            number = number + 1
            new_colony = Colony(colony_name, center = (location[0], location[1], 0), wellObject=self)
            colony_dict [colony_name] = new_colony
            colony_list.append(new_colony)
        self.add_colonies(colony_dict)
        return colony_list

    def get_well_object(self):
        '''Get well object for subclass.
        
        Input:
         none
         
        Output:
         wellObject: object for well
        '''
        wellObject = self
        return wellObject
    
    def set_plate_position_numeric(self, position):
        '''Set row and column number.
        
        Input:
         position: (column, row) as integer tuple (e.g. (0,0) for well A1
         
        Output:
         none
        '''
        
        self.wellPositionNumeric = position

    def get_plate_position_numeric(self):
        '''Get row and column number.
        
        Input:
         none
         
        Output:
         well_position_numeric: (column, row) as integer tuple (e.g. (0,0) for well A1
        '''
        try:
            well_position_numeric = self.wellPositionNumeric
        except:
            well_position_numeric = None
        return well_position_numeric

    def set_plate_position_string(self, position):
        '''Set row and column as strings.
        
        Input:
         position: (row, column) as string tuple (e.g. ('A','1') for well A1)
         
        Output:
         none
        '''
        
        self.wellPositionString = position

    def get_plate_position_string(self):
        '''Get row and column as string.
        
        Input:
         none
         
        Output:
         well_position_string: (row, column) as string tuple (e.g. ('A','1') for well A1)
        '''
        try:
            well_position_string = self.wellPositionString
        except:
            well_position_string = None
        return well_position_string
        
    def set_setDiameter(self, setDiameter):
        '''Set diameter from specifications or measured externally for well.
        
        Input:
         setDiameter: predefined diameter in mum (e.g from plate specifications or other instrument)
         
        Output:
         none
        '''
        self.setDiameter=setDiameter

    def get_setDiameter(self):
        '''Get well diameter for well as measured by external means.
        
        Input:
         none
         
        Output
         set_diameter: predefined diameter in mum (e.g from plate specifications or other instrument)
        '''
        try:
            set_diameter = self.setDiameter
        except:
            set_diameter = None
        return set_diameter

    def set_measuredDiameter(self, measuredDiameter):
        '''Set diameter measured during experiment for well.
        
        Input:
         measuredDiameter: diameter in mum as measured in find_well_center_fine
         
        Output:
         none
        '''
        self.measuredDiameter=measuredDiameter
        # A measured diameter is always preferred over a diameter from specifications 
        self.set_diameter(measuredDiameter)
        
    def get_measuredDiameter(self):
        '''Get well diameter for well as measured in find_well_center_fine.
        
        Input:
         none
         
        Output
         measured_diameter: diameter in mum as measured in find_well_center_fine
        '''
        try:
            measured_diameter = self.measuredDiameter
        except:
            measured_diameter = None
        return measured_diameter

    def set_diameter(self, diameter):
        '''Set diameter for well.
        
        Input:
         diameter: diameter in mum
         
        Output:
         none
         
        If measured diameter is available it will used, otherwise the setDiameter from specifications is used.
        '''
        self.diameter=diameter

    def get_diameter(self):
        '''Get well diameter for well.
        
        Input:
         none
         
        Output
         diameter: diameter in mum 
         
        If measured diameter is available it will used, otherwise the setDiameter from specifications is used.
        '''
        try:
            diameter = self.diameter
        except:
            diameter = None
        return diameter

    def calculate_well_correction(self, update=True):
        '''Calculate correction factor for well coordinate system.
        
        Input:
         update: if True update correction factor and do not replace to keep earlier corrections in place
                  
        Output:
         none
         
        We find position within the well (e.g. colonies) based on there distance from the center in mum.
        For some experiments we use coordinates measured on other systems.
        Their might be a slight difference in calibration for different systems.
        We will use the well diameter to calculate a compensation factor for these differences.
        '''
        
        measuredDiameter=self.get_measuredDiameter()
        setDiameter=self.get_setDiameter()
        
        # if any of the diameters in not defined (None) set correction factor to 1 and print warning
        if measuredDiameter==None or setDiameter==None:
            correction =1
        else:
            correction=measuredDiameter/setDiameter
         
        # if update==True update correction factor and do not replace to keep earlier corrections in place   
        if update:
            self.update_correction(correction, correction)
        else:
            self.set_correction(correction, correction)

        
    def add_colonies(self, colonyObjectsDict):
        '''Adds colonies to well.
        
        Input:
         colonyObjectsDict: dictionary of form {'name': colonyObject}
         
        Output:
         none
        '''
        self.samples.update(colonyObjectsDict)

    def add_samples(self, sampleObjectsDict):
        '''Adds samples to well.

        Input:
         sampleObjectsDict: dictionary of form {'name': sampleObject}

        Output:
         none
        '''
        self.samples.update(sampleObjectsDict)

    def get_samples(self, sampleType={'Sample','Barcode','Colony'}):
        '''Get all samples in well.
        
        Input:
         sampleType: list with types of samples to retrieve. At this moment {'Sample','Barcode','Colony'} are supported
         
        Output:
         samples: dict with sample objects
        '''
        samples = {}
        try:
            for name, sampleObject in self.samples.iteritems():
                if type(sampleObject).__name__ in sampleType:
                    samples.update({name: sampleObject})
        except:
            samples = None
        return samples
            
    def get_colonies(self):
        '''Get all colonies in well.
        
        Input:
         none
         
        Output:
         colonies: dict with colony objects
        '''
        try:
            colonies = self.get_samples(sampleType='Colony')
        except:
            colonies = None
        return colonies
      
 
    def add_barcode(self, barcodeObjectsDict):
        '''Adds barcode to well.
        
        Input:
         barcodeObjectsDict: dictionary of form {'name': barcodeObject}
         
        Output:
         none
        '''
        self.samples.update(barcodeObjectsDict)
 
       



    def find_well_center_fine(self, experiment, wellDiameter, cameraID, dictPath, verbose = True):
        '''Find center of well with higher precision.
    
        Input:
         experiment: string with imaging conditions as defined within microscope software
         wellDiameter: diameter of reference well in mum
         cameraID: string with name of camera
         dictPath: dictionary to store images
         angles: list with angles around well center to take images for alignment in degree
         diameterFraction: offset from well center to take alignment images as diameter devided by diameterFraction
         focus: use autofocus (default = True)
         verbose: if True print debug information (Default = True)
         
        Output:
         xCenter, yCenter, zCenter: Center of well in absolute stage coordinates in mum. z after drift correction (as if no drift had occured)
     
        Method takes four images of well edges and calculates center.
        Will set origin of well coordinate system to this value.
        '''
        # user positioned right well edge in center of 10x FOW
        # acquire image and find edge coordinates
        name=self.get_name()
        filePath = dictPath + '/WellEdge_' + name + '.czi'
        metaDict = {'aics_well': self.get_name(), 'aics_barcode': self.get_barcode(), 'aics_xTile': '-1', 'aics_yTile': '0'}
        image=self.execute_experiment(experiment, cameraID, add_suffix(filePath, '-1_0'), metaDict = metaDict, verbose = verbose)

        image=self.load_image(image, getMeta=True)

        pixelSize=image.get_meta('PhysicalSizeX')
        edgePosPixels = findWellCenter.find_well_center_fine(image=image.data, \
                                                             direction='-x')

        xPos_0 = edgePosPixels * pixelSize
        xEdge_0 = xPos_0 + image.get_meta('aics_imageAbsPosX')

        # move to right edge, take image, and find edge coordinates
        self.move_delta_xyz(wellDiameter, 0, 0, load = False, verbose = verbose)
        metaDict = {'aics_well': self.get_name(), 'aics_barcode': self.get_barcode(), 'aics_xTile': '1', 'aics_yTile': '0'}
        image=self.execute_experiment(experiment, cameraID, add_suffix(filePath, '1_0'), metaDict = metaDict, verbose = verbose)

        image=self.load_image(image, getMeta=True)
        edgePosPixels = findWellCenter.find_well_center_fine(image=image.data, \
                                                             direction='x')

        xPos_1=edgePosPixels*pixelSize
        xEdge_1=xPos_1+image.get_meta('aics_imageAbsPosX')

        xRadius= (xEdge_1-xEdge_0)/2
        xCenter=xEdge_0+xRadius
        
        # move to top edge, take image, and find edge coordinates
        self.move_delta_xyz(-wellDiameter/2.0, -wellDiameter/2.0, 0, load = False, verbose = verbose)
        metaDict = {'aics_well': self.get_name(), 'aics_barcode': self.get_barcode(), 'aics_xTile': '0', 'aics_yTile': '1'}
        image=self.execute_experiment(experiment, cameraID, add_suffix(filePath, '0_1'), metaDict = metaDict, verbose = verbose)

        image=self.load_image(image, getMeta=True)
        edgePosPixels = findWellCenter.find_well_center_fine(image=image.data, \
                                                             direction='-y')
        yPos_0=edgePosPixels*pixelSize
        yEdge_0=yPos_0+image.get_meta('aics_imageAbsPosY')

        # move to bottom edge, take image, and find edge coordinates
        self.move_delta_xyz(0, wellDiameter, 0, load = False, verbose = verbose)
        metaDict = {'aics_well': self.get_name(), 'aics_barcode': self.get_barcode(), 'aics_xTile': '0', 'aics_yTile': '-1'}
        image=self.execute_experiment(experiment, cameraID, add_suffix(filePath, '0_-1'), metaDict = metaDict, verbose = verbose)

        image=self.load_image(image, getMeta=True)
        edgePosPixels = findWellCenter.find_well_center_fine(image=image.data, \
                                                             direction='y')

        yPos_1=edgePosPixels*pixelSize
        yEdge_1=yPos_1+image.get_meta('aics_imageAbsPosY')
        
        yRadius= (yEdge_1-yEdge_0)/2
        yCenter=yEdge_0+yRadius

        zCenter=image.get_meta('aics_imageAbsPosZ(driftCorrected)')
        self.set_measuredDiameter(measuredDiameter=2 * numpy.mean([xRadius, yRadius]))
        print 'Radius in x (length, x position): ', xRadius, xCenter
        print 'Radius in y (length, y position): ', yRadius, yCenter
        print 'Focus position: ', zCenter
        return xCenter, yCenter, zCenter
        

    def get_tile_positions_list(self, prefs, tile_type = 'Well', verbose = True):
        '''Get positions for tiles in absolute coordinates.
        
        Input: 
         prefs: dictionary with preferences for tiling
         tile_type: type of tiling.  Possible options:
                     - 'None': do not tile
                     - 'Fixed': use fixed number of tiles
                     - 'Well': use enough tiles to cover one well
         verbose: print debugging information
         
        Output:
         tile_position_list: list with absolute positions for tiling
         
         Other classes have additional tile_objects (e.g. ColonySize)
        '''
        # retrieve common tiling parameters, than adjust them for wells if necessary
        try:
            tile_params = self._get_tile_params(prefs, tile_type, verbose = verbose)        
            tile_positions_list = self._compute_tile_positions_list(tile_params)
        except:
            tile_positions_list = None
        return tile_positions_list
    
################################################################
    
   
class Sample(ImagingSystem):
    '''Class to describe and manipulate samples within a Well.
    Input:
    
    Output:
     None
    '''
        
    def __init__(self, name='Sample', wellObject=None, center=[0,0, 0],\
#                   experiment=None, sample=None,\
                  experiment=None,\
                  xFlip=1, yFlip=-1, zFlip=1,\
                  xCorrection=0, yCorrection=0, zCorrection=0,\
                  zCorrectionXSlope=0, zCorrectionYSlope=0):
        '''Initialize class Sample
        
        Input:
         well: object of class Well that contains Sample
         center: (x, y, z) center of sample relative to well center in mum used for imaging
         experiment: string with name of experiment as defined in microscope software used to imageAICS experiment
         sample: string with name of sample (optional)
         xFlip, yFlip, zFlip: -1 if coordinate system of plate holder is flipped in respect to stage
         xCorrection1, yCorrection, zCorrection: correction factor if there is a discrepancy between the stage and the plate holder calibration

        Output:
         None
        '''
        super(Sample, self).__init__(container=wellObject, name=name,\
                                    xZero=center[0], yZero=center[1], zZero=center[2],\
                                    xFlip=xFlip, yFlip=yFlip, zFlip=zFlip,\
                                    xCorrection=xCorrection, yCorrection=yCorrection, zCorrection=zCorrection,\
                                    zCorrectionXSlope=zCorrectionXSlope, zCorrectionYSlope=zCorrectionYSlope)
        self.microscopeObject=self.wellObject.microscopeObject
        self.well=self.wellObject.name
        self.plateLayout=self.wellObject.plateLayout
        self.stageID=self.wellObject.stageID

        self.center=center
        self.experiment=experiment


class Barcode(ImagingSystem):
    '''Class to image and read barcode.
    '''
    def __init__(self, name='Barcode', wellObject=None,center =[0,0,0],\
                 xFlip=1, yFlip=-1, zFlip=1,\
                 xCorrection=0, yCorrection=0, zCorrection=0,\
                zCorrectionXSlope=0, zCorrectionYSlope=0):
        '''Initialize class Well
        
        Input:
         name: string with name for barcode. Name has to be unique if multiple barcodes are attached to single well.
         wellObject: object of class well of well the barcode is attached to
         xFlip, yFlip, zFlip: -1 if coordinate system of plate holder is flipped in respect to stage
         xCorrection1, yCorrection, zCorrection: correction factor if there is a discrepancy between the stage and the plate holder calibration

        Output:
         None
        '''
        super(Barcode, self).__init__(container=wellObject, name=name,\
                                       xZero=center[0], yZero=center[1], zZero=center[2],\
                                       xFlip=xFlip, yFlip=yFlip, zFlip=zFlip,\
                                       xCorrection=xCorrection, yCorrection=yCorrection,\
                                       zCorrectionXSlope=zCorrectionXSlope, zCorrectionYSlope=zCorrectionYSlope)
#         self.container=wellObject

    def read_barcode_data_acquisition(self, experiment, cameraID, filePath, verbose = True):
        '''Take image of barcode.
        
        Input:
         experiment: string with name for experiment used in microscope software
         cameraID: unique ID for camera used to acquire image
         filePath: path to directory for alignment images
         verbose: if True print debug information (Default = True)
         
        Output: 
         image: Image of barcode. 
                Images will be used to decode barcode.

        '''
        image=self.execute_experiment(experiment, cameraID, filePath=filePath, verbose = verbose)
        return image

    def read_barcode(self, experiment, cameraID, filePath, verbose = True):
        '''Take image of barcode and return code.
    
        Input:
         experiment: string with imaging conditions as defined within microscope sofware
         cameraID: string with name of camera
         filePath: filename with path to store images
         verbose: if True print debug information (Default = True)
         
        Output:
         code: string encoded in barcode
        '''
        image=self.read_barcode_data_acquisition(experiment, cameraID, filePath, verbose = verbose)
        image=self.load_image(image, getMeta=False)
#         code=read_barcode(image)
        code ='Not implemented'
        return code

class Colony(ImagingSystem):
    '''Class to describe and manipulate colonies within a Well.
    '''
    def __init__(self, name = 'Colony',  center=[0,0,0], wellObject=None, image = True, ellipse=[0,0,0], meta=None, \
                 xFlip=1, yFlip=-1, zFlip=1,\
                 xCorrection=1 , yCorrection=1, zCorrection=1,\
                 zCorrectionXSlope=0, zCorrectionYSlope=0):
        '''Initialize class Colony.
        
        Input:
         name: id for colony
         image: True, if colony should be imaged
         center: (x, y, z) center of colony relative to well center in mum 
         ellipse: (long axis, short axis, orientation) for ellipse around colony 
         meta: additional meta data for colony
         wellObject: object of type Well the colony is associated with
         xFlip, yFlip, zFlip: -1 if coordinate system of plate holder is flipped in respect to stage
         xCorrection1, yCorrection, zCorrection: correction factor if there is a discrepancy between the stage and the plate holder calibration

        Output:
         None
        '''
        super(Colony, self).__init__(container=wellObject, name=name,\
                                    image = True,\
                                    xZero=center[0], yZero=center[1], zZero=center[2],\
                                    xFlip=xFlip, yFlip=yFlip, zFlip=zFlip,\
                                    xCorrection=xCorrection, yCorrection=yCorrection, zCorrection=zCorrection,\
                                    zCorrectionXSlope=zCorrectionXSlope, zCorrectionYSlope=zCorrectionYSlope)
#         self.container=wellObject
        self.cells={}
        
#         self.name=name   
        self.ellipse=ellipse
#         self.xCenter, self.yCenter=center 
        if meta:
            self.area=meta.Area     
            self.meta=meta 
    
    def set_cell_line(self, cellLine):
        '''Set name of cell line.
        
        Input:
         cellLine: string with name of cell line
         
        Output:
         none
        '''
        self.cellLine = cellLine

    def set_interactive_positions(self,imageData, location_list=None, app=None):
        """ Opens up the interactive mode and lets user select cells and return the list of coordinates selected

        Input:
        tileImageData: The pixel data of the image of the colony - numpy array
        location_list: Coordinates to be preplotted on the image
        app: pyqt application object

        Output:
        location_list: Returns the list of cells selected by the user
        """
        # Using pyqtgraph module
        if location_list is None:
            location_list = []
        interactive_plot = ImageLocationPicker(imageData, location_list, app)
        interactive_plot.plot_points("Colony Overview Image")
        return interactive_plot.location_list

    def get_cell_line(self):
        '''Get name of cell line.
        
        Input:
         none
         
        Output:
         cell_line: string with name of cell line
        '''
        try:
            cell_line = self.cellLine
        except:
            cell_line = None
        return cell_line

    def set_clone(self, clone):
        '''Set name of clone.
        
        Input:
         clone: string with name of clone
         
        Output:
         none
        '''
        self.clone = clone
        
    def get_clone(self):
        '''Get name of clone.
        
        Input:
         none
         
        Output:
         clone: string with name of clone
        '''
        try:
            clone = self.clone
        except:
            clone = None
        return clone
        
    def update_zero(self, images, verbose = True):
        '''Update zero position of colony in well coordinates
        
        Input:
         images: list with image objects of class imageAICS
         verbose: if True print debug information (Default = True)
         
        Output:
         x, y, x: new zero position
         
        z after drift correction (as if no drift had happended)
        '''
        # calculate median of all x, y, z-Positions
        xStagePositions = []
        yStagePositions = []
        zStagePositions = []
        for image in images:
            xStagePositions.append(image.get_meta('aics_imageAbsPosX'))
            yStagePositions.append(image.get_meta('aics_imageAbsPosY'))
            zStagePositions.append(image.get_meta('aics_imageAbsPosZ(driftCorrected'))
        xStageMedian = numpy.median(numpy.array(xStagePositions))
        yStageMedian = numpy.median(numpy.array(yStagePositions))
        zStageMedian = numpy.median(numpy.array(zStagePositions))

        x, y, z = self.get_container().get_pos_from_abs_pos(xStageMedian, yStageMedian, zStageMedian, verbose = verbose)
        self.set_zero(x, y, z)  
            
    def add_cells(self, cellObjectsDict):
        '''Adds cells to colony.
        
        Input:
         cellObjectsDict: dictionary of form {'name': cellObject}
         
        Output:
         none
         
        This method will update cell line and clone information foe cells based on clone information (if available)
        '''
        self.cells.update(cellObjectsDict)
        
        for cell in cellObjectsDict.itervalues():
            cell.set_cell_line(self.get_cell_line())
            cell.set_clone(self.get_clone())

    def get_cells(self):
        '''Get all cells in colony.
        
        Input:
         none
         
        Output:
         cells: list with cell objects
        '''
        try:
            cells = self.cells
        except:
            cells = None
        return cells

    def number_cells(self):
        return len(self.cells)
    
    def find_cells_cell_profiler(self, prefs, image):
        # TODO Add comments plus clean up
        '''Find locations of cells to be imaged in colony and add them to colony.
        
        Input:
         prefs: preferences read with module preferences with criteria for cells
         image: imageAICS object with colony
         
        Output:
         none
        '''
        cell_name = self.name + "_0001"
        new_cell = Cell(name=cell_name, center=[0, 0, 0], colonyObject=self)
        cell_dict = {cell_name: new_cell}
        self.add_cells(cell_dict)

    def find_cells_distance_map(self, prefs, image):
        # TODO Add comments + clean up
        '''Find locations of cells to be imaged in colony and add them to colony.

        Input:
        prefs: preferences read with module preferences with criteria for cells
        image: imageAICS object with colony

        Output:
        none
        '''
        from . import findCells
        if image.get_data() is None:
            li = LoadImageCzi()
            li.load_image(image, True)
        if prefs.getPref('Tile', validValues=VALID_TILE) != 'Fixed':
            image.data = numpy.transpose(image.data, (1, 0, 2))
        cell_finder = findCells.CellFinder(image, prefs.getPrefAsMeta('CellFinder'), self)
        cell_dict = cell_finder.find_cells()
        self.add_cells(cell_dict)

    def find_cell_interactive_distance_map (self, location):
        cell_dict ={}
        cell_name = self.name + "_{:04}".format(1)
        cell_to_add = Cell(name=cell_name, center=[location[0], location[1], 0], colonyObject=self)
        cell_dict[cell_name] = cell_to_add
        self.add_cells(cell_dict)
        return cell_to_add


    def execute_experiment(self, experiment, cameraID, reference_object = None, filePath=None,  metaDict = None, verbose = True):
        '''acquire single image using settings defined in microscope software and optionally save.
        
        Input:
         experiment: string with experiment name as defined within microscope software
         cameraID: string with unique camera ID
         reference_object: object of type sample (ImagingSystem) used to correct for xyz offset between different objectives
         filePath: filename with path to save image in original format. Default=None: no saving
         metaDict: directory with additional meta data, e.g. {'aics_well':, 'A1'}
         focus: use autofocus (default = False)
         verbose: if True print debug information (Default = True)
         
        Output:
         image: imageAICS object. At this moment they do not include the pixel data. Get pixel data with load_image.
         
        Methods calls method of container instance until container has method implemented 
        that actually performs action.
        '''
        try:
            clone = self.get_clone()
        except:
            clone = None
        try:
            cell_line = self.get_cell_line()
        except:
            cell_line = None
        metaDict.update({'aics_colonyClone': clone,
                        'aics_colonyCellLine': cell_line})
        image=self.container.execute_experiment(experiment, 
                                                cameraID, 
                                                reference_object = reference_object,
                                                filePath = filePath, 
                                                metaDict = metaDict, 
                                                verbose = verbose)
        return image

position_number = 1
class Cell(ImagingSystem):
    '''Class to describe and manipulate cells within a colony.
    Input:
    
    Output:
     None
    '''
 
    def __init__(self, name='Cell', center=[0,0,0], colonyObject=None,\
                 xFlip=1, yFlip=1, zFlip=1,\
                 xCorrection=1 , yCorrection=1, zCorrection=1,\
                 zCorrectionXSlope=0, zCorrectionYSlope=0):
        '''Initialize class Cell.
        
        Input:
         name: id for cell
         center: (x, y, z) center of cell relative to colony center in mum 
         colonyObject: object of type Colony the cell is associated with
         xFlip, yFlip, zFlip: -1 if coordinate system of plate holder is flipped in respect to stage
         xCorrection1, yCorrection, zCorrection: correction factor if there is a discrepancy between the stage and the plate holder calibration
        Output:
         None
        '''
        super(Cell, self).__init__(container=colonyObject, name=name,\
                                   xZero=center[0], yZero=center[1], zZero=center[2],\
                                    xFlip=xFlip, yFlip=yFlip, zFlip=zFlip,\
                                    xCorrection=xCorrection, yCorrection=yCorrection, zCorrection=zCorrection,\
                                    zCorrectionXSlope=zCorrectionXSlope, zCorrectionYSlope=zCorrectionYSlope)
        global position_number
        self.position_number = position_number
        position_number = position_number + 1
 
    def set_cell_line(self, cellLine):
        '''Set name of cell line.
        
        Input:
         cellLine: string with name of cell line
         
        Output:
         none
        '''
        self.cellLine = cellLine
        
    def get_cell_line(self):
        '''Get name of cell line.
        
        Input:
         none
         
        Output:
         cellLine: string with name of cell line
        '''
        try:
            cell_line = self.cellLine
        except:
            cell_line = None
        return cell_line

    def set_clone(self, clone):
        '''Set name of clone.
        
        Input:
         clone: string with name of clone
         
        Output:
         none
        '''
        self.clone = clone
        
    def get_clone(self):
        '''Get name of clone.
        
        Input:
         none
         
        Output:
         clone: string with name of clone
        '''
        try:
            clone = self.clone
        except:
            clone = None
        return clone

    def set_interactive_positions(self, imageData, location_list=[]):
        """ Opens up the interactive mode and lets user select objects and return the list of coordinates selected

        Input:
        tileImageData: The pixel data of the image of the cell - numpy array

        Output:
        location_list: Returns the list of objects selected by the user
        """
        # Using pyqtgraph module
        interactive_plot = ImageLocationPicker(imageData, location_list)
        interactive_plot.plot_points("Cell Overview Image")
        return interactive_plot.location_list

    def execute_experiment(self, experiment, cameraID, reference_object = None, filePath=None,  metaDict = {}, verbose = True):
        '''acquire single image using settings defined in microscope software and optionally save.
        
        Input:
         experiment: string with experiment name as defined within microscope software
         cameraID: string with unique camera ID
         reference_object: object of type sample (ImagingSystem) used to correct for xyz offset between different objectives
         filePath: filename with path to save image in original format. Default=None: no saving
         metaDict: directory with additional meta data, e.g. {'aics_well':, 'A1'}
         verbose: if True print debug information (Default = True)
         
        Output:
         image: imageAICS object. At this moment they do not include the pixel data. Get pixel data with load_image.
         
        Methods calls method of container instance until container has method implemented 
        that actually performs action.
        '''
        if metaDict is None:
            metaDict = {}
        metaDict.update({'aics_cellClone': self.get_clone(),        \
                        'aics_cellCellLine': self.get_cell_line()})
        image=self.container.execute_experiment(experiment, 
                                                cameraID, 
                                                reference_object = reference_object,
                                                filePath = filePath, 
                                                metaDict = metaDict, 
                                                verbose = verbose)

        return image

#################################################################
#
# Functions for testing of module
#
#################################################################

def create_microscope(software, prefs):
    '''Create a microscope object.
    
    Input:
     software: sting with name of software that controlls microscope (e.g. 'ZEN Blue', 'Test')
     prefs: dictionary with preferences
     
    Output:
     microscope: microscope object
    '''
        # create microscope 
    # we need module hardware only for testing
    import hardware as hw      
    
    # get object to connect to software based on software name   
    connectObject=hardware.ControlSoftware(software)
    # create microscope components
    # create two sCMOS cameras
    c1=hardware.Camera('Camera1 (Back)',
                       pixelSize = (6.5, 6.5),
                       pixelNumber=(2048/2, 2048/2),
                       pixelType= numpy.int32,
                       name='Orca Flash 4.0V2',
                       detectorType='sCMOS',
                       manufacturer='Hamamatsu',
                       )

    c2=hardware.Camera('sCMOS_mCherry',
                       pixelSize = (6.5, 6.5),
                       pixelNumber=(2048/2, 2048/2),
                       pixelType= numpy.int32,
                       name='Orca Flash 4.0V2',
                       detectorType='sCMOS',
                       manufacturer='Hamamatsu')

    s=hardware.Stage('TestStage')
    fd=hardware.FocusDrive('Focus')
    oc=hardware.ObjectiveChanger('Nosepiece', nPositions = 6)
    p=hardware.Pump(pump_id ='Immersion', seconds = 1, port='COM1', baudrate=19200)

    # Create safety object to avoid hardware damage and add to Microscope
    # if multiple overlapping safety areas are created, the minimum of all allowed z values is selected
    # stage will not be allowed to travel outside safety area 
    safetyObject_immersion = hardware.Safety('SaveArea_immersion')
    stage_area = [(10,10), (10, 90), (90, 90), (90,10)]
    safetyObject_immersion.add_save_area(stage_area, 'Stage', 9000)
    pump_area = [(30, 10), (40,10), (40, -5), (30, -5)]
    safetyObject_immersion.add_save_area(pump_area, 'Pump', 100)

    safetyObject_plateHolder = hardware.Safety('SaveArea_plateHolder')
    stage_area = [(10,10), (10, 90), (90, 90), (90,10)]
    safetyObject_plateHolder.add_save_area(stage_area, 'PlateHolder', 9000)
 
 
    # create microscope and add components
    m=hardware.Microscope(name ='Test Microscope',
                          controlSoftwareObject=connectObject,
                          safeties = [safetyObject_immersion, safetyObject_plateHolder],
                          microscope_components = [fd, s, oc, c1, c2, p])

    return m     

def create_plate_holder_manually():
    '''create plate holder manually instead of using setupAutomaiton.
    Not tested'''
        # create plate holder and fill with plate, wells, colonies, cells, and water delivery
    # create plate holder and connect it to microscope
    ph=PlateHolder(name = 'PlateHolder',
                 microscopeObject = m,
                 stageID = 'TestStage',
                 focusID = 'Focus',
                 objectiveChangerID = 'Nosepiece',
                 safetyID = 'SaveArea_plateHolder',
                 center=[0,0,0], xFlip=1, yFlip=1, zFlip=1,\
                 xCorrection=1 , yCorrection=1, zCorrection=1,\
                 zCorrectionXSlope=0, zCorrectionYSlope=0)
    metaDataFilePath = get_meta_data_path(prefs)
    metaDataFormat = prefs.getPref('MetaDataFormat')
    metaDataFileObject = meta_data_file(metaDataFilePath, metaDataFormat)
    ph.add_meta_data_file(metaDataFileObject)
               
    print 'PlateHolder created'

    # create immersion delivery system as part of PlateHolder and add to PlateHolder
    pumpObject = hardware.Pump('Immersion')
    m.add_microscope_object(pumpObject)
     
    # Add pump to plateHolder
    im=ImmersionDelivery(name='Immersion', plateHolderObject=ph,center = [0,0,0])
#     ph.add_immersionDelivery(immersionDeliverySystemsDict={'Water Immersion': im})
    ph.immersionDeliverySystem = im

    # create Plate as part of PlateHolder and add it to PlateHolder
    p=Plate(name='Plate', plateHolderObject=ph, center = [6891, 3447, 9500],\
                 xFlip=1, yFlip=1, zFlip=1,\
                 xCorrection=1 , yCorrection=1, zCorrection=1,\
                 zCorrectionXSlope=0, zCorrectionYSlope=0)
    p.set_barcode(1234)
    ph.add_plates(plateObjectDict={'Test Plate': p})             
    print 'Plate created and added to PlateHolder'

    # create Wells as part of Plate and add to Plate
    plateLayout=create_plate('96')

    d5=Well(name='D5', center=plateLayout['D5'], diameter=plateLayout['wellDiameter'], plateObject=p,\
                 wellPositionNumeric = (4,5), wellPositionString = ('D','5'),\
                 xFlip=1, yFlip=1, zFlip=1,\
                 xCorrection=1 , yCorrection=1, zCorrection=1,\
                 zCorrectionXSlope=0, zCorrectionYSlope=0)
    d6=Well(name='D6', center=plateLayout['D6'], diameter=plateLayout['wellDiameter'], plateObject=p,\
                 wellPositionNumeric = (5,5), wellPositionString = ('D','6'),\
                 xFlip=1, yFlip=1, zFlip=1,\
                 xCorrection=1 , yCorrection=1, zCorrection=1,\
                 zCorrectionXSlope=0, zCorrectionYSlope=0)

    wellDict={'D5': d5, 'D6': d6}
    p.add_wells(wellDict)
    print 'Wells created and added to Plate'
    
    # create Colonies as part of Wells and add to Wells
    metaDict={'ImageNumber': 134, 'ColonyNumber': 1, 'WellRow': 'C', 'WellColumn': 3, 'Center_X': 800.16150465195233, 'Center_Y': -149.09623005031244, 'Area': 3854.0, 'ColonyMajorAxis': 137.58512073673762, 'ColonyMinorAxis': 49.001285888466853, 'Orientation': 50.015418444799394, 'WellCenter_ImageCoordinates_X': 3885.1862986357551, 'WellCenter_ImageCoordinates_Y': 4153.2891461366862, 'Well': 'C3'}
    meta=pandas.DataFrame(metaDict, index=[804])
    # meta data not checked for compatibility with settings below
    c1d5=Colony(name = 'C1D5', image = True, center=[0,0,0], ellipse=[1000,1000,1000], meta=meta, wellObject=d5,\
                 xFlip=1, yFlip=-1, zFlip=1,\
                 xCorrection=1 , yCorrection=1, zCorrection=1,\
                 zCorrectionXSlope=0, zCorrectionYSlope=0)
    c1d5.set_cell_line('AICS0')
    c1d5.set_clone('123')
    c2d5=Colony(name = 'C2D5', image = True, center=[50, 50, 50], ellipse=[1000,1000,1000], meta=meta, wellObject=d5,\
                 xFlip=1, yFlip=-1, zFlip=1,\
                 xCorrection=1 , yCorrection=1, zCorrection=1,\
                 zCorrectionXSlope=0, zCorrectionYSlope=0)
    c2d5.set_cell_line('AICS0')
    c2d5.set_clone('123')

    colonyDict_d5={'C1D5': c1d5,'C2D5': c2d5}
    d5.add_colonies(colonyDict_d5)
 
    print 'Colonies created and added to Wells'

    # create cells and add to colonies
    c1d5_1=Cell(name='c1d5_1', center=[0,0,0], colonyObject=c1d5,\
                 xFlip=1, yFlip=1, zFlip=1,\
                 xCorrection=1 , yCorrection=1, zCorrection=1,\
                 zCorrectionXSlope=0, zCorrectionYSlope=0)

    cellsDict_c1d5={'c1d5_1': c1d5_1}
    c1d5.add_cells(cellsDict_c1d5)
 
    print '\n______________________________________________\n'
    
    print 'Cells created and added to Colonies:\n'
    
    print 'Number of cells in colonie ', c1d5.name, ': ', c1d5.number_cells()

def test_samples(software, filePath, test=['find_well_center','find_well_center_fine','move_to_zero']):
    '''Test suite to test module with Zeiss SD hardware or test hardware.
    
    Input:
     software: software to connect to hardware (e.g. ''ZEN Blue', 'Test)
     filePath: path to store test images
     test: list with tests to perform
     
    Output: 
     Success: True when test was passed
    '''

    import setupAutomation
    
    # get all information about experiment
    prefs=preferences.Preferences(get_prefs_path())

    # create microscope
#     m=create_microscope(software, prefs)
    # setup microscope
    m = setupAutomation.setup_microscope(prefs)
 
    ph = setupAutomation.setup_plate(prefs, colonyFile = None, microscopeObject = m)

    # test background correction
    if 'test_background_correction' in test:
        c1d5_1.acquire_image(experiment = 'ScanCells.czexp', cameraID = 'sCMOS_mCherry', filePath = None)
    
    # test water delivery system for immersion water
    if 'test_immersion_delivery' in test:
        # set up immersion delivery system
            # TODO: this function should be part of pump.initialize() in module hardware.py
        # set debugging level
        verbose = True
        print '\n\nSet-up water immersion system (setup_immersion_system)'

        # get immersion delivery system object
    #     name=prefs.getPref('NameImmersionSystem')
        immersionDelivery = ph.immersionDeliverySystem
     
        # move objective under immersion water outlet and assign position of outlet to immersionDelivery object
        focusObject = ph.get_focus()
        loadPos = focusObject.get_load_position()
    
        # get communication object
        communication_object = ph.microscope.get_control_software().connection
    
        # Make sure load position is defined for focus drive
        if loadPos == None:
            message.operate_message("Move objective to load position.")
            focusObject.define_load_position(communication_object)
            loadPos = focusObject.get_load_position()

        xPos = 50
        yPos = 70
    
        #Execute experiment before moving stage to ensure that proper objective (typically 10x) in in place to avoid collision.
        experiment = 'ExperimentSetupImmersionSystem'
        cameraID = 'sCMOS_mCherry'

        immersionDelivery.execute_experiment(experiment, cameraID, filePath=None, verbose =verbose)
        immersionDelivery.move_to_abs_position(xPos, yPos, loadPos, 
                                               reference_object = self.get_reference_object(),
                                               load = True, 
                                               verbose =verbose)
    
        # take image of water outlet
        immersionDelivery.live_mode_start(cameraID, experiment)
        message.operate_message("Move objective under water outlet.\nUse flashlight from below stage to see outlet.")
        immersionDelivery.live_mode_stop(cameraID, experiment)
    
        # drop objective to load position and store position for water delivery
        # water will always be delivered with objective in load position to avoid collision
        focusObject.goto_load(communication_object)
        immersionDelivery.set_zero(verbose =verbose)
    
        # move away from delivery system to avoid later collisions
        immersionDelivery.move_to_save()
        magnification = 100
        immersionDelivery.magnification = magnification
 
        # test immersion delivery system
        
    
    # test retrieve wells with given content
    if 'test_get_by_type' in test:
        for type in ['Colony', 'Barcode', 'Sample']:
            print 'Wells of type ', type, ': ',p.get_wells_by_type(type)
            
                 
    # Test coordinate systems

    if 'test_coordinates' in test:
        print '\n______________________________________________\n'

#         testList = [ph, p, d5, c1d5, c1d5_1]
        testList = [c2d5]
        for obj in testList :
            objName = obj.get_name()
            
            print '\nTesting ', objName
            container = obj.get_container()
            if container is not None:
                contName = container.get_name()
            else:
                contName ='None'
            xStage, yStage, zStage = obj.get_abs_position()
            print 'Position of ' + objName + ' in absolute stage coordinates (ph.get_abs_position()): ',xStage, yStage, zStage

            if obj.get_container() is not None:
                xObject_0, yObject_0, zObject_0 = obj.get_obj_pos_from_container_pos(0, 0, 0, verbose=True)
                print 'Object position for container position (0,0,0): ', xObject_0, yObject_0, zObject_0
                xObject_10, yObject_20, zObject_30 = obj.get_obj_pos_from_container_pos(10,20,30, verbose=True)
                print 'Object position for container position (10,20,30): ', xObject_10, yObject_20, zObject_30
                print 'Container position for container position (0,0,0): ', obj.get_container_pos_from_obj_pos(xObject_0, yObject_0, zObject_0)
                print 'Container position for container position (10,20,30): ', obj.get_container_pos_from_obj_pos(xObject_10, yObject_20, zObject_30)
      
            # Return center of object in container coordinates.
            x, y, z = obj.get_zero()
            print 'Position of ' + objName + ' in ' + contName + ' coordinates (get_zero): ', x, y, z
          
            # Return current position in object coordinates in mum
            x, y, z = obj.get_pos_from_abs_pos()
            print 'Position of ' + objName + ' in ' + objName + ' coordinates (get_pos_from_abs_pos()): ', x, y, z
     
            x, y, z = obj.get_pos_from_abs_pos(xStage, yStage, zStage)
            print 'Position of ' + objName + ' in ' + objName + ' calculated coordinates(get_pos_from_abs_pos(xStage, yStage, zStage)): ', x, y, z
          
            try:
                x, y, z = obj.get_abs_pos_from_obj_pos(x, y, z)   
                print 'Position of ' + objName + ' in absolute stage coordinates (get_abs_pos_from_obj_pos(), should be (0,0,0)): ', x, y, z
            except:
                print 'get_abs_pos_from_obj_pos failed'

            if isinstance(obj, Colony):
                zero_pos = obj.move_to_zero()
                print('Moved colony to zero, new position: {}'.format(zero_pos))
                x, y, z = obj.get_pos_from_abs_pos()
                print('Position of stage in {} coordinates (get_pos_from_abs_pos()): {}, {}, {}'.format(objName, x, y, z))
                col_zero = obj.get_zero()
                print('Zero position of {}: {}, {}, {}'.format(objName, *col_zero))
                xStage, yStage, zStage = obj.get_abs_position()
                print 'Position of ' + objName + ' in absolute stage coordinates (ph.get_abs_position()): ',xStage, yStage, zStage
                x, y, z = obj.get_pos_from_abs_pos(xStage, yStage, zStage)
                print 'Position of stage in ' + objName + ' calculated coordinates(get_pos_from_abs_pos(xStage, yStage, zStage), should be the same): ', x, y, z
                cont = obj.get_container()
            
            print '\n______________________________________________\n'

    
    
    
    if 'find_well_center' in test:
        # Find center of well based on 1.25x objective image
   
        # test find center of well
        print 'Find center of well'
        x, y, z = d5.get_abs_pos_from_obj_pos(0, 0)
        print 'Position of well a1 in absolute stage coordinates before calibration: ', x, y, z
        d5.set_zero(x, y, z)
    
        x, y, z=d5.get_zero()
        print 'Zero position of well a1  absolute well coordinates before calibration: ', x, y, z
    
        print 'Position of well a1 in absolute stage coordinates before calibration: ', x, y
        x, y, z=d5.find_well_center_fine(experiment='ImageFindWellCenter.czexp',  wellDiameter = 6134,cameraID='sCMOS_mCherry', dictPath=filePath)
        print 'Position of well center in absolute well coordinates (calculated): ', x, y, z
    
        d5.set_zero(x, y)
        d5.move_to_zero()
        x, y, z= d5.get_abs_pos_from_obj_pos(0, 0)
        print 'Position of well a1 in absolute stage coordinates (calculated): ', x, y, z
    
        d5.execute_experiment(experiment='ImageFindWellCenter.czexp',  \
                              cameraID='sCMOS_mCherry', \
                              filePath=filePath+'wellCenterTest.czi')   

    if 'find_well_center_fine' in test:
        # Find center of well based on 10x objective image
        message.operate_message("Please focus with 10x on right edge of well " +
                               '\nto find zero position')

   
        # find center of well and use this value as zero value for plate
        experiment='ImageFindWellCenter_10x'
        wellDiameter=6011
        cameraID='sCMOS_mCherry'
    
        xCenterAbs, yCenterAbs, zCenterAbs = d5.find_well_center_fine(experiment=experiment,\
                                                                     wellDiameter=wellDiameter,\
                                                                     cameraID=cameraID,\
                                                                     dictPath=filePath)
    
        # get plate object  
        # get dictionary of all plates associated with plate holder
        plateObjects=ph.get_plates()    
        # get object for plate with name plateName, typically the barcode
        plateObject=plateObjects['Test Plate']
    
        # Update zero position for plate
        plateObject.set_zero(xCenterAbs, yCenterAbs, zCenterAbs)

#     if 'move_to_zero' in test:
#         # Find center of well based on 10x objective image

    if 'test_auto_focus' in test:
    # test setting and recall of auto focus
        print ('\n______________________________________________\n')
        print ('Test auto-focus')
        
        # get first plate
        plate = ph.get_plates().values()[0]
        # get well D5 on first plate
        d5 = plate.get_well('D5')
        
        x, y, z = d5.move_to_zero(load=True, verbose=False)
        print ('Center position of well {} is x = {}, y = {}, z = {}'.format(d5.get_name(), x, y, z))
        
        # enable autofocus
        autoFocusStatus = ph.recover_hardware(d5.set_use_autofocus, 'True')
        if autoFocusStatus:
            print ('Autofocus enabled')
        else:
            print ('Autofocus disabled')
            
        
        # move to edge of left well and keep focal position
        deltaX = 6134/2
        x, y, z = ph.recover_hardware(d5.move_delta_xyz, -deltaX, 0, 0, load = True, verbose = False)
        
        # get focal position of edge
        message.operate_message("Please focus with 10x to edge of well. ")
        x, y, zEdge = ph.recover_autofocus(d5.get_abs_position)
        print ('Edge position of well {} is x = {}, y = {}, z = {}'.format(d5.get_name(), x, y, zEdge))
        
        #update zero for well d6
        # get z position in object coordinates
        x, y, newZ = ph.recover_autofocus(d5.get_pos_from_abs_pos, verbose = False)
        print ('Edge position in object coordinates of well {} is x = {}, y = {}, z = {}'.format(d5.get_name(), x, y, newZ))
        d6.update_zero(z = newZ, verbose = True)
        
        # move to center of d6
        x, y, z = ph.recover_autofocus(d6.move_to_zero, load = True, verbose = False)
        print ('Center position of well {} is x = {}, y = {}, z = {}'.format(d6.get_name(), x, y, z))
        
        # move to edge of right well and keep focal position
        deltaX = 6134/2
        x, y, z = ph.recover_autofocus(d5.move_delta_xyz, deltaX, 0, 0, load = True, verbose = False)
        print ('Edge position of well {} is x = {}, y = {}, z = {}'.format(d6.get_name(), x, y, z))
        
    # move stage to cells and acquire image
    if 'image_cells' in test:
        # enable autofocus
        p.set_use_autofocus(True)
        
        # iterate through wells
        for wellName, wellObject in p.wells.iteritems():
            print 'Well: ', wellName
            print 'Zero well position: ', wellObject.get_zero()
            print 'Well position in stage coordinates after move: ', wellObject.move_to_zero()
            message.operate_message("Check if position is correct")
            for colName, colObject in wellObject.get_colonies().iteritems():
                print '.Colony: ', colName
                print 'Zero colony position: ', colObject.get_zero()
                print colObject.move_to_zero()
                message.operate_message("Check if position is correct")
                for cellName, cellObject in colObject.cells.iteritems():
                    # get preferences for cell imaging
                    cellPrefs = prefs.getPrefAsMeta('ScanCells')
                    print '...Well: ', wellName
                    print '...Colony: ', colName
                    print '...Cell: ', cellName
                    print 'Zero cell position: ', cellObject.get_zero()
                    print cellObject.move_to_zero()
                    message.operate_message("Check if position is correct")
                    metaDict={'aics_well': wellName, 'aics_colony': colName, \
                             'aics_cell': cellName, 'aics_barcode': p.get_name(), \
                             'aics_xTile': 0, 'aics_yTile': 0}
                    # acquire and save image using test.czexp settings and save as .czi file
                    image = cellObject.execute_experiment(experiment='test.czexp', \
                                                  cameraID='Camera1 (Back)', \
                                                  filePath=filePath+'test2.czi', \
                                                  metaDict = metaDict)
                    print 'Image acquired and saved at ', filePath+'test2.czi'
                    print ('Meta data: ', image.get_meta())
                    
                    # repeat experiment and assemble file name based on pattern stored in preferences
                    template = cellPrefs.getPref('FileName')
                    template.insert(-1, cellName)
                    fileName = image.create_file_name(template)
                    fileDirPath = os.path.join(filePath, fileName)
                    image = cellObject.execute_experiment(experiment='test.czexp', \
                                                  cameraID='Camera1 (Back)', \
                                                  filePath = fileDirPath, \
                                                  metaDict = metaDict)
                    print ('Image acquired and saved at ', fileDirPath)
                    print ('Meta data: ', image.get_meta())
                    

    # acquire tile scan in well
    if 'test_tile_scan' in test:
        print ('Test tiling')
        
        # Define how to tile 
        # - NoTiling:  no tiling
        # - Fixed: use predifined number of tiles
        # - ColonySize:  based on size of colony
        # - Well:  image whole well (if only part of well set PercentageWell to value smaller 100)
        tile_type = 'NoTiling'
        
        # Use well d5
        posList = None
        print ('List with tile positions for tile_object {}: {}'.format(tile_type, posList))
        images = d5.acquire_images(experiment = 'DummyExperiment', 
                                 cameraID = 'Camera1 (Back)',
                                 filePath = filePath, 
                                 posList=posList,
                                 load = False, 
                                 metaDict = {}, 
                                 verbose = False)
        print (images)
        
        try:
            tile_type = 'Fixed'
            imaging_settings = prefs.getPrefAsMeta('ScanPlate')
            posList = d5.get_tile_positions_list(imaging_settings, tile_type = tile_type, verbose = True)
            print ('List with tile positions for tile_object {}: {}'.format(tile_type, posList))
            images = d5.acquire_images(experiment = 'DummyExperiment', 
                                     cameraID = 'Camera1 (Back)',
                                     filePath = filePath, 
                                     posList=posList,
                                     load = False, 
                                     metaDict = {}, 
                                     verbose = False)
            print (images)
        except:
            print ('Error in scan tiles of type {}'.format(tile_type))


        try:
            tile_type = 'ColonySize'
            # requires colonies to work
            imaging_settings = prefs.getPrefAsMeta('ScanColonies')
            posList = c1d5.get_tile_positions_list(imaging_settings, tile_type = tile_type, verbose = True)
            print ('List with tile positions for tile_object {}: {}'.format(tile_type, posList))
            images = d5.acquire_images(experiment = 'DummyExperiment', 
                                     cameraID = 'Camera1 (Back)',
                                     filePath = filePath, 
                                     posList=posList,
                                     load = False, 
                                     metaDict = {}, 
                                     verbose = False)
            print (images)
        except:
            print ('Error in scan tiles of type {}'.format(tile_type))
     
        try:
            tile_type = 'Well'
            imaging_settings = prefs.getPrefAsMeta('ScanPlate')
            posList = d5.get_tile_positions_list(imaging_settings, tile_type = tile_type, verbose = True)
            print ('List with tile positions for tile_object {}: {}'.format(tile_type, posList))
            images = d5.acquire_images(experiment = 'DummyExperiment', 
                                     cameraID = 'Camera1 (Back)',
                                     filePath = filePath, 
                                     posList=posList,
                                     load = False, 
                                     metaDict = {}, 
                                     verbose = False)
            print (images)
        except:
            print ('Error in scan tiles of type {}'.format(tile_type))
            
    return True

####################################################################################################
#
# Start main
#
####################################################################################################    

if __name__ == '__main__':
    # import libraries used for testing only
    import argparse
    
    # define filePath to store results
    filePath="D:\\Winfried\\testImages\\"
#     filePath="F:\\Winfried\\Testdata\\"
    if getpass.getuser() == 'mattb':
        filePath="C:/Users/matthewbo/Git/microscopeautomation/data/testImages"
#     filePath="/Users/winfriedw/Documents/Programming/ResultTestImages/"
    # Regularized argument parsing
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument('-p', '--preferences', help="path to the preferences file")
    args = arg_parser.parse_args()
    if args.preferences is not None:
        set_pref_file(args.preferences)

    
    # test classes
    # list with tests to perform
#     test=['test_background_correction', 
#           'test_immersionDelivery', 
#           'test_get_by_type', 
#           'test_coordinates',
#           'find_well_center',
#           'find_well_center_fine',
#           'move_to_zero', 
#           'test_auto_focus', 
#           'image_cells',
#           'test_tile_scan']
    test=['test_auto_focus']
    software='ZEN Blue'
#     software='Test'

    if test_samples(software=software,filePath=filePath, test=test):
        print 'Tests performed successful: ', test
  
    