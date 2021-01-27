"""
Created on Aug 23, 2018

Tools to find positions for imaging
@author: winfriedw
"""
from microscope_automation.samples import samples
from microscope_automation.samples.well_overview_segmentation import WellSegmentation


def copy_zero_position(sample_object, output_class, image, z_center_background=0):
    """Create new object with identical zero position.

    Input:
     sampleObject: object that is searched

     output_class: string with name of class of new created output object

     image: image of class imageAICS searched

     z_center_background: center of background in the z direction

    Output:
     new_objects: list with objects of class output_class
    """
    new_objects_dict = {}
    # retrieve possible sample classes from module samples
    class_ = getattr(samples, output_class)
    if output_class == "Background":
        bg_name = sample_object.get_name() + "_background"
        new_object = class_(
            name=bg_name, center=[0, 0, z_center_background], well_object=sample_object
        )
        new_objects_dict[bg_name] = new_object
        # Add background to the associated plate object
        sample_object.get_container().add_attached_image(bg_name, image)
    else:
        new_object = class_()
        new_object.set_container(sample_object)

    new_objects = [new_object]
    return [new_objects, new_objects_dict]


def copy_image_position(sample_object, output_class, image, offset=(0, 0, 0)):
    """Create new object with zero position relative to center of image.

    Input:
     sample_object: object that is searched

     output_class: string with name of class of new created output object

     image: image of class imageAICS

     offset: offset in um relative to center of image as (x, y, z)
             Default: (0, 0, 0) (center of image)

    Output:
     new_object: object of class output_class
    """
    # retrieve possible sample classes from module samples
    class_ = getattr(samples, output_class)
    new_object = class_()
    new_object.set_container(sample_object)

    # get object coordinates from image position and set as zero position of new image
    x = image.get_meta("aics_imageObjectPosX") + offset[0]
    y = image.get_meta("aics_imageObjectPosY") + offset[1]
    z = image.get_meta("aics_imageObjectPosZ") + offset[2]
    new_object.set_zero(x, y, z, verbose=False)
    return new_object


def convert_location_list(location_list, image, image_type="czi"):
    """Function to convert the coordinates to microns
    and relative to the center of the image.
    First all the locations are converted to microns using the pixel size of the image.
    Then the locations are converted so that they are relative
    to the center of the image instead of the bottom right corner.
    This calculation is done using the size of image.

    Input:
     location_list: list of coordinates

     image: imageAICS object with all the meta data

     image_type: tiff or czi: both have different units for physical pixel size

    Output:
     location_list_relative_to_zero: corrected location list
    """
    # 1. Convert the locations to microns
    # pixel size is in um (it's in meters if cziReader is used)
    pixel_size_data_x = image.get_meta("PhysicalSizeX")
    pixel_size_data_y = image.get_meta("PhysicalSizeY")
    if image_type == "czi":
        # conversion to um if type is czi
        pixel_size_data_x = pixel_size_data_x * 1000000
        pixel_size_data_y = pixel_size_data_y * 1000000
    new_location_list = []
    for location in location_list:
        xdata = location[0] * pixel_size_data_x
        ydata = location[1] * pixel_size_data_y
        # Rounding to 8 digits for consistency
        new_location_list.append((round(xdata, 8), round(ydata, 8)))
    # 2. Convert the location relative to the center of the image
    # The length of x-dimension of the image (in microns)
    image_size_x = image.get_data().shape[0] * pixel_size_data_x
    # The length of y-dimension of the image (in microns)
    image_size_y = image.get_data().shape[1] * pixel_size_data_y
    location_list_relative_to_zero = []
    for location in new_location_list:
        # the origin of pixel data in ZEN blue is the top left corner
        xdata = location[0] - image_size_x / 2
        ydata = location[1] - image_size_y / 2
        location_list_relative_to_zero.append((round(xdata, 8), round(ydata, 8)))
    return location_list_relative_to_zero


def get_single_slice(image):
    """Return single image slice.

    Input:
     image: image of class imageAICS

    Output:
     image_data: 2D numpy array
    """
    image_data = image.get_data()
    if image_data.ndim == 3:
        # Remove the channel dimension before calling the location_picker module
        # Because the module only deals with the XY dimension.
        image_data = image_data[:, :, 0]
    return image_data


def location_to_object(sample_object, output_class, image, location_list):
    """Convert position list to new objects.

    Input:
     sample_object: object that is searched

     output_class: string with name of class of new created output object

     image: image of class imageAICS

     location_list: list of coordinates

    Output:
     [new_objects, new_objects_dict]: [list with objects of class output_class,
     dictionary with name and objects]
    """
    # Populate colony / cell dictionary based on output_class
    new_objects = []
    new_objects_dict = {}
    # class_ = getattr(samples, output_class)
    ind = 1
    for location in location_list:
        new_object_name = sample_object.get_name() + "_{:04}".format(ind)
        ind = ind + 1
        # locations in correct_location_list are relative to the image center
        # The image center is not necessarily (0, 0, 0) in object coordinates
        # Center position of the image in object coordinates stored in image meta data
        new_object = copy_image_position(
            sample_object, output_class, image, offset=(location[0], location[1], 0)
        )

        new_objects.append(new_object)
        new_objects_dict[new_object_name] = new_object
    return [new_objects, new_objects_dict]


def find_interactive_position(sample_object, output_class, image, app):
    """Create new object with zero position based on interactive selection.

    Input:
     sample_object: object that is searched

     output_class: string with name of class of new created output object

     image: image of class imageAICS

     app: object of class QtGui.QApplication

    Output:
     new_objects: list with objects of class output_class
    """
    image_data = get_single_slice(image)

    pre_plotted_locations = []
    location_list = sample_object.set_interactive_positions(
        image_data, pre_plotted_locations, app
    )
    print("Locations clicked = ", location_list)
    correct_location_list = convert_location_list(location_list, image)
    print("Correct location list = ", correct_location_list)
    return location_to_object(sample_object, output_class, image, correct_location_list)


def segmentation(image_data, segmentation_type="colony", segmentation_settings=None):
    """Different algorithms to segment sample.

    Input:
     image_data: 2D numpy array with image data

     segmentation_type: possible values:
      'colony': segment hiPSC colonies (default)
      'otsu': intensity  segmentation based on Ostu algorithm

     segmentation_settings: settings from preferences file.
     Default (None) use default settings

    Output:
     segmented_position_list: list with (x, y) positions
    """
    if segmentation_type == "colony":
        # 1. Call segment well module to find imageable positions
        filters = segmentation_settings.getPref("Filters")
        try:
            canny_sigma = segmentation_settings.getPref("CannySigma")
            canny_low_threshold = segmentation_settings.getPref("CannyLowThreshold")
            remove_small_holes_area_threshold = segmentation_settings.getPref(
                "RemoveSmallHolesAreaThreshold"
            )
            segmented_well = WellSegmentation(
                image_data,
                colony_filters_dict=filters,
                mode="A",
                canny_sigma=canny_sigma,
                canny_low_threshold=canny_low_threshold,
                remove_small_holes_area_threshold=remove_small_holes_area_threshold,
            )
        except Exception:
            # if the preferences are not set, call with default ones
            segmented_well = WellSegmentation(image_data, colony_filters_dict=filters)

        segmented_well.segment_and_find_positions()
        segmented_position_list = segmented_well.point_locations
    return segmented_position_list


def find_interactive_distance_map(
    sample_object, output_class, image, segmentation_settings=None, app=None
):
    """Create new object with zero position based on interactive selection.

    Input:
     sampleObject: object that is searched

     output_class: string with name of class of new created output object

     image: image of class imageAICS

     segmentation_settings: settings from preferences file

     app: object of class QtGui.QApplication

    Output:
     [new_objects, new_objects_dict]: [list with objects of class output_class,
     dictionary with name and objects]
    """
    image_data = get_single_slice(image)

    segmented_position_list = segmentation(
        image_data,
        segmentation_type="colony",
        segmentation_settings=segmentation_settings,
    )

    # 2. Call image location picker module to let the user adjust positions
    location_list = sample_object.set_interactive_positions(
        image_data, segmented_position_list, app
    )
    print("Cells selected at positions (in coordinates): ", location_list)
    # 3. Change the location list into microns & relative to the center of the well
    correct_location_list = convert_location_list(location_list, image)
    print("Cells selected at positions (in microns): ", correct_location_list)
    return location_to_object(sample_object, output_class, image, correct_location_list)


def create_output_objects_from_parent_object(
    find_type,
    sample_object,
    imaging_settings,
    image,
    output_class,
    app,
    offset=(0, 0, 0),
):
    """This function has methods to create output objects (cells, colonies, background)
    from the parent object(Well, colony)

    Input:
     find_type: string with name of search algorithm. Possible values:
      'copy_zero_position': keep position
      'copy_image_position': use center of image as object zero position
      'CenterMassCellProfiler' : find cells using cell profiler
      'TwofoldDistanceMap' : find cells in a colony using two fold distance map
      'Interactive': select position interactively
      'InteractiveDistanceMap': shows recommended positions (by segmentation)
      & can select them interactively

     sample_object: object that is searched

     imaging_settings: settings from preferences file

     image: image of class imageAICS searched

     output_class: class of new created output object

     app: object of class QtGui.QApplication

     offset: offset in um relative to center of image as (x, y, z)
             Default: (0, 0, 0) (center of image)

    Output:
     [new_objects, new_objects_dict]: [list with objects of class output_class,
     dictionary with name and objects]
    """
    new_objects = None
    new_objects_dict = {}

    # copy objects from previous step
    if find_type == "copy_zero_position":
        return_objects = copy_zero_position(
            sample_object, output_class, image, z_center_background=0
        )
        return return_objects

    if find_type == "copy_image_position":
        new_object = copy_image_position(
            sample_object, output_class, image, offset=offset
        )
        new_objects = [new_object]

    # find cells and add them to colony
    if find_type == "CenterMassCellProfiler":
        # Called on the colony object to find cells using cell profiler
        if isinstance(sample_object, samples.Colony):
            sample_object.find_cells_cell_profiler(imaging_settings, image)
            new_objects_dict = sample_object.get_cells()
            new_objects = new_objects_dict.values()
        else:
            raise TypeError("CenterMassCellProfiler not called on colony object")

    if find_type == "TwofoldDistanceMap":
        # Called on the colony object to find cells using two fold distance map
        if isinstance(sample_object, samples.Colony):
            sample_object.find_cells_distance_map(imaging_settings, image)
            new_objects_dict = sample_object.get_cells()
            new_objects = new_objects_dict.values()
        else:
            raise TypeError(
                "TwofoldDistanceMap can currently only called on a colony object"
            )

    if find_type == "Interactive":
        # Called on Well object to interactively select colonies
        return_objects = find_interactive_position(
            sample_object, output_class, image, app
        )
        return return_objects

    if find_type == "InteractiveDistanceMap":
        # Called on a well object to find cells using two fold distance map
        return_objects = find_interactive_distance_map(
            sample_object,
            output_class,
            image,
            segmentation_settings=imaging_settings,
            app=app,
        )
        return return_objects

    if find_type == "None":
        # Do nothing and return empty object list
        new_objects = None

    return [new_objects, new_objects_dict]
