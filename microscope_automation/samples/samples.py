"""
Classes to describe and manipulate samples
Created on Jul 11, 2016

@author: winfriedw
"""

import logging
import math
import string
import pandas
import getpass
import numpy
from os import path
import warnings
from collections import OrderedDict

# import modules from project microscope_automation
from ..get_path import (
    get_images_path,
    get_meta_data_path,
    get_prefs_path,
    add_suffix,
    set_pref_file,
)
from .draw_plate import draw_plate
from .. import automation_messages_form_layout as message
from . import find_well_center
from . import correct_background
from . import tile_images
from ..load_image_czi import LoadImageCzi
from .meta_data_file import MetaDataFile
from .positions_list import CreateTilePositions
from .interactive_location_picker_pyqtgraph import ImageLocationPicker
from ..automation_exceptions import (
    ObjectiveNotDefinedError,
    FileExistsError,
    MetaDataNotSavedError,
)

# we need module hardware only for testing
from ..hardware import hardware_control

# create logger
logger = logging.getLogger("microscopeAutomation")

################################################################################
#
# constants with valid preferences values
#
################################################################################

VALID_FUNCTIONNAME = [
    "initialize_microscope",
    "set_up_objectives",
    "update_plate_well_z_zero",
    "calculate_plate_correction",
    "calculate_all_wells_correction",
    "setup_immersion_system",
    "scan_samples",
]
VALID_SETUPFILES = [True, False]
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
VALID_TILE = ["NoTiling", "Fixed", "Size"]
VALID_FINDOBJECTS = ["None", "Cells", "Colonies"]
VALID_TYPEFINDCELLS = ["False", "CenterMassCellProfiler", "TwofoldDistanceMap"]

################################################################################
#
# Helper functions
#
################################################################################


def create_plate(plate_format):
    """Set up coordinates for different plate layouts for standard plates to be
    used with class Plate.

    Input:
     plate_format: sting for format of plate ('12', '24', '96')

    Output:
     plate_layout: dictionary to describe plate with entries
      name: name of plate

      well_diameter: diameter of well in mum

      well_names: (x,y) coordinates of well center in plate coordinates in mum.
      The center of well A1 = (0,0)
    """
    if plate_format == "12":
        n_row = 3
        n_col = 4
        pitch = 26000
        diameter = 22050
        z_center_well = 104
    elif plate_format == "24":
        n_row = 4
        n_col = 6
        pitch = 19300
        diameter = 15540
        z_center_well = 104
    elif plate_format == "96":
        n_row = 8
        n_col = 12
        pitch = 9000
        diameter = 6134
        z_center_well = 104

    # calculate name and position of wells
    # Center of well A1 is considered the origin
    plate_layout = {"name": plate_format, "well_diameter": diameter}
    for x in range(n_col):
        x_name = str(x + 1)
        x_coord = x * pitch
        for y in range(n_row):
            y_name = string.ascii_uppercase[y]
            y_coord = y * pitch
            plate_layout[y_name + x_name] = (x_coord, y_coord, z_center_well)
    return plate_layout


def create_rect_tile(n_col, n_row, x_pitch, y_pitch, z_pos=0):
    """Create coordinates for rectangular tile scan..
    The tiles will be centered around the current stage position.

    Input:
     n_col, n_row: number of tiles in x and y

     x_pitch, y_pitch: distance between tile centers in x and y

     z_pos: offset in z in mum

    Output:
     pos_list: list with tuples (x,y) for tile centers.
    """
    pos_list = []
    n_col_int = int(math.ceil(n_col))
    n_row_int = int(math.ceil(n_row))
    for i in [n - (n_col_int - 1) / 2.0 for n in range(n_col_int)]:
        for j in [k - (n_row_int - 1) / 2.0 for k in range(n_row_int)]:
            pos_list.append((i * x_pitch, j * y_pitch, z_pos))
    return pos_list


################################################################################
#
# Classes for sample hierarchy
#
################################################################################


class ImagingSystem(object):
    def __init__(
        self,
        container=None,
        name="",
        image=True,
        x_zero=0,
        y_zero=0,
        z_zero=0,
        x_flip=1,
        y_flip=1,
        z_flip=1,
        x_correction=0,
        y_correction=0,
        z_correction=0,
        z_correction_x_slope=0,
        z_correction_y_slope=0,
        z_correction_z_slope=0,
        x_safe_position=None,
        y_safe_position=None,
        z_safe_position=None,
        reference_object=None,
        x_ref=None,
        y_ref=None,
        z_ref=None,
        microscope_object=None,
        stage_id=None,
        focus_id=None,
        auto_focus_id=None,
        objective_changer_id=None,
        safety_id=None,
    ):
        """This is the superclass for all sample related classes
        (e.g. well, colony, etc).

        Input:
         container: class that contains object (e.g. Plate is container for Well)

         name: sting name of object

         image: include in list of samples that will be imaged

         x_zero, y_zero, z_zero: position of object center in container coordinates
         in mum

         x_flip, y_flip, z_flip: -1 if coordinate system is flipped compared to
         container, otherwise 1. E.g. PlateHolder has origin in lower left corner,
         Zeiss SD stage has origin in upper left corner, thus x_flip =1 and y_flip=-1

         x_correction, y_correction, z_correction: correction factor for coordinate
         system relative to container coordinates,
         e.g. if 1 mum in well coordinates is not exactly 1 mum in plate coordinates.

         x_safe_position, y_safe_position, z_safe_position: position to start
         any movements without danger of objective or other collisions

         reference_object: any object of type sample used as reference to correct
         for xyz offset between different objectives.
         Use only one of reference object or reference positions

         x_ref, y_ref, z_ref: positions used as reference to correct for xyz
         offset between different objectives.
         Use only one of reference object or reference positions

        Output:
         None
        """
        self.images = []
        self.set_name(name)

        # object self is part of, is contained in
        self.set_container(container)

        # We can attach images to objects
        # E.g. images for background correction
        self.image_dict = {}

        # Decide weather sample should be imaged
        self.set_image(image)

        # positions of object center in container coordinates
        self.set_zero(x_zero, y_zero, z_zero)

        # set safe position for start of any movement
        self.set_safe(x_safe_position, y_safe_position, z_safe_position)

        # flip of coordinate system compared to enclosing container
        # e.g. typically we assume a cartesian coordinate system with origin
        # in the lower left corner
        # the Zeiss SD stage coordinates have their origin in the upper left corner,
        # thus the y axis of the PlateHolder is flipped by -1
        self.set_flip(x_flip, y_flip, z_flip)

        # correction for calibration.
        # E.g. these values can be used when well diameter or distance between wells
        # are used for calibration.
        self.set_correction(
            x_correction,
            y_correction,
            z_correction,
            z_correction_x_slope,
            z_correction_y_slope,
            z_correction_z_slope,
        )

        # attach additional meta data
        self.meta_dict = None

        # Directory with list of objects to be imaged
        self.image_dirs = {}

        self.set_hardware(
            microscope_object=microscope_object,
            stage_id=stage_id,
            focus_id=focus_id,
            auto_focus_id=auto_focus_id,
            objective_changer_id=objective_changer_id,
            safety_id=safety_id,
        )

        # reference positions for auto-focus
        # when switching objective user focuses on identical object at this position.
        # the difference between the stored and the new position is used to calculate
        # par-centricity and par-focuality
        self.set_reference_object(reference_object)
        self.set_reference_position(x_ref, y_ref, z_ref)
        self.reference_objective = None
        self.reference_objective_changer = None

        # Position used to define zero position for plate z
        self.update_z_zero_pos = None

    def __repr__(self):
        return "<class {}: '{}'>".format(self.__class__.__name__, self.get_name())

    def set_hardware(
        self,
        microscope_object=None,
        stage_id=None,
        focus_id=None,
        auto_focus_id=None,
        objective_changer_id=None,
        safety_id=None,
    ):
        """Store object that describes connection to hardware.

        Input:
         microscope_object: object of class Microscope from module hardware

         stage_id: id string for stage.

         focus_id: id string with name for focus drive

         auto_focus_id: id string with name for auto-focus

         objective_changer_id: id string with name for objective changer

         safety_id: id string for safety area that prevents objective damage
         during stage movement

        Output:
         none
        """
        self.microscope = microscope_object
        self.stage_id = stage_id
        self.focus_id = focus_id
        self.auto_focus_id = auto_focus_id
        self.objective_changer_id = objective_changer_id
        self.safety_id = safety_id

    def set_name(self, name=""):
        """Set name of object

        Input:
         name: string with name of object
        Output:
         none
        """
        self.name = name

    def get_name(self):
        """Return name of object.

        Input:
         none

        Output:
         name: string name of object
        """
        return self.name

    ################################################################################
    # Begin
    # Methods to find positions in image
    #
    ################################################################################

    def set_interactive_positions(self, tileImageData, location_list=[], app=None):
        """Opens up the interactive mode and lets user select colonies and
        return the list of coordinates selected

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
    # Methods to handle reference used to correct for xyz offset between objectives.
    #
    #################################################################

    def set_reference_object(self, reference_object):
        """Set reference object to correct for xyz offset between different objectives.
        Avoid setting reference positions and connect reference object to same sample.

        Input:
         reference_object: any object of type sample

        Output:
         none


        """
        self.reference_object = reference_object

    def get_reference_object(self):
        """Get reference object to correct for xyz offset between different objectives.

        Input:
         none

        Output:
         reference_object: any object of type sample

        Searches through all containers until id is found
        """
        try:
            reference_object = self.reference_object
            if reference_object is None:
                reference_object = self.get_container().get_reference_object()
        except Exception:
            reference_object = None
        return reference_object

    def set_reference_position(self, x, y, z):
        """Set position used as reference to correct for xyz offset between different
        objectives. Avoid setting reference positions and connect reference object to
        the same sample.

        Input:
         x, y, z: position of reference structure in object coordinates. Can be None

         Output:
          none
        """
        if self.get_reference_object() and self.get_reference_object() is not self:
            warnings.warn(
                """The object {} has already the reference object {} attached.
                            One should avoid to use reference positions and objects at
                            the same time""".format(
                    self.get_name(), self.get_reference_object().get_name()
                )
            )

        # We have to allow to set reference positions to none during initialization
        # if x is None and y is None and z is None:
        #     return
        self.x_ref = x
        self.y_ref = y
        self.z_ref = z

    def get_reference_position(self):
        """Return position used as reference to correct for xyz offset between
        different objectives.

        Get position from reference object if available.
        If none is available use zero postion

        Input:
         none

        Output:
         x, y, z: position of reference structure in object coordinates
        """
        if self.get_reference_object() and self.get_reference_object() is not self:
            if self.x_ref or self.y_ref or self.z_ref:
                warnings.warn(
                    """The object {} has reference positions and the reference
                                object {} attached. Reference positions from reference
                                object will be used.""".format(
                        self.get_name(), self.get_reference_object().get_name()
                    )
                )
            x, y, z = self.get_reference_object().get_reference_position()
        else:
            if (
                self.x_ref is not None
                and self.y_ref is not None
                and self.z_ref is not None
            ):  # noqa
                x = self.x_ref
                y = self.y_ref
                z = self.z_ref
            else:
                # reference position was not defined
                x, y, z = (None, None, None)
        return x, y, z

    #################################################################
    #
    # Methods to handle reference used to correct for xyz offset between objectives.
    # End
    #################################################################

    def add_samples(self, sampleObjectsDict):
        """Adds colonies to well.

        Input:
         colonyObjectsDict: dictionary of form {'name': colonyObject}

        Output:
         none
        """
        self.samples.update(sampleObjectsDict)

    def get_well_object(self):
        """Get well object for subclass.

        Input:
         none

        Output:
         well_object: object for well
        """
        well_object = self.container.get_well_object()
        return well_object

    def set_image(self, image=True):
        """Define if sample should be included in imaging.

        Input:
         image: if True, include in imaging

        Output:
         none
        """
        self.image = image

    def get_image(self):
        """Return image property that defines if sample is included in imaging.

        Input:
         none

        Output:
         image: if True, include in imaging
        """
        image = self.image
        return image

    def add_to_image_dir(self, list_name, sample_object=None, position=None):
        """Add sample object to list with name listName of objects to be imaged.

        Input:
         list_name: string with name of list (e.g. 'ColoniesPreScan'

         sample_object: object to be imaged. Can be list. List will always added at end

         position: position of object in list. Position will determine order of imaging.
                    Default: None = Append to end. Has no effect if object is list.

        Output:
         none
        """
        if list_name not in self.image_dirs.keys():
            self.image_dirs[list_name] = []
        if isinstance(sample_object, list):
            self.image_dirs[list_name].extend(sample_object)
        else:
            if position is None:
                self.image_dirs[list_name].append(sample_object)
            else:
                self.image_dirs[list_name].insert(sample_object, position)

    def get_from_image_dir(self, listName):
        """Get list with name listName of objects to be imaged.

        Input:
         listName: string with name of list (e.g. 'ColoniesPreScan'

        Output:
         sampleObjects: list of name listName with objects to be imaged
        """
        sampleObjects = None
        for key in self.image_dirs.keys():
            if listName in self.image_dirs.keys():
                sampleObjects = self.image_dirs[listName]
        return sampleObjects

    def set_barcode(self, barcode):
        """Set barcode for plate.

        Input:
         barcode: string with barcode

        Output:
         none
        """
        self.barcode = self.container.set_barcode(barcode)

    def get_barcode(self):
        """Get barcode for plate.

        Input:
         none
        Output:
         barcode: string with barcode
        """
        try:
            barcode = self.container.get_barcode()
        except Exception:
            barcode = None
        return barcode

    def set_container(self, container=None):
        """Object is part of container object (e.g. Plate is container for Well).

        Input:
         container: object for container
        Output:
         none
        """
        self.container = container

    def get_container(self):
        """Return container object that encloses object.

        Input:
         none

        Output:
         container: container object
        """
        return self.container

    def get_sample_type(self):
        """Return sample type.

        Input:
         none

        Output:
         sampleType: string with name of object type
        """
        sampleType = type(self).__name__
        return sampleType

    def set_zero(self, x=None, y=None, z=None, verbose=True):
        """Set center position of object in container coordinates.

        Input:
         x, y, z: position of object center in mum in coordinate system
         of enclosing container. If None, use current position

         verbose: if True print debug information (Default = True)

        Output:
         x_zero, y_zero, z_zero: new center position in container coordinates
        """
        if (x is None) or (y is None) or (z is None):
            if self.container is None:
                x_zero, y_zero, z_zero = self.get_corrected_stage_position(
                    verbose=verbose
                )
            else:
                x_zero, y_zero, z_zero = self.container.get_pos_from_abs_pos(
                    verbose=verbose
                )
        if x is None:
            x = x_zero
        if y is None:
            y = y_zero
        if z is None:
            z = z_zero
        self.x_zero = x
        self.y_zero = y
        self.z_zero = z
        return self.x_zero, self.y_zero, self.z_zero

    def update_zero(self, x=None, y=None, z=None, verbose=True):
        """Update center position of object in container coordinates.
        Input:
         x, y, z: position of object center in mum in coordinate system
         of inclosing container. If None, use current position

         verbose: if True print debug information (Default = True)

        Output:
         x_zero, y_zero, z_zero: new center position in container coordinates
        """
        if x is not None:
            self.x_zero = x
        if y is not None:
            self.y_zero = y
        if z is not None:
            self.z_zero = z
        return self.x_zero, self.y_zero, self.z_zero

    def get_zero(self):
        """Return center of object in container coordinates.

        Input:
         none

        Output:
         x_zero, y_zero, z_zero: center of object in mum in container coordinates
        """
        return (self.x_zero, self.y_zero, self.z_zero)

    def get_abs_zero(self, verbose=True):
        """Return center of object in stage coordinates.

        Input:
         verbose: if True print debug information (Default = True)

        Output:
         x_zero, y_zero, z_zero: center of object in mum in stage coordinates
        """
        xStageZero, yStageZero, zStageZero = self.get_abs_pos_from_obj_pos(
            0, 0, 0, verbose=verbose
        )
        return (xStageZero, yStageZero, zStageZero)

    def set_safe(self, x, y, z):
        """Set safe stage position to start any movement without danger
        of collision in sample coordinates.

        Input:
         x, y, z: safe position in sample coordinates.

        Output:
         x_safe, y_safe, z_safe: safe position in sample coordinates.
        """
        # check if input is a number or None
        try:
            if x is None:
                self.x_safe = None
            else:
                self.x_safe = float(x)

            if y is None:
                self.y_safe = None
            else:
                self.y_safe = float(y)
            if z is None or z == "None":
                "safe z position in load position"
                self.z_safe = None
            else:
                self.z_safe = float(z)
        except Exception:
            print("{}, {}, {} should all be numbers or None".format(x, y, z))
            raise
        return self.x_safe, self.y_safe, self.z_safe

    def get_safe(self):
        """Get safe stage position to start any movement without danger .
        of collision in sample coordinates.

        Input:
         None

        Output:
         x, y, z: safe position in sample coordinates.
        """
        x = self.x_safe
        y = self.y_safe
        z = self.z_safe
        if (x is None) or (y is None):
            x, y, z = self.get_container().get_safe()
        return x, y, z

    def set_flip(self, x_flip=1, y_flip=1, z_flip=1):
        """Set if object coordinate system is flipped relative
        to container coordinate system.

        Input:
         x_flip, y_flip, z_flip: 1 if system is not flipped, otherwise -1

        Output:
         none
        """
        self.x_flip = x_flip
        self.y_flip = y_flip
        self.z_flip = z_flip

    def update_flip(self, x_flip=1, y_flip=1, z_flip=1):
        """Set if object coordinate system should be flippedcompared
        to current settings.

        Input:
         x_flip, y_flip, z_flip: 1 if coordinate system flip should stay the same,
         otherwise -1

        Output:
         x_flip, y_flip, z_flip: updated parameters
        """
        self.x_flip = self.x_flip * x_flip
        self.y_flip = self.y_flip * y_flip
        self.z_flip = self.z_flip * z_flip

    def get_flip(self):
        """Return if object coordinate system is flipped relative
        to container coordinate system.

        Input:
         none

        Output:
         x_flip, y_flip: 1 if system is not flipped, otherwise -1
        """
        return self.x_flip, self.y_flip, self.z_flip

    def set_correction(
        self,
        x_correction=1,
        y_correction=1,
        z_correction=1,
        z_correction_x_slope=0,
        z_correction_y_slope=0,
        z_correction_z_slope=0,
        z_correction_offset=0,
    ):
        """Set correction term if scaling for object coordinate system is
        slightly off relative to container coordinate system.

        Input:
         x_correction, y_correction, z_correction: Correction terms

        Output:
         none
        """
        self.x_correction = x_correction
        self.y_correction = y_correction
        self.z_correction = z_correction
        self.z_correction_x_slope = z_correction_x_slope
        self.z_correction_y_slope = z_correction_y_slope
        self.z_correction_z_slope = z_correction_z_slope
        self.z_correction_offset = z_correction_offset

    def update_correction(
        self,
        x_correction=1,
        y_correction=1,
        z_correction=1,
        z_correction_x_slope=0,
        z_correction_y_slope=0,
        xyz_correction_x_zero=0,
        xyz_correction_y_zero=0,
    ):
        """Multiply existing correction terms if scaling for object coordinate
        system is slightly off relative to container coordinate system
        with additional correction term.

        Input:
         x_correction, y_correction, z_correction z_correction_x_slope,
         xyz_correction_x_zero, xyz_correction_y_zero:
         Additional multiplicative correction terms

        Output:
         x_correction, y_correction, z_correction: updated parameters
        """
        self.x_correction = self.x_correction * x_correction
        self.y_correction = self.y_correction * y_correction
        self.z_correction = self.z_correction * z_correction
        #         self.z_correction_offset=self.z_correction_offset*z_correction_offset
        self.z_correction_x_slope = self.z_correction_x_slope * z_correction_x_slope
        self.z_correction_y_slope = self.z_correction_y_slope * z_correction_y_slope
        self.xyz_correction_x_zero = xyz_correction_x_zero
        self.xyz_correction_y_zero = xyz_correction_y_zero

        return self.x_correction, self.y_correction, self.z_correction

    def get_correction(self):
        """Get correction term if scaling for object coordinate system is
        slightly off relative to container coordinate system.

        Input:
         none

        Output:
         x_correction, y_correction, z_correction: Correction terms
        """
        return {
            "x_correction": self.x_correction,
            "y_correction": self.y_correction,
            "z_correction": self.z_correction,
            "z_correction_x_slope": self.z_correction_x_slope,
            "z_correction_y_slope": self.z_correction_y_slope,
            "z_correction_z_slope": self.z_correction_z_slope,
            "z_correction_offset": self.z_correction_offset,
        }

    ################################################################################
    #
    # Methods to move stage and focus
    #
    ################################################################################

    def microscope_is_ready(
        self,
        experiment,
        reference_object=None,
        load=True,
        use_reference=True,
        use_auto_focus=True,
        make_ready=True,
        trials=3,
        verbose=True,
    ):
        """Check if microscope is ready and setup up for data acquisition.

        Input:
         experiment: string with name of experiment as defined in microscope software

         reference_object: object used to set parfocality and parcentricity

         load: move objective into load position before moving stage

         use_reference: initialize reference position if not set

         make_ready: if True, make attempt to ready microscope, e.g. setup autofocus
         (Default: True)

         trials: maximum number of attempt to initialize microscope.
         Will allow user to make adjustments on microscope. (Default: 3)

         verbose: print debug messages (Default: True)

        Output:
         ready: True if microscope is ready for use, False if not
        """
        stage_id = self.get_stage_id()
        focus_drive_id = self.get_focus_id()
        auto_focus_id = self.get_auto_focus_id()
        objective_changer_id = self.get_objective_changer_id()
        safety_object_id = self.get_safety_id()
        microscope_object = self.get_microscope()

        test_ready_dict = OrderedDict(
            [
                (stage_id, []),
                (focus_drive_id, ["set_load"] if load else []),
                (objective_changer_id, ["set_reference"] if use_reference else []),
                (auto_focus_id, ["no_find_surface"] if use_auto_focus else []),
            ]
        )
        is_ready = microscope_object.microscope_is_ready(
            experiment=experiment,
            component_dict=test_ready_dict,
            focus_drive_id=focus_drive_id,
            objective_changer_id=objective_changer_id,
            safety_object_id=safety_object_id,
            reference_object=reference_object,
            load=load,
            make_ready=make_ready,
            trials=trials,
            verbose=verbose,
        )

        return is_ready["Microscope"]

    def move_to_abs_position(
        self, x=None, y=None, z=None, reference_object=None, load=True, verbose=True
    ):
        """Move stage to position x, y, z.

        Input:
         x, y: Position stage should move to in stage coordinates in mum.
         If None, stage will not move

         z: Focus position in mum. If not provided focus will not be changed,
         but autofocus might engage

         reference_object: object of type sample (ImagingSystem) used to correct
         for xyz offset between different objectives

         load: Move focus in load position before move. Default: True

         verbose: if True print debug information (Default = True)

        Output:
         x, y: New stage position

        If use_autofocus is set, correct z value according to new autofocus position.
        """
        if self.get_container() is None:
            return self.set_stage_position(
                x, y, z, reference_object=reference_object, load=load, verbose=verbose
            )
        else:
            return self.container.move_to_abs_position(
                x, y, z, reference_object=reference_object, load=load, verbose=verbose
            )

    def move_to_zero(self, load=True, verbose=True):
        """Move to center of object.

        Input:
         load: Move focus in load position before move. Default: True

         verbose: if True print debug information (Default = True)

        Output:
         x, y, z: new position in stage coordinates in mum
        """
        return self.move_to_xyz(x=0, y=0, z=0, load=load, verbose=verbose)

    def move_to_safe(self, load=True, verbose=True):
        """Move to safe position for object.

        Input:
         load: Move focus in load position before move. Default: True

         verbose: if True print debug information (Default = True)

        Output:
         x, y, z: new position in stage coordinates in mum
        """

        x, y, z = self.get_safe()
        if z is None:
            focusDriveObject = self.get_focus()
            z = focusDriveObject.get_load_position()

        return self.move_to_abs_position(x, y, z, load=load, verbose=verbose)

    def move_to_xyz(self, x, y, z=None, reference_object=None, load=True, verbose=True):
        """Move to position in object coordinates in mum.

        If use_autofocus is set, correct z value according to new autofocus position.

        Input:
         x, y, z; Position in object coordinates in mum.
         If z == None do not change z position

         reference_object: object of type sample (ImagingSystem) used to correct
         for xyz offset between different objectives

         load: Move focus in load position before move. Default: True

         verbose: if True print debug information (Default = True)

        Output:
         x_abs, y_abs, z_abs: new position in absolute stage coordinates in mum
        """
        x_abs, y_abs, z_abs = self.get_abs_pos_from_obj_pos(x, y, z, verbose=verbose)
        return self.move_to_abs_position(
            x_abs,
            y_abs,
            z_abs,
            reference_object=reference_object,
            load=load,
            verbose=verbose,
        )

    def move_to_r_phi(self, r, phi, load=True, verbose=True):
        """moves to position r [mum], phi [degree] in radial coordinates.
        (0,0) is the center of unit (e.g. well). 0 degrees is in direction of x axis.

        Input:
         r: radius in mum for radial coordinates (center = 0)

         phi: angle in degree for radial coordinates (right = 0 degree)

         load: Move focus in load position before move. Default: True

         verbose: if True print debug information (Default = True)

        Output:
         xStage, yStage: x, y position on stage in mum
        """
        phi_r = math.radians(phi)
        x = r * math.sin(phi_r)
        y = r * math.cos(phi_r)
        xStage, yStage, zStage = self.move_to_xyz(
            x, y, z=None, load=load, verbose=verbose
        )
        return xStage, yStage, zStage

    def move_delta_xyz(self, x, y, z=0, load=True, verbose=True):
        """Move in direction x,y,z in micrometers from current position.

        Input:
         x, y, z: step size in micrometers

         load: Move focus in load position before move. Default: True

         verbose: if True print debug information (Default = True)

        Output:
         xStage, yStage: x, y position on stage in mum
        """
        # get current stage position in absolute stage coordinates
        xStage, yStage, zStage = self.get_abs_position()
        xNew = xStage + x
        yNew = yStage + y
        zNew = zStage + z

        xNewStage, yNewStage, zNewStage = self.move_to_abs_position(
            xNew, yNew, zNew, load=load, verbose=verbose
        )
        return xNewStage, yNewStage, zNewStage

    def get_abs_position(self, stage_id=None, focus_id=None):
        """Return current stage position.
        Input:
         stage_id: string id to identify stage information is collected from

         focus_id: string id to identify focus drive information is collected from

        Output:
         absPos: absolute (x, y, z) position of stage in mum

        Positions are corrected for centricity and parfocality
        """
        # use stage_id and focus_id from most top level object
        # (e.g. use from well if available, not from plate)
        if stage_id is None:
            stage_id = self.stage_id
        if focus_id is None:
            focus_id = self.focus_id

        if self.get_container() is None:
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
    def calculate_slope_correction(self, x, y, verbose=True):
        """Calculate offset in z because of tilted sample.

        Input:
         x, y: x and y positions in object coordinates in um the correction is
         to be calculated

         verbose: if True print debug information (Default = True)

        Output:
         zSlopeCorrection: offset in z in um
        """
        if self.z_correction_z_slope == 0:
            zSlopeCorrection = 0
        else:
            zSlopeCorrection = (
                self.z_correction_offset
                - (x * self.z_correction_x_slope)
                - (y * self.z_correction_y_slope)
            ) / self.z_correction_z_slope

        if verbose:
            print(
                "\ncalculate_slope_correction in module samples.py for object ",
                self.get_name(),
            )
            print(" Calculate correction for position (in object coordinates): ", x, y)
            print(" z_correction_x_slope: ", self.z_correction_x_slope)
            print(" z_correction_y_slope: ", self.z_correction_y_slope)
            print(" z_correction_z_slope: ", self.z_correction_z_slope)
            print(" z_correction_offset: ", self.z_correction_offset)
            print(" Calculated slope correction offset: ", zSlopeCorrection)

        return zSlopeCorrection

    def get_obj_pos_from_container_pos(
        self, x_container, y_container, z_container, verbose=True
    ):
        """Calculate object coordinates from container coordinates.

        Input:
         x_container, y_container, z_container: container coordinates in mum

         verbose: if True print debug information (Default = True)

        Output:
         xObject, yObject, zObject: object coordinates in mum for container coordinates
        """
        # calculate translation
        # the origin of the object coordinate system in container coordinates
        # is given by (self.x_zero, self.y_zero, self.z_zero)
        x_offfset_container = x_container - self.x_zero
        y_offfset_container = y_container - self.y_zero
        z_offfset_container = z_container - self.z_zero

        # The coordinate system of the object might be stretched and flipped
        # compared to the container
        if self.y_flip == -1:
            pass

        xObject = x_offfset_container * self.x_flip * self.x_correction
        yObject = y_offfset_container * self.y_flip * self.y_correction
        zObject = (
            z_offfset_container * self.z_flip * self.z_correction
            - self.calculate_slope_correction(xObject, yObject, verbose=verbose)
        )

        # Output for debugging
        if verbose:
            if self.get_container() is None:
                container_name = "Stage Position"
            else:
                container_name = self.get_container().get_name()
            print(
                "\nResults from method get_obj_pos_from_container_pos(xContainer, yContainer, zContainer)"
            )  # noqa
            print(
                " "
                + self.get_name()
                + " coordinates calculated from "
                + container_name
                + " coordinates"
            )
            print(" Container coordinates: ", x_container, y_container, z_container)
            print(" Object coordinates: ", xObject, yObject, zObject)
            print(
                " ObjectObject.zero in container coordinates (flip not applied): ",
                self.x_zero,
                self.y_zero,
                self.z_zero,
            )
            print(
                " Object flip relative to container: ",
                self.x_flip,
                self.y_flip,
                self.z_flip,
            )

        return xObject, yObject, zObject

    def get_pos_from_abs_pos(self, x=None, y=None, z=None, verbose=True):
        """Return current position in object coordinates in mum.
        or transforms (x,y,z) from stage coordinates into object coordinates.
        This method is based on focus coordinates after drift correction.

        Input:
         x, y, z: Absolute stage coordinates in mum. If not given or None
         retrieve current stage position and express in object coordinates.

         verbose: if True print debug information (Default = True)

        Output:
         xPos, yPos, zPos: current or position passed in stage coordinate returned
         in object coordinates
        """
        if self.get_container() is None:
            if (x is None) or (y is None) or (z is None):
                xStage, yStage, zStage = self.get_corrected_stage_position()
            if x is None:
                x = xStage
            if y is None:
                y = yStage
            if z is None:
                z = zStage
            xPos = x - self.x_zero
            yPos = y - self.y_zero
            zPos = z - self.z_zero
        else:
            (
                xContainer,
                yContainer,
                zContainer,
            ) = self.get_container().get_pos_from_abs_pos(x, y, z, verbose=verbose)
            xPos, yPos, zPos = self.get_obj_pos_from_container_pos(
                xContainer, yContainer, zContainer, verbose=verbose
            )
        return (xPos, yPos, zPos)

    #####################################################################################
    #
    # Transformations from object coordinates to container coordinates
    #  Correction factors for this transformation are attached to the object
    #
    #####################################################################################
    def get_container_pos_from_obj_pos(
        self, x_object, y_object, z_object, verbose=True
    ):
        """Calculate container coordinates for given object coordinates.

        Input:
         x_object, y_object, z_object: Object coordinates in mum

         verbose: if True print debug information (Default = True)

        Output:
         x_container, y_container, z_container: Container coordinates in mum
         for object coordinates
        """
        # The coordinate system of the container might be stretched and fliped
        # compared to the object
        x_container_offset = x_object / self.x_correction * self.x_flip
        y_container_offset = y_object / self.y_correction * self.y_flip
        if z_object is None:
            z_container = None
        else:
            z_container_offset = z_object / self.z_correction * self.z_flip

        # calculate translation
        # the origin of the object coordinate system in container coordinates
        # is given by (self.x_zero, self.y_zero, self.z_zero)
        x_container = x_container_offset + self.x_zero
        y_container = y_container_offset + self.y_zero
        if z_object is not None:
            z_container = (
                z_container_offset + self.z_zero
            ) + self.calculate_slope_correction(
                x_container, y_container, verbose=verbose
            )

        # Output for debugging
        if verbose:
            if self.get_container() is None:
                containerName = "Stage Position"
            else:
                containerName = self.get_container().get_name()
            print(
                "\nResults from method get_container_pos_from_obj_pos(xObject, yObject, zObject)"
            )  # noqa
            print(
                " "
                + containerName
                + " coordinates calculated from "
                + self.get_name()
                + " coordinates"
            )
            print(" Object coordinates: ", x_object, y_object, z_object)
            print(" Container coordinates: ", x_container, y_container, z_container)
            print(
                " Object.zero in container coordinates (flip not applied): ",
                self.x_zero,
                self.y_zero,
                self.z_zero,
            )
            print(
                " Object flip relative to container: ",
                self.x_flip,
                self.y_flip,
                self.z_flip,
            )

        return x_container, y_container, z_container

    def get_abs_pos_from_obj_pos(self, x_object, y_object, z_object=None, verbose=True):
        """Convert object coordinates into stage coordinates.

        Input:
         x_object, y_object, z_object: Object coordinates in mum

         verbose: if True print debug information (Default = True)

        Output:
         x, y, z: coordinates in absolute stage coordinates in mum
        """
        x_container, y_container, z_container = self.get_container_pos_from_obj_pos(
            x_object, y_object, z_object, verbose
        )
        if self.get_container() is None:
            return x_container, y_container, z_container
        else:
            x_object = x_container
            y_object = y_container
            z_object = z_container
            (
                x_container,
                y_container,
                z_container,
            ) = self.get_container().get_abs_pos_from_obj_pos(
                x_object, y_object, z_object, verbose
            )
            return x_container, y_container, z_container

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
        """Set flag to enable the use of autofocus.

        Input:
         flag: if true, use autofocus

        Output:
         use_autofocus: status of use_autofocus
        """
        return self.container.set_use_autofocus(flag)

    def get_use_autofocus(self):
        """Return flag about autofocus usage

        Input:
         none

        Output:
         use_autofocus: boolean varaible indicating if autofocus should be used
        """
        return self.container.get_use_autofocus()

    def find_surface(self, trials=3, verbose=True):
        """Find cover slip using Definite Focus 2.

        Input:
         trials: number of trials before initialization is aborted

         verbose: if True, print debug messages (Default: True)

        Output:
         z: position of focus drive after find surface
        """
        return self.container.find_surface(
            reference_object=self.get_reference_object(), trials=trials, verbose=verbose
        )

    def store_focus(self, focus_reference_obj=None, trials=3, verbose=True):
        """Store actual focus position as offset from coverslip.

        Input:
         focus_reference_obj: Sample object used as reference for autofocus

         trials: number of trials before initialization is aborted

         verbose: if True, print debug messages (Default: True)

        Output:
         z: position of focus drive after store focus
        """
        if focus_reference_obj is None:
            focus_reference_obj = self
        return self.container.store_focus(
            focus_reference_obj, trials=trials, verbose=verbose
        )

    def recall_focus(self, cameraID, experiment):
        """Find stored focus position as offset from coverslip.

        Input:
         cameraID: sting with camera ID for experiment

         experiment: string with experiment name as defined in microscope software.

        Output:
         z: position of focus drive after recall focus
        """
        return self.container.recall_focus(cameraID, experiment)

    def live_mode_start(self, cameraID, experiment):
        """Start live mode in microscope software.

        Methods calls method of container instance until container has
        method implemented that actually performs action.

        Input:
         cameraID: string with unique camera ID

         experiment: string with experiment name as defined within microscope software
         If None use actual experiment.

        Output:
          none
        """
        self.container.live_mode_start(cameraID, experiment)

    def live_mode_stop(self, cameraID, experiment=None):
        """Stop live mode in microscope software.

        Methods calls method of container instance until container has
        method implemented that actually performs action.

        Input:
         cameraID: string with unique camera ID

         experiment: string with experiment name as defined within microscope software
         If None use actual experiment.

        Output:
         none
        """
        self.container.live_mode_stop(cameraID, experiment)

    def execute_experiment(
        self,
        experiment,
        cameraID,
        reference_object=None,
        file_path=None,
        meta_dict={},
        verbose=True,
    ):
        """Acquire single image using settings defined in microscope software
        and optionally save.


        Methods calls method of container instance until container has
        method implemented that actually performs action.

        Input:
         experiment: string with experiment name as defined within microscope software

         cameraID: string with unique camera ID

         reference_object: object of type sample (ImagingSystem) used to correct
         for xyz offset between different objectives

         file_path: filename with path to save image in original format.
         Default=None: no saving

         meta_dict: directory with additional meta data, e.g. {'aics_well':, 'A1'}

         focus: use autofocus (default = False)

         verbose: if True print debug information (Default = True)

        Output:
         image: ImageAICS object. At this moment they do not include the pixel data.
         Get pixel data with load_image.
        """
        # add name and type of object to meta data
        className = self.__class__.__name__
        if meta_dict is None:
            meta_dict = {}
        meta_dict.update(
            {
                "aics_objectContainerName": self.get_container().get_name(),
                "aics_type": className,
                "aics_containerType": self.get_container().__class__.__name__,
                "aics_barcode": self.get_barcode(),
            }
        )

        # add relative positions to meta data
        posX, posY, posZ = self.get_zero()
        meta_dict.update(
            {
                "aics_cellInColonyPosX": posX,
                "aics_cellInColonyPosY": posY,
                "aics_cellInColonyPosZ": posZ,
            }
        )

        # add correction terms to meta data
        corrections = self.get_correction()

        meta_dict.update(
            {
                "aics_xCorrection": corrections["x_correction"],
                "aics_yCorrection": corrections["y_correction"],
                "aics_zCorrection": corrections["z_correction"],
                "aics_zCorrectionXSlope": corrections["z_correction_x_slope"],
                "aics_zCorrectionYSlope": corrections["z_correction_y_slope"],
                "aics_zCorrectionZSlope": corrections["z_correction_z_slope"],
                "aics_zCorrectionOffset": corrections["z_correction_offset"],
            }
        )
        flip = self.get_flip()
        meta_dict.update(
            {"aics_xFlip": flip[0], "aics_yFlip": flip[1], "aics_zFlip": flip[2]}
        )

        image = self.container.execute_experiment(
            experiment,
            cameraID,
            reference_object=reference_object,
            file_path=file_path,
            meta_dict=meta_dict,
            verbose=verbose,
        )

        # use x, y, z values corrected for objective offset to calculate object
        # positions, otherwise they would be different for different objectives
        x_abs = image.get_meta("aics_imagePosX (centricity_corrected)")
        if x_abs is None:
            x_abs = image.get_meta("aics_imagePosX (absolute)")
        y_abs = image.get_meta("aics_imagePosY (centricity_corrected)")
        if y_abs is None:
            y_abs = image.get_meta("aics_imagePosY (absolute)")
        z_abs = image.get_meta("aics_imagePosZ (focality_drift_corrected)")
        if z_abs is None:
            z_abs = image.get_meta("aics_imagePosZ (absolute)")
        posX, posY, posZ = self.get_pos_from_abs_pos(
            x_abs, y_abs, z_abs, verbose=verbose
        )
        image.add_meta(
            {
                "aics_imageObjectPosX": posX,
                "aics_imageObjectPosY": posY,
                "aics_imageObjectPosZ": posZ,
            }
        )
        return image

    def acquire_images(
        self,
        experiment,
        cameraID,
        reference_object=None,
        file_path=None,
        pos_list=None,
        load=True,
        use_reference=True,
        use_auto_focus=False,
        meta_dict={},
        verbose=True,
    ):
        """Acquire image or set of images using settings defined in microscope software
        and optionally save.

        Methods calls method of container instance until container has
        method implemented that actually performs action.

        Input:
         experiment: string with experiment name as defined within microscope software

         cameraID: string with unique camera ID

         reference_object: object used to set parfocality and parcentricity,
         typically a well in plate

         file_path: string for filename with path to save image in original format
         or tuple with string to directory and list with template for file name.
         Default=None: no saving

         pos_list: coordinates if multiple images (e.g. tile) should be acquired.
         The coordinates are absolute stage positions in mum not corrected for
         objective offset.

         load: Move focus in load position before move. Default: True


         meta_dict: directory with additional meta data, e.g. {'aics_well':, 'A1'}

         use_autofocus: use autofocus (default = False)

         use_reference: use reference object (default = True)

         verbose: if True print debug information (Default = True)

        Output:
         images: list with ImageAICS objects. Does not include the pixel data.
         Get pixel data with load_image.
        """
        if pos_list is None:
            images = [
                self.execute_experiment(
                    experiment,
                    cameraID,
                    reference_object=reference_object,
                    file_path=file_path,
                    meta_dict=meta_dict,
                    verbose=verbose,
                )
            ]
        else:
            # xCurrent, yCurrent, zCurrent = self.get_abs_position()
            images = []
            for x, y, z in pos_list:
                # check if microscope is ready and initialize if necessary
                self.get_microscope().microscope_is_ready(
                    experiment=experiment,
                    component_dict={self.get_objective_changer_id(): []},
                    focus_drive_id=self.get_focus_id(),
                    objective_changer_id=self.get_objective_changer_id(),
                    safety_object_id=self.get_safety_id(),
                    reference_object=self.get_reference_object(),
                    load=load,
                    use_reference=use_reference,
                    use_auto_focus=use_auto_focus,
                    make_ready=True,
                    verbose=verbose,
                )
                self.move_to_abs_position(
                    x,
                    y,
                    z,
                    reference_object=reference_object,
                    load=load,
                    verbose=verbose,
                )
                newPath = file_path
                # Currently not needed - might be needed later for metadata extraction
                # if file_path != None:
                #     if isinstance(file_path, tuple):
                #         # file_path is tuple containing path to directory and template for file name  # noqa
                #         # use list() to make sure that newTemplate has a copy of file_path[1] and not only a reference  # noqa
                #         newTemplate = list(file_path[1])
                #         newTemplate.insert(-1, '_x'+ str(x) + '_y' + str(y) + \
                #             '_z' + str(z))
                #         newPath = (file_path[0], newTemplate)
                #     else:
                #         # file_path is single string with directory and filename
                #         splitPath=path.splitext(file_path)
                #         newPath=splitPath[0]+'_x'+ str(x) + '_y' + str(y) + '_z' \
                #             + str(z) + splitPath[1]
                # else:
                #     newPath=None
                if meta_dict is not None:
                    ###############################################################
                    #
                    # TODO: add relative pixel positions for stitching to meta data
                    #
                    ###############################################################
                    # meta_dict.update({'aics_objectName': self.get_name()'aics_xTile': xTileName, 'aics_yTile': yTileName})  # noqa
                    meta_dict.update({"aics_objectName": self.get_name()})
                    try:
                        meta_dict.update({"aics_positionNumber": self.position_number})
                    except AttributeError:
                        pass
                image = self.execute_experiment(
                    experiment,
                    cameraID,
                    reference_object,
                    newPath,
                    meta_dict=meta_dict,
                    verbose=verbose,
                )
                images.append(image)
        return images

    def _get_tile_params(self, prefs, tile_object="None", verbose=True):
        """Retrieve settings to define tiles from preferences.

        Input:
         prefs: dictionary with preferences for tiling

         verbose: print logging comments

        Output:
         tile_params: directory with parameters to calculate tile positions
        """
        # retrieve center of sample object. This will be the center of all tiles.
        center = self.get_abs_zero(verbose)

        # tile_object describes the object (e.g. colony, well) that should be
        # covered with tiles. This has to be translated into tile_type.
        # tile_type describes how the arrangement of tiles is calculated
        # different subclasses might allow additional options
        if tile_object == "NoTiling":
            tile_type = "none"
            tile_number = (1, 1)
            tile_size = (None, None)
            degrees = None
            percentage = 100
        elif tile_object == "Fixed":
            tile_type = "rectangle"
            tile_number = (prefs.get_pref("nColTile"), prefs.get_pref("nRowTile"))
            tile_size = (prefs.get_pref("xPitchTile"), prefs.get_pref("yPitchTile"))
            degrees = prefs.get_pref("RotationTile")
            percentage = 100
        elif tile_object == "Well":
            tile_type = "ellipse"
            percentage = prefs.get_pref("PercentageWell")
            well_diameter = self.get_diameter() * math.sqrt(percentage / 100.0)
            tile_size = (prefs.get_pref("xPitchTile"), prefs.get_pref("yPitchTile"))
            tile_number = (
                math.ceil(well_diameter / tile_size[0]),
                math.ceil(well_diameter / tile_size[1]),
            )
            degrees = prefs.get_pref("RotationTile")
        elif tile_object == "ColonySize":
            tile_type = "ellipse"
            tile_number = (None, None)
            tile_size = (prefs.get_pref("xPitchTile"), prefs.get_pref("yPitchTile"))
            degrees = None
            percentage = 100
        else:
            # Tile object is not implemented
            raise (ValueError, "Tiling object not implemented")

        tile_params = {
            "center": center,
            "tile_type": tile_type,
            "tile_number": tile_number,
            "tile_size": tile_size,
            "degrees": degrees,
            "percentage": percentage,
        }
        return tile_params

    def _compute_tile_positions_list(self, tile_params):
        """Get positions for tiles in absolute coordinates.
        Private method that is called from get_tile_positions_list().

        Input:
         tile_params: directory with parameters to calculate tile positions

        Output:
         tile_position_list: list with absolute positions for tiling
        """

        tileObject = CreateTilePositions(
            tile_type=tile_params["tile_type"],
            tile_number=tile_params["tile_number"],
            tile_size=tile_params["tile_size"],
            degrees=tile_params["degrees"],
        )
        tile_positions_list = tileObject.get_pos_list(tile_params["center"])
        return tile_positions_list

    def get_tile_positions_list(self, prefs, tile_type="NoTiling", verbose=True):
        """Get positions for tiles in absolute coordinates.
        Subclasses have additional tile_objects (e.g. ColonySize, Well).

        Input:
         prefs: dictionary with preferences for tiling

         tile_type: type of tiling.  Possible options:
          'NoTiling': do not tile
          'rectangle': calculate tiling to image a rectangular area
          'ellipse': cover ellipse (e.g. well) with tiles

         verbose: print debugging information

        Output:
         tile_position_list: list with absolute positions for tiling
        """
        tile_params = self._get_tile_params(prefs, tile_type, verbose=verbose)
        tile_positions_list = self._compute_tile_positions_list(tile_params)
        return tile_positions_list

    def load_image(self, image, get_meta):
        """Load image and meta data in object of type ImageAICS.

        Methods calls method of container instance until container has
        method implemented that actually performs action.

        Input:
         image: image object of class ImageAICS. Holds meta data at this moment,
         no image data.

         get_meta: if true, retrieve meta data from file.

        Output:
         image: image with data and meta data as ImageAICS class
        """
        if image.get_data() is None:
            image = self.container.load_image(image, get_meta)
        return image

    def get_images(self, load=True, get_meta=False):
        """Retrieve dictionary with images.

        Input:
         load: if true, will load image data before returning dictionary
         get_meta: if true, load meta data

        Output:
         imageDir: directory with images.
        """
        for imageName, imageObject in self.images:
            if imageObject.data is None:
                self.load_image(imageObject, get_meta=get_meta)
        return self.images

    def background_correction(self, uncorrected_image, settings):
        """Correct background using background images attached to object
        or one of it's superclasses.

        Input:
         image: object of class ImageAICS

        Output:
         corrected: object of class ImageAICS after background correction.
        """
        image = self.load_image(uncorrected_image, get_meta=True)
        image_data = uncorrected_image.get_data()
        if len(image_data.shape) == 2:
            image_data = image_data[:, :, numpy.newaxis]
        n_channels = image_data.shape[2]
        prefs = settings.get_pref("ChannelDefinitions")

        # iterate through channels and apply appropriate background correction
        for ch, channelPref in enumerate(prefs):
            if ch >= n_channels:
                continue
            background_name = channelPref.get("BackgroundCorrection")
            black_reference_name = channelPref.get("BlackReference")
            background = self.get_attached_image(background_name)
            black_reference = self.get_attached_image(black_reference_name)
            if black_reference is None or background is None:
                continue
            background_data = background.get_data()
            black_reference_data = black_reference.get_data()
            channel_data = image_data[:, :, ch]
            corrected_data = correct_background.illumination_correction(
                channel_data, black_reference_data, background_data
            )
            # corrected_data = channel_data
            image_data[:, :, ch] = corrected_data

        image.add_data(image_data)
        return image

    def tile_images(self, images, settings):
        """Create tile of all images associated with object.

        Input:
         images: list with image objects of class ImageAICS

        Output:
         tile: ImageAICS object with tile
        """
        # Information about tiling should be int he image meta data
        # (e.g. image positions)
        #         if not settings.get_pref('Tile', validValues = VALID_TILE):
        #             return images[(len(images)-1)/2] # return the x-0, y-0 image

        corrected_images = []
        # apply background correction

        ######################################################################
        #
        # ToDo: Catch if background image does not exist
        #
        ######################################################################
        for i, image in enumerate(images):
            if settings.get_pref("CorrectBackground"):
                # TODO: figure out if this can be a float with negative values
                corrected_images.append(self.background_correction(image, settings))
            else:
                corrected_images.append(self.load_image(image, get_meta=True))

        print("Done with Background correction")
        # create path and filename for tiled image
        folder_path = get_images_path(settings, sub_dir=settings.get_pref("TileFolder"))
        file_name_pattern = settings.get_pref("TileFileName")
        file_name = images[int(len(images) / 2)].create_file_name(file_name_pattern)
        image_output_path = path.normpath(path.join(folder_path, file_name))
        # use tiling method 'anyShape' for arbitrary shaped tile regions, use 'stack'
        # if tile region is a rectangle.
        # return _ list = [return_image, x_pos_list, y_pos_list]
        tiled_image, x_border_list, y_border_list = tile_images.tile_images(
            corrected_images,
            method="anyShape",
            output_image=True,
            image_output_path=image_output_path,
        )
        return [tiled_image, x_border_list, y_border_list]

    def add_attached_image(self, key, image):
        """Attach image to sample object.

        Input:
         key:  string with name of image (e.g. 'backgroundGreen_10x')
         image: image object of class ImageAICS

        Output:
         none
        """
        self.image_dict.update({key: image})

    def get_attached_image(self, key):
        """Retrieve attached image.

        Input:
         key:  string with name of image (e.g. 'backgroundGreen_10x')

        Output:
         image: image object of class ImageAICS
        """
        image = self.image_dict.get(key)
        if not (image):
            if self.container is not None:
                image = self.container.get_attached_image(key)
            else:
                # need to get a default image here
                print("Default Image")

        return image

    def remove_images(self, image):
        """Remove all images from microscope software display.

        Input:
         image: image taken with same camera as images to be removed

        Output:
         none
        """
        image = self.container.remove_images(image)
        return image

    ################################################################################
    #
    # Get hardware ids and microscope object used to image sample
    #
    ################################################################################

    def get_microscope(self):
        """Return object that describes connection to hardware.

        Input:
         none

        Output:
         microscope_object: object of class Microscope from module hardware
        """
        try:
            microscope_object = self.container.get_microscope()
        except AttributeError:
            microscope_object = None
        return microscope_object

    def get_stage_id(self):
        """Return id for stage used with this sample.

        Input:
         none

        Output:
         stage_id: id for stage used with this sample

        Searches through all containers until id is found
        """
        try:
            stage_id = self.stage_id
            if stage_id is None:
                stage_id = self.get_container().get_stage_id()
        except AttributeError:
            stage_id = None
        return stage_id

    def get_focus_id(self):
        """Return id for focus used with this sample.

        Input:
         none

        Output:
         focus_id: id for focus used with this sample

        Searches through all containers until id is found
        """
        try:
            focus_id = self.focus_id
            if focus_id is None:
                focus_id = self.get_container().get_focus_id()
        except AttributeError:
            focus_id = None
        return focus_id

    def get_auto_focus_id(self):
        """Return id for auto-focus used with this sample.

        Input:
         none

        Output:
         auto_focus_id: id for auto-focus used with this sample

        Searches through all containers until id is found
        """
        try:
            auto_focus_id = self.auto_focus_id
            if auto_focus_id is None:
                auto_focus_id = self.get_container().get_auto_focus_id()
        except AttributeError:
            auto_focus_id = None
        return auto_focus_id

    def get_objective_changer_id(self):
        """Return id for objective changer used with this sample.

        Input:
         none

        Output:
         objective_changer_id: id for objective changer used with this sample

        Searches through all containers until id is found
        """
        try:
            objective_changer_id = self.objective_changer_id
            if objective_changer_id is None:
                objective_changer_id = self.get_container().get_objective_changer_id()
        except AttributeError:
            objective_changer_id = None
        return objective_changer_id

    def get_safety_id(self):
        """Return id for safety object. Safety object describes travel safe areas
        for stage and objectives.

        Input:
         none

        Output:
         saftey_id: id for safety object used with this sample

        Searches through all containers until id is found
        """
        try:
            safety_id = self.safety_id
            if safety_id is None:
                safety_id = self.get_container().get_safety_id()
        except AttributeError:
            safety_id = None
        return safety_id

    def get_cameras_ids(self):
        """Return ids for cameras used with this sample.
        Searches through all containers until id is found.

        Input:
         none

        Output:
         cameras_ids: list with ids for cameras used with this sample
        """
        #########################################
        # TODO: camera_ids not implemented
        #############################################
        try:
            cameras_ids = self.cameras_ids
            if cameras_ids is None:
                cameras_ids = self.get_container().get_cameras_ids()
        except AttributeError:
            cameras_ids = None
        return cameras_ids

    def get_immersion_delivery_systems(self):
        """Return dictionary with objects that describes immersion water delivery system

        Input:
         none

        Output:
         immersion_delivery_systems: object of class Pump from module hardware
        """
        try:
            immersion_delivery_systems = self.container.get_immersion_delivery_systems()
        except AttributeError:
            immersion_delivery_systems = None
        return immersion_delivery_systems

    def get_immersion_delivery_system(self, name):
        """Return dictionary with objects that describes immersion water delivery system

        Input:
         name: string id for immersion water delivery system

        Output:
         immersion_delivery_system: object of class ImmersionDelivery
        """
        try:
            immersion_delivery_system = self.container.get_immersion_delivery_system(
                name
            )
        except (AttributeError, KeyError):
            immersion_delivery_system = None
        return immersion_delivery_system

    ################################################################################
    #
    # Handle meta data
    #
    ################################################################################

    def add_meta(self, meta_dict):
        """Update dictionary with meta data.

        Input:
         meta_dict: dictionary with meta data

        Output:
         updated_meta_dict: dictionary with additional meta data
        """
        if self.meta_dict is None:
            self.meta_dict = meta_dict
        else:
            self.meta_dict.update(meta_dict)
        return self.meta_dict

    def get_meta(self):
        """Return dictionary with meta data.

        Input:
         none

        Output:
         meta_dict: dictionary with meta data
        """
        try:
            meta_dict = self.meta_dict
        except AttributeError:
            meta_dict = None
        return meta_dict

    def add_meta_data_file(self, meta_data_file_object):
        """Add object that handles saving of meta data to disk.

        Input:
         meta_data_file_object: object of type meta_data_file

        Output:
         none
        """
        self.meta_data_file = meta_data_file_object

    def get_meta_data_file(self):
        """Return object that handles saving of meta data to disk.

        Input:
         none

        Output:
         meta_data_file_object: object of type meta_data_file.
         None if no meta data file exists
        """
        try:
            meta_data_file_object = self.meta_data_file
        except AttributeError:
            meta_data_file_object = None
        return meta_data_file_object


class Background(ImagingSystem):
    """Class for the background object associated with each plate.
    It will be used to do background correction.
    """

    def __init__(
        self,
        name="Background",
        center=[0, 0, 0],
        well_object=None,
        image=True,
        ellipse=[0, 0, 0],
        meta=None,
        x_flip=1,
        y_flip=-1,
        z_flip=1,
        x_correction=1,
        y_correction=1,
        z_correction=1,
        z_correction_x_slope=0,
        z_correction_y_slope=0,
    ):
        """Initialize class Background.

        Input:
         name: id for background

         image: True, if background should be imaged

         center: (x, y, z) center of background relative to well center in mum

         ellipse: (long axis, short axis, orientation) for ellipse around the background

         meta: additional meta data for background

         well_object: object of type Well the background is associated with

         x_flip, y_flip, z_flip: -1 if coordinate system of plate holder
         is flipped in respect to stage

         x_correction, y_correction, z_correction: correction factor
         if there is a discrepancy between the stage and the plate holder calibration

        Output:
         none
        """
        super(Background, self).__init__(
            container=well_object,
            name=name,
            image=True,
            x_zero=center[0],
            y_zero=center[1],
            z_zero=center[2],
            x_flip=x_flip,
            y_flip=y_flip,
            z_flip=z_flip,
            x_correction=x_correction,
            y_correction=y_correction,
            z_correction=z_correction,
            z_correction_x_slope=z_correction_x_slope,
            z_correction_y_slope=z_correction_y_slope,
        )


class PlateHolder(ImagingSystem):
    """Class to describe and navigate Stage.

    A Stage is the superclass for everything that can be imaged on a microscope
    (e.g. plates, wells, colonies, cells).

    A Stage has it's own coordinate system measured in mum and nows it's position
    in stage coordinates.

    A Stage can be moved to a position and acquire images.
    It will take track of the last image. To keep the image the user has to save it.
    """

    def __init__(
        self,
        name="PlateHolder",
        microscope_object=None,
        stage_id=None,
        focus_id=None,
        auto_focus_id=None,
        objective_changer_id=None,
        safety_id=None,
        immersion_delivery=None,
        cameraIdList=[],
        center=[0, 0, 0],
        x_flip=1,
        y_flip=1,
        z_flip=1,
        x_correction=1,
        y_correction=1,
        z_correction=1,
        z_correction_x_slope=0,
        z_correction_y_slope=0,
        x_safe_position=55600,
        y_safe_position=31800,
        z_safe_position=0,
    ):
        """Send all commands to microscope hardware

        Input:
         name: string with unique name for plate holder

         microscope_object: object of class Microscope from module hardware

         stage_id: id string for stage.

         focus_id: id string with name for focus drive

         auto_focus_id: id string with name for auto-focus

         objective_changer_id: id string with name for objective changer

         safety_id: id string for safety area that prevents objective damage
         during stage movement

         immersion_delivery: instance of class ImmersionDelivery

         center: [x,y,z] zero position of plate holder in respect to stage

         x_flip, y_flip, z_flip: -1 if coordinate system of plate holder
         is flipped in respect to stage

         x_correction, y_correction, z_correction: correction factor if there
         is a discrepancy between the stage and the plate holder calibration

         x_safe_position, y_safe_position, z_safe_position: position to start any
         movements without danger of objective or other collisions

        Output:
         none
        """
        self.immersion_delivery_system = immersion_delivery
        self.plates = {}  # will hold plate objects
        super(PlateHolder, self).__init__(
            container=None,
            name=name,
            x_zero=center[0],
            y_zero=center[1],
            z_zero=center[2],
            x_flip=x_flip,
            y_flip=y_flip,
            z_flip=z_flip,
            x_correction=x_correction,
            y_correction=y_correction,
            z_correction=z_correction,
            z_correction_x_slope=z_correction_x_slope,
            z_correction_y_slope=z_correction_y_slope,
            x_safe_position=x_safe_position,
            y_safe_position=y_safe_position,
            z_safe_position=z_safe_position,
            microscope_object=microscope_object,
            stage_id=stage_id,
            focus_id=focus_id,
            auto_focus_id=auto_focus_id,
            objective_changer_id=objective_changer_id,
            safety_id=safety_id,
        )

    def get_microscope(self):
        """Return object that describes connection to hardware.

        Input:
         none

        Output:
         microscope_object: object of class Microscope from module hardware
        """
        try:
            microscope_object = self.microscope
        except AttributeError:
            microscope_object = None
        return microscope_object

    def get_stage(self):
        """Return object that describes connection to microscope stage.

        Input:
         none

        Output:
         stage_object: object of class Stage from module hardware
        """
        try:
            stage_object = self.stage
        except AttributeError:
            stage_object = None
        return stage_object

    def get_focus(self):
        """Return object that describes connection to microscope focus drive.

        Input:
         none

        Output:
         focus_drive: object of class focusDrive from module hardware
        """
        return self.focus_drive

    def get_objective_changer(self):
        """Return object that describes objective changer and information
        about objectives.

        Input:
         none

        Output:
         objective_changer: object of class ObjectiveChanger from module hardware
        """
        return self.objective_changer

    def get_cameras(self):
        """Return objects that describes connection to cameras.

        Input:
         none

        Output:
         cameraObjects: object of class Camera from module hardware
        """
        return self.cameras

    def get_immersion_delivery_systems(self):
        """Return dictionary with objects that describes immersion water delivery system

        Input:
         none

        Output:
         pump_dict: dictionary of objects of class Pump from module hardware
        """
        return self.immersion_delivery_systems

    def get_immersion_delivery_system(self, name):
        """Return object that describes immersion water delivery system.

        Input:
         name: string id for immersion water delivery system

        Output:
         immersion_object: object of class ImmersionDelivery
        """
        immersion_dict = self.get_immersion_delivery_systems()
        immersion_object = immersion_dict[name]
        return immersion_object

    def add_plates(self, plateObjectDict):
        """Adds Plate to Stage.

        Input:
         name: string with unique name of plate

        Output:
         none
        """
        self.plates.update(plateObjectDict)

    def get_plates(self):
        """Return list will all plateObjects associated with plateholder.

        Input:
         none

        Output:
         plate_objects: list with plate objects
        """
        try:
            plate_objects = self.plates
        except AttributeError:
            plate_objects = []
        return plate_objects

    def add_slide(self, slide_object):
        """Adds Slide to PlateHolder.

        Input:
         slide_object: object of class slide

        Output:
         none
        """
        self.slide = slide_object

    def get_slide(self):
        """Return Slide object attached to PlateHolder

        Input:
         none

        Output:
         slide_object: Slide object
        """
        try:
            slide_object = self.slide
        except AttributeError:
            slide_object = []
        return slide_object

    def set_plate_holder_pos_to_zero(self, x=None, y=None, z=None):
        """Set current stage position as zero position for Stage in stage coordinates.

        Superclass for all sample related classes. Handles connection to microscope
        hardware through Microscope class in module hardware.

        Input:
         x, y, z: optional position in stage coordinates to set as zero position
         for Stage. If omitted, actual stage position will be used.

        Output:
         x, y, z: new zero position in stage coordinates
        """
        if (x is None) or (y is None) or (z is None):
            xStage, yStage, zStage = self.get_corrected_stage_position()
        if x is None:
            x = xStage
        if y is None:
            y = yStage
        if z is None:
            z = zStage

        self.set_zero(x_zero=x, y_zero=y, z_zero=z)
        return x, y, z

    def get_corrected_stage_position(self, verbose=False):
        """Get current position in stage coordinates and focus position in mum.

        Input:
         none

        Output:
         Stage position after centricity correction
         Focus position after drift corrections (as if no drift occurred)
        """
        # get position in x and y from stage and z focus drive
        positions_dict = self.get_microscope().get_information([self.stage_id])

        xy_positions = positions_dict[self.stage_id]["centricity_corrected"]
        if len(xy_positions) == 0:
            xy_positions = positions_dict[self.stage_id]["absolute"]
        z_positions = self.get_microscope().get_z_position(
            self.focus_id, self.auto_focus_id
        )
        if "focality_drift_corrected" in z_positions.keys():
            z = z_positions["focality_drift_corrected"]
        else:
            z = z_positions["absolute"]
        return xy_positions[0], xy_positions[1], z

    def get_abs_stage_position(self, stage_id=None, focus_drive_id=None):
        """Get current position in stage coordinates and focus position
        in mum corrected for parcentricity.

        Input:
         stage_id: id string for stage.

         focus_id: id string with name for focus drive

        Output:
         Real focus position not corrected for drift.
        """
        if stage_id is None:
            stage_id = self.stage_id
        if focus_drive_id is None:
            focus_drive_id = self.focus_id

        # get position in x and y from stage and z focus drive
        positions_dict = self.get_microscope().get_information(
            [stage_id, focus_drive_id]
        )
        x, y = positions_dict[self.stage_id]["centricity_corrected"]
        z_positions = self.get_microscope().get_z_position(
            focus_drive_id, self.auto_focus_id
        )
        z = z_positions["focality_corrected"]
        return x, y, z

    def set_stage_position(
        self,
        xStage,
        yStage,
        zStage=None,
        reference_object=None,
        load=True,
        verbose=True,
    ):
        """Move stage to position in stage coordinates in mum.

        Input:
         xStage, yStage, zStage: stage position in mum

         reference_object: object of type sample (ImagingSystem).
         Used to correct for xyz offset between different objectives

         load: Move focus in load position before move. Default: True

         verbose: if True print debug information (Default = True)

        Output:
         x, y, z: actual stage position

        If use_autofocus is set, correct z value according to new autofocus position.
        """
        x, y, z = self.microscope.move_to_abs_pos(
            stage_id=self.stage_id,
            focus_drive_id=self.focus_id,
            objective_changer_id=self.objective_changer_id,
            auto_focus_id=self.auto_focus_id,
            safety_id=self.safety_id,
            x_target=xStage,
            y_target=yStage,
            z_target=zStage,
            reference_object=reference_object,
            load=load,
            verbose=verbose,
        )

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
    #             message.operate_message('Press ok and wait until autofocus found coverslip.\nThan focus on {} to set autofocus reference.'.format(referenceObj.get_name()))  # noqa
    #             # start with autofocus to find coverslip.
    #             focusDriveObject = self.get_focus()
    #             if isinstance(error, AutofocusObjectiveChangedError):
    #                 z = focusDriveObject.focusDrive.recover_focus()
    #             referenceObj.find_surface()
    #             message.operate_message('Is focus ok?')
    #             referenceObj.store_focus(referenceObj)
    #             # update z_zero position for plate
    #             xPlate, yPlate, zPlate = referenceObj.get_pos_from_abs_pos(verbose=False)
    #             x_zero, y_zero, z_zero = referenceObj.get_zero()
    #             new_z_zero_plate = z_zero + zPlate
    #             xPlate, yPlate, z_zeroPlate = referenceObj.update_zero(z=new_z_zero_plate)
    #
    #         except AutofocusError as error:
    #             focus_reference_obj = error.focus_reference_obj
    #             message.operate_message(
    #                 'Autofocus returned with error:\n"{}"\nPlease focus on {}\nor cancel program.'.format(error.message, focus_reference_obj.get_name()),  # noqa
    #                 returnCode = False)
    #             focus_reference_obj.set_use_autofocus(False)
    #
    #             # update z_zero position for reference object
    #             xPlate, yPlate, zPlate = self.recover_hardware(
    #                 focus_reference_obj.get_pos_from_abs_pos, verbose=False)
    #             x_zero, y_zero, z_zero = self.recover_hardware(
    #                 focus_reference_obj.get_zero)
    #                 xPlate, yPlate, zPlate = self.recover_hardware(
    #                     focus_reference_obj.get_pos_from_abs_pos, verbose=False)
    #             x_zero, y_zero, z_zero = self.recover_hardware(
    #                 focus_reference_obj.get_zero)
    #
    #             new_z_zero_plate = z_zero + zPlate
    #             x_pate, y_plate, z_zero_plate = focus_reference_obj.update_zero(
    #                 z = new_z_zero_plate)

    def set_use_autofocus(self, flag):
        """Set flag to enable the use of autofocus.

        Input:
         flag: if true, use autofocus

        Output:
         use_autofocus: status of use_autofocus
        """
        microscope_object = self.get_microscope()
        microscope_object.set_microscope(
            {self.get_auto_focus_id(): {"use_auto_focus": flag}}
        )
        #         self.recover_hardware(self.focusDrive.set_use_autofocus, flag)
        return self.get_use_autofocus()

    def get_use_autofocus(self):
        """Return flag about autofocus usage

        Input:
         none

        Output:
         use_autofocus: boolean variable indicating if autofocus should be used
        """
        microscope_object = self.get_microscope()
        use_autofocus = microscope_object.get_information([self.get_auto_focus_id()])[
            self.get_auto_focus_id()
        ]["use"]
        #         use_autofocus = self.recover_hardware(self.focusDrive.get_use_autofocus)
        return use_autofocus

    def find_surface(self, reference_object=None, trials=3, verbose=True):
        """Find cover slip using Definite Focus 2 and store position
        focus_drive object

        Input:
         reference_object: Used for setting up of autofocus

         trials: number of trials before initialization is aborted

         verbose: if True, print debug messages (Default: True)

        Output:
         positions_dict: dictionary {'absolute': z_abs, 'focality_corrected': z_cor}
         with focus position in mum
        """
        # communication_object = self.get_microscope(
        #    )._get_control_software().connection
        # z = self.recover_hardware(self.focusDrive.find_surface, communication_object)
        microscope_object = self.get_microscope()
        microscope_object.initialize_hardware(
            initialize_components_ordered_dict={
                self.get_auto_focus_id(): ["find_surface"]
            },
            reference_object=reference_object,
            trials=trials,
            verbose=verbose,
        )
        positions_dict = microscope_object.get_information(
            components_list=[self.get_auto_focus_id()]
        )
        return positions_dict

    def store_focus(self, focus_reference_obj=None, trials=3, verbose=True):
        """Store actual focus position as offset from coverslip.

        Input:
         focus_reference_obj: Sample object used as reference for autofocus

         trials: number of trials before initialization is aborted

         verbose: if True, print debug messages (Default: True)

        Output:
         positions_dict: dictionary {'absolute': z_abs, 'focality_corrected': z_cor}
         with focus position in mum
        """
        microscope_object = self.get_microscope()
        microscope_object.initialize_hardware(
            initialize_components_ordered_dict={
                self.get_auto_focus_id(): ["no_find_surface", "no_interaction"]
            },
            reference_object=focus_reference_obj,
            trials=trials,
            verbose=verbose,
        )
        positions_dict = microscope_object.get_information(
            components_list=[self.get_auto_focus_id()]
        )
        return positions_dict

    def execute_experiment(
        self,
        experiment,
        cameraID,
        reference_object=None,
        file_path=None,
        meta_dict={
            "aics_well": "",
            "aics_barcode": "",
            "aics_xTile": "",
            "aics_yTile": "",
        },
        verbose=True,
    ):
        """Acquire image using settings defined in microscope software
        and optionally save.

        Input:
         experiment: string with experiment name as defined within microscope software

         cameraID: string with unique camera ID

         reference_object: object of type sample (ImagingSystem) used to correct for .
         xyz offset between different objectives

         file_path: filename with path to save image in original format.
         Default=None: no saving

         meta_dict: directory with additional meta data, e.g. {'aics_well':, 'A1'}

         verbose: if True print debug information (Default = True)

        Output:
          image: image of class ImageAICS

        Method adds cameraID to image.
        """
        # The method execute_experiment will send a command to the microscope
        # software to acquire an image.
        # experiment is the name of the settings used by the microscope software
        # to acquire the image. The method does not return the image, nor does it
        # save it. use PlateHolder.save_image to trigger the microscope software
        # to save the image.

        # Use an instance of Microscope from module hardware.
        microscope_instance = self.get_microscope()
        image = microscope_instance.execute_experiment(experiment)

        # retrieve information about camera and add to meta data
        image.add_meta({"aics_cameraID": cameraID})

        # retrieve information hardware status
        information_dict = microscope_instance.get_information()
        stage_z_corrected = microscope_instance.get_z_position(
            focus_drive_id=self.focus_id,
            auto_focus_id=self.auto_focus_id,
            reference_object=reference_object,
            verbose=verbose,
        )

        for key, position in information_dict[self.stage_id].items():
            if len(position) == 0:
                position = [None, None]
            image.add_meta({"aics_imagePosX (" + key + ")": position[0]})
            image.add_meta({"aics_imagePosX (" + key + ")": position[1]})

        # stage_z_corrected is dictionary with
        #     'absolute': absolute position of focus drive as shown in software
        #     'z_focus_offset': parfocality offset
        #     'focality_corrected': absolute focus position - z_focus_offset
        #     'auto_focus_offset': change in autofocus position
        #     'focality_drift_corrected': focality_corrected position -
        #         auto_focus_offset
        #     'load_position': load position of focus drive
        #     'work_position': work position of focus drive
        # with focus positions in um

        for key, position in stage_z_corrected.items():
            image.add_meta({"aics_imagePosZ (" + key + ")": position})

        # image.add_meta({'aics_imageAbsPosZ': stage_z_corrected['absolute']})
        # image.add_meta({'aics_imageAbsPosZ(focality_corrected)': stage_z_corrected['focality_corrected']})  # noqa
        # image.add_meta({'aics_imageAbsPosZ(z_focus_offset)': stage_z_corrected['z_focus_offset']})  # noqa
        # image.add_meta({'aics_imageAbsPosZ(focality_drift_corrected)': stage_z_corrected['focality_drift_corrected']})  # noqa
        # image.add_meta({'aics_imageAbsPosZ(auto_focus_offset)': stage_z_corrected['auto_focus_offset']})  # noqa
        # image.add_meta({'aics_imageAbsPosZ(load_position)': stage_z_corrected['load_position']})  # noqa
        # image.add_meta({'aics_imageAbsPosZ(work_position)': stage_z_corrected['work_position']})  # noqa

        if self.objective_changer_id in information_dict.keys():
            image.add_meta(
                {
                    "aics_objectiveMagnification": int(
                        information_dict[self.objective_changer_id]["magnification"]
                    ),
                    "aics_objectiveName": information_dict[self.objective_changer_id][
                        "name"
                    ],
                }
            )

        # add meta data imported into method
        image.add_meta(meta_dict)

        if None not in file_path:
            image = self.save_image(file_path, cameraID, image)
        return image

    def live_mode_start(self, camera_id, experiment=None):
        """Start live mode in microscope software.

        Input:
         camera_id: string with unique camera ID

         experiment: string with experiment name as defined within microscope software
         If None use actual experiment.

        Output:
          None
        """
        # Use an instance of a Camera from module hardware.
        # The method starts live mode for adjustments in the software.
        # It does not acquire an image
        # experiment is the name of the settings used by the microscope software
        # to acquire the image.

        # self.recover_hardware(self.microscope.live_mode, camera_id, experiment,
        #                       live=True)
        self.microscope.live_mode(camera_id, experiment, live=True)

    def live_mode_stop(
        self,
        camera_id,
        experiment=None,
    ):
        """Start live mode in microscopy software.

        Input:
         camera_id: string with unique camera ID

         experiment: string with experiment name as defined within microscope software
         If None use actual experiment.

        Output:
          None
        """
        # Use an instance of a Camera from module hardware.
        # The method stops live mode for adjustments in the software.
        # It does not acquire an image
        # experiment is the name of the settings used by the microscope software
        # to acquire the image.

        # self.recover_hardware(self.microscope.live_mode, camera_id, experiment,
        #                       live=False)
        self.microscope.live_mode(camera_id, experiment, live=False)

    def save_image(self, file_path, cameraID, image):
        """save original image acquired with given camera using microscope software

        Input:
         file_path: string with filename with path for saved image in original format
                    or tuple with path to directory and template for file name
         cameraID: name of camera used for data acquisition
         image: image of class ImageAICS

        Output:
         image: image of class ImageAICS

        """
        # if file_path is a string use this string
        # if file_path is a list create file name including meta data defined in list
        file_path_updated = image.create_file_name(file_path)
        # create new filename if filename already exists
        splitExt = path.splitext(file_path_updated)
        success = False
        counter = 0
        while not success:
            try:
                # Do Not need the file_path counter - Better for uploading it to FMS
                # file_pathCounter = splitExt[0] + '_{}'.format(counter) + splitExt[1]
                # image=self.cameras[cameraID].save_image(file_pathCounter, image)
                image = self.get_microscope().save_image(file_path_updated, image)
            except FileExistsError:
                # We need to update the file_path, otherwise there's an infinite loop
                counter = counter + 1
                file_path_updated = splitExt[0] + "_{}".format(counter) + splitExt[1]
            else:
                success = True

        meta_data = image.get_meta()
        try:
            self.get_meta_data_file().write_meta(meta_data)
        except Exception:
            MetaDataNotSavedError(
                "Sample object {} has not meta data file path.".format(self.get_name())
            )

        return image

    def load_image(self, image, get_meta):
        """load image and meta data in object of type ImageAICS

        Input:
         image: meta data as ImageAICS object. No image data loaded so far
         (if image data exists, it will be replaced)

        Output:
         image: image and meta data as ImageAICS object
        """
        image = self.get_microscope().load_image(image, get_meta)
        return image

    def remove_images(self, image):
        """Remove all images from microscope software display.

        Input:
         image: image taken with same camera as images to be removed

        Output:
         none
        """
        self.get_microscope().remove_images()


#######################################################


class ImmersionDelivery(ImagingSystem):
    """Class for pump and tubing to deliver immersion water to objective."""

    def __init__(
        self,
        name=None,
        plate_holder_object=None,
        safety_id=None,
        center=[0, 0, 0],
        x_flip=1,
        y_flip=1,
        z_flip=1,
        x_correction=1,
        y_correction=1,
        z_correction=1,
        z_correction_x_slope=0,
        z_correction_y_slope=0,
    ):
        """Initialize immersion water delivery system.

        Input:
         name: name of immersion delivery system (string)

         plate_holder_object: objet for plateHolder the system is attached to

         safety_id: id string for safety area that prevents objective damage
         during stage movement

         center: position of the water outlet in plateholder coordinates in mum

         x_flip, y_flip, z_flip: -1 if coordinate system of plate holder
         is flipped in respect to stage

         x_correction, y_correction, z_correction: correction factor if
         there is a discrepancy between the stage and the plate holder calibration

        Output:
         none
        """
        super(ImmersionDelivery, self).__init__(
            container=plate_holder_object,
            name=name,
            x_zero=center[0],
            y_zero=center[1],
            z_zero=center[2],
            x_correction=x_correction,
            y_correction=y_correction,
            z_correction=z_correction,
            z_correction_x_slope=z_correction_x_slope,
            z_correction_y_slope=z_correction_y_slope,
        )
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
    #          magnification: magnification of objective used with immersion delivery
    #          system as float
    #         '''
    #         return self.magnification

    def trigger_pump(self):
        """Trigger pump to deliver immersion water.

        Input:
         pumpID: string with name for pump to be used

        Output:
         none
        """
        self.recover_hardware(self.pump.trigger_pump)

    def get_water(self, objective_magnification=None, verbose=True, automatic=False):
        """Move objective to water outlet and add drop of water to objective.

        Input:
         objective_magnification: add water to specific objective with given
         magnification as float number. Keep current objective if set to None.

         verbose: if True print debug information (Default = True)

         automatic: if True, trigger pump, else show dialog

        Output:
         none
        """
        # get autofocus status and switch off autofocus
        autofocusUse = self.get_use_autofocus()
        self.set_use_autofocus(flag=False)

        # Get original position of stage and focus
        xPos, yPos, zPos = self.get_abs_position()
        # Move objective in load positionss
        focusObject = self.get_focus()
        self.recover_hardware(focusObject.goto_load)

        # Change objective
        if objective_magnification is not None:
            objective_changer_object = self.get_objective_changer()
            try:
                objective_changer_object.change_magnification(
                    objective_magnification,
                    self,
                    use_safe_position=True,
                    verbose=verbose,
                )
            except ObjectiveNotDefinedError as error:
                message.error_message(
                    'Please switch objective manually.\nError:\n"{}"'.format(
                        error.message
                    ),
                    returnCode=False,
                )
        # Move objective below water outlet, do not use autofocus
        storeAutofocusFlag = self.get_use_autofocus()
        self.set_use_autofocus(False)
        self.move_to_zero(load=True, verbose=verbose)
        self.set_use_autofocus(storeAutofocusFlag)
        # trigger pump
        if automatic:
            self.trigger_pump()
        else:
            message.operate_message(
                "Please add immersion water to objective.", returnCode=False
            )

        # Return to original position
        self.move_to_abs_position(
            xPos,
            yPos,
            zPos,
            reference_object=self.get_reference_object(),
            load=True,
            verbose=verbose,
        )

        # Switch autofocus back on if it was switch on when starting get_water
        self.set_use_autofocus(flag=autofocusUse)

    def add_counter(self, increment=1):
        """Increment counter.

        Input:
         increment: integer to increment counter value.
                     default = 1

        Output:
         count: counter setting after increment
        """
        self.count += increment
        return self.count

    def get_counter(self):
        """Get current counter value.

        Input:
         none

        Output:
         count: current counter value
        """
        try:
            count = self.count
        except AttributeError:
            count = None
        return count

    def reset_counter(self):
        """Reset counter value to 0.

        Input:
         none

        Output:
         count: current counter value
        """
        self.count = 0
        return self.count

    def set_counter_stop_value(self, counterStopValue):
        """Set value to stop counter and trigger pumping of immersion water.

        Input:
         none

        Output:
         counterStopValue: current counter stop value
        """
        self.counterStopValue = counterStopValue
        return self.counterStopValue

    def get_counter_stop_value(self):
        """Get value for counter to stop.

        Input:
         none

        Output:
         counter_stop_value: value for counter to stop
        """
        try:
            counter_stop_value = self.counterStopValue
        except AttributeError:
            counter_stop_value = None
        return counter_stop_value

    def count_and_get_water(
        self, objective_magnification=None, increment=1, verbose=True, automatic=False
    ):
        """Move objective to water outlet and add drop of water to objective.

        Input:
         objective_magnification: add water to specific objective with given
         magnification as float number. Keep current objective if set to None.

         increment: integer to increment counter value. Default = 1

         verbose: if True print debug information (Default = True)

         automatic: if True, trigger pump, else show dialog (Default = False)

        Output:
         counter: counter value after increment
        """
        # increase counter and compare to stop value
        counter = self.add_counter(increment=increment)

        if counter >= self.get_counter_stop_value():
            self.recover_hardware(
                self.get_water,
                objective_magnification=objective_magnification,
                verbose=verbose,
            )

        return counter


#######################################################


class Plate(ImagingSystem):
    """Class to describe and navigate Plate."""

    def __init__(
        self,
        name="Plate",
        plate_holder_object=None,
        center=[0, 0, 0],
        x_flip=1,
        y_flip=1,
        z_flip=1,
        x_correction=1,
        y_correction=1,
        z_correction=1,
        z_correction_x_slope=0,
        z_correction_y_slope=0,
        # reference_well = None
    ):
        """Initialize microwell plate

        Input:
         microscope_object: object of class Microscope from module hardware

         name: name of plate, typically barcode

         stageID: id string for stage. Stage can only be on one stage

         x_flip, y_flip, z_flip: -1 if coordinate system of plate holder
         is flipped in respect to stage

         x_correction, y_correction, z_correction: correction factor if there is a
         discrepancy between the stage and the plate holder calibration

         reference_well: name of reference well to get initial coordinates
         for reference position to correct parfocality

        Output:
         None
        """
        super(Plate, self).__init__(
            container=plate_holder_object,
            name=name,
            x_zero=center[0],
            y_zero=center[1],
            z_zero=center[2],
            x_flip=x_flip,
            y_flip=y_flip,
            z_flip=z_flip,
            x_correction=x_correction,
            y_correction=y_correction,
            z_correction=z_correction,
            z_correction_x_slope=z_correction_x_slope,
            z_correction_y_slope=z_correction_y_slope,
        )
        # self.name=name
        self.container = plate_holder_object
        self.wells = {}
        # reference well to get initial coordinates for reference position
        # to correct parfocality
        # self.reference_well = reference_well

    def set_barcode(self, barcode):
        """Set barcode for plate.

        Input:
         barcode: string with barcode

        Output:
         none
        """
        self.barcode = barcode

    def get_barcode(self):
        """Get barcode for plate.

        Input:
         none
        Output:
         barcode: string with barcode
        """
        try:
            barcode = self.barcode
        except Exception:
            barcode = None
        return barcode

    def add_wells(self, well_objects_dict):
        """Adds well to plate.

        Input:
         well_objects_dict: dictionary of form {'name': instance of Well class}

        Output:
         none
        """
        self.wells.update(well_objects_dict)

    def get_wells(self):
        """Return list with all instancess of class Well associated with plate.

        Input:
         none

        Output:
         well_objects: dict with well objects
        """
        try:
            well_objects = self.wells
        except Exception:
            well_objects = None
        return well_objects

    def get_wells_by_type(self, sample_type):
        """Return list with all Well Objects associated with plate that
        contain samples of given type.

        Input:
         sampleType: string or set with sample type(s)
         (e.g. {'Sample', 'Colony', 'Barcode'})

        Output:
         well_objects_of_type: dict with well objects
        """
        try:
            # create set of sampleTypes if only one same type was given as string
            if isinstance(sample_type, str):
                sample_type = {sample_type}
            # retrieve list of all well objects for plate
            well_objects = self.get_wells()
            well_objects_of_type = {
                well_name: well_object
                for well_name, well_object in well_objects.iteritems()
                if len(well_object.get_samples(sampleType=sample_type)) > 0
            }
        except Exception:
            well_objects_of_type = {}
        return well_objects_of_type

    def get_well(self, well_name):
        """Return wellOjbect for well with name wellName.

        Input:
         well_name: name of well in form 'A1'

        Output:
         well_object: object for one well with name wellName.
         None if no Well object with well_name exists
        """
        try:
            well_object = self.wells.get(well_name)
        except Exception:
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
    #         x=wellX+Plate.x_zero
    #         y=wellY+Plate.y_zero
    #         z=wellZ+Plate.z_zero
    #         return x, y, z

    def move_to_well(self, well):
        """moves stage to center of well

        Input:
         well: name of well in format 'A1'

        Output:
         xStage, yStage: x, y position on Stage in mum
        """
        wellX, wellY, wellZ = self.layout[well]
        xStage, yStage, zStage = self.set_plate_position(wellX, wellY, wellZ)
        return xStage, yStage, zStage

    def show(self, n_col=4, n_row=3, pitch=26, diameter=22.05):
        """show ImageAICS of plate layout

        Input:
         n_col: number of columns, labeled from 1 to n_col
         n_row: number of rows, labeled alphabetically
         pitch: distance between individual wells in mm
         diameter: diameter of Well in mm

        Output:
         none
        """
        draw_plate(n_col, n_row, pitch, diameter)


class Slide(ImagingSystem):
    """Class to describe and navigate slide."""

    def __init__(
        self,
        name="Slide",
        plate_holder_object=None,
        center=[0, 0, 0],
        x_flip=1,
        y_flip=1,
        z_flip=1,
        x_correction=1,
        y_correction=1,
        z_correction=1,
        z_correction_x_slope=0,
        z_correction_y_slope=0,
    ):
        """Initialize slide

        Input:
         plate_holder_object: object of class PlateHolder

         name: name of slide

         x_flip, y_flip, z_flip: -1 if coordinate system of plate holder
         is flipped in respect to stage

         x_correction, y_correction, z_correction: correction factor if
         there is a discrepancy between the stage and the plate holder calibration

        Output:
         none
        """
        super(Slide, self).__init__(
            container=plate_holder_object,
            name=name,
            x_zero=center[0],
            y_zero=center[1],
            z_zero=center[2],
            x_flip=x_flip,
            y_flip=y_flip,
            z_flip=z_flip,
            x_correction=x_correction,
            y_correction=y_correction,
            z_correction=z_correction,
            z_correction_x_slope=z_correction_x_slope,
            z_correction_y_slope=z_correction_y_slope,
        )

        self.container = plate_holder_object


class Well(ImagingSystem):
    """Class to describe and navigate single Well"""

    def __init__(
        self,
        name="Well",
        center=[0, 0, 0],
        diameter=1,
        plateObject=None,
        wellPositionNumeric=(1, 1),
        wellPositionString=("A", "1"),
        x_flip=1,
        y_flip=1,
        z_flip=1,
        x_correction=1,
        y_correction=1,
        z_correction=1,
        z_correction_x_slope=0,
        z_correction_y_slope=0,
    ):
        """Initialize class Well

        Input:
         name: string with well name in format 'A1'

         center: center position of well in plate coordinates in mum

         diameter: diameter of well in mum

         plateObject: object of type Plate the well is associated with

         wellPositionNumeric: (column, row) as integer tuple (e.g. (0,0) for well A1)

         wellPositionString: (row, column) as string tuple (e.g. ('A','1'))

         x_flip, y_flip, z_flip: -1 if coordinate system of plate holder
         is flipped in respect to stage

         x_correction, y_correction, z_correction: correction factor if there
         is a discrepancy between the stage and the plate holder calibration

        Output:
         none
        """
        super(Well, self).__init__(
            container=plateObject,
            name=name,
            x_zero=center[0],
            y_zero=center[1],
            z_zero=center[2],
            x_flip=x_flip,
            y_flip=y_flip,
            z_flip=z_flip,
            x_correction=x_correction,
            y_correction=y_correction,
            z_correction=z_correction,
            z_correction_x_slope=z_correction_x_slope,
            z_correction_y_slope=z_correction_y_slope,
        )

        self.samples = {}
        self.set_set_diameter(set_diameter=diameter)
        # As long as only a set diameter from specifications exists,
        # use this value for all calculation.
        # Replace this value with a measured value as soon as possible
        self.set_diameter(diameter)
        self.set_plate_position_numeric(position=wellPositionNumeric)
        self._failed_image = False

    def get_name(self):
        return self.name

    def failed_image(self):
        return self._failed_image

    def set_interactive_positions(self, tileImageData, location_list=None, app=None):
        """Opens up the interactive mode and lets user select colonies
        and return the list of coordinates selected

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
            new_colony = Colony(
                colony_name, center=(location[0], location[1], 0), well_object=self
            )
            colony_dict[colony_name] = new_colony
            colony_list.append(new_colony)
        self.add_colonies(colony_dict)
        return colony_list

    def get_well_object(self):
        """Get well object for subclass.

        Input:
         none

        Output:
         well_object: object for well
        """
        well_object = self
        return well_object

    def set_plate_position_numeric(self, position):
        """Set row and column number.

        Input:
         position: (column, row) as integer tuple (e.g. (0,0) for well A1

        Output:
         none
        """

        self.wellPositionNumeric = position

    def get_plate_position_numeric(self):
        """Get row and column number.

        Input:
         none

        Output:
         well_position_numeric: (column, row) as integer tuple (e.g. (0,0) for well A1
        """
        try:
            well_position_numeric = self.wellPositionNumeric
        except Exception:
            well_position_numeric = None
        return well_position_numeric

    def set_plate_position_string(self, position):
        """Set row and column as strings.

        Input:
         position: (row, column) as string tuple (e.g. ('A','1') for well A1)

        Output:
         none
        """
        self.wellPositionString = position

    def get_plate_position_string(self):
        """Get row and column as string.

        Input:
         none

        Output:
         well_position_string: (row, column) as string tuple
         (e.g. ('A','1') for well A1)
        """
        try:
            well_position_string = self.wellPositionString
        except AttributeError:
            well_position_string = None
        return well_position_string

    def set_set_diameter(self, set_diameter):
        """Set diameter from specifications or measured externally for well.

        Input:
         set_diameter: predefined diameter in mum
         (e.g from plate specifications or other instrument)

        Output:
         none
        """
        self.set_diameter = set_diameter

    def get_set_diameter(self):
        """Get well diameter for well as measured by external means.

        Input:
         none

        Output
         set_diameter: predefined diameter in mum
         (e.g from plate specifications or other instrument)
        """
        try:
            set_diameter = self.set_diameter
        except AttributeError:
            set_diameter = None
        return set_diameter

    def set_measured_diameter(self, measured_diameter):
        """Set diameter measured during experiment for well.

        Input:
         measured_diameter: diameter in mum as measured in find_well_center_fine

        Output:
         none
        """
        self.measured_diameter = measured_diameter
        # A measured diameter is always preferred over a diameter from specifications
        self.set_diameter(measured_diameter)

    def get_measured_diameter(self):
        """Get well diameter for well as measured in find_well_center_fine.

        Input:
         none

        Output
         measured_diameter: diameter in mum as measured in find_well_center_fine
        """
        try:
            measured_diameter = self.measured_diameter
        except AttributeError:
            measured_diameter = None
        return measured_diameter

    def set_diameter(self, diameter):
        """Set diameter for well. If measured diameter is available it will used,
        otherwise the set_diameter from specifications is used.

        Input:
         diameter: diameter in mum

        Output:
         none
        """
        self.diameter = diameter

    def get_diameter(self):
        """Get well diameter for well. If measured diameter is available it will used,
        otherwise the set_diameter from specifications is used.

        Input:
         none

        Output
         diameter: diameter in mum
        """
        try:
            diameter = self.diameter
        except AttributeError:
            diameter = None
        return diameter

    def calculate_well_correction(self, update=True):
        """Calculate correction factor for well coordinate system.

        We find position within the well (e.g. colonies) based on their distance
        from the center in mum. For some experiments we use coordinates measured
        on other systems. Their might be a slight difference in calibration for
        different systems. We will use the well diameter to calculate a compensation
        factor for these differences.

        Input:
         update: if True update correction factor and do not replace to keep
         earlier corrections in place

        Output:
         none
        """
        measured_diameter = self.get_measured_diameter()
        set_diameter = self.get_set_diameter()

        # if any of the diameters in not defined (None)
        # set correction factor to 1 and print warning
        if measured_diameter is None or set_diameter is None:
            correction = 1
        else:
            correction = measured_diameter / set_diameter

        # if update==True update correction factor
        # and do not replace to keep earlier corrections in place
        if update:
            self.update_correction(correction, correction)
        else:
            self.set_correction(correction, correction)

    def add_colonies(self, colonyObjectsDict):
        """Adds colonies to well.

        Input:
         colonyObjectsDict: dictionary of form {'name': colonyObject}

        Output:
         none
        """
        self.samples.update(colonyObjectsDict)

    def add_samples(self, sampleObjectsDict):
        """Adds samples to well.

        Input:
         sampleObjectsDict: dictionary of form {'name': sampleObject}

        Output:
         none
        """
        self.samples.update(sampleObjectsDict)

    def get_samples(self, sampleType={"Sample", "Barcode", "Colony"}):
        """Get all samples in well.

        Input:
         sampleType: list with types of samples to retrieve.
         At this moment {'Sample', 'Barcode', 'Colony'} are supported

        Output:
         samples: dict with sample objects
        """
        samples = {}
        try:
            for name, sampleObject in self.samples.iteritems():
                if type(sampleObject).__name__ in sampleType:
                    samples.update({name: sampleObject})
        except Exception:
            samples = None
        return samples

    def get_colonies(self):
        """Get all colonies in well.

        Input:
         none

        Output:
         colonies: dict with colony objects
        """
        try:
            colonies = self.get_samples(sampleType="Colony")
        except Exception:
            colonies = None
        return colonies

    def add_barcode(self, barcodeObjectsDict):
        """Adds barcode to well.

        Input:
         barcodeObjectsDict: dictionary of form {'name': barcodeObject}

        Output:
         none
        """
        self.samples.update(barcodeObjectsDict)

    def find_well_center_fine(
        self, experiment, well_diameter, cameraID, dictPath, verbose=True
    ):
        """Find center of well with higher precision.

        Method takes four images of well edges and calculates center.
        Will set origin of well coordinate system to this value.

        Input:
         experiment: string with imaging conditions defined within microscope software

         well_diameter: diameter of reference well in mum

         cameraID: string with name of camera

         dictPath: dictionary to store images

         angles: list with angles around well center to take images
         for alignment in degree

         diameterFraction: offset from well center to take alignment images
         as diameter devided by diameterFraction

         focus: use autofocus (default = True)

         verbose: if True print debug information (Default = True)

        Output:
         xCenter, yCenter, zCenter: Center of well in absolute stage coordinates in mum.
         z after drift correction (as if no drift had occured)

        """
        # user positioned right well edge in center of 10x FOW
        # acquire image and find edge coordinates
        name = self.get_name()
        file_path = dictPath + "/WellEdge_" + name + ".czi"
        meta_dict = {
            "aics_well": self.get_name(),
            "aics_barcode": self.get_barcode(),
            "aics_xTile": "-1",
            "aics_yTile": "0",
        }
        image = self.execute_experiment(
            experiment,
            cameraID,
            add_suffix(file_path, "-1_0"),
            meta_dict=meta_dict,
            verbose=verbose,
        )

        image = self.load_image(image, get_meta=True)

        pixelSize = image.get_meta("PhysicalSizeX")
        edgePosPixels = find_well_center.find_well_center_fine(
            image=image.data, direction="-x"
        )

        xPos_0 = edgePosPixels * pixelSize
        xEdge_0 = xPos_0 + image.get_meta("aics_imageAbsPosX")

        # move to right edge, take image, and find edge coordinates
        self.move_delta_xyz(well_diameter, 0, 0, load=False, verbose=verbose)
        meta_dict = {
            "aics_well": self.get_name(),
            "aics_barcode": self.get_barcode(),
            "aics_xTile": "1",
            "aics_yTile": "0",
        }
        image = self.execute_experiment(
            experiment,
            cameraID,
            add_suffix(file_path, "1_0"),
            meta_dict=meta_dict,
            verbose=verbose,
        )

        image = self.load_image(image, get_meta=True)
        edgePosPixels = find_well_center.find_well_center_fine(
            image=image.data, direction="x"
        )

        xPos_1 = edgePosPixels * pixelSize
        xEdge_1 = xPos_1 + image.get_meta("aics_imageAbsPosX")

        xRadius = (xEdge_1 - xEdge_0) / 2
        xCenter = xEdge_0 + xRadius

        # move to top edge, take image, and find edge coordinates
        self.move_delta_xyz(
            -well_diameter / 2.0, -well_diameter / 2.0, 0, load=False, verbose=verbose
        )
        meta_dict = {
            "aics_well": self.get_name(),
            "aics_barcode": self.get_barcode(),
            "aics_xTile": "0",
            "aics_yTile": "1",
        }
        image = self.execute_experiment(
            experiment,
            cameraID,
            add_suffix(file_path, "0_1"),
            meta_dict=meta_dict,
            verbose=verbose,
        )

        image = self.load_image(image, get_meta=True)
        edgePosPixels = find_well_center.find_well_center_fine(
            image=image.data, direction="-y"
        )
        yPos_0 = edgePosPixels * pixelSize
        yEdge_0 = yPos_0 + image.get_meta("aics_imageAbsPosY")

        # move to bottom edge, take image, and find edge coordinates
        self.move_delta_xyz(0, well_diameter, 0, load=False, verbose=verbose)
        meta_dict = {
            "aics_well": self.get_name(),
            "aics_barcode": self.get_barcode(),
            "aics_xTile": "0",
            "aics_yTile": "-1",
        }
        image = self.execute_experiment(
            experiment,
            cameraID,
            add_suffix(file_path, "0_-1"),
            meta_dict=meta_dict,
            verbose=verbose,
        )

        image = self.load_image(image, get_meta=True)
        edgePosPixels = find_well_center.find_well_center_fine(
            image=image.data, direction="y"
        )

        yPos_1 = edgePosPixels * pixelSize
        yEdge_1 = yPos_1 + image.get_meta("aics_imageAbsPosY")

        yRadius = (yEdge_1 - yEdge_0) / 2
        yCenter = yEdge_0 + yRadius

        zCenter = image.get_meta("aics_imageAbsPosZ(driftCorrected)")
        self.set_measured_diameter(measured_diameter=2 * numpy.mean([xRadius, yRadius]))
        print("Radius in x (length, x position): ", xRadius, xCenter)
        print("Radius in y (length, y position): ", yRadius, yCenter)
        print("Focus position: ", zCenter)
        return xCenter, yCenter, zCenter

    def get_tile_positions_list(self, prefs, tile_type="Well", verbose=True):
        """Get positions for tiles in absolute coordinates.

        Input:
         prefs: dictionary with preferences for tiling

         tile_type: type of tiling.  Possible options:
          'None': do not tile
          'Fixed': use fixed number of tiles
          'Well': use enough tiles to cover one well

         verbose: print debugging information

        Output:
         tile_position_list: list with absolute positions for tiling

         Other classes have additional tile_objects (e.g. ColonySize)
        """
        # retrieve common tiling parameters, than adjust them for wells if necessary
        try:
            tile_params = self._get_tile_params(prefs, tile_type, verbose=verbose)
            tile_positions_list = self._compute_tile_positions_list(tile_params)
        except Exception:
            tile_positions_list = None
        return tile_positions_list


################################################################


class Sample(ImagingSystem):
    """Class to describe and manipulate samples within a Well.
    Input:

    Output:
     None
    """

    def __init__(
        self,
        name="Sample",
        well_object=None,
        center=[0, 0, 0],
        experiment=None,
        x_flip=1,
        y_flip=-1,
        z_flip=1,
        x_correction=0,
        y_correction=0,
        z_correction=0,
        z_correction_x_slope=0,
        z_correction_y_slope=0,
    ):
        """Initialize class Sample

        Input:
         well: object of class Well that contains Sample

         center: center of sample relative to well center used for imaging
         in mum in form [x, y, z]

         experiment: string with name of experiment as defined in microscope software.
         Used to ImageAICS experiment

         sample: string with name of sample (optional)

         x_flip, y_flip, z_flip: -1 if coordinate system of plate holder
         is flipped in respect to stage

         x_correction, y_correction, z_correction: correction factor if
         there is a discrepancy between the stage and the plate holder calibration

        Output:
         none
        """
        super(Sample, self).__init__(
            container=well_object,
            name=name,
            x_zero=center[0],
            y_zero=center[1],
            z_zero=center[2],
            x_flip=x_flip,
            y_flip=y_flip,
            z_flip=z_flip,
            x_correction=x_correction,
            y_correction=y_correction,
            z_correction=z_correction,
            z_correction_x_slope=z_correction_x_slope,
            z_correction_y_slope=z_correction_y_slope,
        )
        self.microscope_object = self.well_object.microscope_object
        self.well = self.well_object.name
        self.plate_layout = self.well_object.plate_layout
        self.stageID = self.well_object.stageID

        self.center = center
        self.experiment = experiment


class Barcode(ImagingSystem):
    """Class to image and read barcode."""

    def __init__(
        self,
        name="Barcode",
        well_object=None,
        center=[0, 0, 0],
        x_flip=1,
        y_flip=-1,
        z_flip=1,
        x_correction=0,
        y_correction=0,
        z_correction=0,
        z_correction_x_slope=0,
        z_correction_y_slope=0,
    ):
        """Initialize class Well

        Input:
         name: string with name for barcode. Name has to be unique
         if multiple barcodes are attached to single well.

         well_object: object of class well of well the barcode is attached to

         x_flip, y_flip, z_flip: -1 if coordinate system of plate holder
         is flipped in respect to stage

         x_correction, y_correction, z_correction: correction factor if
         there is a discrepancy between the stage and the plate holder calibration

        Output:
         none
        """
        super(Barcode, self).__init__(
            container=well_object,
            name=name,
            x_zero=center[0],
            y_zero=center[1],
            z_zero=center[2],
            x_flip=x_flip,
            y_flip=y_flip,
            z_flip=z_flip,
            x_correction=x_correction,
            y_correction=y_correction,
            z_correction=z_correction,
            z_correction_x_slope=z_correction_x_slope,
            z_correction_y_slope=z_correction_y_slope,
        )
        # self.container = well_object

    def read_barcode_data_acquisition(
        self, experiment, cameraID, file_path, verbose=True
    ):
        """Take image of barcode.

        Input:
         experiment: string with name for experiment used in microscope software

         cameraID: unique ID for camera used to acquire image

         file_path: path to directory for alignment images

         verbose: if True print debug information (Default = True)

        Output:
         image: Image of barcode. Images will be used to decode barcode.
        """
        image = self.execute_experiment(
            experiment, cameraID, file_path=file_path, verbose=verbose
        )
        return image

    def read_barcode(self, experiment, cameraID, file_path, verbose=True):
        """Take image of barcode and return code.

        Input:
         experiment: string with imaging conditions as defined within microscope sofware

         cameraID: string with name of camera

         file_path: filename with path to store images

         verbose: if True print debug information (Default = True)

        Output:
         code: string encoded in barcode
        """
        image = self.read_barcode_data_acquisition(
            experiment, cameraID, file_path, verbose=verbose
        )
        image = self.load_image(image, get_meta=False)
        # code=read_barcode(image)
        code = "Not implemented"
        return code


class Colony(ImagingSystem):
    """Class to describe and manipulate colonies within a Well."""

    def __init__(
        self,
        name="Colony",
        center=[0, 0, 0],
        well_object=None,
        image=True,
        ellipse=[0, 0, 0],
        meta=None,
        x_flip=1,
        y_flip=-1,
        z_flip=1,
        x_correction=1,
        y_correction=1,
        z_correction=1,
        z_correction_x_slope=0,
        z_correction_y_slope=0,
    ):
        """Initialize class Colony.

        Input:
         name: id for colony

         image: True, if colony should be imaged

         center: (x, y, z) center of colony relative to well center in mum

         ellipse: (long axis, short axis, orientation) for ellipse around colony

         meta: additional meta data for colony

         well_object: object of type Well the colony is associated with

         x_flip, y_flip, z_flip: -1 if coordinate system of plate holder .
         is flipped in respect to stage

         x_correction, y_correction, z_correction: correction factor if
         there is a discrepancy between the stage and the plate holder calibration

        Output:
         None
        """
        super(Colony, self).__init__(
            container=well_object,
            name=name,
            image=True,
            x_zero=center[0],
            y_zero=center[1],
            z_zero=center[2],
            x_flip=x_flip,
            y_flip=y_flip,
            z_flip=z_flip,
            x_correction=x_correction,
            y_correction=y_correction,
            z_correction=z_correction,
            z_correction_x_slope=z_correction_x_slope,
            z_correction_y_slope=z_correction_y_slope,
        )
        #         self.container=well_object
        self.cells = {}

        #         self.name=name
        self.ellipse = ellipse
        #         self.xCenter, self.yCenter=center
        if meta:
            self.area = meta.Area
            self.meta = meta

    def set_cell_line(self, cell_line):
        """Set name of cell line.

        Input:
         cell_line: string with name of cell line

        Output:
         none
        """
        self.cell_line = cell_line

    def set_interactive_positions(self, imageData, location_list=None, app=None):
        """Opens up the interactive mode and lets user select cells and
        return the list of coordinates selected

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
        """Get name of cell line.

        Input:
         none

        Output:
         cell_line: string with name of cell line
        """
        try:
            cell_line = self.cell_line
        except AttributeError:
            cell_line = None
        return cell_line

    def set_clone(self, clone):
        """Set name of clone.

        Input:
         clone: string with name of clone

        Output:
         none
        """
        self.clone = clone

    def get_clone(self):
        """Get name of clone.

        Input:
         none

        Output:
         clone: string with name of clone
        """
        try:
            clone = self.clone
        except AttributeError:
            clone = None
        return clone

    def update_zero(self, images, verbose=True):
        """Update zero position of colony in well coordinates.

        Input:
         images: list with image objects of class ImageAICS

         verbose: if True print debug information (Default = True)

        Output:
         x, y, z: new zero position
         z after drift correction (as if no drift had happended)

        """
        # calculate median of all x, y, z-Positions
        xStagePositions = []
        yStagePositions = []
        zStagePositions = []
        for image in images:
            xStagePositions.append(image.get_meta("aics_imageAbsPosX"))
            yStagePositions.append(image.get_meta("aics_imageAbsPosY"))
            zStagePositions.append(image.get_meta("aics_imageAbsPosZ(driftCorrected"))
        xStageMedian = numpy.median(numpy.array(xStagePositions))
        yStageMedian = numpy.median(numpy.array(yStagePositions))
        zStageMedian = numpy.median(numpy.array(zStagePositions))

        x, y, z = self.get_container().get_pos_from_abs_pos(
            xStageMedian, yStageMedian, zStageMedian, verbose=verbose
        )
        self.set_zero(x, y, z)

    def add_cells(self, cell_objects_dict):
        """Adds cells to colony.

        This method will update cell line and clone information foe cells based
        on clone information (if available)

        Input:
         cell_objects_dict: dictionary of form {'name': cellObject}

        Output:
         none
        """
        self.cells.update(cell_objects_dict)

        for cell in cell_objects_dict.itervalues():
            cell.set_cell_line(self.get_cell_line())
            cell.set_clone(self.get_clone())

    def get_cells(self):
        """Get all cells in colony.

        Input:
         none

        Output:
         cells: list with cell objects
        """
        try:
            cells = self.cells
        except AttributeError:
            cells = None
        return cells

    def number_cells(self):
        return len(self.cells)

    def find_cells_cell_profiler(self, prefs, image):
        # TODO Add comments plus clean up
        """Find locations of cells to be imaged in colony and add them to colony.

        Input:
         prefs: preferences read with module preferences with criteria for cells

         image: ImageAICS object with colony

        Output:
         none
        """
        cell_name = self.name + "_0001"
        new_cell = Cell(name=cell_name, center=[0, 0, 0], colonyObject=self)
        cell_dict = {cell_name: new_cell}
        self.add_cells(cell_dict)

    def find_cells_distance_map(self, prefs, image):
        # TODO Add comments + clean up
        """Find locations of cells to be imaged in colony and add them to colony.

        Input:
        prefs: preferences read with module preferences with criteria for cells

        image: ImageAICS object with colony

        Output:
        none
        """
        from . import find_cells

        if image.get_data() is None:
            # TODO: Works only with Zeiss, not with 3i
            li = LoadImageCzi()
            li.load_image(image, True)
        if prefs.get_pref("Tile", validValues=VALID_TILE) != "Fixed":
            image.data = numpy.transpose(image.data, (1, 0, 2))
        cell_finder = find_cells.CellFinder(
            image, prefs.get_pref_as_meta("CellFinder"), self
        )
        cell_dict = cell_finder.find_cells()
        self.add_cells(cell_dict)

    def find_cell_interactive_distance_map(self, location):
        cell_dict = {}
        cell_name = self.name + "_{:04}".format(1)
        cell_to_add = Cell(
            name=cell_name, center=[location[0], location[1], 0], colonyObject=self
        )
        cell_dict[cell_name] = cell_to_add
        self.add_cells(cell_dict)
        return cell_to_add

    def execute_experiment(
        self,
        experiment,
        cameraID,
        reference_object=None,
        file_path=None,
        meta_dict=None,
        verbose=True,
    ):
        """Acquire single image using settings defined in microscope software
        and optionally save.

        Methods calls method of container instance until container has method
        implemented that actually performs action.

        Input:
         experiment: string with experiment name as defined within microscope software

         cameraID: string with unique camera ID

         reference_object: object of type sample (ImagingSystem) used to correct for
         xyz offset between different objectives

         file_path: filename with path to save image in original format.
         Default=None: no saving

         meta_dict: directory with additional meta data, e.g. {'aics_well':, 'A1'}

         focus: use autofocus (default = False)

         verbose: if True print debug information (Default = True)

        Output:
         image: ImageAICS object. At this moment they do not include the pixel data.
         Get pixel data with load_image.
        """
        clone = self.get_clone()
        cell_line = self.get_cell_line()
        meta_dict.update({"aics_colonyClone": clone, "aics_colonyCellLine": cell_line})
        image = self.container.execute_experiment(
            experiment,
            cameraID,
            reference_object=reference_object,
            file_path=file_path,
            meta_dict=meta_dict,
            verbose=verbose,
        )
        return image


position_number = 1


class Cell(ImagingSystem):
    """Class to describe and manipulate cells within a colony.
    Input:

    Output:
     None
    """

    def __init__(
        self,
        name="Cell",
        center=[0, 0, 0],
        colonyObject=None,
        x_flip=1,
        y_flip=1,
        z_flip=1,
        x_correction=1,
        y_correction=1,
        z_correction=1,
        z_correction_x_slope=0,
        z_correction_y_slope=0,
    ):
        """Initialize class Cell.

        Input:
         name: id for cell

         center: (x, y, z) center of cell relative to colony center in mum

         colonyObject: object of type Colony the cell is associated with

         x_flip, y_flip, z_flip: -1 if coordinate system of plate holder
         is flipped in respect to stage

         x_correction, y_correction, z_correction: correction factor if
         there is a discrepancy between the stage and the plate holder calibration

        Output:
         None
        """
        super(Cell, self).__init__(
            container=colonyObject,
            name=name,
            x_zero=center[0],
            y_zero=center[1],
            z_zero=center[2],
            x_flip=x_flip,
            y_flip=y_flip,
            z_flip=z_flip,
            x_correction=x_correction,
            y_correction=y_correction,
            z_correction=z_correction,
            z_correction_x_slope=z_correction_x_slope,
            z_correction_y_slope=z_correction_y_slope,
        )
        global position_number
        self.position_number = position_number
        position_number = position_number + 1

    def set_cell_line(self, cell_line):
        """Set name of cell line.

        Input:
         cell_line: string with name of cell line

        Output:
         none
        """
        self.cell_line = cell_line

    def get_cell_line(self):
        """Get name of cell line.

        Input:
         none

        Output:
         cell_line: string with name of cell line
        """
        try:
            cell_line = self.cell_line
        except AttributeError:
            cell_line = None
        return cell_line

    def set_clone(self, clone):
        """Set name of clone.

        Input:
         clone: string with name of clone

        Output:
         none
        """
        self.clone = clone

    def get_clone(self):
        """Get name of clone.

        Input:
         none

        Output:
         clone: string with name of clone
        """
        try:
            clone = self.clone
        except AttributeError:
            clone = None
        return clone

    def set_interactive_positions(self, image_data, location_list=[]):
        """Opens up the interactive mode and lets user select objects and
        return the list of coordinates selected

        Input:
        image_data: The pixel data of the image of the cell - numpy array

        Output:
        location_list: Returns the list of objects selected by the user
        """
        # Using pyqtgraph module
        interactive_plot = ImageLocationPicker(image_data, location_list)
        interactive_plot.plot_points("Cell Overview Image")
        return interactive_plot.location_list

    def execute_experiment(
        self,
        experiment,
        cameraID,
        reference_object=None,
        file_path=None,
        meta_dict={},
        verbose=True,
    ):
        """Acquire single image using settings defined in microscope software
        and optionally save.

        Methods calls method of container instance until container has
        method implemented that actually performs action.

        Input:
         experiment: string with experiment name as defined within microscope software

         cameraID: string with unique camera ID

         reference_object: object of type sample (ImagingSystem) used to correct for
         xyz offset between different objectives

         file_path: filename with path to save image in original format.
         Default=None: no saving

         meta_dict: directory with additional meta data, e.g. {'aics_well':, 'A1'}

         verbose: if True print debug information (Default = True)

        Output:
         image: ImageAICS object. At this moment they do not include the pixel data.
         Get pixel data with load_image.
        """
        if meta_dict is None:
            meta_dict = {}
        meta_dict.update(
            {
                "aics_cellClone": self.get_clone(),
                "aics_cellCellLine": self.get_cell_line(),
            }
        )
        image = self.container.execute_experiment(
            experiment,
            cameraID,
            reference_object=reference_object,
            file_path=file_path,
            meta_dict=meta_dict,
            verbose=verbose,
        )

        return image


#################################################################
#
# Functions for testing of module
#
#################################################################


def create_microscope(software, prefs):
    """Create a microscope object.

    Input:
     software: sting with name of software that controlls microscope
     (e.g. 'ZEN Blue', 'Test')

     prefs: dictionary with preferences

    Output:
     microscope: microscope object
    """
    # create microscope
    # we need module hardware only for testing
    # import hardware_control as hw  # noqa

    # get object to connect to software based on software name
    connectObject = hardware_control.ControlSoftware(software)
    # create microscope components
    # create two sCMOS cameras
    c1 = hardware_control.Camera(
        "Camera1 (Back)",
        pixel_size=(6.5, 6.5),
        pixel_number=(2048 / 2, 2048 / 2),
        pixel_type=numpy.int32,
        name="Orca Flash 4.0V2",
        detector_type="sCMOS",
        manufacturer="Hamamatsu",
    )

    c2 = hardware_control.Camera(
        "sCMOS_mCherry",
        pixel_size=(6.5, 6.5),
        pixel_number=(2048 / 2, 2048 / 2),
        pixel_type=numpy.int32,
        name="Orca Flash 4.0V2",
        detector_type="sCMOS",
        manufacturer="Hamamatsu",
    )

    s = hardware_control.Stage("TestStage")
    fd = hardware_control.FocusDrive("Focus")
    oc = hardware_control.ObjectiveChanger("Nosepiece", n_positions=6)
    p = hardware_control.Pump(
        pump_id="Immersion", seconds=1, port="COM1", baudrate=19200
    )

    # Create safety object to avoid hardware damage and add to Microscope
    # if multiple overlapping safety areas are created,
    # the minimum of all allowed z values is selected
    # stage will not be allowed to travel outside safety area
    safetyObject_immersion = hardware_control.Safety("SafeArea_immersion")
    stage_area = [(10, 10), (10, 90), (90, 90), (90, 10)]
    safetyObject_immersion.add_safe_area(stage_area, "Stage", 9000)
    pump_area = [(30, 10), (40, 10), (40, -5), (30, -5)]
    safetyObject_immersion.add_safe_area(pump_area, "Pump", 100)

    safetyObject_plateHolder = hardware_control.Safety("SafeArea_plateHolder")
    stage_area = [(10, 10), (10, 90), (90, 90), (90, 10)]
    safetyObject_plateHolder.add_safe_area(stage_area, "PlateHolder", 9000)

    # create microscope and add components
    m = hardware_control.Microscope(
        name="Test Microscope",
        control_software_object=connectObject,
        safeties=[safetyObject_immersion, safetyObject_plateHolder],
        microscope_components=[fd, s, oc, c1, c2, p],
    )

    return m


def create_plate_holder_manually(m, prefs):
    """Create plate holder manually instead of using setupAutomaiton.
    Not tested"""
    # create plate holder and fill with plate, wells, colonies, cells, & water delivery
    # create plate holder and connect it to microscope
    ph = PlateHolder(
        name="PlateHolder",
        microscope_object=m,
        stage_id="TestStage",
        focus_id="Focus",
        objective_changer_id="Nosepiece",
        safety_id="SafeArea_plateHolder",
        center=[0, 0, 0],
        x_flip=1,
        y_flip=1,
        z_flip=1,
        x_correction=1,
        y_correction=1,
        z_correction=1,
        z_correction_x_slope=0,
        z_correction_y_slope=0,
    )
    meta_data_file_path = get_meta_data_path(prefs)
    meta_data_format = prefs.get_pref("MetaDataFormat")
    meta_data_file_object = MetaDataFile(meta_data_file_path, meta_data_format)
    ph.add_meta_data_file(meta_data_file_object)

    print("PlateHolder created")

    # create immersion delivery system as part of PlateHolder and add to PlateHolder
    pumpObject = hardware_control.Pump("Immersion")
    m.add_microscope_object(pumpObject)

    # Add pump to plateHolder
    im = ImmersionDelivery(name="Immersion", plate_holder_object=ph, center=[0, 0, 0])
    #     ph.add_immersionDelivery(immersion_delivery_systemsDict={'Water Immersion': im})
    ph.immersion_delivery_system = im

    # create Plate as part of PlateHolder and add it to PlateHolder
    p = Plate(
        name="Plate",
        plate_holder_object=ph,
        center=[6891, 3447, 9500],
        x_flip=1,
        y_flip=1,
        z_flip=1,
        x_correction=1,
        y_correction=1,
        z_correction=1,
        z_correction_x_slope=0,
        z_correction_y_slope=0,
    )
    p.set_barcode(1234)
    ph.add_plates(plateObjectDict={"Test Plate": p})
    print("Plate created and added to PlateHolder")

    # create Wells as part of Plate and add to Plate
    plate_layout = create_plate("96")

    d5 = Well(
        name="D5",
        center=plate_layout["D5"],
        diameter=plate_layout["well_diameter"],
        plateObject=p,
        wellPositionNumeric=(4, 5),
        wellPositionString=("D", "5"),
        x_flip=1,
        y_flip=1,
        z_flip=1,
        x_correction=1,
        y_correction=1,
        z_correction=1,
        z_correction_x_slope=0,
        z_correction_y_slope=0,
    )
    d6 = Well(
        name="D6",
        center=plate_layout["D6"],
        diameter=plate_layout["well_diameter"],
        plateObject=p,
        wellPositionNumeric=(5, 5),
        wellPositionString=("D", "6"),
        x_flip=1,
        y_flip=1,
        z_flip=1,
        x_correction=1,
        y_correction=1,
        z_correction=1,
        z_correction_x_slope=0,
        z_correction_y_slope=0,
    )

    wellDict = {"D5": d5, "D6": d6}
    p.add_wells(wellDict)
    print("Wells created and added to Plate")

    # create Colonies as part of Wells and add to Wells
    meta_dict = {
        "ImageNumber": 134,
        "ColonyNumber": 1,
        "WellRow": "C",
        "WellColumn": 3,
        "Center_X": 800.16150465195233,
        "Center_Y": -149.09623005031244,
        "Area": 3854.0,
        "ColonyMajorAxis": 137.58512073673762,
        "ColonyMinorAxis": 49.001285888466853,
        "Orientation": 50.015418444799394,
        "WellCenter_ImageCoordinates_X": 3885.1862986357551,
        "WellCenter_ImageCoordinates_Y": 4153.2891461366862,
        "Well": "C3",
    }
    meta = pandas.DataFrame(meta_dict, index=[804])
    # meta data not checked for compatibility with settings below
    c1d5 = Colony(
        name="C1D5",
        image=True,
        center=[0, 0, 0],
        ellipse=[1000, 1000, 1000],
        meta=meta,
        well_object=d5,
        x_flip=1,
        y_flip=-1,
        z_flip=1,
        x_correction=1,
        y_correction=1,
        z_correction=1,
        z_correction_x_slope=0,
        z_correction_y_slope=0,
    )
    c1d5.set_cell_line("AICS0")
    c1d5.set_clone("123")
    c2d5 = Colony(
        name="C2D5",
        image=True,
        center=[50, 50, 50],
        ellipse=[1000, 1000, 1000],
        meta=meta,
        well_object=d5,
        x_flip=1,
        y_flip=-1,
        z_flip=1,
        x_correction=1,
        y_correction=1,
        z_correction=1,
        z_correction_x_slope=0,
        z_correction_y_slope=0,
    )
    c2d5.set_cell_line("AICS0")
    c2d5.set_clone("123")

    colonyDict_d5 = {"C1D5": c1d5, "C2D5": c2d5}
    d5.add_colonies(colonyDict_d5)

    print("Colonies created and added to Wells")

    # create cells and add to colonies
    c1d5_1 = Cell(
        name="c1d5_1",
        center=[0, 0, 0],
        colonyObject=c1d5,
        x_flip=1,
        y_flip=1,
        z_flip=1,
        x_correction=1,
        y_correction=1,
        z_correction=1,
        z_correction_x_slope=0,
        z_correction_y_slope=0,
    )

    cellsDict_c1d5 = {"c1d5_1": c1d5_1}
    c1d5.add_cells(cellsDict_c1d5)

    print("\n______________________________________________\n")

    print("Cells created and added to Colonies:\n")

    print("Number of cells in colony ", c1d5.name, ": ", c1d5.number_cells())

    return c1d5


def test_samples(
    software,
    file_path,
    test=["find_well_center", "find_well_center_fine", "move_to_zero"],
):
    """Test suite to test module with Zeiss SD hardware or test hardware.

    Input:
     software: software to connect to hardware (e.g. ''ZEN Blue', 'Test)

     file_path: path to store test images

     test: list with tests to perform

    Output:
     Success: True when test was passed
    """
    import setup_samples
    from ..preferences import Preferences

    # get all information about experiment
    prefs = Preferences(get_prefs_path())

    # create microscope
    m = create_microscope(software, prefs)
    # setup microscope
    m = setup_samples.setup_microscope(prefs)

    ph = setup_samples.setup_plate(prefs, colony_file=None, microscope_object=m)

    # TODO: check with Winfried this is the right way to get cell out of colony
    c1d5_1 = create_plate_holder_manually(m, prefs).get_cells()["c1d5_1"]

    # test background correction
    if "test_background_correction" in test:
        c1d5_1.acquire_image(
            experiment="ScanCells.czexp", cameraID="sCMOS_mCherry", file_path=None
        )

    # test water delivery system for immersion water
    if "test_immersion_delivery" in test:
        # TODO: this function should be part of pump.initialize() in hardware_control.py
        # set up immersion delivery system
        # set debugging level
        verbose = True
        print("\n\nSet-up water immersion system (setup_immersion_system)")

        # get immersion delivery system object
        # name = prefs.get_pref('NameImmersionSystem')
        immersion_delivery = ph.immersion_delivery_system

        # move objective under immersion water outlet and assign position of outlet
        # to immersion_delivery object
        focusObject = ph.get_focus()
        loadPos = focusObject.get_load_position()

        # get communication object
        communication_object = ph.microscope._get_control_software().connection

        # Make sure load position is defined for focus drive
        if loadPos is None:
            message.operate_message("Move objective to load position.")
            focusObject.define_load_position(communication_object)
            loadPos = focusObject.get_load_position()

        xPos = 50
        yPos = 70

        # Execute experiment before moving stage to ensure that proper objective
        # (typically 10x) in in place to avoid collision.
        experiment = "ExperimentSetupImmersionSystem"
        cameraID = "sCMOS_mCherry"

        immersion_delivery.execute_experiment(
            experiment, cameraID, file_path=None, verbose=verbose
        )
        immersion_delivery.move_to_abs_position(
            xPos,
            yPos,
            loadPos,
            reference_object=immersion_delivery.get_reference_object(),
            load=True,
            verbose=verbose,
        )

        # take image of water outlet
        immersion_delivery.live_mode_start(cameraID, experiment)
        message.operate_message(
            "Move objective under water outlet.\nUse flashlight from below stage to see outlet."
        )  # noqa
        immersion_delivery.live_mode_stop(cameraID, experiment)

        # drop objective to load position and store position for water delivery
        # water will always be delivered with objective in load position
        # to avoid collision
        focusObject.goto_load(communication_object)
        immersion_delivery.set_zero(verbose=verbose)

        # move away from delivery system to avoid later collisions
        immersion_delivery.move_to_safe()
        magnification = 100
        immersion_delivery.magnification = magnification

        # test immersion delivery system

    # create Plate object
    # get plate object
    # get dictionary of all plates associated with plate holder
    plate_objects = ph.get_plates()
    # get object for plate with name plateName, typically the barcode
    p = plate_objects["Test Plate"]

    # test retrieve wells with given content
    if "test_get_by_type" in test:
        for type in ["Colony", "Barcode", "Sample"]:
            print("Wells of type ", type, ": ", p.get_wells_by_type(type))

    # move stage to cells and acquire image
    if "image_cells" in test:
        # enable autofocus
        p.set_use_autofocus(True)

        # iterate through wells
        for well_name, well_object in p.wells.iteritems():
            print("Well: ", well_name)
            print("Zero well position: ", well_object.get_zero())
            print(
                "Well position in stage coordinates after move: ",
                well_object.move_to_zero(),
            )
            message.operate_message("Check if position is correct")
            for col_name, col_object in well_object.get_colonies().iteritems():
                print(".Colony: ", col_name)
                print("Zero colony position: ", col_object.get_zero())
                print(col_object.move_to_zero())
                message.operate_message("Check if position is correct")
                for cell_name, cell_object in col_object.cells.iteritems():
                    # get preferences for cell imaging
                    cell_prefs = prefs.get_pref_as_meta("ScanCells")
                    print("...Well: ", well_name)
                    print("...Colony: ", col_name)
                    print("...Cell: ", cell_name)
                    print("Zero cell position: ", cell_object.get_zero())
                    print(cell_object.move_to_zero())
                    message.operate_message("Check if position is correct")
                    meta_dict = {
                        "aics_well": well_name,
                        "aics_colony": col_name,
                        "aics_cell": cell_name,
                        "aics_barcode": p.get_name(),
                        "aics_xTile": 0,
                        "aics_yTile": 0,
                    }
                    # acquire and save image using test.czexp settings
                    # and save as .czi file
                    image = cell_object.execute_experiment(
                        experiment="test.czexp",
                        cameraID="Camera1 (Back)",
                        file_path=file_path + "test2.czi",
                        meta_dict=meta_dict,
                    )
                    print("Image acquired and saved at ", file_path + "test2.czi")
                    print("Meta data: ", image.get_meta())

                    # repeat experiment
                    # assemble file name based on pattern stored in preferences
                    template = cell_prefs.get_pref("FileName")
                    template.insert(-1, cell_name)
                    fileName = image.create_file_name(template)
                    fileDirPath = path.join(file_path, fileName)
                    image = cell_object.execute_experiment(
                        experiment="test.czexp",
                        cameraID="Camera1 (Back)",
                        file_path=fileDirPath,
                        meta_dict=meta_dict,
                    )
                    print("Image acquired and saved at ", fileDirPath)
                    print("Meta data: ", image.get_meta())

    return True


################################################################################
#
# Start main
#
################################################################################


if __name__ == "__main__":
    # import libraries used for testing only
    import argparse

    # define file_path to store results
    file_path = "D:\\Winfried\\testImages\\"
    #     file_path="F:\\Winfried\\Testdata\\"
    if getpass.getuser() == "mattb":
        file_path = "C:/Users/matthewbo/Git/microscopeautomation/data/testImages"
    #     file_path="/Users/winfriedw/Documents/Programming/ResultTestImages/"
    # Regularized argument parsing
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument("-p", "--preferences", help="path to the preferences file")
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
    test = ["test_auto_focus"]
    software = "ZEN Blue"
    #     software='Test'

    if test_samples(software=software, file_path=file_path, test=test):
        print("Tests performed successful: ", test)
