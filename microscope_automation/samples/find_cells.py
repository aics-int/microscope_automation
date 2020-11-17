# from aicsimagetools import CziReader, TifReader
import os
import matplotlib
import matplotlib.pyplot as plt
import numpy
from skimage import exposure, feature, morphology, measure, segmentation
from scipy import ndimage
from matplotlib.pyplot import imshow
import queue
import threading
import time
import multiprocessing
import psutil
import gc
from .samples import Cell
from .. import automation_messages_form_layout as form


class CellFinder:
    def __init__(self, image, prefs, parent_colony_object):
        """Find cells in an ImageAICS image

        Input:
         image: ImageAICS image to find cells in

         prefs: preferences for image analysis

         parent_colony_object: colony object which is using this CellFinder
        """
        self.original = image
        self.original_data = None
        self.seg = None
        self.d_map = None
        self.prefs = prefs
        self.image_locations = []
        self.cell_dict = {}
        self.colony_object = parent_colony_object
        self.calibrate = self.prefs.get_pref("Calibrate")
        self.viewer = CalibrationViewer()
        if os.environ.get("SCIPY_PIL_IMAGE_VIEWER") is None:
            os.environ["SCIPY_PIL_IMAGE_VIEWER"] = self.prefs.get_pref("ImageViewer")

    def set_calibration(self, value):
        assert value is bool
        self.calibrate = value

    def find_cells(self):
        """Find cells in a given image. General outline:

        - segment colony
        - choose location to image
        - return cell information

        Input:
         none

        Output:
         cell_dict: dictionary of the form {'name': cell_object}
        """
        try:
            self.segment_image()
            self.choose_imaging_location()
            self.export_cells()
        except AssertionError as e:
            print(e.args)
        return self.cell_dict

    def segment_image(self):
        """Segment a given image. General outline:

        - get original data
        - adjust image for edge detection
        - initial edge detection
        - dilation and hole filling
        - filtering
        - final edge detection

        Input:
         none

        Output:
         seg: segmented image
        """
        self.get_original_data()
        self.adjust_image()
        self.initial_edge_detection()
        self.improve_initial_edges()
        self.filter_objects()
        # self.final_edge_detection()
        print("Done with Segmentation")
        return self.seg

    def choose_imaging_location(self):
        """Choose a location (or locations) to image. General outline:

        - if looking for smooth locations, use twofold distance map algorithm
        - if looking for rough locations (TBD)
        - convert image locations to stage coordinates

        Input:
         none

        Output:
         none
        """
        if self.prefs.get_pref("FindSmoothAreas"):
            self.twofold_distance_map()
        # if calibration succeeded and continuous calibration not desired
        if self.calibrate and not self.prefs.get_pref("DevCalibration"):
            self.calibrate = False
            self.prefs.setPref("Calibrate", self.calibrate)

    def export_cells(self):
        """Convert the cell list into Cell objects.
        Add operation metadata to original image
        """
        for (ind, point) in enumerate(self.image_locations, start=1):
            name = self.colony_object.name + "_{:04}".format(ind)
            x_pos = point[0] - self.seg.shape[0] / 2
            y_pos = self.seg.shape[1] / 2 - point[1]
            print("Cell Position: ({}, {})".format(x_pos, y_pos))
            cell_to_add = Cell(
                name=name, center=[x_pos, y_pos, 0], colony_object=self.colony_object
            )
            self.cell_dict.update({name: cell_to_add})
        metadata = {}
        # Add non-boolean (i.e. non-flag) values to metadata with prefix "cf_"
        for key, value in self.prefs.prefs.iteritems():
            if type(value) is not bool:
                metadata.update({"cf_" + key: value})
        self.original.add_meta(metadata)

    def get_original_data(self):
        """Retrieve data from original image. Currently ImageAICS type.
        Will need to be converted to float and normalized between 0 and 1

        Input:
         image: ImageAICS image

        Output:
         seg: 2D numpy array of image data
        """
        # only retrieve original data if segmentation hasn't already occurred
        if self.seg is None:
            img_data = self.original.get_data()
            if len(img_data.shape) == 2:
                self.original_data = img_data.astype(numpy.float)
            else:
                # TODO: fix this transpose
                # self.original_data = self.original.get_data()[:, :, self.prefs.get_pref('ImageIndex')].astype(np.float)  # noqa
                # self.original_data = np.transpose(self.original_data, (0, 1))
                self.original_data = self.original.get_data()[
                    :, :, self.prefs.get_pref("ImageIndex")
                ].astype(numpy.float)
            # self.original_data = np.transpose(self.original_data, (1, 0))
            # self.original_data /= self.original_data.max()
            self.original_data = exposure.rescale_intensity(
                self.original_data, out_range=(0.0, 1.0)
            )
        self.seg = numpy.copy(self.original_data)
        return self.seg

    def adjust_image(self):
        """Adjust contrast, gamma, etc.
        Will have additional parameters for adjustment preferences.

        Input:
         none

        Output:
         seg: 2D numpy array of image data
        """
        fields = ["Sigmoid Threshold", "Sigmoid Gain", "Gamma"]
        names = ["SigmoidThreshold", "SigmoidGain", "Gamma"]
        values = [float(self.prefs.get_pref(name)) for name in names]
        adjusted = exposure.adjust_sigmoid(self.seg, values[0], values[1])
        adjusted = exposure.adjust_gamma(adjusted, values[2])
        if self.calibrate:
            self.viewer.display_image(adjusted)
            if self.validate(
                "Calibrate Contrast",
                "Calibrate sigmoid and gamma adjustment values",
                [fields, names, values],
            ):
                self.viewer.close()
                self.adjust_image()
            else:
                self.seg = adjusted
                self.viewer.close()
        else:
            self.seg = adjusted
        return self.seg

    def initial_edge_detection(self):
        """Initial edge detection.

        Input:
         none

        Output:
         seg: 2D numpy array of image data
        """
        fields = ["Canny Standard Deviation Threshold"]
        names = ["Canny1Sigma"]
        values = [float(self.prefs.get_pref(name)) for name in names]
        edge = feature.canny(self.seg, values[0])
        # Remove edge detection that occurs because of image edge artifacts
        if self.prefs.get_pref("ClearEdges") and self.prefs.get_pref("Tile"):
            height = 0
            width = 0
            columns = self.prefs.get_pref("nColTile")
            rows = self.prefs.get_pref("nRowTile")
            # clear columns based on tiling
            for _ in range(1, columns):
                height += edge.shape[1] / columns
                edge[:, height - min(3, columns) : height + min(3, columns)] = 0
            # clear rows based on tiling
            for _ in range(1, rows):
                width += edge.shape[0] / rows
                edge[width - min(3, rows) : width + min(3, rows)] = 0

        if self.calibrate:
            self.viewer.display_image(edge)
            if self.validate(
                "Calibrate Initial Edge Detection",
                "Calibrate the sigma threshold for first canny edge detection",
                [fields, names, values],
            ):
                self.viewer.close()
                self.initial_edge_detection()
            else:
                self.seg = edge
                self.viewer.close()
        else:
            self.seg = edge
        return self.seg

    def improve_initial_edges(self):
        """Improve initial edge detection with dilation, hole filling, etc.

        Input:
         none

        Output:
         seg: 2D numpy array of image data
        """
        fields = ["Dilation Size"]
        names = ["DilationSize"]
        values = [int(self.prefs.get_pref(name)) for name in names]
        improve = morphology.dilation(self.seg, morphology.diamond(values[0]))
        improve = ndimage.binary_fill_holes(improve)
        if self.calibrate:
            self.viewer.display_image(improve)
            if self.validate(
                "Calibrate Dilation and Hole Filling",
                "Adjust dilation size to improve hole filling",
                [fields, names, values],
            ):
                self.viewer.close()
                self.improve_initial_edges()
            else:
                self.seg = improve
                self.viewer.close()
        else:
            self.seg = improve
        return self.seg

    def filter_objects(self):
        """Filter objects in image to identify best colonies.

        Input:
         none

        Output:
         seg: 2D numpy array of image data
        """
        filter_type = self.prefs.get_pref("FilterBy")
        label_objects, nb_labels = ndimage.label(self.seg)
        if filter_type == "Size":
            # find the object of the largest size and use that as imaging colony
            sizes = numpy.bincount(label_objects.ravel())
            sizes[0] = 0  # clear first item, which is the background
            name = "SizeThreshold"
            if sizes.max() < self.prefs.get_pref(name):
                if self.calibrate:
                    result = form.value_calibration_form(
                        "Calibrate Size Threshold",
                        "Minimum colony size: {}\n, adjust lower bound?".format(
                            sizes.max()
                        ),
                        False,
                        ("Minimum Size", self.prefs.get_pref(name)),
                    )
                    if result is None:
                        form.stop_script()
                    elif not result[-1]:
                        self.prefs.setPref(name, result[0])
                    else:
                        if self.prefs.get_pref("UseOutlier"):
                            thresh_mask = (
                                self.is_outlier(
                                    sizes, self.prefs.get_pref("OutlierThreshold")
                                )
                                * sizes
                            )
                        else:
                            thresh_mask = numpy.zeros_like(sizes)
                            thresh_mask[sizes.argmax()] = 1
                        filtered = thresh_mask[label_objects].astype(bool)
                        border = segmentation.clear_border(filtered)
                        if border.any():
                            # don't apply border filter if border is only object
                            filtered = border
                        self.seg = filtered
                        return self.seg
                else:
                    assert "Colony too small to image"
            if self.prefs.get_pref("UseOutlier"):
                thresh_mask = (
                    self.is_outlier(sizes, self.prefs.get_pref("OutlierThreshold"))
                    * sizes
                )
            else:
                thresh_mask = numpy.zeros_like(sizes)
                thresh_mask[sizes.argmax()] = 1
            filtered = thresh_mask[label_objects].astype(bool)
        elif filter_type == "Center":
            # get the object in the center of the FOV and use that as imaging colony
            # this requires that a labeled object be in the center of the image
            # should only be used if pre-scanning and selecting colonies individually
            center_label = label_objects[(self.seg.shape[0] / 2, self.seg.shape[1] / 2)]
            center_mask = numpy.zeros_like(self.seg)
            center_mask[label_objects == center_label] = 1
            filtered = label_objects.astype(bool) * center_mask
        else:
            raise ValueError("Filter type not specified in preferences")
        border = segmentation.clear_border(filtered)
        if border.any():
            # don't apply border filter if border is only object
            filtered = border
        self.seg = filtered
        return self.seg

    def final_edge_detection(self):
        """Find improved edges.

        Input:
         none

        Output:
         seg: 2D numpy array of image data
        """
        edge = feature.canny(self.seg, self.prefs.get_pref("Canny2Sigma"))
        self.seg = edge
        # plt.imsave('/home/mattb/git/microscopeautomation/data/test_data_matthew/2017_3_7/canny2.png',
        #            self.seg, cmap=matplotlib.cm.gray)
        return self.seg

    def twofold_distance_map(self):
        """Compute the entire distance map for a segmented colony"""
        fields = [
            "Minimum Distance from Edge",
            "Maximum Distance from Edge",
            "Gaussian Filter Threshold",
            "Canny Edge Detection Threshold",
        ]
        names = ["DistanceMin", "DistanceMax", "GaussianFilter", "Canny3Sigma"]
        values = [float(self.prefs.get_pref(name)) for name in names]
        distance_map = ndimage.distance_transform_edt(self.seg)
        d_max = distance_map.max()
        distance_map *= (distance_map > (d_max * values[0])) & (
            distance_map < (d_max * values[1])
        )
        distance_map = distance_map.astype(bool)
        # might need to switch this from original to adjusted image
        colony_only = ndimage.gaussian_filter(self.original_data, values[2])
        colony_only *= distance_map
        colony_edges = feature.canny(colony_only, values[3])
        inner_edges = ndimage.distance_transform_edt(~colony_edges * distance_map)

        # helper function to avoid repeated code,
        # checks with user that point chosen is suitable
        def verify_smooth_point():
            smooth_point = numpy.where(inner_edges == inner_edges.max())
            point = numpy.copy(self.original_data)
            point[
                smooth_point[0][0] - 3 : smooth_point[0][0] + 3,
                smooth_point[1][0] - 3 : smooth_point[1][0] + 3,
            ] = 1
            self.viewer.display_image(point)
            if self.validate(
                "Chosen point", "Is this chosen point acceptable?", [], default=True
            ):
                self.viewer.close()
                # form.stop_script("Point after calibration was found to be unacceptable")  # noqa
                # restart calibration
                self.calibrate = True
                self.find_cells()
            self.viewer.close()
            self.image_locations.append((smooth_point[0][0], smooth_point[1][0]))

        if self.calibrate:
            self.viewer.display_image(colony_edges)
            if self.validate(
                "Calibrate Twofold Distance Detection",
                "Calibrate the values for twofold distance map smooth point detection",
                [fields, names, values],
            ):
                self.viewer.close()
                self.twofold_distance_map()
            else:
                self.viewer.close()
                verify_smooth_point()
        elif self.prefs.get_pref("PreScanVerify"):
            verify_smooth_point()
        else:
            smooth_point = numpy.where(inner_edges == inner_edges.max())
            self.image_locations.append((smooth_point[0][0], smooth_point[1][0]))

    # HELPER FUNCTIONS

    @staticmethod
    def is_outlier(points, thresh=3.5):
        """Returns a boolean array with True if points are outliers and False
        otherwise.

        Input:
         points: An num_observations by num_dimensions array of observations

         thresh: The modified z-score to use as a threshold. Observations with
         a modified z-score (based on the median absolute deviation) greater
         than this value will be classified as outliers.

        Output:
         mask: A num_observations-length boolean array.

        References:
            Boris Iglewicz and David Hoaglin (1993), "Volume 16: How to Detect and
            Handle Outliers", The ASQC Basic References in Quality Control:
            Statistical Techniques, Edward F. Mykytka, Ph.D., Editor.
        """
        if len(points.shape) == 1:
            points = points[:, None]
        median = numpy.median(points, axis=0)
        diff = numpy.sum((points - median) ** 2, axis=-1)
        diff = numpy.sqrt(diff)
        med_abs_deviation = numpy.median(diff)

        modified_z_score = 0.6745 * diff / med_abs_deviation

        return modified_z_score > thresh

    def validate(self, form_title, form_comment, pref_data, default=False):
        """Function to calibrate steps of the cell finding process

        Input:
         form_title: title of form to be displayed

         form_comment: comment for form to be displayed

         pref_data: (list) contains form fields, preference names, preference values,
         and (in that order)

         default: checked or unchecked as default for continuing. (Default = False)

        Output:
         boolean for whether to continue recursion
        """
        assert len(set(len(x) for x in pref_data)) <= 1, "Mismatched parameter lengths"
        args = (
            [(pref_data[0][i], pref_data[2][i]) for i in range(len(pref_data[2]))]
            if len(pref_data)
            else []
        )
        time.sleep(2)  # timeout for image to display
        result = form.value_calibration_form(form_title, form_comment, default, *args)
        if result is None:
            self.viewer.close()
            form.stop_script()
        # calibration incorrect
        elif not result[-1] and len(pref_data) == 0:
            return True
        # values were not correct
        elif not result[-1] and not all(
            result[i] == pref_data[2][i] for i in range(len(pref_data[2]))
        ):
            for ii in range(len(pref_data[1])):
                self.prefs.setPref(pref_data[1][ii], result[ii])
            return True
        else:
            return False


class CalibrationViewer:
    """This class is intended to be a bookkeeper for image viewing threads.
    Scipy's imshow doesn't play nice with
    """

    def __init__(self):
        self.process = None
        self.filename = None

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def display_image(self, image, cmap="Greys_r"):
        self.process = multiprocessing.Process(target=imshow, args=[image])
        self.process.start()

    def close(self):
        if self.process is not None:
            self.process.terminate()
        for proc in psutil.process_iter():
            if proc.name().startswith("display") or proc.name().startswith(
                "PicasaPhotoViewer"
            ):
                proc.kill()


def display_and_save(
    image,
    name,
    location="/home/mattb/git/microscopeautomation/data/test_data_matthew/segmentationtest/",  # noqa
    display=False,
):
    if display:
        plt.imshow(image, cmap="Greys")
        plt.title(name)
        plt.show()
    filename = location + name + ".png"
    plt.imsave(filename, image, cmap=matplotlib.cm.gray)


def segment_dir(directory, multi=True):
    file_match = [
        img
        for img in filter(
            lambda x: x.endswith(".tif"),
            [os.path.join(directory, loc) for loc in os.listdir(directory)],
        )
    ]
    location = "/home/mattb/git/microscopeautomation/data/test_data_matthew/segmentationtest/size_filter/"  # noqa

    thread_list = ["T1", "T2", "T3", "T4"]
    queue_lock = threading.Lock()
    img_queue = queue.Queue(100)
    threads = []
    threadID = 1
    exit_flag = False

    class MultiThread(threading.Thread):
        def __init__(self, threadID, name, q):
            threading.Thread.__init__(self)
            self.threadID = threadID
            self.name = name
            self.q = q

        def run(self):
            print("Starting " + self.name)
            process_data(self.q)
            print("Exiting " + self.name)

    if multi:

        def process_data(q):
            while not exit_flag:
                queue_lock.acquire()
                if not img_queue.empty():
                    queue_data = q.get()
                    queue_lock.release()
                    segment(*queue_data)
                    gc.collect()
                else:
                    queue_lock.release()
                time.sleep(1)

        for name in thread_list:
            thread = MultiThread(threadID, name, img_queue)
            thread.start()
            threads.append(thread)
            threadID += 1

        count = 0
        queue_lock.acquire()
        for img in file_match:
            if count > numpy.iinfo(numpy.uint8).max:
                break
            file_loc = os.path.basename(img)
            per_parent = os.path.join(location, file_loc)
            if not os.path.exists(per_parent):
                os.mkdir(per_parent)
            img_queue.put([img, per_parent + os.sep])
            count += 1
        queue_lock.release()

        while not img_queue.empty():
            pass

        exit_flag = True

        for t in threads:
            t.join()
            # segment(img, per_parent + os.sep)
            # segmented = segment(img, per_parent)
            # filename = file_loc + ".png"
            # plt.imshow(segmented, cmap='Greys')
            # plt.imsave(location + filename, segmented, cmap=matplotlib.cm.gray)
    else:
        for img in file_match:
            file_loc = os.path.basename(img)
            per_parent = os.path.join(location, file_loc)
            if not os.path.exists(per_parent):
                os.mkdir(per_parent)
            segment(img, per_parent + os.sep)


# @jit
def segment(image, img_dir):
    """FOR TESTING PURPOSES ONLY

    Input:
     image:

     img_dir:

    Output:
     none
    """
    # img = TifReader(image)
    img = []
    img_data = img.load()
    if len(img_data.shape) == 3:
        img_data = measure.block_reduce(img_data, (1, 10, 10), func=numpy.mean)[0, :, :]
    elif len(img_data.shape) == 4:
        img_data = measure.block_reduce(img_data, (1, 1, 10, 10), func=numpy.mean)[
            0, 0, :, :
        ]
    img_data = img_data.astype(numpy.float) / img_data.max()
    display_and_save(img_data, "00Original", img_dir, False)

    sigmoid = exposure.adjust_sigmoid(img_data, 0.5, 10)
    display_and_save(sigmoid, "01Sigmoid", img_dir, False)
    gamma_corrected = exposure.adjust_gamma(sigmoid, 2)
    display_and_save(gamma_corrected, "02Gamma", img_dir, False)
    g_edges = feature.canny(gamma_corrected, 1)
    display_and_save(g_edges, "03Canny1", img_dir, False)
    dilation = morphology.dilation(g_edges, morphology.diamond(3))
    display_and_save(dilation, "04Dilation", img_dir, False)
    filled = ndimage.binary_fill_holes(dilation)
    display_and_save(filled, "05Filled", img_dir, False)

    label_objects, nb_labels = ndimage.label(filled)
    sizes = numpy.bincount(label_objects.ravel())
    sizes[0] = 0  # clear first item, which is the background
    thresh_mask = numpy.zeros_like(sizes)
    thresh_mask[sizes.argmax()] = sizes.max()
    # It seems like all sizes below 450,000 are garbage/too small to image

    # with open('/home/mattb/git/microscopeautomation/data/test_data_matthew/segmentationtest/sizes.txt', 'a') as f:  # noqa
    #     f.write("{} == {} \n".format(os.path.basename(image), sizes.max()))
    cleaned = thresh_mask[label_objects]  # this line is magic that I don't understand
    cleaned = cleaned.astype(numpy.float) / cleaned.max()
    display_and_save(cleaned, "06Cleaned", img_dir, False)

    border = segmentation.clear_border(cleaned)
    if not border.any():
        border = cleaned
    display_and_save(border, "07Border", img_dir, False)

    binary = border.astype(bool)
    display_and_save(binary, "08Binary", img_dir, False)

    final_edges = feature.canny(binary, 0)
    display_and_save(final_edges, "09Edges", img_dir, False)

    # binary = ndi.binary_fill_holes(final_edges)
    # display_and_save(binary, "9Binary", img_dir, False)
    overlay = numpy.copy(img_data)
    overlay[final_edges] = 1
    display_and_save(overlay, "10Overlay", img_dir, False)

    distance = ndimage.distance_transform_edt(binary)
    display_and_save(distance, "11Distance", img_dir, False)

    d_max = distance.max()
    top_percent = distance * ((distance > (d_max * 0.5)) & ((d_max * 1.0) >= distance))
    # top_percent = np.zeros_like(distance)
    # cond = distance > (distance.max() * 0.8)
    # top_percent[cond] = 1
    display_and_save(top_percent, "12DistancePercent", img_dir, False)

    # smoothing
    colony_only = ndimage.gaussian_filter(img_data, 1.5)
    colony_mask = colony_only * top_percent.astype(bool)
    display_and_save(colony_mask, "15ColonyMask", img_dir, False)

    colony_edges = feature.canny(colony_mask)
    display_and_save(colony_edges, "16ColonyEdges", img_dir, False)

    inner_edges = ndimage.distance_transform_edt(
        ~colony_edges * top_percent.astype(bool)
    )
    display_and_save(inner_edges, "17InnerDistance", img_dir, False)

    smooth_point = numpy.where(inner_edges == inner_edges.max())
    smooth_point = (smooth_point[0][0], smooth_point[1][0])
    smooth_dist = numpy.copy(inner_edges)
    smooth_dist[
        smooth_point[0] - 3 : smooth_point[0] + 3,
        smooth_point[1] - 3 : smooth_point[1] + 3,
    ] = (
        smooth_dist.max() * 3
    )
    display_and_save(smooth_dist, "18SmoothMax", img_dir, False)

    overlay[
        smooth_point[0] - 3 : smooth_point[0] + 3,
        smooth_point[1] - 3 : smooth_point[1] + 3,
    ] = 0
    display_and_save(overlay, "19SmoothOverlay", img_dir, False)

    dist_edges = feature.canny(top_percent.astype(bool))
    display_and_save(dist_edges, "20DistanceEdges", img_dir, False)

    overlay[dist_edges] = 0
    display_and_save(overlay, "21DistanceOverlay", img_dir, False)

    bottom_percent = distance * (distance < (d_max * 0.5))
    display_and_save(bottom_percent, "22BottomPercent", img_dir, False)

    colony_mask = colony_only * bottom_percent.astype(bool)
    display_and_save(colony_mask, "23BottomSmoothed", img_dir, False)

    colony_edges = feature.canny(colony_mask)
    display_and_save(colony_edges, "24RoughEdges", img_dir, False)

    outer_edges = ndimage.distance_transform_edt(
        ~colony_edges * bottom_percent.astype(bool)
    )
    display_and_save(outer_edges, "25OuterDistance", img_dir, False)

    bottom_mask = (bottom_percent * (distance * (distance > (d_max * 0.1)))).astype(
        bool
    )
    outer_edges += (~bottom_mask).astype(float) * outer_edges.max()
    display_and_save(outer_edges, "26OuterMasking", img_dir, False)

    rough_point = numpy.where(outer_edges == outer_edges.min())
    rough_point = (rough_point[0][0], rough_point[1][0])
    rough_dist = numpy.copy(outer_edges)
    rough_dist[
        rough_point[0] - 3 : rough_point[0] + 3, rough_point[1] - 3 : rough_point[1] + 3
    ] = (rough_dist.max() * 3)
    display_and_save(rough_dist, "27RoughMin", img_dir, False)

    overlay[
        rough_point[0] - 3 : rough_point[0] + 3, rough_point[1] - 3 : rough_point[1] + 3
    ] = 1
    display_and_save(overlay, "28RoughOverlay", img_dir, False)

    glcm = feature.greycomatrix(img_data, [5], [0])
    display_and_save(glcm[:, :, 0, 0], "29GLCM", img_dir, False)

    # mean_mask = img_data * distance.astype(bool)
    # mean = filters.rank.mean(mean_mask, morphology.square(3))
    # display_and_save(mean, "29MeanImage", img_dir, False)

    # display_and_save(overlay, "ChosenPointOverlay-" + str(time.time()), '/home/mattb/git/microscopeautomation/data/test_data_matthew/segmentationtest/roughness_comparison/', False)  # noqa

    # return overlay
    img.close()
