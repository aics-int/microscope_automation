'''
Created on Aug 23, 2018

Tools to find positions for imaging
@author: winfriedw
'''
import samples
import pyqtgraph
from pyqtgraph.Qt import QtGui
from well_overview_segmentation import WellSegmentation

def copy_zero_position(sample_object, output_class, image, z_center_background = 0):
    '''Create new object with identical zero position.

    Input:
     sampleObject: object that is searched
     output_class: string with name of class of new created output object
     image: image of class imageAICS searched
     z_center_background: center of background in the z direction

    Output:
     new_objects: list with objects of class output_class
    '''
    new_objects_dict = {}
    # retrieve possible sample classes from module samples
    class_ = getattr(samples, output_class)
    if output_class == 'Background':
        bg_name = sample_object.get_name() + "_background"
        new_object = class_(name=bg_name, center=[0, 0, z_center_background], wellObject=sample_object)
        new_objects_dict[bg_name] = new_object
        # Add background to the associated plate object
        sample_object.get_container().add_attached_image(bg_name, image)
    else:
        new_object = class_()
        new_object.set_container(sample_object)

    new_objects = [new_object]
    return [new_objects, new_objects_dict]

def copy_image_position(sample_object, output_class, image, offset = (0, 0, 0)):
    '''Create new object with zero position relative to center of image.

    Input:
     sampleObject: object that is searched
     output_class: string with name of class of new created output object
     image: image of class imageAICS
     offset: offset in um relative to center of image as (x, y, z)
             Default: (0, 0, 0) (center of image)

    Output:
     new_object:  object of class output_class
    '''
    # retrieve possible sample classes from module samples
    class_ = getattr(samples, output_class)
    new_object = class_()
    new_object.set_container(sample_object)

    # get object coordinates from image position and set as zero position of new image
    x = image.get_meta('aics_imageObjectPosX') + offset[0]
    y = image.get_meta('aics_imageObjectPosY') + offset[1]
    z = image.get_meta('aics_imageObjectPosZ') + offset[2]
    new_object.set_zero(x, y, z, verbose = False)
    return new_object

def convert_location_list(location_list, image, image_type='czi'):
    """
    Function to convert the coordinates to microns and relative to the center of the image.
    First all the locations are converted to microns using the pixel size of the image
    Then the locations are converted so that they are relative to the center of the image
    instead of the bottom right corner. This calculation is done using the size of image.

    :param location_list: list of coordinates
    :param image: imageAICS object with all the meta data
    :param image_type: tiff or czi: both have different units for physical pixel size
    :return: returns the corrected location list
    """
    # 1. Convert the locations to microns
    pixel_size_datax = image.get_meta('PhysicalSizeX')  # pixel size is in um (it's in meters if cziReader is used)
    pixel_size_datay = image.get_meta('PhysicalSizeY')
    if image_type == 'czi':
        # conversion to um if type is czi
        pixel_size_datax = pixel_size_datax * 1000000
        pixel_size_datay = pixel_size_datay * 1000000
    new_location_list = []
    for location in location_list:
        xdata = location[0] * pixel_size_datax
        ydata = location[1] * pixel_size_datay
        new_location_list.append((round(xdata, 8), round(ydata, 8)))  # Rounding to 8 digits for consistency
    # 2. Convert the location relative to the center of the image
    image_sizeX = image.get_data().shape[0] * pixel_size_datax  # The length of x-dimension of the image (in microns)
    image_sizeY = image.get_data().shape[1] * pixel_size_datay  # The length of y-dimension of the image (in microns)
    location_list_relative_to_zero = []
    for location in new_location_list:
        # the origin of pixel data in ZEN blue is the top left corner
        xdata = (location[0] - image_sizeX / 2)
        ydata = (location[1] - image_sizeY / 2)
        location_list_relative_to_zero.append((round(xdata, 8), round(ydata, 8)))
    return location_list_relative_to_zero

def get_single_slice(image):
    '''Return single image slice.

    Input:
     image: image of class imageAICS

    Output:
     image_data: 2D numpy array
    '''
    image_data = image.get_data()
    if image_data.ndim == 3:
        # Remove the channel dimension before calling the location_picker module
        # Because the module only deals with the XY dimension.
        image_data = image_data[:, :, 0]
    return image_data

def location_to_object(sample_object, output_class, image, location_list):
    '''Convert position list to new objects.

    Input:
     sample_object: object that is searched
     output_class: string with name of class of new created output object
     image: image of class imageAICS
     location_list: list of coordinates
    Output:
     [new_objects, new_objects_dict]: [list with objects of class output_class, dictionary with name and objects]
    '''
        # Populate colony / cell dictionary based on output_class
    new_objects = []
    new_objects_dict = {}
    class_ = getattr(samples, output_class)
    ind = 1
    for location in location_list:
        new_object_name = sample_object.get_name() + "_{:04}".format(ind)
        ind = ind + 1
        # locations in correct_location_list are relative to the image center
        # The image center is not necessarily (0, 0, 0) in object coordinates
        # The center position of the image in object coordinates is stored in image meta data
        new_object = copy_image_position(sample_object,
                                         output_class,
                                         image,
                                         offset = (location[0], location[1], 0))

        new_objects.append(new_object)
        new_objects_dict[new_object_name] = new_object
    return [new_objects, new_objects_dict]

def find_interactive_position(sample_object, output_class, image, app):
    '''Create new object with zero position based on interactive selection.

    Input:
     sampleObject: object that is searched
     output_class: string with name of class of new created output object
     image: image of class imageAICS
     app: object of class QtGui.QApplication

    Output:
     new_objects: list with objects of class output_class
    '''
    image_data = get_single_slice(image)

    pre_plotted_locations = []
    location_list = sample_object.set_interactive_positions(image_data, pre_plotted_locations, app)
    print("Locations clicked = ", location_list)
    correct_location_list = convert_location_list(location_list, image)
    print("Correct location list = ", correct_location_list)
    return location_to_object(sample_object, output_class, image, correct_location_list)

def segmentation(image_data, segmentation_type = 'colony', segmentation_settings = None ):
    '''Different algorithms to segment sample.
    Input:
     image_data: 2D numpy array with image data
     segmentation_type: possible values:
                         'colony': segment hiPSC colonies (default)
                         'otsu': intensity  segmentation based on Ostu algorithm
     segmentation_settings: settings from preferences file
                            Default (None) use default settings

    Output:
     segmented_position_list: list with (x, y) positions
    '''
    if segmentation_type == 'colony':
        # 1. Call segment well module to find imageable positions
        filters = segmentation_settings.getPref('Filters')
        try:
            canny_sigma = segmentation_settings.getPref('CannySigma')
            canny_low_threshold = segmentation_settings.getPref('CannyLowThreshold')
            remove_small_holes_area_threshold = segmentation_settings.getPref('RemoveSmallHolesAreaThreshold')
            segmented_well = WellSegmentation(image_data, colony_filters_dict=filters, mode='A',
                                              canny_sigma=canny_sigma, canny_low_threshold=canny_low_threshold,
                                              remove_small_holes_area_threshold=remove_small_holes_area_threshold)
        except:
            # if the preferences are not set, call with default ones
            segmented_well = WellSegmentation(image_data, colony_filters_dict=filters)

        segmented_well.segment_and_find_positions()
        segmented_position_list = segmented_well.point_locations
    return segmented_position_list

def find_interactive_distance_map(sample_object, output_class, image, segmentation_settings = None, app = None):
    '''Create new object with zero position based on interactive selection.

    Input:
     sampleObject: object that is searched
     output_class: string with name of class of new created output object
     image: image of class imageAICS
     segmentation_settings: settings from preferences file
     app: object of class QtGui.QApplication

    Output:
     [new_objects, new_objects_dict]: [list with objects of class output_class, dictionary with name and objects]
    '''
    image_data = get_single_slice(image)

    segmented_position_list = segmentation(image_data, segmentation_type = 'colony', segmentation_settings = segmentation_settings )

    # 2. Call image location picker module to let the user adjust positions to image further
    location_list = sample_object.set_interactive_positions(image_data, segmented_position_list, app)
    print("Cells selected at positions (in coordinates): ", location_list)
    # 3. Change the location list into microns & relative to the center of the well
    correct_location_list = convert_location_list(location_list, image)
    print("Cells selected at positions (in microns): ", correct_location_list)
    return location_to_object(sample_object, output_class, image, correct_location_list)



def create_output_objects_from_parent_object(find_type,
                                             sample_object,
                                             imaging_settings,
                                             image,
                                             output_class,
                                             app,
                                             offset = (0, 0, 0)):
    """ This function has methods to create output objects (cells, colonies, background)
    from the parent object(Well, colony)

    Input:
     find_type: string with name of search algorithm
                 'copy_zero_position': keep position
                 'copy_image_position': use center of image as object zero position
                 'CenterMassCellProfiler' : find cells using cell profiler
                 'TwofoldDistanceMap' : find cells in a colony using two fold distance map
                 'Interactive': select position interactively
                 'InteractiveDistanceMap': shows recommended positions (by segmentation)& can select them interactively
     sampleObject: object that is searched
     sample_counter: Which sample number is it on
     number_of_samples: Total number of samples being scanned in the experiment, to interrupt only after the last object
     imaging_settings: settings from preferences file
     image: image of class imageAICS searched
     output_class: class of new created output object
     app: object of class QtGui.QApplication
     offset: offset in um relative to center of image as (x, y, z)
             Default: (0, 0, 0) (center of image)

    Output:
     [new_objects, new_objects_dict]: [list with objects of class output_class, dictionary with name and objects]
    """
#     pathHardwareSettings = setupAutomation.get_hardware_settings_path(imaging_settings)
#     hardwareSettings = preferences.Preferences(pathHardwareSettings)
#     z_center_background = hardwareSettings.getPref('zCenterBackground')
    new_objects = None
    new_objects_dict = {}

    # copy objects from previous step
    if find_type == 'copy_zero_position':
        return_objects = copy_zero_position(sample_object, output_class, image, z_center_background = 0)
        return return_objects

    if find_type == 'copy_image_position':
        new_object = copy_image_position(sample_object, output_class, image, offset = offset)
        new_objects = [new_object]

    # find cells and add them to colony
    if find_type == 'CenterMassCellProfiler':
        # Called on the colony object to find cells using cell profiler
        if isinstance(sample_object, samples.Colony):
            sample_object.find_cells_cell_profiler(imaging_settings, image)
            new_objects_dict = sample_object.get_cells()
            new_objects = new_objects_dict.values()
        else:
            raise TypeError("CenterMassCellProfiler not called on colony object")

    if find_type == 'TwofoldDistanceMap':
        # Called on the colony object to find cells using two fold distance map
        if isinstance(sample_object, samples.Colony):
            sample_object.find_cells_distance_map(imaging_settings, image)
            new_objects_dict = sample_object.get_cells()
            new_objects = new_objects_dict.values()
        else:
            raise TypeError("TwofoldDistanceMap can currently only called on a colony object")

    if find_type == 'Interactive':
        # Called on Well object to interactively select colonies
        return_objects = find_interactive_position(sample_object, output_class, image, app)
        return return_objects

    if find_type == 'InteractiveDistanceMap':
        # Called on a well object to find cells using two fold distance map
        return_objects = find_interactive_distance_map(sample_object,
                                                       output_class,
                                                       image,
                                                       segmentation_settings = imaging_settings,
                                                       app = app)
        return return_objects

    if find_type == 'None':
        # Do nothing and return empty object list
        new_objects = None

    return [new_objects, new_objects_dict]




def test_findInteractive(prefs, image_save_path, find_types = ['copy_image_position'], app = None):
    '''Test find_interactive position for one objective.

    Input:
     prefs: path to experiment preferences
     image_save_path: path to directory to save test images
     find_types: list with algorithms to be tested
     app: object of class QtGui.QApplication
    '''
    # print debug messages?
    verbose = False
    test_ok = False

    # setup microscope
    import setupAutomation
    import microscopeAutomation

    microscope_object = setupAutomation.setup_microscope(prefs)

    # setup plateholder with slide
    plate_holder_object = setupAutomation.setup_slide(prefs, microscopeObject = microscope_object)
    # get slide object, we will need object coordinates in order reference correction to work
    slide_object = plate_holder_object.get_slide()

    # set initialization experiment for definite focus to experiment used to locate reference object
    objective_changer = microscope_object.get_microscope_object('6xMotorizedNosepiece')

    # switch to live mode with 20 x and select position
    microscope_object.live_mode(camera_id = 'Camera1 (Back)', experiment = 'Setup_20x', live = True)
    # set position for next experiments
    raw_input('Move to image position')
    images = slide_object.acquire_images('ScanWell_20x',
                                         'Camera1 (Back)',
                                         reference_object = slide_object.get_reference_object(),
                                         filePath = image_save_path + 'image1.czi',
                                         posList = None,
                                         load = False,
                                         verbose = False)


    # find position of new object
    image = microscope_object.load_image(images[0], getMeta=True)
    imaging_settings = prefs.getPrefAsMeta('SegmentWells')
    for find_type in find_types:
        nextExperimentObjectsList = create_output_objects_from_parent_object(find_type,
                                                                             slide_object,
                                                                             imaging_settings = imaging_settings,
                                                                             image = image,
                                                                             output_class = 'Cell',
                                                                             app = app,
                                                                             offset = (0, 0, 0))
        print('Zero position of new Cell object: {}'.format(nextExperimentObjectsList[0][0].get_zero()))
        nextExperimentObjects = nextExperimentObjectsList[0]

        for sample_object in nextExperimentObjects:
            # not tested after changing to get_zero
            posList = sample_object.get_zero(load = False,
                                             verbose = False)
            images = sample_object.acquire_images('CellStack_20x',
                                              'Camera1 (Back)',
                                              reference_object = slide_object.get_reference_object(),
                                              filePath = None,
                                              posList = posList,
                                              load = False,
                                              verbose = False)

def test_findPositions(prefs, image_save_path, find_types = ['copy_image_position'], app = None):
    '''Test different aspects of findPositions.

    Input:
     prefs: path to experiment preferences
     image_save_path: path to directory to save test images
     find_types: list with algorithms to be tested
     app: object of class QtGui.QApplication

    '''
    # print debug messages?
    verbose = False

    # setup microscope
    import setupAutomation

    microscope_object = setupAutomation.setup_microscope(prefs)

    # setup plateholder with slide
    plate_holder_object = setupAutomation.setup_slide(prefs, microscopeObject = microscope_object)
    # get slide object, we will need object coordinates in order reference correction to work
    slide_object = plate_holder_object.get_slide()

    # set initialization experiment for definite focus to experiment used to locate reference object
    objective_changer = microscope_object.get_microscope_object('6xMotorizedNosepiece')

    # set objective offset for 20x and 10x
    objective_changer.set_init_experiment('Setup_20x')
    # include setting load position in initialization
    microscope_object.initialize_hardware(initialize_components_OrderedDict = {'MotorizedFocus': {'set_load'}, '6xMotorizedNosepiece': {'no_find_surface'}},
                                 reference_object = slide_object.get_reference_object(),
                                 trials = 3,
                                 verbose = verbose)

    objective_changer.set_init_experiment('Setup_10x')
    microscope_object.initialize_hardware(initialize_components_OrderedDict = {'6xMotorizedNosepiece': {'no_find_surface'}},
                                 reference_object = slide_object.get_reference_object(),
                                 trials = 3,
                                 verbose = verbose)


    # switch to live mode with 10 x and select position
    microscope_object.live_mode(camera_id = 'Camera1 (Back)', experiment = 'Setup_20x', live = True)
    # set position for next experiments
    raw_input('Move to image position 1')
    images_1 = slide_object.acquire_images('ScanWell_20x',
                                         'Camera1 (Back)',
                                         reference_object = slide_object.get_reference_object(),
                                         filePath = image_save_path + 'image1.czi',
                                         posList = None,
                                         load = False,
                                         verbose = False)

    # find position of new objects using different algorithms
    image = microscope_object.load_image(images_1[0], getMeta=True)
    imaging_settings = prefs.getPrefAsMeta('SegmentWells')

    nextExperimentObjects = []
    for find_type in find_types:
        nextExperimentObjectsList = create_output_objects_from_parent_object(find_type,
                                                                                 slide_object,
                                                                                 imaging_settings = imaging_settings,
                                                                                 image = image,
                                                                                 output_class = 'Cell',
                                                                                 app = app,
                                                                                 offset = (0, 0, 0))


    nextExperimentObjects.extend(nextExperimentObjectsList[0])

    objective_changer_object = microscope_object.get_microscope_object('6xMotorizedNosepiece')

    for i in range(1):
        for sample_object in nextExperimentObjects:
            # image object with 10x
            objective_name = microscope_object.change_objective('CellStack_10x', objective_changer_object)
            print('New objective: {}'.format(objective_name))
            # not tested after changing to get_zero
            posList = [sample_object.get_abs_zero()]
            images = sample_object.acquire_images('CellStack_10x',
                                              'Camera1 (Back)',
                                              reference_object = slide_object.get_reference_object(),
                                              filePath = None,
                                              posList = posList,
                                              load = False,
                                              verbose = False)

            objective_name = microscope_object.change_objective('CellStack_20x', objective_changer_object)
            print('New objective: {}'.format(objective_name))
            sample_object.move_to_zero(load = False,
                                     verbose = False)
            images = sample_object.acquire_images('CellStack_20x',
                                                 'Camera1 (Back)',
                                                 reference_object = slide_object.get_reference_object(),
                                                 filePath = None,
                                                 posList = None,
                                                 load = False,
                                                 verbose = False)



if __name__ == '__main__':
    # load preferences
    import argparse
    from getPath import *
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument('-p', '--preferences', help="path to the preferences file")
    args = arg_parser.parse_args()
    if args.preferences is not None:
        set_pref_file(args.preferences)

    prefs = Preferences(get_prefs_path())
    image_save_path = 'D:\\Winfried\\Production\\testing\\'
#     image_save_path = '/Users/winfriedw/Documents/Programming/ResultTestImages'

#     find_types = ['copy_zero_position', 'copy_image_position', 'Interactive', 'InteractiveDistanceMap']
    find_types = ['Interactive']
    # initialize the pyqt application object here (not in the location picker module)
    # as it only needs to be initialized once
    app = QtGui.QApplication([])
#     test_findInteractive(prefs = prefs,
#                        image_save_path = image_save_path,
#                        find_types = find_types,
#                        app = app)
    test_findPositions(prefs = prefs,
                       image_save_path = image_save_path,
                       find_types = find_types,
                       app = app)
    print('Done')
    # Properly close pyqtgraph to avoid exit crash
    pyqtgraph.exit()
    print('After exit pyqtgraph')
