"""
Function to setup hardware and samples based on reference files
Created on Aug 1, 2016
Split into it's own module: 05/21/2020

@author: winfriedw
"""
# import standard Python modules
import string
import pandas
import numpy
import math

# import external modules written for MicroscopeAutomation
from ..preferences import Preferences
from .. import automation_messages_form_layout as message
from ..get_path import get_hardware_settings_path, get_colony_file_path
from . import samples

# create logger
import logging

logger = logging.getLogger("microscope_automation")


###########################################################################
#
# Create plate and add colonies from plate scanner and other content (barcode, controls)
#
############################################################################


def get_colony_data(prefs, colony_file):
    """Get data and positions of colonies.

    Input:
     prefs: preferences with information about colony file

     colony_file: path to .csv file with colony data.

    Output:
     colonies: pandas frame with content of .csv file
    """
    # setup logging
    logger = logging.getLogger(  # noqa
        "microscope_automation.samples.setup_samples.get_colony_data"
    )

    ##############################
    # this portion will be replaces by calls to LIMS system
    ##############################

    # load .csv file with one row header
    # we should define the colomn type here
    # tried to use usecols to read data read in -> does not work
    print("Read file {}".format(colony_file))
    colonies_all = pandas.read_csv(colony_file)

    # select plate to process
    # Use plateID list to be able to expand to multiple plates
    plate_id_list = list(colonies_all.loc[:, "PlateID"].unique())

    selected_plate_id_list = [
        message.pull_down_select_dialog(
            plate_id_list,
            (
                "Please select barcode of plate on microscope.\n"
                "947 is a good example."
            ),
        )
    ]
    plate_selector = colonies_all.loc[:, "PlateID"].isin(selected_plate_id_list)

    # select columns as defined in preferences.yml file
    # and rename to software internal names
    colony_columns = prefs.get_pref("ColonyColumns")
    colonies = colonies_all.loc[plate_selector, colony_columns.keys()]
    colonies.rename(columns=colony_columns, inplace=True)

    # get information about colonies to image
    print("summary statistics about all colonies on plate ", plate_id_list)
    print(colonies.describe())

    # calculate additional columns
    colonies.loc[:, "WellColumn"] = colonies.loc[:, "WellColumn"].fillna(-1)
    colonies.loc[:, "Well"] = colonies.loc[:, "WellRow"].str.cat(
        colonies.loc[:, "WellColumn"].astype(int).astype(str)
    )
    colonies.loc[:, "Center_X^2"] = colonies.loc[:, "Center_X"].apply(
        math.pow, args=(2,)
    )
    colonies.loc[:, "Center_Y^2"] = colonies.loc[:, "Center_Y"].apply(
        math.pow, args=(2,)
    )
    colonies.loc[:, "CenterDistance"] = (
        colonies.loc[:, "Center_X^2"]
        .add(colonies.loc[:, "Center_Y^2"])
        .apply(math.sqrt)
    )
    count_per_well = pandas.DataFrame(
        colonies.groupby(["PlateID", "Well"]).size(), columns=["CountPerWell"]
    ).reset_index()
    colonies = pandas.merge(
        colonies,
        count_per_well,
        left_on=["PlateID", "Well"],
        right_on=["PlateID", "Well"],
    )
    return colonies


###########################################################################


def filter_colonies(prefs, colonies, well_dict):
    """Select colonies to image based on settings in preferences file.

    Input:
     prefs: preferences with selection criteria

     colonies: table with colony data

     well_dict: list with wells that should be considered. Well names in format 'A1'.

    Output:
     slected_colonies: subset of colonies to be imaged
    """
    # get names of wells to scan
    well_list = well_dict.keys()
    wells_select = colonies["Well"].isin(well_list)

    # scan only wells with a minimum number of colonies in a give well before filtering
    min_count_per_well = prefs.get_pref("MinCountPerWell")
    min_count_select = colonies.CountPerWell >= min_count_per_well

    # scan only wells with a maximum number of colonies in a give well before filtering
    maxCountPerWell = prefs.get_pref("MaxCountPerWell")
    max_count_select = colonies.CountPerWell <= maxCountPerWell

    # scan only colonies that are larger than MinAreaColonies
    # based on Celigo measurements in mum^2
    min_area_colonies = prefs.get_pref("MinAreaColonies")
    min_area_select = colonies.Area >= min_area_colonies

    # scan only colonies that are smaller than MinAreaColonies
    # based on Celigo measurements in mum^2
    max_area_colonies = prefs.get_pref("MaxAreaColonies")
    max_area_select = colonies.Area <= max_area_colonies

    # scan only colonies that are within a circle around the well center
    # with radius MaxDistanceToCenter based on Celigo measurements in mum
    max_distance_to_center = prefs.get_pref("MaxDistanceToCenter")
    max_distance_select = colonies.CenterDistance <= max_distance_to_center

    # remove colonies that are not in the correct wells
    filtered_colonies = colonies.loc[
        min_count_select
        & max_count_select
        & min_area_select
        & max_area_select
        & max_distance_select
        & wells_select
    ]

    # we want to scan a maximum number of colonies per well
    # if there are more valid colonies in a given well than select random colonies
    selected_colonies = pandas.DataFrame()
    for well, number_images in well_dict.items():
        # find all colonies within well
        well_select = filtered_colonies.Well == well
        colonies_in_well = filtered_colonies.loc[well_select]
        if colonies_in_well.shape[0] >= number_images:
            selected_colonies = selected_colonies.append(
                colonies_in_well.sample(number_images)
            )

    print("summary statistics about colonies after filtering")
    print(selected_colonies.describe())
    return selected_colonies


###########################################################################


def add_colonies(well_object, colonies, hardware_settings):
    """Add colonies from Celigo scan to well.

    Input:
     well_object: instance of well_object from module samples

     colonies: pandas frame with colony information.
     This information was extracted with CellProfiler from plate-scanner images.

     hardware_settings: preferences with description of microscope components,
     here coordinate transformation between colonies and well

    Output:
     colony_list: list with all colony objects
    """
    # select all colonies that are located within well
    well = well_object.name

    well_data = colonies["Well"] == well

    # get calibration options for colonies
    x_flip = int(hardware_settings.get_pref("xFlipColony"))
    y_flip = int(hardware_settings.get_pref("yFlipColony"))
    z_flip = int(hardware_settings.get_pref("zFlipColony"))
    x_correction = float(hardware_settings.get_pref("xCorrectionColony"))
    y_correction = float(hardware_settings.get_pref("yCorrectionColony"))
    z_correction = float(hardware_settings.get_pref("zCorrectionColony"))

    # List with all colonies to be imaged
    colony_list = []
    for colony in colonies[well_data].itertuples():
        center = (colony.Center_X, colony.Center_Y, 0)
        ellipse = (colony.ColonyMajorAxis, colony.ColonyMinorAxis, colony.Orientation)
        colony_name = well + "_" + str(colony.ColonyNumber).zfill(4)
        colony_object = samples.Colony(
            name=colony_name,
            image=True,
            center=center,
            ellipse=ellipse,
            meta=colony,
            well_object=well_object,
            x_flip=x_flip,
            y_flip=y_flip,
            z_flip=z_flip,
            x_correction=x_correction,
            y_correction=y_correction,
            z_correction=z_correction,
        )

        # add additional meta data
        colony_object.set_cell_line(colony.CellLine)
        colony_object.set_clone(colony.CloneID)
        colony_object.add_meta(colony._asdict())
        colony_list.append(colony_object)
        well_object.add_colonies({colony_name: colony_object})

    return colony_list


###########################################################################


def add_barcode(name, well_object, layout):
    """Add barcode to well.

    Input:
     name: string with name for barcode

     well_object: instance of Well class from module samples

     layout: preferences for plate layout

    Output:
     none
    """
    # get calibration options for barcode
    center = [
        float(layout.get_pref("xBarcodePos")),
        float(layout.get_pref("yBarcodePos")),
        float(layout.get_pref("zBarcodePos")),
    ]
    x_flip = int(layout.get_pref("xFlipBarcode"))
    y_flip = int(layout.get_pref("yFlipBarcode"))
    z_flip = int(layout.get_pref("zFlipBarcode"))
    x_correction = float(layout.get_pref("xCorrectionBarcode"))
    y_correction = float(layout.get_pref("yCorrectionBarcode"))
    z_correction = float(layout.get_pref("zCorrectionBarcode"))

    barcode_object = samples.Barcode(
        name=name,
        well_object=well_object,
        center=center,
        x_flip=x_flip,
        y_flip=y_flip,
        z_flip=z_flip,
        x_correction=x_correction,
        y_correction=y_correction,
        z_correction=z_correction,
    )
    well_object.add_barcode({name: barcode_object})


###########################################################################


def setup_plate(prefs, colony_file=None, microscope_object=None, barcode=None):
    """Create object of class plateholder from module sample
    that holds information about all colonies scanned with plate reader.

    Input:
     prefs: preferences file for experiment

     colony_file: path to .csv file with colony data.

     microscope_object: object create by setup_microscope describing hardware components

     barcode: string barcode for plate. If not provided can be read from colony file
     or will be requested by pop-up window.

    Output:
     plate_holder_object: object that contains all wells with sample information.
    """
    # get description for microscope components
    path_hardware_settings = get_hardware_settings_path(prefs)
    specifications = Preferences(path_hardware_settings)

    # we will first get information about colonies to image.
    # Some of this information (e.g. barcode) required
    # to set up other components (e.g. plates)
    mean_diameter = None
    if colony_file is not None:
        # load file with colony data and filter colonies that should be imaged
        # get subset of preferences for colony scanning
        add_colonies_preferences = prefs.get_pref_as_meta("AddColonies")

        # calculate correction factor for wells
        colonies_path = get_colony_file_path(add_colonies_preferences, colony_file)
        colonies = get_colony_data(add_colonies_preferences, colonies_path)

        # get names of wells to scan
        wells_definitions = add_colonies_preferences.get_pref("Wells")

        colonies = filter_colonies(
            add_colonies_preferences, colonies, well_dict=wells_definitions
        )

        # get barcode from colonies and attach to plate
        barcode = colonies["PlateID"].unique()
        if barcode.size > 1:
            print("More than one barcode selected for plate. Will use only first one.")
        barcode = barcode[0]

        # calculate median well diameter
        well_minor_axis_grouped = colonies[["Well", "WellMinorAxis"]].groupby("Well")
        well_major_axis_grouped = colonies[["Well", "WellMajorAxis"]].groupby("Well")
        well_minor_axis_median = numpy.median(
            well_minor_axis_grouped.aggregate(numpy.median)
        )
        well_major_axis_median = numpy.median(
            well_major_axis_grouped.aggregate(numpy.median)
        )
        mean_diameter = numpy.mean([well_minor_axis_median, well_major_axis_median])

    # create plate holder and fill with plate, wells, colonies, cells, & water delivery
    # create plate holder and connect it to microscope
    plate_holder = specifications.get_pref_as_meta("PlateHolder")
    plate_holder_object = samples.PlateHolder(
        name=plate_holder.get_pref("Name"),
        microscope_object=microscope_object,
        stage_id=plate_holder.get_pref("StageID"),
        focus_id=plate_holder.get_pref("FocusID"),
        auto_focus_id=plate_holder.get_pref("AutoFocusID"),
        objective_changer_id=plate_holder.get_pref("ObjectiveChangerID"),
        safety_id=plate_holder.get_pref("SafetyID"),
        center=[
            plate_holder.get_pref("xCenter"),
            plate_holder.get_pref("yCenter"),
            plate_holder.get_pref("zCenter"),
        ],
        x_flip=plate_holder.get_pref("xFlip"),
        y_flip=plate_holder.get_pref("yFlip"),
        z_flip=plate_holder.get_pref("zFlip"),
        x_correction=plate_holder.get_pref("xCorrection"),
        y_correction=plate_holder.get_pref("yCorrection"),
        z_correction=plate_holder.get_pref("zCorrection"),
        x_safe_position=plate_holder.get_pref("xSafePosition"),
        y_safe_position=plate_holder.get_pref("ySafePosition"),
        z_safe_position=plate_holder.get_pref("zSafePosition"),
    )

    # create immersion delivery system as part of PlateHolder and add to PlateHolder
    pump = specifications.get_pref_as_meta("Pump")

    if pump:
        immersion_delivery_object = samples.ImmersionDelivery(
            name=pump.get_pref("Name"),
            plate_holder_object=plate_holder_object,
            center=[
                pump.get_pref("xCenter"),
                pump.get_pref("yCenter"),
                pump.get_pref("zCenter"),
            ],
            x_flip=pump.get_pref("xFlip"),
            y_flip=pump.get_pref("yFlip"),
            z_flip=pump.get_pref("zFlip"),
            x_correction=pump.get_pref("xCorrection"),
            y_correction=pump.get_pref("yCorrection"),
            z_correction=pump.get_pref("zCorrection"),
        )
        plate_holder_object.immersion_delivery_system = immersion_delivery_object

    plate = specifications.get_pref_as_meta("Plate")
    plate_object = samples.Plate(
        name=plate.get_pref("Name"),
        plate_holder_object=plate_holder_object,
        center=[
            plate.get_pref("xCenter"),
            plate.get_pref("yCenter"),
            plate.get_pref("zCenter"),
        ],
        x_flip=plate.get_pref("xFlip"),
        y_flip=plate.get_pref("yFlip"),
        z_flip=plate.get_pref("zFlip"),
        x_correction=plate.get_pref("xCorrection"),
        y_correction=plate.get_pref("yCorrection"),
        z_correction=plate.get_pref("zCorrection"),
    )

    # barcode is typically retrieved from colony file, otherwise prompt for input
    if barcode is None:
        barcode = message.read_string(
            "Barcode", "Barcode:", default="123", return_code=False
        )
    plate_object.set_barcode(barcode)
    plate_holder_object.add_plates(plate_object_dict={barcode: plate_object})

    # create Wells and add to Plate
    # get information from microscopeSpecifications.yml file
    ncol = int(specifications.get_pref("ColumnsWell"))
    n_row = int(specifications.get_pref("RowsWell"))
    pitch = float(specifications.get_pref("PitchWell"))
    diameter = float(specifications.get_pref("DiameterWell"))
    z_center_wells = float(specifications.get_pref("zCenterWell"))

    x_flip = int(specifications.get_pref("xFlipWell"))
    y_flip = int(specifications.get_pref("yFlipWell"))
    z_flip = int(specifications.get_pref("zFlipWell"))
    x_correction = float(specifications.get_pref("xCorrectionWell"))
    y_correction = float(specifications.get_pref("yCorrectionWell"))
    z_correction = float(specifications.get_pref("zCorrectionWell"))

    # create all wells for plate and add to plate
    for col_index in range(ncol - 1):
        col_name = str(col_index + 1)
        col_coord = col_index * pitch
        for row_index in range(n_row - 1):
            # create well
            row_name = string.ascii_uppercase[row_index]
            y_coord = row_index * pitch
            name = row_name + col_name

            well_object = samples.Well(
                name=name,
                center=(col_coord, y_coord, z_center_wells),
                diameter=diameter,
                plate_object=plate_object,
                well_position_numeric=(col_index, row_index),
                well_position_string=(row_name, col_name),
                x_flip=x_flip,
                y_flip=y_flip,
                z_flip=z_flip,
                x_correction=x_correction,
                y_correction=y_correction,
                z_correction=z_correction,
            )

            plate_object.add_wells({name: well_object})

    # update well diameter based on platescanner reads stored in colonies file
    if mean_diameter is not None:
        [
            well_obj.set_assigned_diameter(mean_diameter)
            for well_name, well_obj in plate_object.get_wells().items()
        ]

    # add reference well
    reference_well = plate.get_pref("InitialReferenceWell")
    reference_object = plate_object.get_well(reference_well)
    plate_object.set_reference_object(reference_object)

    # add colonies to wells
    if colony_file is not None:
        wellsColoniesList = [
            add_colonies(well_obj, colonies, specifications)
            for well_name, well_obj in plate_object.get_wells().items()
        ]

        colony_list = []
        for wellEntry in wellsColoniesList:
            if wellEntry is True:
                colony_list.extend(wellEntry)
        image_dir_key = prefs.prefs["AddColonies"]["NextName"]
        plate_object.add_to_image_dir(image_dir_key, colony_list, position=None)
        # TODO: add barcodes to wells

    # TODO:add controls to wells

    # add default reference images
    # get black reference images
    #     default_images = prefs.get_pref('DefaultImages')
    #     li = LoadImage()
    #     for reference in default_images:
    #         name = reference['Name']
    #         location = get_calibration_path(prefs) if reference['CalibrationFolder']
    #             else reference['CalibrationLocation']
    #         metaDir = {
    #             'aics_SampleType': reference['Type'],
    #             'aics_SampleName': name,
    #             'aics_barcode': barcode,
    #             'aics_filePath': location + name + reference['FileType']
    #         }
    #         ref_image = ImageAICS(meta=metaDir)
    #         li.load_image(ref_image, True)
    #         plate_holder_object.add_attached_image(name, ref_image)

    return plate_holder_object


def setup_slide(prefs, microscope_object=None):
    """Create basic object of class slide from module sample that
    consists of plate holder and slide.

    Input:
     prefs: preferences file for experiment

    Output:
     plate_holder_object: object that contains one slide.
    """
    # get description for microscope components
    path_hardware_settings = get_hardware_settings_path(prefs)
    hardware_settings = Preferences(path_hardware_settings)

    # Read settings for coordinate system of slide relative to stage (plate holder)
    # from microscopeSpecifications.yml file
    plate_holder = hardware_settings.get_pref_as_meta("PlateHolder")
    plate_holder_object = samples.PlateHolder(
        name=plate_holder.get_pref("Name"),
        microscope_object=microscope_object,
        stage_id=plate_holder.get_pref("StageID"),
        focus_id=plate_holder.get_pref("FocusID"),
        auto_focus_id=plate_holder.get_pref("AutoFocusID"),
        objective_changer_id=plate_holder.get_pref("ObjectiveChangerID"),
        safety_id=plate_holder.get_pref("SafetyID"),
        center=[
            plate_holder.get_pref("xCenter"),
            plate_holder.get_pref("yCenter"),
            plate_holder.get_pref("zCenter"),
        ],
        x_flip=plate_holder.get_pref("xFlip"),
        y_flip=plate_holder.get_pref("yFlip"),
        z_flip=plate_holder.get_pref("zFlip"),
        x_correction=plate_holder.get_pref("xCorrection"),
        y_correction=plate_holder.get_pref("yCorrection"),
        z_correction=plate_holder.get_pref("zCorrection"),
        x_safe_position=plate_holder.get_pref("xSafePosition"),
        y_safe_position=plate_holder.get_pref("ySafePosition"),
        z_safe_position=plate_holder.get_pref("zSafePosition"),
    )

    # create slide of class Sample as part of PlateHolder
    # and add it to PlateHolder get description for plate dimensions
    # and coordinate system from microscopeSpecifications.yml
    slide = hardware_settings.get_pref_as_meta("Slide")
    slide_object = samples.Slide(
        name=slide.get_pref("Name"),
        plate_holder_object=plate_holder_object,
        center=[
            slide.get_pref("xCenter"),
            slide.get_pref("yCenter"),
            slide.get_pref("zCenter"),
        ],
        x_flip=slide.get_pref("xFlip"),
        y_flip=slide.get_pref("yFlip"),
        z_flip=slide.get_pref("zFlip"),
        x_correction=slide.get_pref("xCorrection"),
        y_correction=slide.get_pref("yCorrection"),
        z_correction=slide.get_pref("zCorrection"),
    )

    reference_object = samples.Slide(
        name="Reference", plate_holder_object=slide_object, center=[0, 0, 0]
    )
    slide_object.set_reference_object(reference_object)
    plate_holder_object.add_slides({slide.get_pref("Name"): slide_object})
    return plate_holder_object
