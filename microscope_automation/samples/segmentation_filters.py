import numpy
from scipy import ndimage
import math


def filter_by_size(input_image, filter_values):
    """Function to filter segmented objects by their area.

    Input:
     input_image: The image (numpy array) to the filter to be applied on

     filter_values: (list) [minimum area, maximum area (optional)]

    Output:
     filtered_image: Image (numpy array) after applying the filter mask
    """
    # Error Checking - there should be at least one value in the list - for the min area
    min_area = 0
    if not filter_values:
        raise ValueError(
            "Filter Values not provided." " Please check the preference file."
        )
    min_area = filter_values[0]
    label_objects, nb_labels = ndimage.label(input_image)
    # Calculating the sizes of the object
    sizes = numpy.bincount(label_objects.ravel())
    if len(filter_values) == 2:
        max_area = filter_values[1]
    else:
        max_area = max(sizes)
    # Selecting objects above a certain size threshold
    size_mask = (sizes > min_area) & (sizes < max_area)
    size_mask[0] = 0
    filtered = label_objects.copy()
    filtered_image = size_mask[filtered]
    return filtered_image


def filter_by_distance(input_image, filter_values):
    """
    Function to filter segmented objects by their distance from the center of the image

    Input:
     input_image: The image (numpy array) to the filter to be applied on

     filter_values: (list) [max distance from the center, number of objects requested]

    Output:
     filtered_image: Image (numpy array) after applying the filter mask
    """
    xdim = input_image.shape[0]
    ydim = input_image.shape[1]
    if not filter_values:
        raise ValueError(
            "Filter Values not provided. Please check the preference file."
        )
    max_distance = filter_values[0]
    num_objects_requested = filter_values[1]
    center_image = (xdim / 2, ydim / 2)
    label_objects, nb_labels = ndimage.label(input_image)
    center_objects = ndimage.measurements.center_of_mass(
        input_image, label_objects, range(1, nb_labels + 1)
    )
    distance_from_center = []
    for item in center_objects:
        xdata = item[0] - center_image[0]
        ydata = item[1] - center_image[1]
        distance = math.sqrt(xdata * xdata + ydata * ydata)
        distance_from_center.append(distance)
    bool_dist = [
        False,
    ]
    # Get the list of index of colonies that pass through the distance filter
    dist_filter_index_list = []
    for index, dist in enumerate(distance_from_center):
        if dist < max_distance:
            bool_dist.append(True)
            dist_filter_index_list.append(index)
        else:
            bool_dist.append(False)
    # Rank the colonies based on size
    sizes = numpy.bincount(label_objects.ravel())
    sizes[0] = 0
    # Get the sizes that passed through the distance filter
    filtered_sizes = sizes * bool_dist
    # Calculate how many objects need to be returned
    if num_objects_requested > len(bool_dist):
        num_objects_requested = len(bool_dist)

    # Pick the last n indices based on the size
    top_sizes_indices = []
    if num_objects_requested != 0:
        top_sizes_indices = numpy.argsort(filtered_sizes)[-num_objects_requested:]

    # Update everything but those indices to be False in the mask
    for index, value in enumerate(bool_dist):
        if index not in top_sizes_indices:
            bool_dist[index] = False
    # Apply the mask
    distance_mask = numpy.asarray(bool_dist)
    filtered_image = distance_mask[label_objects]
    return filtered_image


FILTER_MAPPING = {"minArea": filter_by_size, "distFromCenter": filter_by_distance}


def apply_filter(filter_name, input_image, filter_values):
    return FILTER_MAPPING[filter_name](input_image, filter_values)
