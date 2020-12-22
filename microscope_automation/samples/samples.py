"""
Classes to describe and manipulate samples
Created on Jul 11, 2016

@author: winfriedw
"""

import logging
import math
import string
import pandas
import numpy
from os import path
import warnings
from collections import OrderedDict

# import modules from project microscope_automation
from ..get_path import (
    get_images_path,
    add_suffix,
    get_well_edge_path,
)
from .draw_plate import draw_plate
from .. import automation_messages_form_layout as message
from . import find_well_center
from . import correct_background
from . import tile_images
from ..load_image_czi import LoadImageCzi
from .positions_list import CreateTilePositions
from .interactive_location_picker_pyqtgraph import ImageLocationPicker
from ..automation_exceptions import (
    ObjectiveNotDefinedError,
    FileExistsError,
    MetaDataNotSavedError,
)

# we need module hardware only for testing
from ..hardware import hardware_components

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
VALID_TILE = ["NoTiling", "Fixed", "ColonySize", "Well"]
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
        camera_ids=[],
    ):
        """This is the superclass for all sample related classes
        (e.g. well, colony, etc).

        Input:
         container: class which holds this object (e.g. Plate is container for Well)

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

         microscope_object: object of class Microscope from module hardware

         stage_id: id string for stage.

         focus_id: id string with name for focus drive

         auto_focus_id: id string with name for auto-focus

         objective_changer_id: id string with name for objective changer

         safety_id: id string for safety area that prevents objective damage
         during stage movement

         camera_ids: list with ids for cameras used with this sample

        Output:
         None
        """
        self.samples = {}
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
            camera_ids=camera_ids,
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
        camera_ids=[],
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

         camera_ids: list with ids for cameras used with this sample

        Output:
         none
        """
        self.microscope = microscope_object
        self.stage_id = stage_id
        self.focus_id = focus_id
        self.auto_focus_id = auto_focus_id
        self.objective_changer_id = objective_changer_id
        self.safety_id = safety_id
        self.camera_ids = camera_ids

    def add_camera_id(self, camera_id):
        """Add ID to camera_ids without removing the existing IDs.

        Input:
         camera_id: ID to add to the list of IDs

        Output:
         none
        """
        self.camera_ids.append(camera_id)

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

    def set_interactive_positions(self, tile_image_data, location_list=[], app=None):
        """Opens up the interactive mode and lets user select colonies and
        return the list of coordinates selected

        Input:
        tile_image_data: The pixel data of the image of the well - numpy array

        location_list: The list of coordinates to be pre plotted on the image.

        app: pyqt application object initialized in microscopeAutomation.py

        Output:
         location_list: Returns the list of colonies selected by the user
        """
        # Using pyqtgraph module
        interactive_plot = ImageLocationPicker(tile_image_data, location_list, app)
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

    def add_samples(self, sample_objects_dict):
        """Adds samples to imaging system.

        Input:
         sample_objects_dict: dictionary of form {'name': sample_object}

        Output:
         none
        """
        self.samples.update(sample_objects_dict)

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
        """Add sample object to list with name list_name of objects to be imaged.

        Input:
         list_name: string with name of list (e.g. 'ColoniesPreScan')

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
        elif sample_object:
            if position is None:
                self.image_dirs[list_name].append(sample_object)
            else:
                self.image_dirs[list_name].insert(position, sample_object)

    def get_from_image_dir(self, list_name):
        """Get list with name list_name of objects to be imaged.

        Input:
         list_name: string with name of list (e.g. 'ColoniesPreScan')

        Output:
         sample_objects: list of name list_name with objects to be imaged
        """
        sample_objects = None
        for key in self.image_dirs.keys():
            if list_name in self.image_dirs.keys():
                sample_objects = self.image_dirs[list_name]
        return sample_objects

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
        except AttributeError:
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
         sample_type: string with name of object type
        """
        sample_type = type(self).__name__
        return sample_type

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
        x_stage_zero, y_stage_zero, z_stage_zero = self.get_abs_pos_from_obj_pos(
            0, 0, 0, verbose=verbose
        )
        return (x_stage_zero, y_stage_zero, z_stage_zero)

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
        z_correction_x_slope=1,
        z_correction_y_slope=1,
        z_correction_z_slope=1,
        z_correction_offset=1,
    ):
        """Multiply existing correction terms if scaling for object coordinate
        system is slightly off relative to container coordinate system
        with additional correction term.

        Input:
         x_correction, y_correction, z_correction z_correction_x_slope,
         z_correction_y_slope, z_correction_z_slope, z_correction_offset:
         Additional multiplicative correction terms

        Output:
         x_correction, y_correction, z_correction: updated parameters
        """
        self.x_correction = self.x_correction * x_correction
        self.y_correction = self.y_correction * y_correction
        self.z_correction = self.z_correction * z_correction
        self.z_correction_x_slope = self.z_correction_x_slope * z_correction_x_slope
        self.z_correction_y_slope = self.z_correction_y_slope * z_correction_y_slope
        self.z_correction_z_slope = self.z_correction_z_slope * z_correction_z_slope
        self.z_correction_offset = self.z_correction_offset * z_correction_offset

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
        if reference_object and use_reference:
            reference_object_id = reference_object.get_name()
        else:
            reference_object_id = None

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
            reference_object_id=reference_object_id,
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
            z = self.microscope.get_load_position(self.focus_id)

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
         x_stage, y_stage: x, y position on stage in mum
        """
        phi_r = math.radians(phi)
        x = r * math.sin(phi_r)
        y = r * math.cos(phi_r)
        x_stage, y_stage, z_stage = self.move_to_xyz(
            x, y, z=None, load=load, verbose=verbose
        )
        return x_stage, y_stage, z_stage

    def move_delta_xyz(self, x, y, z=0, load=True, verbose=True):
        """Move in direction x,y,z in micrometers from current position.

        Input:
         x, y, z: step size in micrometers

         load: Move focus in load position before move. Default: True

         verbose: if True print debug information (Default = True)

        Output:
         x_stage, y_stage: x, y position on stage in mum
        """
        # get current stage position in absolute stage coordinates
        x_stage, y_stage, z_stage = self.get_abs_position()
        x_new = x_stage + x
        y_new = y_stage + y
        z_new = z_stage + z

        x_new_stage, y_new_stage, z_new_stage = self.move_to_abs_position(
            x_new, y_new, z_new, load=load, verbose=verbose
        )
        return x_new_stage, y_new_stage, z_new_stage

    def get_abs_position(self, stage_id=None, focus_id=None):
        """Return current stage position.
        Positions are corrected for centricity and parfocality.

        Input:
         stage_id: string id to identify stage information is collected from

         focus_id: string id to identify focus drive information is collected from

        Output:
         abs_pos: absolute (x, y, z) position of stage in mum
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
            abs_pos = self.get_container().get_abs_position(stage_id, focus_id)
        return abs_pos

    ##############################################################################
    #
    # Transformations from container coordinates to object coordinates
    #  Correction factors for this transformation are attached to the object
    #
    ##############################################################################
    def calculate_slope_correction(self, x, y, verbose=True):
        """Calculate offset in z because of tilted sample.

        Input:
         x, y: x and y positions in object coordinates in um the correction is
         to be calculated

         verbose: if True print debug information (Default = True)

        Output:
         z_slope_correction: offset in z in um
        """
        if self.z_correction_z_slope == 0:
            z_slope_correction = 0
        else:
            z_slope_correction = (
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
            print(" Calculated slope correction offset: ", z_slope_correction)

        return z_slope_correction

    def get_obj_pos_from_container_pos(
        self, x_container, y_container, z_container, verbose=True
    ):
        """Calculate object coordinates from container coordinates.

        Input:
         x_container, y_container, z_container: container coordinates in mum

         verbose: if True print debug information (Default = True)

        Output:
         x_object, y_object, z_object: object coordinates in mum for container
         coordinates
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

        x_object = x_offfset_container * self.x_flip * self.x_correction
        y_object = y_offfset_container * self.y_flip * self.y_correction
        z_object = (
            z_offfset_container * self.z_flip * self.z_correction
            - self.calculate_slope_correction(x_object, y_object, verbose=verbose)
        )

        # Output for debugging
        if verbose:
            if self.get_container() is None:
                container_name = "Stage Position"
            else:
                container_name = self.get_container().get_name()
            print(
                "\nResults from method get_obj_pos_from_container_pos(xContainer, yContainer, zContainer)"  # noqa
            )
            print(
                " "
                + self.get_name()
                + " coordinates calculated from "
                + container_name
                + " coordinates"
            )
            print(" Container coordinates: ", x_container, y_container, z_container)
            print(" Object coordinates: ", x_object, y_object, z_object)
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

        return x_object, y_object, z_object

    def get_pos_from_abs_pos(self, x=None, y=None, z=None, verbose=True):
        """Return current position in object coordinates in mum.
        or transforms (x,y,z) from stage coordinates into object coordinates.
        This method is based on focus coordinates after drift correction.

        Input:
         x, y, z: Absolute stage coordinates in mum. If not given or None
         retrieve current stage position and express in object coordinates.

         verbose: if True print debug information (Default = True)

        Output:
         x_pos, y_pos, z_pos: current or position passed in stage coordinate
         returned in object coordinates
        """
        if self.get_container() is None:
            if (x is None) or (y is None) or (z is None):
                x_stage, y_stage, z_stage = self.get_corrected_stage_position()
            if x is None:
                x = x_stage
            if y is None:
                y = y_stage
            if z is None:
                z = z_stage
            x_pos = x - self.x_zero
            y_pos = y - self.y_zero
            z_pos = z - self.z_zero
        else:
            (
                x_container,
                y_container,
                z_container,
            ) = self.get_container().get_pos_from_abs_pos(x, y, z, verbose=verbose)
            x_pos, y_pos, z_pos = self.get_obj_pos_from_container_pos(
                x_container, y_container, z_container, verbose=verbose
            )
        return (x_pos, y_pos, z_pos)

    ##############################################################################
    #
    # Transformations from object coordinates to container coordinates
    #  Correction factors for this transformation are attached to the object
    #
    ##############################################################################
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
                container_name = "Stage Position"
            else:
                container_name = self.get_container().get_name()
            print(
                "\nResults from method get_container_pos_from_obj_pos(xObject, yObject, zObject)"  # noqa
            )
            print(
                " "
                + container_name
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

    def recall_focus(self, auto_focus_id, pre_set_focus=True):
        """Find difference between stored focus position and actual autofocus position.
        Recall focus will move the focus drive to it's stored position.

        Input:
         auto_focus_id: string of ID for autofocus to use

         pre_set_focus: Move focus to previous auto-focus position.
         This makes definite focus more robust

        Output:
         delta_z: difference between stored z position of focus drive
         and position after recall focus
        """
        return self.container.recall_focus(auto_focus_id, pre_set_focus)

    def live_mode_start(self, camera_id, experiment):
        """Start live mode in microscope software.

        Methods calls method of container instance until container has
        method implemented that actually performs action.

        Input:
         camera_id: string with unique camera ID

         experiment: string with experiment name as defined within microscope software
         If None use actual experiment.

        Output:
          none
        """
        self.container.live_mode_start(camera_id, experiment)

    def live_mode_stop(self, camera_id, experiment=None):
        """Stop live mode in microscope software.

        Methods calls method of container instance until container has
        method implemented that actually performs action.

        Input:
         camera_id: string with unique camera ID

         experiment: string with experiment name as defined within microscope software
         If None use actual experiment.

        Output:
         none
        """
        self.container.live_mode_stop(camera_id, experiment)

    def execute_experiment(
        self,
        experiment,
        camera_id,
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

         camera_id: string with unique camera ID

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
        class_name = self.__class__.__name__
        if meta_dict is None:
            meta_dict = {}
        meta_dict.update(
            {
                "aics_objectContainerName": self.get_container().get_name(),
                "aics_type": class_name,
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
            camera_id,
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
        camera_id,
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

         camera_id: string with unique camera ID

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
                    camera_id,
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
                self.microscope_is_ready(
                    experiment=experiment,
                    reference_object=reference_object,
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
                    camera_id,
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
         prefs: Preferences object with preferences for tiling

         verbose: print logging comments

         tile_object: tile object passed in by preferences. Possible options:
          'NoTiling': do not tile

          'Fixed': calculate tiling to image a rectangular area

          'Well': cover a well with tiles using an elliptical area

          'ColonySize': cover a colony with tiles using an ellipse

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
            raise ValueError("Tiling object not implemented")

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
        tile_object = CreateTilePositions(
            tile_type=tile_params["tile_type"],
            tile_number=tile_params["tile_number"],
            tile_size=tile_params["tile_size"],
            degrees=tile_params["degrees"],
        )
        tile_positions_list = tile_object.get_pos_list(tile_params["center"])
        return tile_positions_list

    def get_tile_positions_list(self, prefs, tile_object="NoTiling", verbose=True):
        """Get positions for tiles in absolute coordinates.
        Subclasses have additional tile_objects (e.g. ColonySize, Well).

        Input:
         prefs: Preferences object with preferences for tiling

         tile_object: tile object passed in by preferences. Possible options:
          'NoTiling': do not tile

          'Fixed': calculate tiling to image a rectangular area

          'Well': cover a well with tiles using an elliptical area

          'ColonySize': cover a colony with tiles using an ellipse

         verbose: print debugging information

        Output:
         tile_position_list: list with absolute positions for tiling
        """
        tile_params = self._get_tile_params(prefs, tile_object, verbose=verbose)
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
         images: list of images.
        """
        if load:
            for (image_name, image_object) in self.image_dict.items():
                if image_object.data is None:
                    self.image_dict[image_name] = self.load_image(
                        image_object, get_meta=get_meta
                    )
        return self.image_dict

    def background_correction(self, uncorrected_image, settings):
        """Correct background using background images attached to object
        or one of it's superclasses.

        Input:
         uncorrected_image: object of class ImageAICS

         settings: object of class Preferences which holds image settings

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

         settings: object of class Preferences which holds image settings

        Output:
         tile: ImageAICS object with tile
        """
        # Information about tiling should be int he image meta data
        # (e.g. image positions)
        #         if not settings.get_pref('Tile', validValues = VALID_TILE):
        #             return images[(len(images)-1)/2] # return the x-0, y-0 image

        # apply background correction
        corrected_images = []

        ######################################################################
        #
        # Todo: Catch if background image does not exist
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
        if not image:
            if self.container is not None:
                image = self.container.get_attached_image(key)
            else:
                # TODO: need to get a default image here
                print("Default Image")

        return image

    def remove_images(self):
        """Remove all images from microscope software display.

        Input:
         none

        Output:
         none
        """
        self.container.remove_images()

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
            microscope_object = self.microscope
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

    def get_camera_ids(self):
        """Return ids for cameras used with this sample.
        Searches through all containers until id is found.

        Input:
         none

        Output:
         camera_ids: list with ids for cameras used with this sample
        """
        ###############################################
        # TODO: camera_ids not implemented in container
        ###############################################
        try:
            camera_ids = self.camera_ids
            if camera_ids is []:
                camera_ids = self.get_container().get_camera_ids()
        except AttributeError:
            camera_ids = []
        return camera_ids

    def get_immersion_delivery_system(self):
        """Return the object that describes immersion water delivery system

        Input:
         none

        Output:
         immersion_delivery_system: object of class ImmersionDelivery
        """
        try:
            immersion_delivery_system = self.container.get_immersion_delivery_system()
        except AttributeError:
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
        return self.meta_dict

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

    A PlateHolder is the superclass for everything that can be imaged on a microscope
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
        camera_ids=[],
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
        self.slides = {}
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
            camera_ids=camera_ids,
        )

    def get_microscope(self):
        """Return object that describes connection to hardware.

        Input:
         none

        Output:
         microscope_object: object of class Microscope from module hardware
        """
        return self.microscope

    def get_camera_ids(self):
        """Return a list of camera objects associated with this sample

        Input:
         none

        Output:
         camera_ids: list of objects of class Camera
        """
        return self.camera_ids

    def get_immersion_delivery_system(self):
        """Return object that describes immersion water delivery system for
        this plate holder.

        Input:
         none

        Output:
         immersion_object: object of class ImmersionDelivery
        """
        return self.immersion_delivery_system

    def add_plates(self, plate_object_dict):
        """Adds Plate to Stage.

        Input:
         plate_object_dict: dictionary of the form {"name": plate_object}

        Output:
         none
        """
        self.plates.update(plate_object_dict)

    def get_plates(self):
        """Return dictionary of all plate_objects associated with plateholder.

        Input:
         none

        Output:
         plate_objects: dictionary with plate objects
        """
        return self.plates

    def add_slides(self, slide_object_dict):
        """Adds Slide to PlateHolder.

        Input:
         slide_object_dict:dictionary of the form {"name": slide_object}

        Output:
         none
        """
        self.slides.update(slide_object_dict)

    def get_slides(self):
        """Return Slide object attached to PlateHolder

        Input:
         none

        Output:
         slide_object: dictionary with slide objects
        """
        return self.slides

    def set_plate_holder_pos_to_zero(self, x=None, y=None, z=None):
        """Set current stage position as zero position for PlateHolder.

        Input:
         x, y, z: optional position in stage coordinates to set as zero position
         for PlateHolder. If omitted, actual stage position will be used.

        Output:
         x, y, z: new PlateHolder zero position
        """
        if (x is None) or (y is None) or (z is None):
            xStage, yStage, zStage = self.get_corrected_stage_position()
        if x is None:
            x = xStage
        if y is None:
            y = yStage
        if z is None:
            z = zStage

        self.set_zero(x, y, z)
        return x, y, z

    def get_corrected_stage_position(self, verbose=False):
        """Get current position in stage coordinates and focus position in mum.

        Input:
         none

        Output:
         x, y, z: Stage position after centricity correction
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
         x, y, z: real focus position not corrected for drift.
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
        x_stage,
        y_stage,
        z_stage=None,
        reference_object=None,
        load=True,
        verbose=True,
    ):
        """Move stage to position in stage coordinates in mum.

        Input:
         x_stage, y_stage, z_stage: stage position in mum

         reference_object: object of type sample (ImagingSystem).
         Used to correct for xyz offset between different objectives

         load: Move focus in load position before move. Default: True

         verbose: if True print debug information (Default = True)

        Output:
         x, y, z: actual stage position

        If use_autofocus is set, correct z value according to new autofocus position.
        """
        if reference_object:
            reference_object_id = reference_object.get_name()
        else:
            reference_object_id = None

        x, y, z = self.microscope.move_to_abs_pos(
            stage_id=self.stage_id,
            focus_drive_id=self.focus_id,
            objective_changer_id=self.objective_changer_id,
            auto_focus_id=self.auto_focus_id,
            safety_id=self.safety_id,
            x_target=x_stage,
            y_target=y_stage,
            z_target=z_stage,
            reference_object_id=reference_object_id,
            load=load,
            verbose=verbose,
        )

        return x, y, z

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
        if reference_object:
            reference_object_id = reference_object.get_name()
        else:
            reference_object_id = None

        microscope_object = self.get_microscope()
        microscope_object.initialize_hardware(
            initialize_components_ordered_dict={
                self.get_auto_focus_id(): ["find_surface"]
            },
            reference_object_id=reference_object_id,
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
        if focus_reference_obj:
            reference_object_id = focus_reference_obj.get_name()
        else:
            reference_object_id = None

        microscope_object = self.get_microscope()
        microscope_object.initialize_hardware(
            initialize_components_ordered_dict={
                self.get_auto_focus_id(): ["no_find_surface", "no_interaction"]
            },
            reference_object_id=reference_object_id,
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
        camera_id,
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

         camera_id: string with unique camera ID

         reference_object: object of type sample (ImagingSystem) used to correct for .
         xyz offset between different objectives

         file_path: filename with path to save image in original format.
         Default=None: no saving

         meta_dict: directory with additional meta data, e.g. {'aics_well':, 'A1'}

         verbose: if True print debug information (Default = True)

        Output:
          image: image of class ImageAICS

        Method adds camera_id to image.
        """
        # The method execute_experiment will send a command to the microscope
        # software to acquire an image.
        # experiment is the name of the settings used by the microscope software
        # to acquire the image. The method does not return the image, nor does it
        # save it. use PlateHolder.save_image to trigger the microscope software
        # to save the image.
        if reference_object:
            reference_object_id = reference_object.get_name()
        else:
            reference_object_id = None

        # Use an instance of Microscope from module hardware.
        microscope_instance = self.get_microscope()
        image = microscope_instance.execute_experiment(experiment)

        # retrieve information about camera and add to meta data
        image.add_meta({"aics_cameraID": camera_id})

        # retrieve information hardware status
        information_dict = microscope_instance.get_information()
        stage_z_corrected = microscope_instance.get_z_position(
            focus_drive_id=self.focus_id,
            auto_focus_id=self.auto_focus_id,
            reference_object_id=reference_object_id,
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

        if file_path:
            image = self.save_image(file_path, camera_id, image)
        return image

    def recall_focus(self, auto_focus_id, pre_set_focus=True):
        """Find difference between stored focus position and actual autofocus position.
        Recall focus will move the focus drive to it's stored position.

        Input:
         auto_focus_id: string of ID for autofocus to use

         pre_set_focus: Move focus to previous auto-focus position.
         This makes definite focus more robust

        Output:
          delta_z: difference between stored z position of focus drive
          and position after recall focus
        """
        return self.microscope.recall_focus(
            auto_focus_id,
            reference_object_id=self.get_name(),
            pre_set_focus=pre_set_focus,
        )

    def live_mode_start(self, camera_id, experiment=None):
        """Start live mode in microscope software.

        Input:
         camera_id: string with unique camera ID

         experiment: string with experiment name as defined within microscope software
         If None use actual experiment.

        Output:
          none
        """
        # Use an instance of a Camera from module hardware.
        # The method starts live mode for adjustments in the software.
        # It does not acquire an image
        # experiment is the name of the settings used by the microscope software
        # to acquire the image.
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
        self.microscope.live_mode(camera_id, experiment, live=False)

    def save_image(self, file_path, camera_id, image):
        """save original image acquired with given camera using microscope software

        Input:
         file_path: string with filename with path for saved image in original format
         or tuple with path to directory and template for file name

         camera_id: name of camera used for data acquisition

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
                # image=self.cameras[camera_id].save_image(file_pathCounter, image)
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

         get_meta: boolean of whether to obtain meta data for the image

        Output:
         image: image and meta data (if requested) as ImageAICS object
        """
        image = self.get_microscope().load_image(image, get_meta)
        return image

    def remove_images(self):
        """Remove all images from microscope software display.

        Input:
         none

        Output:
         none
        """
        self.get_microscope().remove_images()


class ImmersionDelivery(ImagingSystem):
    """Class for pump and tubing to deliver immersion water to objective."""

    def __init__(
        self,
        name="ImmersionDelivery",
        plate_holder_object=None,
        safety_id=None,
        pump_id=None,
        center=[0, 0, 0],
        x_flip=1,
        y_flip=1,
        z_flip=1,
        x_correction=1,
        y_correction=1,
        z_correction=1,
        z_correction_x_slope=0,
        z_correction_y_slope=0,
        microscope_object=None,
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
            microscope_object=microscope_object,
        )
        self.set_pump_id(pump_id)
        self.id = name
        self.safety_id = safety_id
        # counter will be incremented by self.add_counter
        self.count = 0

    def set_pump_id(self, pump_id=None):
        """Store id of pump associated with this ImmersionDelivery object.

        Input:
         stage_id: id string for pump

        Output:
         none
        """
        self.pump_id = pump_id

    def get_pump_id(self):
        """Return id for pump used with this ImmersionDelivery object.

        Input:
         none

        Output:
         pump_id: id for objective changer used with this sample
        """
        return self.pump_id

    def trigger_pump(self, pump_id=None):
        """Trigger pump to deliver immersion water.

        Input:
         pump_id: id of pump to trigger. None by default, which selects the pump_id
         already associated with this ImmersionDelivery object

        Output:
         none
        """
        if pump_id:
            self.get_microscope().trigger_pump(pump_id)
        else:
            self.get_microscope().trigger_pump(self.get_pump_id())

    def get_water(
        self, objective_magnification=None, pump_id=None, verbose=True, automatic=False
    ):
        """Move objective to water outlet and add drop of water to objective.

        Input:
         objective_magnification: add water to specific objective with given
         magnification as float number. Keep current objective if set to None.

         pump_id: id of pump to trigger. None by default, which selects the pump_id
         already associated with this ImmersionDelivery object

         verbose: if True print debug information (Default = True)

         automatic: if True, trigger pump, else show dialog

        Output:
         none
        """
        # get autofocus status and switch off autofocus
        autofocus_use = self.get_use_autofocus()
        self.set_use_autofocus(flag=False)

        # Get original position of stage and focus
        x_pos, y_pos, z_pos = self.get_abs_position()
        # Move objective in load positionss
        self.microscope.goto_load(self.get_focus_id())

        # Change objective
        if objective_magnification is not None:
            # objective_changer_object = self.get_objective_changer_id()
            try:
                self.get_microscope().change_magnification(
                    self.get_objective_changer_id(),
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
                    return_code=False,
                )
        # Move objective below water outlet, do not use autofocus
        store_autofocus_flag = self.get_use_autofocus()
        self.set_use_autofocus(False)
        self.move_to_zero(load=True, verbose=verbose)
        self.set_use_autofocus(store_autofocus_flag)
        # trigger pump
        if automatic:
            self.trigger_pump()
        else:
            message.operate_message(
                "Please add immersion water to objective.", return_code=False
            )

        # Return to original position
        self.move_to_abs_position(
            x_pos,
            y_pos,
            z_pos,
            reference_object=self.get_reference_object(),
            load=True,
            verbose=verbose,
        )

        # Switch autofocus back on if it was switch on when starting get_water
        self.set_use_autofocus(flag=autofocus_use)

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
        return self.count

    def reset_counter(self):
        """Reset counter value to 0.

        Input:
         none

        Output:
         count: current counter value
        """
        self.count = 0
        return self.count

    def set_counter_stop_value(self, counter_stop_value):
        """Set value to stop counter and trigger pumping of immersion water.

        Input:
         none

        Output:
         counter_stop_value: current counter stop value
        """
        self.counter_stop_value = counter_stop_value
        return self.counter_stop_value

    def get_counter_stop_value(self):
        """Get value for counter to stop.

        Input:
         none

        Output:
         counter_stop_value: value for counter to stop
        """
        try:
            counter_stop_value = self.counter_stop_value
        except AttributeError:
            counter_stop_value = None
        return counter_stop_value

    def count_and_get_water(
        self,
        objective_magnification=None,
        pump_id=None,
        increment=1,
        verbose=True,
        automatic=False,
    ):
        """Move objective to water outlet and add drop of water to objective.

        Input:
         objective_magnification: add water to specific objective with given
         magnification as float number. Keep current objective if set to None.

         pump_id: id of pump to trigger. None by default, which selects the pump_id
         already associated with this ImmersionDelivery object

         increment: integer to increment counter value. Default = 1

         verbose: if True print debug information (Default = True)

         automatic: if True, trigger pump, else show dialog (Default = False)

        Output:
         counter: counter value after increment
        """
        counter = 0
        while counter < self.get_counter_stop_value():
            counter = self.add_counter(increment=increment)
            self.get_water(
                objective_magnification=objective_magnification,
                pump_id=pump_id,
                verbose=verbose,
                automatic=automatic,
            )

        return counter


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
        except AttributeError:
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
         wells: dict with well objects
        """
        return self.wells

    def get_wells_by_type(self, sample_type):
        """Return dictionary with all Well Objects associated with plate that
        contain samples of given type.

        Input:
         sample_type: string or set with sample type(s)
         (e.g. {'Sample', 'Colony', 'Barcode'})

        Output:
         well_objects_of_type: dict with well objects
        """
        try:
            # create set of sample_type if only one same type was given as string
            if isinstance(sample_type, str):
                sample_type = {sample_type}
            # retrieve list of all well objects for plate
            well_objects = self.get_wells()
            print(well_objects)
            well_objects_of_type = {
                well_name: well_object
                for well_name, well_object in well_objects.items()
                if len(well_object.get_samples(sample_type=sample_type)) > 0
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
        return self.wells.get(well_name)

    def move_to_well(self, well):
        """Moves stage to center of well

        Input:
         well: name of well in format 'A1'

        Output:
         x_stage, y_stage, z_stage: x, y, z position on Stage in mum
        """
        well_x, well_y, well_z = self.get_well(well).get_zero()
        x_stage, y_stage, z_stage = self.set_zero(well_x, well_y, well_z)
        return x_stage, y_stage, z_stage

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
        plate_object=None,
        well_position_numeric=(0, 0),
        well_position_string=("A", "1"),
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

         plate_object: object of type Plate the well is associated with

         well_position_numeric: (column, row) as integer tuple (e.g. (0,0) for well A1)

         well_position_string: (row, column) as string tuple (e.g. ('A','1'))

         x_flip, y_flip, z_flip: -1 if coordinate system of plate holder
         is flipped in respect to stage

         x_correction, y_correction, z_correction: correction factor if there
         is a discrepancy between the stage and the plate holder calibration

        Output:
         none
        """
        super(Well, self).__init__(
            container=plate_object,
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
        # As long as only a set diameter from specifications exists,
        # use this value for all calculation.
        # Replace this value with a measured value as soon as possible
        self.set_diameter(diameter)
        self.set_assigned_diameter(diameter)
        self.set_well_position_numeric(well_position_numeric)
        self.set_well_position_string(well_position_string)
        self._failed_image = False

    def get_name(self):
        return self.name

    def get_failed_image(self):
        return self._failed_image

    def set_interactive_positions(self, tile_image_data, location_list=None, app=None):
        """Opens up the interactive mode and lets user select colonies
        and return the list of coordinates selected

        Input:
         tile_image_data: The pixel data of the image of the well - numpy array

         location_list: The list of coordinates to be pre plotted on the image.

         app: pyqt application object initialized in microscopeAutomation.py

        Output:
         location_list: Returns the list of colonies selected by the user
        """
        if location_list is None:
            location_list = []
        # Using pyqtgraph module
        interactive_plot = ImageLocationPicker(tile_image_data, location_list, app)
        title = "Well Overview Image - Well " + self.name
        interactive_plot.plot_points(title)
        self._failed_image = interactive_plot.failed_image()
        if self.get_failed_image():
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

    def set_well_position_numeric(self, position):
        """Set row and column number.

        Input:
         position: (column, row) as integer tuple (e.g. (0,0) for well A1

        Output:
         none
        """
        self.well_position_numeric = position

    def get_well_position_numeric(self):
        """Get row and column number.

        Input:
         none

        Output:
         well_position_numeric: (column, row) as integer tuple (e.g. (0,0) for well A1
        """
        return self.well_position_numeric

    def set_well_position_string(self, position):
        """Set row and column as strings.

        Input:
         position: (row, column) as string tuple (e.g. ('A','1') for well A1)

        Output:
         none
        """
        self.well_position_string = position

    def get_well_position_string(self):
        """Get row and column as string.

        Input:
         none

        Output:
         well_position_string: (row, column) as string tuple
         (e.g. ('A','1') for well A1)
        """
        return self.well_position_string

    def set_assigned_diameter(self, assigned_diameter):
        """Set diameter from specifications or measured externally for well.

        Input:
         assigned_diameter: predefined diameter in mum
         (e.g from plate specifications or other instrument)

        Output:
         none
        """
        self.assigned_diameter = assigned_diameter

    def get_assigned_diameter(self):
        """Get well diameter for well as measured by external means.

        Input:
         none

        Output
         assigned_diameter: predefined diameter in mum
         (e.g from plate specifications or other instrument)
        """
        return self.assigned_diameter

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
        return self.diameter

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
        assigned_diameter = self.get_assigned_diameter()

        # if any of the diameters in not defined (None)
        # set correction factor to 1 and print warning
        if measured_diameter is None or assigned_diameter is None:
            correction = 1
        else:
            correction = measured_diameter / assigned_diameter

        # if update==True update correction factor
        # and do not replace to keep earlier corrections in place
        if update:
            self.update_correction(correction, correction)
        else:
            self.set_correction(correction, correction)

    def add_colonies(self, colony_objects_dict):
        """Adds colonies to well.
        Raises TypeError if non-colony object is added.

        Input:
         colony_objects_dict: dictionary of form {'name': colony_object}

        Output:
         none
        """
        if not all(isinstance(v, Colony) for v in colony_objects_dict.values()):
            raise TypeError("All objects must be of type Colony")

        self.samples.update(colony_objects_dict)

    def add_samples(self, sample_objects_dict):
        """Adds samples to well.

        Input:
         sample_objects_dict: dictionary of form {'name': sample_object}

        Output:
         none
        """
        self.samples.update(sample_objects_dict)

    def get_samples(self, sample_type={"Sample", "Barcode", "Colony"}):
        """Get all samples in well.

        Input:
         sample_type: list with types of samples to retrieve.
         At this moment {'Sample', 'Barcode', 'Colony'} are supported

        Output:
         samples: dict with sample objects
        """
        samples = {}
        try:
            for name, sample_obj in self.samples.items():
                if type(sample_obj).__name__ in sample_type:
                    samples.update({name: sample_obj})
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
            colonies = self.get_samples(sample_type="Colony")
        except Exception:
            colonies = None
        return colonies

    def add_barcode(self, barcode_objects_dict):
        """Adds barcode to well.
        Raises TypeError if non-barcode object is added.

        Input:
         barcode_objects_dict: dictionary of form {'name': barcodeObject}

        Output:
         none
        """
        if not all(isinstance(v, Barcode) for v in barcode_objects_dict.values()):
            raise TypeError("All objects must be of type Barcode")

        self.samples.update(barcode_objects_dict)

    def find_well_center_fine(
        self, experiment, well_diameter, camera_id, settings, verbose=True, test=False
    ):
        """Find center of well with higher precision.

        Method takes four images of well edges and calculates center.
        Will set origin of well coordinate system to this value.

        Input:
         experiment: string with imaging conditions defined within microscope software

         well_diameter: diameter of reference well in mum

         camera_id: string with name of camera

         settings: object of class Preferences which holds image settings

         verbose: if True print debug information (Default = True)

         test: if True will call find_well_center.find_well_center_fine
         in test mode. (Default = False)

        Output:
         x_center, y_center, z_center: Center of well in absolute stage coordinates
         in mum. z after drift correction (as if no drift had occured)
        """
        # user positioned right well edge in center of 10x FOW
        # acquire image and find edge coordinates
        name = self.get_name()
        print(get_well_edge_path(settings))
        file_path = path.join(get_well_edge_path(settings), name + ".czi")
        meta_dict = {
            "aics_well": self.get_name(),
            "aics_barcode": self.get_barcode(),
            "aics_xTile": "-1",
            "aics_yTile": "0",
        }
        image = self.execute_experiment(
            experiment,
            camera_id,
            file_path=add_suffix(file_path, "-1_0"),
            meta_dict=meta_dict,
            verbose=verbose,
        )

        image = self.load_image(image, get_meta=True)

        pixel_size = image.get_meta("PhysicalSizeX")
        edge_pos_pixels = find_well_center.find_well_center_fine(
            image=image.data, direction="-x", test=test
        )

        x_pos_0 = edge_pos_pixels * pixel_size
        x_edge_0 = x_pos_0 + image.get_meta("aics_imageAbsPosX")

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
            camera_id,
            file_path=add_suffix(file_path, "1_0"),
            meta_dict=meta_dict,
            verbose=verbose,
        )

        image = self.load_image(image, get_meta=True)
        edge_pos_pixels = find_well_center.find_well_center_fine(
            image=image.data, direction="x", test=test
        )

        x_pos_1 = edge_pos_pixels * pixel_size
        x_edge_1 = x_pos_1 + image.get_meta("aics_imageAbsPosX")

        x_radius = (x_edge_1 - x_edge_0) / 2
        x_center = x_edge_0 + x_radius

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
            camera_id,
            file_path=add_suffix(file_path, "0_1"),
            meta_dict=meta_dict,
            verbose=verbose,
        )

        image = self.load_image(image, get_meta=True)
        edge_pos_pixels = find_well_center.find_well_center_fine(
            image=image.data, direction="-y", test=test
        )
        y_pos_0 = edge_pos_pixels * pixel_size
        y_edge_0 = y_pos_0 + image.get_meta("aics_imageAbsPosY")

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
            camera_id,
            file_path=add_suffix(file_path, "0_-1"),
            meta_dict=meta_dict,
            verbose=verbose,
        )

        image = self.load_image(image, get_meta=True)
        edge_pos_pixels = find_well_center.find_well_center_fine(
            image=image.data, direction="y", test=test
        )

        y_pos_1 = edge_pos_pixels * pixel_size
        y_edge_1 = y_pos_1 + image.get_meta("aics_imageAbsPosY")

        y_radius = (y_edge_1 - y_edge_0) / 2
        y_center = y_edge_0 + y_radius

        z_center = image.get_meta("aics_imageAbsPosZ(driftCorrected)")
        self.set_measured_diameter(2 * numpy.mean([x_radius, y_radius]))
        print("Radius in x (length, x position): ", x_radius, x_center)
        print("Radius in y (length, y position): ", y_radius, y_center)
        print("Focus position: ", z_center)
        return x_center, y_center, z_center

    def get_tile_positions_list(self, prefs, tile_object="Well", verbose=True):
        """Get positions for tiles in absolute coordinates.
        Other classes have additional tile_objects (e.g. ColonySize).

        Input:
         prefs: Preferences object with preferences for tiling

         tile_object: tile object passed in by preferences. Possible options:
          'NoTiling': do not tile

          'Fixed': calculate tiling to image a rectangular area

          'Well': cover a well with tiles using an elliptical area

          'ColonySize': cover a colony with tiles using an ellipse

         verbose: print debugging information

        Output:
         tile_position_list: list with absolute positions for tiling
        """
        # retrieve common tiling parameters, than adjust them for wells if necessary
        try:
            tile_params = self._get_tile_params(prefs, tile_object, verbose=verbose)
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
        if well_object:
            self.microscope = well_object.microscope
            self.well = well_object.name
            self.plate_layout = well_object.plate_layout
            self.stage_id = well_object.stage_id

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
        self, experiment, camera_id, file_path, verbose=True
    ):
        """Take image of barcode.

        Input:
         experiment: string with name for experiment used in microscope software

         camera_id: unique ID for camera used to acquire image

         file_path: filename with path to store images.
         If None, image is not saved

         verbose: if True print debug information (Default = True)

        Output:
         image: Image of barcode. Images will be used to decode barcode.
        """
        image = self.execute_experiment(
            experiment, camera_id, file_path=file_path, verbose=verbose
        )
        return image

    def read_barcode(self, experiment, camera_id, file_path, verbose=True):
        """Take image of barcode and return code.

        Input:
         experiment: string with imaging conditions as defined within microscope sofware

         camera_id: string with name of camera

         file_path: filename with path to store images.
         If None, image is not saved

         verbose: if True print debug information (Default = True)

        Output:
         code: string encoded in barcode
        """
        image = self.read_barcode_data_acquisition(
            experiment, camera_id, file_path, verbose=verbose
        )
        image = self.load_image(image, get_meta=False)
        # code = read_barcode(image)
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
        if meta is not None:
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

    def set_interactive_positions(self, image_data, location_list=None, app=None):
        """Opens up the interactive mode and lets user select cells and
        return the list of coordinates selected

        Input:
         image_data: The pixel data of the image of the colony - numpy array

         location_list: Coordinates to be preplotted on the image

         app: pyqt application object

        Output:
         location_list: Returns the list of cells selected by the user
        """
        # Using pyqtgraph module
        if location_list is None:
            location_list = []
        interactive_plot = ImageLocationPicker(image_data, location_list, app)
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
        x_stage_positions = []
        y_stage_positions = []
        z_stage_positions = []
        for image in images:
            x_stage_positions.append(image.get_meta("aics_imageAbsPosX"))
            y_stage_positions.append(image.get_meta("aics_imageAbsPosY"))
            z_stage_positions.append(
                image.get_meta("aics_imageAbsPosZ(driftCorrected)")
            )

        print(x_stage_positions)
        x_stage_median = numpy.median(numpy.array(x_stage_positions))
        y_stage_median = numpy.median(numpy.array(y_stage_positions))
        z_stage_median = numpy.median(numpy.array(z_stage_positions))

        x, y, z = self.get_container().get_pos_from_abs_pos(
            x_stage_median, y_stage_median, z_stage_median, verbose=verbose
        )
        return self.set_zero(x, y, z)

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

        for cell in cell_objects_dict.values():
            cell.set_cell_line(self.get_cell_line())
            cell.set_clone(self.get_clone())

    def get_cells(self):
        """Get all cells in colony.

        Input:
         none

        Output:
         cells: dictionary of form {'name': cellObject}
        """
        return self.cells

    def number_cells(self):
        return len(self.cells)

    def find_cells_cell_profiler(self):
        # TODO Add comments plus clean up
        """Find locations of cells to be imaged in colony and add them to colony.

        Input:
         none

        Output:
         none
        """
        cell_name = self.name + "_0001"
        new_cell = Cell(name=cell_name, center=[0, 0, 0], colony_object=self)
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
        if prefs.get_pref("Tile", valid_values=VALID_TILE) != "Fixed":
            image.data = numpy.transpose(image.data, (1, 0, 2))
        print(prefs.get_pref_as_meta("CellFinder"))
        cell_finder = find_cells.CellFinder(
            image, prefs.get_pref_as_meta("CellFinder"), self
        )
        cell_dict = cell_finder.find_cells()
        self.add_cells(cell_dict)

    def find_cell_interactive_distance_map(self, location):
        """Find locations of cells to be imaged in colony and add them to colony.

        Input:
         location: center of the cell in the form (x, y)

        Output:
         cell_to_add: object of class Cell
        """
        cell_dict = {}
        cell_name = self.name + "_{:04}".format(1)
        cell_to_add = Cell(
            name=cell_name, center=[location[0], location[1], 0], colony_object=self
        )
        cell_dict[cell_name] = cell_to_add
        self.add_cells(cell_dict)
        return cell_to_add

    def execute_experiment(
        self,
        experiment,
        camera_id,
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

         camera_id: string with unique camera ID

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
            camera_id,
            reference_object=reference_object,
            file_path=file_path,
            meta_dict=meta_dict,
            verbose=verbose,
        )
        return image


position_number = 1


class Cell(ImagingSystem):
    """Class to describe and manipulate cells within a colony."""

    def __init__(
        self,
        name="Cell",
        center=[0, 0, 0],
        colony_object=None,
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

         colony_object: object of type Colony the cell is associated with

         x_flip, y_flip, z_flip: -1 if coordinate system of plate holder
         is flipped in respect to stage

         x_correction, y_correction, z_correction: correction factor if
         there is a discrepancy between the stage and the plate holder calibration

        Output:
         None
        """
        super(Cell, self).__init__(
            container=colony_object,
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
        camera_id,
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

         camera_id: string with unique camera ID

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
            camera_id,
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


def create_plate_holder_manually(m, prefs):
    """Create plate holder manually instead of using setup_samples."""
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

    print("PlateHolder created")

    # create immersion delivery system as part of PlateHolder and add to PlateHolder
    pump_object = hardware_components.Pump("Immersion")
    m.add_microscope_object(pump_object)

    # Add pump to plateHolder
    im = ImmersionDelivery(name="Immersion", plate_holder_object=ph, center=[0, 0, 0])
    # ph.add_immersionDelivery(immersion_delivery_systemsDict={'Water Immersion': im})
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
    ph.add_plates(plate_object_dict={"Test Plate": p})
    print("Plate created and added to PlateHolder")

    # create Wells as part of Plate and add to Plate
    plate_layout = create_plate("96")

    d5 = Well(
        name="D5",
        center=plate_layout["D5"],
        diameter=plate_layout["well_diameter"],
        plate_object=p,
        well_position_numeric=(4, 5),
        well_position_string=("D", "5"),
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
        plate_object=p,
        well_position_numeric=(5, 5),
        well_position_string=("D", "6"),
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
        colony_object=c1d5,
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
