from matplotlib.pyplot import rcParams
import numpy
import skimage
import random
from skimage import exposure, feature, morphology, transform
from scipy import ndimage
from . import segmentation_filters

rcParams["figure.figsize"] = 15, 12
DOWNSCALING_FACTOR = 4


class WellSegmentation:
    def __init__(
        self,
        image_data,
        colony_filters_dict=None,
        mode="A",
        canny_sigma=0.01,
        canny_low_threshold=0.025,
        remove_small_holes_area_threshold=1000,
    ):
        """
        Input:
         image_data =  numpy image data Image to be segmented (Well or colony)

         filters_dict = dictionary of filters to be applied {filter_name: filter_values}
        """
        self.data = image_data
        self._point_locations = []
        # Downscale the colony dictionary
        self.colony_filters_dict = self.downscale_filter_dictionary(colony_filters_dict)
        if mode == "A" or mode == "C":
            self.mode = mode
        else:
            raise ValueError(
                "Invalid value of mode. Mode can only be 'A' or 'C'."
                " Please check the preference file."
            )
        self.canny_sigma = canny_sigma
        self.canny_low_threshold = canny_low_threshold
        self.remove_small_holes_area_threshold = remove_small_holes_area_threshold

    def downscale_filter_dictionary(self, colony_filters_dict):
        colony_filters_dict_corrected = {}
        colony_filters_dict_corrected["distFromCenter"] = [
            colony_filters_dict["distFromCenter"][0] / DOWNSCALING_FACTOR,
            colony_filters_dict["distFromCenter"][1],
        ]
        colony_filters_dict_corrected["minArea"] = []
        for value in colony_filters_dict["minArea"]:
            colony_filters_dict_corrected["minArea"].append(
                value / (DOWNSCALING_FACTOR ** 2)
            )
        return colony_filters_dict_corrected

    @property
    def point_locations(self):
        return self._point_locations

    def segment_and_find_positions(self):
        """Function segments out the colonies, applied filters
        and find the smooth points based on the mode

        Input:
         none
        Output:
         none
        """
        initial_image = self.data
        xdim = self.data.shape[0]

        ydim = self.data.shape[1]
        downsized_image = transform.resize(
            initial_image,
            (xdim / DOWNSCALING_FACTOR, ydim / DOWNSCALING_FACTOR),
            mode="constant",
        )
        rescaled_image = exposure.rescale_intensity(downsized_image)
        print("Starting Canny filtering")
        g_edges = skimage.feature.canny(
            rescaled_image,
            sigma=self.canny_sigma,
            low_threshold=self.canny_low_threshold,
        )
        print("Starting dilation")
        dilation = morphology.dilation(g_edges, morphology.disk(3))
        print("Starting erosion")
        eroded = morphology.erosion(dilation, morphology.disk(4))
        dilation = morphology.dilation(
            eroded, morphology.diamond(4)
        )  # Dont change to disk
        print("Starting to remove small holes")
        filled = morphology.remove_small_holes(
            dilation, area_threshold=self.remove_small_holes_area_threshold
        )
        print("Starting erosion")
        eroded = morphology.erosion(filled, morphology.diamond(3))
        print("Applying filters")
        filtered_image = eroded
        if self.colony_filters_dict is not None:
            for filter_name in self.colony_filters_dict.keys():
                filtered_image = segmentation_filters.apply_filter(
                    filter_name, filtered_image, self.colony_filters_dict[filter_name]
                )

        colony_edges = morphology.dilation(feature.canny(filtered_image, 0.01))
        print("Starting outlining")
        outline = downsized_image.copy()
        outline[colony_edges] = 65535
        distance = ndimage.distance_transform_edt(filtered_image)
        smoothed_well = ndimage.gaussian_filter(downsized_image, 0.35)
        outline.copy()
        objs, num_objs = ndimage.label(filtered_image)
        print("Applying filters for points")
        if self.mode == "A":
            # point selection: Smoothest point in the center region
            for obj in range(1, num_objs + 1):
                print("On object {} of {}".format(obj, num_objs))
                mask = objs == obj
                dist_mask = distance * mask
                # for each colony,
                # find the maximum distance from the two fold distance map.
                # The edge is at 0% and the center of the colony is at 100%
                d_max = dist_mask.max()
                # Getting the points which is at least 40% away from the edge
                top_percent = dist_mask > (d_max * 0.40)
                colony_mask = smoothed_well * top_percent
                colony_edges = feature.canny(colony_mask, 0.1)
                # applying the second distance transform
                # to find the smoothest point in the correct region
                inner_edges = ndimage.distance_transform_edt(
                    ~colony_edges * top_percent
                )
                smooth_point = numpy.where(inner_edges == inner_edges.max())
                smooth_point = (smooth_point[0][0], smooth_point[1][0])
                smooth_point_corrected = (
                    smooth_point[0] * DOWNSCALING_FACTOR,
                    smooth_point[1] * DOWNSCALING_FACTOR,
                )
                self._point_locations.append(smooth_point_corrected)
        elif self.mode == "C":
            for obj in range(1, num_objs + 1):
                print("On object {} of {}".format(obj, num_objs))
                mask = objs == obj
                dist_mask = distance * mask
                # point selection: edge, ridge & center respectively
                self.get_mode_c_points(dist_mask, 0, 0.03)
                self.get_mode_c_points(dist_mask, 0.15, 0.20)
                self.get_mode_c_points(dist_mask, 0.90, 0.99)

    def get_mode_c_points(self, dist_mask, threshold_min, threshold_max):
        """Function to find a point at the center, edge & ridge in a colony

        Input:
         dist_mask: The image with two fold distance map applied

         threshold_min: The minimum percentage threshold for the distance from the edge

         threshold_max: The maximum percentage threshold for the distance from the edge

        Output:
         smooth_point_corrected: the location of the point
        """
        d_max = dist_mask.max()
        # apply the threshold- different for different type of points
        threshold_mask = (dist_mask > (threshold_min * d_max)) & (
            dist_mask <= (threshold_max * d_max)
        )
        # extract the locations of the points that fulfill that threshold condition
        locations_true = numpy.argwhere(threshold_mask == 1)
        # Randomly pick a point from that list
        smooth_point_list = random.sample(locations_true.tolist(), 1)
        # random.sample returns a list (with one element in this case).
        # Hence extract the element
        smooth_point = smooth_point_list[0]
        smooth_point_corrected = (
            smooth_point[0] * DOWNSCALING_FACTOR,
            smooth_point[1] * DOWNSCALING_FACTOR,
        )
        self._point_locations.append(smooth_point_corrected)
        return smooth_point_corrected
