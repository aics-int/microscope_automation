from aicsimageio import AICSImage
from matplotlib.pyplot import imshow, show, rcParams
import numpy
import skimage
import time
import random
from .interactive_location_picker_pyqtgraph import \
    ImageLocationPicker  # Module to implement selecting points on an image
from skimage import exposure, feature, morphology
from scipy import ndimage
from . import segmentation_filters
rcParams['figure.figsize'] = 15, 12

# TODO Change print statements to log


class WellSegmentation:

    def __init__(self, image_data, x_border_list=[], y_border_list=[], colony_filters_dict=None, mode='A'):
        """
        :param
        image_data =  numpy image data Image to be segmented (Well or colony)
        x_border_list = list of borders in the x dimension for the individual images that were tiled
        y_border_list = list of borders in the y dimension for the individual images that were tiled
        filters_dict = dictionary of filters to be applied { filter_name: filter_values}
        """
        self.data = image_data
        self.image_locations = []  # list of locations of the imageable points
        self.cell_dict = {}
        self.x_border_list = x_border_list
        self.y_border_list = y_border_list
        self.colony_filters_dict = colony_filters_dict
        if mode == 'A' or mode == 'C':
            self.mode = mode
        else:
            raise ValueError("Invalid value of mode. Mode can only be 'A' or 'C'. Please check the preference file.")

    def segment_and_find_positions(self):
        """
        Function segments out the colonies, applied filters and find the smooth points based on the mode
        :return:
        """
        print("Starting to adjust sigmoid")
        sigmoid = exposure.adjust_sigmoid(self.data, 0.3, 12)
        print("Starting gamma exposure")
        gamma = exposure.adjust_gamma(sigmoid, 3)
        print("Starting Canny filtering")
        start = time.time()
        g_edges = skimage.feature.canny(gamma, 0.5)
        print(("Finished in {} seconds".format(time.time() - start)))
        xdim = self.data.shape[0]
        ydim = self.data.shape[1]

        # Removing borders between the individual images that were tiled together
        # Reason - when the individual tiles are stitched together, there are wide borders left which
        # show up in the edge detection, which gives wrong results
        for y in self.y_border_list:
            g_edges[0:xdim, y-10:y+10] = 0
        for x in self.x_border_list:
            g_edges[x-10:x+10, 0:ydim] = 0

        print("Starting dilation")
        dilation = morphology.dilation(g_edges, morphology.diamond(12))
        print("Starting to fill binary holes")
        filled = ndimage.binary_fill_holes(dilation)
        print("Starting erosion")
        eroded = morphology.erosion(filled, morphology.diamond(13))
        # Apply filters
        print("Applying filters")
        filtered_image = eroded
        if self.colony_filters_dict is not None:
            for filter_name in list(self.colony_filters_dict.keys()):
                filtered_image = segmentation_filters.apply_filter(filter_name, filtered_image,
                                                                   self.colony_filters_dict[filter_name])

        colony_edges = morphology.dilation(feature.canny(filtered_image, 0))
        print("Starting outlining")
        outline = self.data.copy()
        self.data[colony_edges] = 65535
        imshow(outline)
        show()
        distance = ndimage.distance_transform_edt(filtered_image)
        smoothed_well = ndimage.gaussian_filter(self.data, 0.75)
        outline_dot = outline.copy()
        objs, num_objs = ndimage.label(filtered_image)
        print("Applying filters for points")
        if self.mode == 'A':
            # point selection: Smoothest point in the center region
            for obj in range(1, num_objs + 1):
                print(("On object {} of {}".format(obj, num_objs)))
                mask = objs == obj
                dist_mask = distance * mask
                # for each colony, find the maximum distance from the two fold distance map.
                # The edge is at 0% and the center of the colony is at 100%
                d_max = dist_mask.max()
                # Getting the points which is at least 25% away from the edge
                top_percent = dist_mask > (d_max * 0.25)
                colony_mask = smoothed_well * top_percent
                colony_edges = feature.canny(colony_mask)
                # applying the second distance transform to find the smoothest point in the correct region
                inner_edges = ndimage.distance_transform_edt(~colony_edges * top_percent)
                smooth_point = numpy.where(inner_edges == inner_edges.max())
                smooth_point = (smooth_point[0][0], smooth_point[1][0])
                self.image_locations.append(smooth_point)
        elif self.mode == 'C':
            for obj in range(1, num_objs + 1):
                print(("On object {} of {}".format(obj, num_objs)))
                mask = objs == obj
                dist_mask = distance * mask
                # point selection: edge, ridge & center respectively
                self.get_mode_c_points(dist_mask, 0, 0.03)
                self.get_mode_c_points(dist_mask, 0.15, 0.20)
                self.get_mode_c_points(dist_mask, 0.90, 0.99)
        return

    def get_mode_c_points(self, dist_mask, threshold_min, threshold_max):
        """
        Function to find a point at the center, edge & ridge in a colony
        :param dist_mask: The image with two fold distance map applied
        :param threshold_min: The minimum percentage threshold for the distance from the edge
        :param threshold_max: The maximum percentage threshold for the distance from the edge
        :return: the location of the point
        """
        d_max = dist_mask.max()
        # apply the threshold- different for different type of points
        threshold_mask = (dist_mask > (threshold_min * d_max)) & (dist_mask <= (threshold_max * d_max))
        # extract the locations of the points that fulfill that threshold condition
        locations_true = numpy.argwhere(threshold_mask == 1)
        # Randomly pick a point from that list
        smooth_point_list = random.sample(locations_true.tolist(), 1)
        # random.sample returns a list (with one element in this case). Hence extract the element
        smooth_point = smooth_point_list[0]
        self.image_locations.append(smooth_point)
        return smooth_point


if __name__ == "__main__":
    im_path = '../data/test_data_shailja/segmentation/wellScanD7_80.tif'
    img = AICSImage(im_path)
    # Hard - coded borders for testing
    y_border_list = [657, 1316, 1973, 2632, 3290, 3947, 4606]
    x_border_list = [926, 1852, 2778, 3704, 4630]
    colony_filters = {
                'minArea': [60000],        # min & max area of the colony
                'distFromCenter': [45500, 5]         # max distance from center & the number of colonies you want
            }
    seg = WellSegmentation(img.data[0, 0, 0], x_border_list, y_border_list,
                           colony_filters_dict=colony_filters, mode='A')
    import cProfile
    cProfile.run('seg.segment_and_find_positions()')
    print("Testing")
    #interactive_image = ImageLocationPicker(seg.data, seg.image_locations)
    #interactive_image.plot_points("Well Overview Image")

