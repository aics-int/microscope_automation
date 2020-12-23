"""
Abstract classes that define common microscope components.
These components are system independent, so not all microscopes implement all classes.
They are the bridge between automation software and hardware specific implementations.
These classes should only be called by hardware_control.Microscope.
Created on Jul 7, 2016
Split into hardware_control and hardware_components on May 25, 2020

@author: winfriedw
"""

import matplotlib.pyplot as plt
from matplotlib.path import Path as mpl_path
import matplotlib.patches as patches
from matplotlib import cm
import math
import inspect

# import modules from project microscope_automation
from ..image_AICS import ImageAICS
from .. import automation_messages_form_layout as message
from ..automation_exceptions import (
    ExperimentNotExistError,
    AutofocusError,
    AutofocusNotSetError,
    AutofocusObjectiveChangedError,
    ObjectiveNotDefinedError,
    LoadNotDefinedError,
    WorkNotDefinedError,
)

# setup logging
import logging

logger = logging


logging.basicConfig(level=logging.WARNING)
logging.debug('Switched on debug level logging in module "{}'.format(__name__))


# keep track of xPos, yPos, and zPos of stage and focus for debugging purposes


def log_method(self, methodName=None):
    """Log name of module and method if logging level is DEBUG.

    Input:
     methodName: string with  name of method

    Output:
     none
    """
    logging.debug("\nlog_method------------------------------")
    logging.debug(
        "Calling '{}' in module '{}'".format(self.__class__.__name__, self.__module__)
    )
    logging.debug("Method: {}".format(methodName))
    logging.debug("Docstring: {}".format(inspect.getdoc(self)))


xPos = 0
yPos = 0
zPos = 0


def log_message(message, methodName=None):
    """Shows message if logging level is INFO.

    Input:
     message: string with message
     methodName: string with  name of method

    Output:
     none
    """
    logging.info("\nlog_message------------------------------")
    logging.info("Message from method '{}':\n".format(methodName))
    logging.info(message)


def log_warning(message, methodName=None):
    """Shows message if logging level is WARNING.

    Input:
     message: string with message
     methodName: string with  name of method

    Output:
     none
    """
    logging.warning("\nlog_warning------------------------------")
    logging.warning("Message from method '{}':\n".format(methodName))
    logging.warning(message)


################################################################################


class Experiment(object):
    """
    Class to validate, read, and write to experiment files
    They are handled in different ways in Zen Blue and Black.
    Hence this feature was moved to hardware level
    """

    def __init__(self, experiment_path=None, name=None, microscope_object=None):
        """Setup and edit experiment file

        Input:
         file_path: File path to the experiment file (in zen black it will be none)

         name: Name of the experiment file

         microscope_object: microscope object that contains the connection
        """
        log_method(self, "__init__")
        self.experiment_name = name
        self.experiment_path = experiment_path
        self.microscope_object = microscope_object

    def validate_experiment(self):
        """
        Function to check if the experiment is defined and valid

        Input:
         none

        Output:
         valid_experiment: bool describing if the experiment is valid or not
        """
        log_method(self, "validate_experiment")
        microscope_connection = (
            self.microscope_object._get_control_software().connection
        )
        valid_experiment = microscope_connection.validate_experiment(
            self.experiment_path, self.experiment_name
        )
        return valid_experiment

    def is_z_stack(self):
        """Function to check if the experiment contains z-stack acquisition.
        Raises ExperimentNotExistError for invalid experiments.

        Input:
         none

        Output:
         is_zstack: bool
        """
        log_method(self, "is_z_stack")
        if not self.validate_experiment():
            raise ExperimentNotExistError(self.experiment_name)

        microscope_connection = (
            self.microscope_object._get_control_software().connection
        )
        is_zstack = microscope_connection.is_z_stack(
            self.experiment_path, self.experiment_name
        )
        return is_zstack

    def z_stack_range(self):
        """
        Function to calculate the range of the first experiment.
        Raises ExperimentNotExistError for invalid experiments.

        Input:
         none

        Output:
         zstack_range: range
        """
        log_method(self, "z_stack_range")
        if not self.validate_experiment():
            raise ExperimentNotExistError(self.experiment_name)

        microscope_connection = (
            self.microscope_object._get_control_software().connection
        )
        zstack_range = microscope_connection.z_stack_range(
            self.experiment_path, self.experiment_name
        )
        return zstack_range

    def is_tile_scan(self):
        """Function to check if the experiment contains a tile scan.
        Raises ExperimentNotExistError for invalid experiments.

        Input:
         none

        Output:
         is_tilescan: bool
        """
        log_method(self, "is_tile_scan")
        if not self.validate_experiment():
            raise ExperimentNotExistError(self.experiment_name)

        microscope_connection = (
            self.microscope_object._get_control_software().connection
        )
        is_tilescan = microscope_connection.is_tile_scan(
            self.experiment_path, self.experiment_name
        )
        return is_tilescan

    def update_tile_positions(self, x_value, y_value, z_value):
        """Function to set the tile position.
        Raises ExperimentNotExistError for invalid experiments.

        Input:
         x_value: x coordinate

         y_value: y coordinate

         z_value: z coordinate

        Output:
         none
        """
        log_method(self, "update_tile_positions")
        if not self.validate_experiment():
            raise ExperimentNotExistError(self.experiment_name)

        microscope_connection = (
            self.microscope_object._get_control_software().connection
        )
        microscope_connection.update_tile_positions(
            self.experiment_path, self.experiment_name, x_value, y_value, z_value
        )

    def get_objective_position(self):
        """Function to get the position of the objective used in the experiment.
        Raises ExperimentNotExistError for invalid experiments.

        Input:
         experiment_path: path of the experiment file

         experiment_name: name of the experiment

        Output:
         position: the integer position of the objective
        """
        log_method(self, "get_objective_position")
        if not self.validate_experiment():
            raise ExperimentNotExistError(self.experiment_name)

        microscope_connection = (
            self.microscope_object._get_control_software().connection
        )
        position = microscope_connection.get_objective_position_from_experiment_file(
            self.experiment_path, self.experiment_name
        )
        return position

    def get_focus_settings(self):
        """Function to get focus settings to test focus setup in test_zen_experiment.py
        Raises ExperimentNotExistError for invalid experiments.

        Input:
         none

        Output:
         focus_settings: All instances of focus settings in experiment file
        """
        log_method(self, "get_focus_settings")
        if not self.validate_experiment():
            raise ExperimentNotExistError(self.experiment_name)

        microscope_connection = (
            self.microscope_object._get_control_software().connection
        )
        focus_settings = microscope_connection.get_focus_settings(
            self.experiment_path, self.experiment_name
        )
        return focus_settings


class MicroscopeComponent(object):
    """Base class for all microscope components."""

    def __init__(self, component_id):
        self.set_id(component_id)
        self.component_type = self.__class__.__name__

        # settings during operation
        self.init_experiment = None
        self.default_camera = None
        self.use_live_mode = False

    def set_id(self, component_id):
        """Set unique id for microscope component.

        Input:
         component_id: string with unique component id

        Output:
         none
        """
        self.id = component_id

    def get_id(self):
        """Get unique id for component.

        Input:
         none

        Output:
         component_id: string with unique component id
        """
        return self.id

    def set_init_experiment(self, experiment):
        """Set experiment that will be used for initialization.

        Input:
         experiment: string with experiment name as defined within microscope software

        Output:
         none
        """
        self.init_experiment = experiment

    def get_init_experiment(self, communication_object=None):
        """Get experiment that will be used for initialization.

        Input:
         communication_object: not usesd

        Output:
         init_experiment: string with experiment name defined within microscope software
        """
        return self.init_experiment

    def initialize(
        self,
        communication_object,
        action_list=[],
        reference_object_id=None,
        verbose=True,
    ):
        """Catch initialization method if not defined in sub class.

        Input:
         communication_object: Object that connects to microscope specific software
         (not used)

         action_list: will not be processed

         reference_object_id: ID of plate the hardware is initialized for.
         Used for setting up of autofocus

         verbose: if True print debug information (Default = True)

        Output:
         none
        """
        self.communication_object = communication_object
        self.action_list = action_list
        self.plate_object_id = reference_object_id

    def set_component(self, settings):
        """Catch settings method if not defined in sub class.

        Input:
         settings: dictionary with flags

        Output:
         new_settings: dictionary with updated flags flags
        """
        return settings

    def get_information(self, communication_object):
        """Catch get_information method if not defined in sub class.

        Input:
         communication_object: Object that connects to microscope specific software
         (not used)

        Output:
         None
        """
        return None


################################################################################


class ControlSoftware(MicroscopeComponent):
    """Connect to software that controls specific Microscope.
    Import correct module based on Microscope software."""

    def __init__(self, software):
        """Connect to microscope software

        Input:
         software: string with software name

        Output:
         none
        """
        log_method(self, "__init__")
        super(ControlSoftware, self).__init__(software)
        # get name for software that controls Microscope
        #         self.software=software
        self.connect_to_microscope_software()

    def connect_to_microscope_software(self):
        """Import connect module based on software name and connect to microscope.

        Input:
         none

        Output:
         none
        """
        log_method(self, "connect_to_microscope_software")
        if self.get_id() == "ZEN Blue":
            from ..zeiss.connect_zen_blue import ConnectMicroscope

            self.connection = ConnectMicroscope()
        elif self.get_id() == "ZEN Black":
            from ..zeiss.connect_zen_black import ConnectMicroscope

            self.connection = ConnectMicroscope()
        elif self.get_id() == "Slidebook":
            # this is the only way to import modules starting with numbers
            from ..slidebook.connect_slidebook import ConnectMicroscope

            self.connection = ConnectMicroscope()
        elif self.get_id() == "ZEN Blue Dummy":
            # create microscope Zeiss spinning disk simulation
            # Uses same module as standard Zen Blue microscope, but without dll
            from ..zeiss.connect_zen_blue import ConnectMicroscope

            self.connection = ConnectMicroscope(connect_dll=False)
        elif self.get_id() == "Slidebook Dummy":
            # this is the only way to import modules starting with numbers
            from ..slidebook.connect_slidebook import ConnectMicroscope

            self.connection = ConnectMicroscope(dummy=True)

        # logger.info('selected software: %s', self.get_id())


################################################################################


class Safety(MicroscopeComponent):
    """Class with methods to avoid hardware damage of microscope."""

    def __init__(self, safety_id):
        """Define safe area for stage to travel.

        Input:
         safety_id: unique string to describe area

        Output:
         none
        """
        log_method(self, "__init__")
        super(Safety, self).__init__(safety_id)
        self.safe_areas = {}

    def add_safe_area(self, safe_vertices, safe_area_id, z_max):
        """Set safe travel area for microscope stage.

        Input:
         safe_vertices: coordinates in absolute stage positions that define safe area
         in the form [(x_0, y_0), (x_1, y_1),c(x_2, y_2), ...).

         safe_area_id: unique string to identify safe area

         z_max: maximum z value in focus drive coordinates within safe area

        Output:
         none
        """
        log_method(self, "add_safe_area")
        safe_verts = safe_vertices + [safe_vertices[0]]
        safe_codes = (
            [mpl_path.MOVETO]
            + [mpl_path.LINETO] * (len(safe_verts) - 2)
            + [mpl_path.CLOSEPOLY]
        )
        safe_area = {"path": mpl_path(safe_verts, safe_codes), "z_max": z_max}
        self.safe_areas[safe_area_id] = safe_area

    def get_safe_area(self, safe_area_id="Compound"):
        """Get safe travel area for microscope stage. Create compound area if requested.
        This compound area is a union of the x-y plane's areas with the minimum z value.

        Input:
         safe_area_id: unique string to identify safe area.
         Default: 'Compound' = combination of all safe areas

        Output:
         safe_area: dictionary of the form:
          path: matplotlib path object of safe area's perimeter

          z_max: maximum value the microscope can safely move in the z direction
        """
        log_method(self, "get_safe_area")
        if safe_area_id in list(self.safe_areas.keys()):
            return self.safe_areas[safe_area_id]

        if safe_area_id == "Compound":
            # create compound area out of all existing safe areas
            compound_path = None
            for safe_area_name, safe_area in self.safe_areas.items():
                safe_path = safe_area["path"]
                if compound_path is None:
                    compound_path = safe_path
                    z_max = safe_area["z_max"]
                else:
                    compound_path = mpl_path.make_compound_path(
                        compound_path, safe_path
                    )
                    z_max = min((z_max, safe_area["z_max"]))

            safe_area = {"path": compound_path, "z_max": z_max}
            return safe_area

    def is_safe_position(self, x, y, z, safe_area_id="Compound"):
        """Test if absolute position is safe.
        Compound area is a union of the x-y plane's areas with the minimum z value.

        Input:
         x, y: absolute stage position in um to be tested

         z: absolute focus position in um to be tested

         safe_area_id: unique string to identify safe area.
         Default: 'Compound' = combination of all safe areas

        Output:
         is_safe: True if position is safe, otherwise False
        """
        log_method(self, "is_safe_position")
        safe_area = self.get_safe_area(safe_area_id)

        is_safe = safe_area["path"].contains_point([x, y]) and safe_area["z_max"] > z
        return is_safe

    def is_safe_travel_path(self, path, z, safe_area_id="Compound", verbose=True):
        """Test if intended travel path is safe.
        Compound area is a union of the x-y plane's areas with the minimum z value.

        Input:
         path: travel path to be tested as matplotlib.Path object

         z: maximum focus position in um of the travel path

         safe_area_id: unique string to identify safe area.
         Default: 'Compound' = combination of all safe areas

         verbose: if True, show travel path and safe area. Default: True

        Output:
         is_safe: True if path is safe, otherwise False
        """
        log_method(self, "is_safe_travel_path")
        safe_area = self.get_safe_area(safe_area_id)

        # Interpolate path. Path.contains_path appears to test only vertices.
        # Find necessary density for interpolation steps
        # Length of path
        length = 0.0
        is_safe = False
        for vert in path.iter_segments():
            if vert[1] == mpl_path.MOVETO:
                start = vert[0]
            if vert[1] == mpl_path.LINETO:
                length = length + math.sqrt(
                    (vert[0][0] - start[0]) ** 2 + (vert[0][1] - start[1]) ** 2
                )
                start = vert[0]
        if int(length) > 0:
            is_safe = (
                safe_area["path"].contains_path(path.interpolated(int(length)))
                and safe_area["z_max"] > z
            )
        else:
            is_safe = True

        return is_safe

    def is_safe_move_from_to(
        self,
        safe_area_id,
        xy_path,
        z_max_pos,
        x_current,
        y_current,
        z_current,
        x_target,
        y_target,
        z_target,
        verbose=True,
    ):
        """Test if it is safe to travel from current to target position.

        Input:
         safe_area_id: string id for safe area

         xy_path: matplotlib path object that describes travel path of stage

         z_max_pos: the highest position for z focus during travel

         x_current, y_current, z_current: current x, y, z positions of stage in um

         x_target, y_target, z_target: target x, y, z positions of stage in um

         verbose: if True, show tavel path and safe area (default = True)

        Output:
         is_safe: True if travel path is safe, otherwise False
        """
        log_method(self, "is_safe_move_from_to")
        # show safe area and travel path if verbose
        if verbose:
            self.show_safe_areas(path=xy_path, point=(x_current, y_current))
        # is start position in safe area?
        if not self.is_safe_position(x_current, y_current, z_current, safe_area_id):
            return False

        # is target position in safe area?
        if not self.is_safe_position(x_target, y_target, z_target, safe_area_id):
            return False

        # is path in safe area?
        if not self.is_safe_travel_path(
            xy_path, z_max_pos, safe_area_id, verbose=verbose
        ):
            return False

        return True

    def show_safe_areas(self, path=None, point=None):
        """Show all safe areas defined in this class instance.

        Input:
         path: travel path to overlay with safe areas as matplotlib.Path object

         point: point to overlay with safe area as (x, y) tuple

        Output:
         none
        """
        log_method(self, "show_safe_areas")
        # setup figure
        fig = plt.figure()
        ax = fig.add_subplot(111)
        cmap = cm.get_cmap("Spectral")
        # add all safe areas to figure
        compound_path = None
        for i, (safe_area_name, safe_area) in enumerate(self.safe_areas.items()):
            safe_path = safe_area["path"]
            color = cmap(1.0 / (i + 1))
            patch = patches.PathPatch(safe_path, facecolor=color, lw=2)
            ax.add_patch(patch)
            # combine all path objects to one compound path
            if compound_path is None:
                compound_path = safe_path
            else:
                compound_path = mpl_path.make_compound_path(compound_path, safe_path)

        # add point and path information to image

        # define size of viewing area
        if point is not None:
            ax.plot(point[0], point[1], "ro")
        if path is not None:
            path_patch = patches.PathPatch(path, facecolor="none", lw=2)
            ax.add_patch(path_patch)
        # get bounding box
        view_box = compound_path.get_extents()

        # increase size of bounding box to view_box
        view_box = view_box.expanded(1.1, 1.1)
        ax.set_xlim(view_box.min[0], view_box.max[0])
        ax.set_ylim(view_box.min[1], view_box.max[1])
        plt.show()


################################################################################


class Camera(MicroscopeComponent, ImageAICS):
    """Class to describe and operate microscope camera"""

    def __init__(
        self,
        camera_id,
        pixel_size=(None, None),
        pixel_number=(None, None),
        pixel_type=None,
        name=None,
        detector_type="generic",
        manufacturer=None,
        model=None,
    ):
        """Describe and operate camera

        Input:
         camera_id: string with unique camera id

         pixel_size: (x, y) pixel size in mum

         pixel_number: (x, y) pixel number

         pixel_type: type of pixels (e.g. int32)

         name: string with brand name of camera, e.g. Flash 4.0

         detector_type: string with camera type, e.g. EMCCD, sCMOS

         manufacturer: string with name of manufacturere, e.g. Hamamatsu

         model: string of the name of the model

        Output:
         none
        """
        log_method(self, "__init__")
        super(Camera, self).__init__(camera_id)

        # keep track of live mode status
        self.live_mode_on = False

        # Specifications for used camera.
        # Names for keys are based on OME-XML
        # http://www.openmicroscopy.org/Schemas/Documentation/Generated/OME-2015-01/ome.html
        self.settings = {
            "aics_cameraID": camera_id,
            # The variable type used to represent each pixel in the image.
            "aics_PixelType": pixel_type,
            # Dimensional size of pixel data array [units:none].
            "aics_SizeX": pixel_number[0],
            # Dimensional size of pixel data array [units:none].
            "aics_SizeY": pixel_number[1],
            # Physical size of a pixel. Units are set by PhysicalSizeXUnit.
            "aics_PhysicalSizeX": pixel_size[0],
            # Physical size of a pixel. Units are set by PhysicalSizeYUnit.
            "aics_PhysicalSizeY": pixel_size[1],
            # The units of the physical size of a pixel - default:microns[micron].
            "aics_PhysicalSizeXUnit": "mum",
            # The units of the physical size of a pixel - default:microns[micron].
            "aics_PhysicalSizeYUnit": "mum",
            # The manufacturer of the component. [plain text string]
            "aics_Manufacturer": manufacturer,
            # The Model of the component. [plain text string]
            "aics_Model": model,
            # The Type of detector. E.g. CCD, PMT, EMCCD etc.
            "aics_Type": detector_type,
        }

    def get_information(self, communication_object):
        """Get camera status

        Input:
         communication_object: Object that connects to microscope specific software.
         Not used by Camera class, but maintained for consistency with
         parent class MicroscopeComponent

        Output:
         camera_dict: dictionary {'live': True/False, 'settings':  dict with settings}
        """
        log_method(self, "get_information")
        return {"live": self.live_mode_on, "settings": self.settings}

    def snap_image(self, communication_object, experiment=None):
        """Snap image with parameters defined in experiment.
        Class ImageAICS is a container for meta and image data.
        To add image data use method load_image.

        Input:
         communication_object: Object that connects to microscope specific software

         experiment: string with name of experiment defined within Microscope software.
         If None uses active/default experiment.

        Return:
         image: image of class ImageAICS to hold metadata.
         Does not contain image data at this moment.
        """
        log_method(self, "snap_image")
        # call snap_image method in ConnectMicroscope instance.
        # This instance will be based on a microscope specific connect module.
        communication_object.snap_image(experiment)
        image = ImageAICS(meta={"aics_Experiment": experiment})
        image.add_meta(self.settings)
        return image

    def live_mode_start(self, communication_object, experiment=None):
        """Start live mode of ZEN software.

        Input:
         communication_object: Object that connects to microscope specific software

         experiment: name of ZEN experiment (default = None)

        Output:
         none
        """
        log_method(self, "live_mode_start")
        communication_object.live_mode_start(experiment)
        self.live_mode_on = True

    def live_mode_stop(self, communication_object, experiment=None):
        """Stop live mode of ZEN software.

        Input:
         communication_object: Object that connects to microscope specific software

         experiment: name of ZEN experiment (default = None).
         If None use actual experiment.

        Output:
         none
        """
        log_method(self, "live_mode_stop")
        communication_object.live_mode_stop(experiment)
        self.live_mode_on = False


################################################################################


class Stage(MicroscopeComponent):
    """Class to describe and operate microscope stage"""

    #     def __init__(self, stageObject, id, safe_area_object = None):
    def __init__(
        self,
        stage_id,
        safe_area=None,
        safe_position=None,
        objective_changer=None,
        microscope_object=None,
        default_experiment=None,
    ):
        """Describe and operate microscope stage

        Input:
         stage_id: string with unique stage id

         safe_area: Name of area to stage can travel safely

         safe_position: Position of stage that is safe

         objective_changer: string with unique id for objective changer assoziated
         with stage required for par-centrizity correction

         microscope_object: microscope component is attached to

         default_experiment: default experiment (ZEN) or capture settings (Slidebook)

        Output:
         none
        """
        log_method(self, "__init__")
        super(Stage, self).__init__(stage_id)
        self.safe_area = safe_area
        if safe_position:
            self.safe_position_x = safe_position[0]
            self.safe_position_y = safe_position[1]
        else:
            self.safe_position_x = None
            self.safe_position_y = None
        self.objective_changer = objective_changer
        self.microscope_object = microscope_object
        self.default_experiment = default_experiment

    def initialize(
        self,
        communication_object,
        action_list=[],
        reference_object_id=None,
        verbose=True,
        test=False,
    ):
        """Initialize stage.

        Input:
         communication_object: Object that connects to microscope specific software

         action_list: not used

         reference_object_id: not used

         verbose: if True print debug information (Default = True)

         test: if True do not move stage

        Output:
         none
        """
        log_method(self, "initialize")
        # Move stage to safe position
        self.move_to_position(
            communication_object,
            x=self.safe_position_x,
            y=self.safe_position_y,
            test=test,
        )

    def get_information(self, communication_object):
        """Get actual stage position from hardware in mum

        Input:
         communication_object: Object that connects to microscope specific software

        Output:
         positions_dict: dictionary with stage position in mum of the form:
          {'absolute': (x, y, z), 'centricity_corrected': ()}

         z is optional depending on microscope used.
        """
        log_method(self, "get_information")
        positions = communication_object.get_stage_pos()
        if positions is None:
            positions = (None, None, None)

        if self.objective_changer:
            obj_changer = self.microscope_object._get_microscope_object(
                self.objective_changer
            )
            obj_info = obj_changer.get_objective_information(communication_object)
            centricity_cor = (obj_info["x_offset"], obj_info["y_offset"])
        else:
            centricity_cor = (None, None)

        return {"absolute": positions, "centricity_corrected": centricity_cor}

    def move_to_position(
        self, communication_object, x, y, z=None, experiment=None, test=False
    ):
        """Set stage position in mum and move stage

        Input:
         communication_object: Object that connects to microscope specific software

         x, y, z: stage position in mum

         experiment: experiment (ZEN) of capture settings (Slidebook) to use
         when operation stage (not allways required).
         None: use default experiment

         test: if True return travel path and do not move stage

        Output:
         xStage, yStage: position of stage after movement in mum

         zStage: position of stage after movement in mum
         (optional depending on whether a z value was input)
        """
        log_method(self, "move_to_position")
        if test:
            xy_path = communication_object.move_stage_to(x, y, zPos=z, test=test)
            path_object = mpl_path(xy_path)
            return path_object
        if experiment is None:
            experiment = self.default_experiment
        positions = communication_object.move_stage_to(x, y, z, experiment)
        if len(positions) == 2:
            return positions[0], positions[1]
        else:
            return positions[0], positions[1], positions[2]


################################################################################


class ObjectiveChanger(MicroscopeComponent):
    """Class to describe and change objectives"""

    def __init__(
        self,
        objective_changer_id,
        n_positions=None,
        objectives=None,
        ref_objective=None,
        microscope_object=None,
    ):
        """Describe and change objectives

        Input:
         objective_changer_id: string with unique objective changer id

         n_positions: number of objective positions

         objectives: dictionary of the form:
          'objective_name':
           'x_offset': x

           'y_offset': y

           'z_offset': z

           'magnification': m

           'immersion': 'type'

           'experiment': 'name'

          ref_objective: string with name of objective which defines reference position

        Output:
         none
        """
        log_method(self, "__init__")

        super(ObjectiveChanger, self).__init__(objective_changer_id)

        self.number_positions = n_positions

        # Set dictionary of objectives with self.get_all_objectives(n)
        # Required when using self.change_magnification(magnification)
        self.objectives_dict = {}
        self.objective_information = objectives

        # set experiment for initialization
        self.reference_objective = ref_objective
        if self.objective_information and self.reference_objective:
            init_experiment = self.objective_information[self.reference_objective][
                "experiment"
            ]
            self.init_experiment = init_experiment
            self.default_camera = self.objective_information[self.reference_objective][
                "camera"
            ]
        else:
            self.default_camera = None
            self.init_experiment = None
        self.use_live_mode = True
        self.microscope_object = microscope_object

    def initialize(
        self,
        communication_object,
        action_list=[],
        reference_object_id=None,
        verbose=True,
    ):
        """Initialize objective changer and set reference positions.

        Input:
         communication_object: Object that connects to microscope specific software

         action_list: list with item 'set_reference'. If empty no action.

         reference_object_id: ID of plate, plate holder, or other sample object
         the hardware is initialized for. Used for setting up of autofocus

         verbose: if True print debug information (Default = True)

        Output:
         none
        """
        log_method(self, "initialize")
        if "set_reference" in action_list:
            # setup microscope to initialize ObjectiveChanger
            self.microscope_object.setup_microscope_for_initialization(
                component_object=self,
                experiment=self.get_init_experiment(),
                before_initialization=True,
            )

            self.microscope_object.reference_position(
                find_surface=False,
                reference_object_id=reference_object_id,
                verbose=verbose,
            )

            # Clean up after initialization
            self.microscope_object.setup_microscope_for_initialization(
                component_object=self,
                experiment=self.get_init_experiment(),
                before_initialization=False,
            )

    def set_number_positions(self, n_positions):
        """Sets the number of objective positions.

        Input:
         n_positions:  number of objective positions

        Output:
         none
        """
        log_method(self, "set_number_positions")
        self.number_positions = n_positions

    def get_number_positions(self):
        """Get the number of objective positions.

        Input:
         none

        Output:
         n_positions:  number of objective positions
        """
        log_method(self, "get_number_positions")
        return self.number_positions

    def get_all_objectives(self, communication_object):
        """Retrieve name and magnification of all objectives.
        Required when using self.change_magnification(magnification)

        Warning! Objectives will move!

        Input:
         communication_object: Object that connects to microscope specific software

        Output:
         objectives_dict: dictionary of all objectives mounted at microscope
         in form {'magnification': {'Position': position, 'Name': name}
        """
        log_method(self, "get_all_objectives")
        number_objectives = self.get_number_positions()
        self.objectives_dict = communication_object.get_all_objectives(
            number_objectives
        )
        return self.objectives_dict

    def get_objectives_dict(self):
        """Retrieves dictionary with all names and magnifications of objectives.

        Requires to run self.get_all_objectives once before usage.

        Input:
         none

        Output:
         objectives_dict: dictionary of all objectives mounted at microscope
         in form {'magnification': {'Position': position, 'Name': name}
        """
        log_method(self, "get_objectives_dict")
        return self.objectives_dict

    def get_objective_magnification(self, communication_object):
        """Get magnification of actual objective.

        Input:
         none

        Output:
         magnification: magnification of actual objective, objective in imaging position
        """
        log_method(self, "get_objective_magnification")
        # get magnification from hardware
        magnification = communication_object.get_objective_magnification()
        return magnification

    def get_objective_information(self, communication_object):
        """Get offset to correct for parfocality and parcentrality for current objective

        Input:
         communication_object: Object that connects to microscope specific software

        Output:
         objective_information: dictionary for the current objective in the form:
          'x_offset': x

          'y_offset': y

          'z_offset': z

          'magnification': m

          'immersion': 'type'

          'experiment': 'name'
        """
        log_method(self, "get_objective_information")
        objective_name = communication_object.get_objective_name()
        if objective_name in self.objective_information:
            objective_information = self.objective_information[objective_name]
        else:
            objective_information = {
                "x_offset": 0,
                "y_offset": 0,
                "z_offset": 0,
                "magnification": None,
                "immersion": None,
            }
            print(
                ("Information for objective {} is not defined".format(objective_name))
            )
        objective_information["name"] = objective_name
        return objective_information

    def update_objective_offset(
        self, communication_object, x_offset, y_offset, z_offset, objective_name=None
    ):
        """Update offset to correct for parfocality and parcentrality

        Input:
         communication_object: Object that connects to microscope specific software

         x_offset, y_offset, z_offset: new offset values in absolute coordinates

         objective_name: string with unique name for objective.
         If None use current objective

        Output:
         objective_information: dictionary for the current objective in the form:
          'x_offset': x

          'y_offset': y

          'z_offset': z

          'magnification': m

          'immersion': 'type'

          'experiment': 'name'
        """
        log_method(self, "update_objective_offset")
        if objective_name is None:
            objective_name = communication_object.get_objective_name()

        try:
            self.objective_information[objective_name]["x_offset"] = x_offset
            self.objective_information[objective_name]["y_offset"] = y_offset
            self.objective_information[objective_name]["z_offset"] = z_offset
        except KeyError:
            raise ObjectiveNotDefinedError(
                message="No objective with name {} defined.".format(objective_name)
            )

        return self.objective_information[objective_name]

    def get_information(self, communication_object):
        """Get name and magnification of actual objective.

        Input:
         communication_object: Object that connects to microscope specific software

        Output:
         name, magnification, position, and experiment of objective in imaging position
        """
        log_method(self, "get_information")
        # get name of objective from hardware
        objective_name = communication_object.get_objective_name()
        objective_magnification = self.get_objective_magnification(communication_object)
        objective_position = communication_object.get_objective_position()
        init_experiment = self.objective_information[objective_name]["experiment"]
        return {
            "name": objective_name,
            "magnification": objective_magnification,
            "position": objective_position,
            "experiment": init_experiment,
        }

    def change_magnification(
        self,
        communication_object,
        magnification,
        sample_object,
        use_safe_position=True,
        verbose=True,
        load=True,
    ):
        """Change to objective with given magnification.

        Input:
         communication_object: object that connects to microscope specific software

         magnification: magnification of selected objective as float.
         Not well defined if multiple objectives with identical magnification exist.

         sample_object: object that has safe coordinates attached.
         If use_safe_position == True than stage and focus drive will move to
         this position before magnification is changed to avoid collision
         between objective and stage.

         use_safe_position: move stage and focus drive to safe position before switching
         magnification to minimize risk of collision (Default: True)

         verbose: if True print debug information (Default = True)

         load: if True, move objective to load position before switching (Default: True)

        Output:
         objective_name: name of new objective
        """
        log_method(self, "change_magnification")
        try:
            objectives_dict = self.get_all_objectives(communication_object)
            objective = objectives_dict[magnification]
        except KeyError:
            raise ObjectiveNotDefinedError(
                "No objective with magnification {}".format(magnification)
            )

        # move to safe position before changing objective
        if use_safe_position:
            sample_object.move_to_safe(load=load, verbose=verbose)
        objective_name = communication_object.switch_objective(
            objective["Position"], load=load
        )
        return objective_name

    def change_position(self, position, communication_object, load=True):
        """Change to objective at given position.
        Requires self.get_all_objectives run once before usage.

        Input:
         position: position of objective

         communication_object: Object that connects to microscope specific software

         load: if True, move objective to load position before switching (Default: True)

        Output:
         objective_name: name of new objective
        """
        log_method(self, "change_position")
        objective_name = communication_object.switch_objective(position, load=load)
        return objective_name


################################################################################


class FocusDrive(MicroscopeComponent):
    """Class to describe and operate focus drive"""

    def __init__(
        self,
        focus_drive_id,
        max_load_position=0,
        min_work_position=10,
        auto_focus_id=None,
        objective_changer=None,
        microscope_object=None,
    ):
        """Describe and operate focus drive

        Input:
         focus_drive_id: string with unique focus drive id

         max_load_position: maximum load position in um (Default = 0)

         min_work_position: minimum work position in um (Default = 10

         auto_focus_id: unique string to identify autofocus used with focus drive
         (None if no autofocus)

         objective_changer: string with unique id for objective changer assoziated
         with stage required for par-centrizity correction

         microscope_object: microscope component is attached to

        Output:
         none
        """
        log_method(self, "__init__")
        super(FocusDrive, self).__init__(focus_drive_id)

        self.auto_focus_id = auto_focus_id

        # define max and min load and work positions
        self.max_load_position = max_load_position
        self.min_work_position = min_work_position

        # predefine focus load and work positions as 0 to avoid crashes
        # between objective and stage
        self.z_load = None
        self.z_work = None

        self.objective_changer = objective_changer
        self.microscope_object = microscope_object

    def initialize(
        self,
        communication_object,
        action_list=[],
        reference_object_id=None,
        verbose=True,
        test=False,
    ):
        """Initialize focus drive.

        Input:
         communication_object: Object that connects to microscope specific software

         action_list: list with items 'set_load' and/or 'set_work'. If empty no action.

         microscope_object: microscope component is attached to

         reference_object_id: not used

         verbose: if True print debug information (Default = True)

        Output:
         none
        """
        log_method(self, "initialize")
        if "set_load" in action_list:
            if not test:
                message.operate_message(
                    "Move focus drive {} to load position.".format(self.get_id()),
                    return_code=False,
                )
            load_pos = self.define_load_position(communication_object)
            if load_pos > self.max_load_position:
                if test:
                    raise LoadNotDefinedError(
                        "Load position {} is higher than allowed maximum {}.".format(
                            load_pos, self.max_load_position
                        )
                    )
                else:
                    message_text = (
                        "Load position {} is higher than allowed maximum {}.".format(
                            load_pos, self.max_load_position
                        )
                    )
                    return_code = message.error_message(
                        'Please move objective to load position or cancel program.\nError message:\n"{}"'.format(  # noqa
                            message_text
                        )
                    )
                    if return_code != -1:
                        raise LoadNotDefinedError(
                            "Load position {} is higher than allowed maximum {}.".format(  # noqa
                                load_pos, self.max_load_position
                            )
                        )

        if "set_work" in action_list:
            if not test:
                message.operate_message(
                    'Please move focus drive "{}" to work position.'.format(
                        self.get_id()
                    ),
                    return_code=False,
                )
            work_pos = self.define_work_position(communication_object)
            if work_pos < self.min_work_position:
                raise WorkNotDefinedError(
                    "Work position {} is lower than allowed minimum {}.".format(
                        work_pos, self.min_work_position
                    )
                )

    def get_abs_position(self, communication_object):
        """get absolute focus position from hardware in mum

        Input:
         communication_object: Object that connects to microscope specific software

        Output:
         z: focus position in mum
        """
        log_method(self, "get_abs_position")
        # get current absolute focus position w/o any drift corrections
        absZ = communication_object.get_focus_pos()
        return absZ

    def get_information(self, communication_object):
        """get absolute and absolute position after drift correction for focus drive.

        Input:
         communication_object: Object that connects to microscope specific software

        Output:
         positions_dict: dictionary with
          'absolute': absolute position of focus drive as shown in software

          'z_focus_offset': parfocality offset

          'focality_corrected': absolute focus position - z_focus_offset

          'load_position': load position of focus drive

          'work_position': work position of focus drive

         with focus positions in um
        """
        log_method(self, "get_information")

        z = self.get_abs_position(communication_object)

        if self.objective_changer:
            obj_changer = self.microscope_object._get_microscope_object(
                self.objective_changer
            )
            obj_info = obj_changer.get_objective_information(communication_object)
            z_focus_offset = obj_info["z_offset"]
            focality_corrected = z - z_focus_offset
        else:
            z_focus_offset = None
            focality_corrected = None

        return {
            "absolute": z,
            "load_position": self.get_load_position(),
            "work_position": self.get_work_position(),
            "focality_corrected": focality_corrected,
            "z_focus_offset": z_focus_offset,
        }

    def move_to_position(self, communication_object, z):
        """Set focus position in mum and move focus drive.
        If use_autofocus is set, correct z value according to new autofocus position.

        Raises HardwareCommandNotDefinedError for Slidebook connections.

        Input:
         communication_object: Object that connects to microscope specific software

         z: focus drive position in mum

        Output:
         zFocus: position of focus drive after movement in mum
        """
        log_method(self, "move_to_position")

        zFocus = communication_object.move_focus_to(z)
        return zFocus

    def goto_load(self, communication_object):
        """Set focus position to load position.

        Input:
         communication_object: Object that connects to microscope specific software

        Output:
         z_load: load position in mum
        """
        log_method(self, "goto_load")
        try:
            z_load = communication_object.move_focus_to_load()
        # check if load was set. If not, ask user to set load
        except LoadNotDefinedError as error:
            # add focus drive instance to exception
            raise LoadNotDefinedError(message=error.message, error_component=self)
        return z_load

    def goto_work(self, communication_object):
        """Set focus position to work position.

        Input:
         communication_object: Object that connects to microscope specific software

        Output:
         z_work: work position in mum
        """
        log_method(self, "goto_work")
        z_work = communication_object.move_focus_to_work()
        return z_work

    def define_load_position(self, communication_object):
        """Define current focus position as load position for focus drive.

        Input:
         communication_object: Object that connects to microscope specific software

        Output:
         z_load: load postion in mum
        """
        log_method(self, "define_load_position")
        z_load = communication_object.set_focus_load_position()
        self.z_load = z_load
        return z_load

    def get_load_position(self):
        """Get load position for focus drive.

        Input:
         none

        Output:
         z_load: load position in mum
        """
        log_method(self, "get_load_position")
        return self.z_load

    def define_work_position(self, communication_object):
        """Define current focus position as work position for focus drive.

        Input:
         communication_object: Object that connects to microscope specific software

        Output:
         z_work: load postion in mum
        """
        log_method(self, "define_work_position")
        z_work = communication_object.set_focus_work_position()
        self.z_work = z_work
        return z_work

    def get_work_position(self):
        """Get work position for focus drive.

        Input:
         none

        Output:
         z_work: load position in mum
        """
        log_method(self, "get_work_position")
        return self.z_work


################################################################################


class AutoFocus(MicroscopeComponent):
    """Class to describe and operate hardware autofocus."""

    def __init__(
        self,
        auto_focus_id,
        default_camera=None,
        objective_changer_instance=None,
        default_reference_position=[[50000, 37000, 6900]],
        microscope_object=None,
    ):
        """Describe and operate hardware autofocus.

        Input:
         auto_focus_id: string with unique autofocus id

         init_experiment: experiment used for live mode during auto-focus

         default_camera: camera used for live mode during auto-focus

         objective_changer_instance: instance of class ObjectiveChanger
         which is connected to this autofocus

         default_reference_position: reference position to set parfocality and
         parcentricity. Used if no reference object (e.g. well center) is used.

        Output:
         none
        """
        log_method(self, "__init__")
        super(AutoFocus, self).__init__(auto_focus_id)

        # enable auto focus
        self.use_autofocus = self.set_use_autofocus(False)

        # settings during operation
        #         self.set_init_experiment(init_experiment)

        if default_camera == "None":
            default_camera = None
        self.default_camera = default_camera

        self.use_live_mode = True

        # object from class ImagingSystem (module samples.py)
        # that is used as reference (zero plane) for autofocus
        self.focus_reference_obj_id = None
        self.objective_changer_instance = objective_changer_instance
        self.initialized_objective = None
        self.default_reference_position = default_reference_position

        # Save position when autofocus was initialized the first time.
        # This value is used to correct for focus drift
        self._initial_autofocus_position = None
        # Store difference between _initial_autofocus_position
        # and autofocus position from 'Recall Focus'
        self.last_delta_z = None
        self.microscope_object = microscope_object

    def get_init_experiment(self, communication_object):
        """Get experiment used for initialization based on current objective.

        Input:
         communication_object: Object that connects to microscope specific software

        Output:
         init_experiment: string with name of experiment used for initialization
        """
        log_method(self, "get_init_experiment")
        # connect to associated objective changer and retrieve current objective
        # retrieve init_experiment for this objective
        try:
            init_experiment = self.objective_changer_instance.get_information(
                communication_object
            )["experiment"]
            return init_experiment
        except KeyError:
            return "Not defined"

    def initialize(
        self,
        communication_object,
        action_list=["find_surface"],
        reference_object_id=None,
        verbose=True,
    ):
        """Initialize auto-focus (default: do nothing if already initialized).

        Input:
         communication_object: Object that connects to microscope specific software

         action_list: if list includes 'no_find_surface' auto-focus will not try
         to find cover slip before operator refocuses

         no_interaction: no user interaction, no live image

         force_initialization: initialize even if already initialized.
         If empty no action

         sample_object: ID of plate, plate holder or other sample object
         the hardware is initialized for. Used for setting up of autofocus

         verbose: if True, print debug messages (Default: True)

        Output:
         none
        """
        log_method(self, "initialize")
        if action_list:
            # if auto-focus is already initialized,
            # initialize only if 'force_initialization' is set in action_list
            if (
                not self.get_autofocus_ready(communication_object)
                or "force_initialization" in action_list
            ):
                # if auto-focus was on, switch off autofocus
                auto_focus_status = self.use_autofocus
                self.set_use_autofocus(False)

                if "no_interaction" not in action_list:
                    self.microscope_object.setup_microscope_for_initialization(
                        component_object=self,
                        experiment=self.get_init_experiment(communication_object),
                        before_initialization=True,
                    )

                    if reference_object_id:
                        self.microscope_object.microscope_is_ready(
                            experiment=self.get_init_experiment(communication_object),
                            component_dict={
                                self.microscope_object._get_objective_changer_id(
                                    reference_object_id
                                ): []
                            },
                            focus_drive_id=self.microscope_object._get_focus_id(
                                reference_object_id
                            ),
                            objective_changer_id=self.microscope_object._get_objective_changer_id(  # noqa
                                reference_object_id
                            ),
                            safety_object_id=self.microscope_object._get_safety_id(
                                reference_object_id
                            ),
                            reference_object_id=reference_object_id,
                            load=False,
                            make_ready=True,
                            verbose=verbose,
                        )

                    if "no_find_surface" not in action_list:
                        self.find_surface(communication_object)
                    else:
                        message.operate_message(
                            message="Please focus on top of cover slip.",
                            return_code=False,
                        )
                        message.operate_message(
                            message="1) Bring the objective to focus position using the TFT\n2) Click Find Surface in ZenBlue",  # noqa
                            return_code=False,
                        )

                    self.microscope_object.setup_microscope_for_initialization(
                        component_object=self,
                        experiment=self.get_init_experiment(communication_object),
                        before_initialization=False,
                    )
                _z_abs = self.store_focus(
                    communication_object, focus_reference_obj_id=reference_object_id
                )

                # Save position when autofocus was initialized the first time.
                # This value is used to correct for focus drift
                self._initial_autofocus_position = _z_abs
                self.set_use_autofocus(auto_focus_status)

    def get_information(self, communication_object):
        """get status of auto-focus.

        Input:
         communication_object: Object that connects to microscope specific software

        Output:
         positions_dict: dictionary with focus position in mum of the form:
          {'absolute': z_abs, 'focality_corrected': z_cor}
        """
        log_method(self, "get_information")
        autofocus_info = {
            "initial_focus": self._initial_autofocus_position,
            "use": self.get_use_autofocus(),
            "experiment": self.get_init_experiment(communication_object),
            "camera": self.default_camera,
            "live_mode": self.use_live_mode,
            "reference_object_id": self.get_focus_reference_obj_id(),
            "delta_z": self.last_delta_z,
        }
        return autofocus_info

    def set_component(self, settings):
        """Switch on/off the use of auto-focus

        Input:
         settings: dictionary {use_auto_focus: True/False}.
         If empty do not change setting

        Output:
         new_settings: dictionary with updated status
        """
        log_method(self, "set_component")
        new_settings = {}
        if settings:
            self.set_use_autofocus(settings["use_auto_focus"])
        new_settings["use_auto_focus"] = self.use_autofocus
        return new_settings

    def set_use_autofocus(self, flag):
        """Set flag to enable the use of autofocus.
        If no autofocus position is stored, store current position.

        Input:
         flag: if True, use autofocus

        Output:
         use_autofocus: status of use_autofocus
        """
        log_method(self, "set_use_autofocus")
        self.use_autofocus = flag
        return self.use_autofocus

    def get_use_autofocus(self):
        """Return flag about autofocus usage

        Input:
         none

        Output:
         use_autofocus: boolean varaible indicating if autofocus should be used
        """
        log_method(self, "get_use_autofocus")
        return self.use_autofocus

    def get_autofocus_ready(self, communication_object):
        """Check if auto-focus is ready

        Input:
         communication_object: Object that connects to microscope specific software

        Output:
         is_ready: True, if auto-focus is ready
        """
        log_method(self, "get_autofocus_ready")
        try:
            is_ready = communication_object.get_autofocus_ready()
        except AutofocusError:
            is_ready = False
        return is_ready

    def find_surface(self, communication_object):
        """Find cover slip using Definite Focus 2. Does not store found position.

        Input:
         communication_object: Object that connects to microscope specific software

        Output:
         z: position of focus drive after find surface
        """
        log_method(self, "find_surface")
        z = communication_object.find_surface()
        #         self.store_focus()
        return z

    def set_focus_reference_obj_id(self, focus_reference_obj_id):
        """Set object from class ImagingSystem (module samples)
        used as zero plane for autofocus.

        Input:
         focus_reference_obj_id: Sample object used as reference for autofocus

        Output:
         none
        """
        log_method(self, "set_focus_reference_obj_id")
        self.focus_reference_obj_id = focus_reference_obj_id

    def get_focus_reference_obj_id(self):
        """Get object from class ImagingSystem (module samples)
        used as zero plane for autofocus.

        Input:
         none

        Output:
         focus_reference_obj_id: Sample object used as reference for autofocus
        """
        log_method(self, "get_focus_reference_obj_id")
        focus_reference_obj_id = self.focus_reference_obj_id
        return focus_reference_obj_id

    def store_focus(self, communication_object, focus_reference_obj_id):
        """Store actual focus position as offset from coverslip.

        Input:
         communication_object: Object that connects to microscope specific software

         focus_reference_obj_id: ID of Sample object used as reference for autofocus

        Output:
         z: position of focus drive after store focus
        """
        log_method(self, "store_focus")
        z = communication_object.store_focus()
        self.set_focus_reference_obj_id(focus_reference_obj_id)
        self.initialized_objective = (
            self.objective_changer_instance.get_objective_information(
                communication_object
            )["name"]
        )
        print(
            (
                "Autofocus position {} stored for {}.".format(
                    z, self.initialized_objective
                )
            )
        )
        return z

    def recall_focus(
        self,
        communication_object,
        reference_object_id=None,
        verbose=False,
        pre_set_focus=True,
    ):
        """Find difference between stored focus position and actual autofocus position.
        Recall focus will move the focus drive to it's stored position.
        Will try to recover if  autofocus failed.

        Input:
         communication_object: Object that connects to microscope specific software

         reference_object_id: ID of object of Sample class used to correct for xyz
         offset between different objectives

         verbose: if True, print debug messages (Default: False)

         pre_set_focus: Move focus to previous auto-focus position.
         This makes definite focus more robust

        Output:
         delta_z: difference between stored z position of focus drive
         and position after recall focus
        """
        log_method(self, "recall_focus")
        if not self.get_use_autofocus():
            # Get store difference between _initial_autofocus_position
            # and autofocus position from last 'Recall Focus'
            delta_z = self.last_delta_z
            return delta_z

        try:
            z = communication_object.recall_focus(pre_set_focus=pre_set_focus)
            if verbose:
                print(
                    "From hardware.FocusDrive.recall_focus: recall_focus = {}".format(z)
                )
        except AutofocusNotSetError as error:
            raise AutofocusNotSetError(
                message=error.message,
                error_component=self,
                focus_reference_obj_id=reference_object_id,
            )

        except AutofocusObjectiveChangedError as error:
            raise AutofocusObjectiveChangedError(
                message=error.message,
                error_component=self,
                focus_reference_obj_id=reference_object_id,
            )

        except AutofocusError as error:
            log_warning(error.message, "recall_focus")
            z = communication_object.recover_focus()
            if verbose:
                print(
                    "From hardware.FocusDrive.recall_focus: recover_focus = {}".format(
                        z
                    )
                )
            z = self.store_focus(
                communication_object, focus_reference_obj_id=reference_object_id
            )
            if verbose:
                print(
                    "From hardware.FocusDrive.recall_focus: store_focus = {}".format(z)
                )
            log_message("Autofocus recoverd at {}".format(z), "recall_focus")

        # _initial_autofocus_position was saved position
        # when autofocus was initialized the first time.
        # delta_z is the difference between the recalled z-position and
        # the saved position and is identical to focus drift or non-even sample
        if self._initial_autofocus_position is not None:
            delta_z = z - self._initial_autofocus_position
        else:
            delta_z = z

        # Store delta_z as backup if auto focus should not be used
        self.last_delta_z = delta_z
        if verbose:
            print(
                (
                    "From hardware.FocusDrive.recall_focus: _initial_autofocus_position, = {}, delta = {}".format(  # noqa
                        self._initial_autofocus_position, delta_z
                    )
                )
            )
        log_message(
            (
                "Autofocus original position in hardware {}"
                "\nAutofocus new position in hardware {}"
                "\nAutofocus delta position in hardware {}"
            ).format(self._initial_autofocus_position, z, delta_z),
            methodName="recall_focus",
        )
        return delta_z


################################################################################

################################################################################


class Pump(MicroscopeComponent):
    """Class to describe and operate pump"""

    def __init__(self, pump_id, seconds=1, port="COM1", baudrate=19200):
        """Describe and operate pump.

        Input:
         pump_id: string with unique stage id

         seconds: the number of seconds pump is activated

         port: com port, default = 'COM1'

         baudrate: baudrate for connection, can be set on pump, typically = 19200

        Output:
         none
        """
        log_method(self, "__init__")
        super(Pump, self).__init__(pump_id)
        #         self.pump=pumpObject.pump
        self.set_connection(port, baudrate)
        self.set_time(seconds)

    def set_connection(self, port, baudrate):
        """Set communication parameters for pump.

        Input:
         port: com port, default = 'COM1'

         baudrate: baudrate for connection, can be set on pump, typically = 19200

        Output:
         none
        """
        log_method(self, "set_connection")
        self.port = port
        self.baudrate = baudrate

    def get_connection(self):
        """Get communication parameters for pump.

        Input:
         none

        Output:
         conPar: dictionary with
          port: com port, default = 'COM1'

          baudrate: baudrate for connection, can be set on pump, typically = 19200
        """
        log_method(self, "get_connection")
        return (self.port, self.baudrate)

    def set_time(self, seconds):
        """Set time pump is activated.

        Input:
         seconds: time in seconds

        Output:
         none
        """
        log_method(self, "set_time")
        self.time = seconds

    def get_time(self):
        """Get communication parameters for pump.

        Input:
         none

        Output:
         seconds: time in seconds
        """
        log_method(self, "get_time")
        return self.time

    def trigger_pump(self, communication_object):
        """Trigger pump.

        Input:
         communication_object: Object that connects to microscope specific software

        Output:
         none
        """
        log_method(self, "trigger_pump")
        con_par = self.get_connection()
        seconds = self.get_time()
        communication_object.trigger_pump(
            seconds=seconds, port=con_par[0], baudrate=con_par[1]
        )
