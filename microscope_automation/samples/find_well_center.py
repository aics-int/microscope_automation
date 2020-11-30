"""
Find center of well based on ImageAICS of well segment.
We will generate an ImageAICS of the whole well
and convolve it with the ImageAICS of the segment.
All dimensions in pixels
Created on Jun 18, 2016

@author: winfriedw
"""

from skimage import draw, feature, exposure, img_as_float
from skimage.filters import threshold_otsu
import skimage.morphology as skimorph
import numpy
import math
import matplotlib.pyplot as plt
from scipy import ndimage


debug = False  # if True, debug images will be shown
summaryDebug = True  # if True, summary debug images will be shown


def show_hist(image):
    """Plot histogram.

    Input:
     image

    Output:
     none

    We have problems with the pyplot.hist function.
    """
    hist, bins = numpy.histogram(image, bins=50)
    width = 0.7 * (bins[1] - bins[0])
    center = (bins[:-1] + bins[1:]) / 2

    fig, axes = plt.subplots(nrows=1, ncols=2)
    axes[0].imshow(image)
    axes[1].bar(center, hist, align="center", width=width)
    plt.show()


def show_debug_image(image):
    """Show ImageAICS when in debug mode.

    Input:
     image: ImageAICS object to display if debug mode is turned on

    Return:
     none
    """
    if debug:
        plt.imshow(image)
        plt.show()


def show_debug_summary(image, well_image, correlation, t_image, corr_x, corr_y):
    """Show all images to calculate new center.

    Input:
     image: microscope image of well center

     well_image: synthetic image of well used for alignment

     correlation: image of crosscorrelation

     t_image: image after thresholding used for crosscorrelation

     corr_x, corr_y: correlation peak

    Output:
     none
    """
    if summaryDebug:
        fig, axes = plt.subplots(nRows=2, nCols=3)

        axes[0, 0].imshow(image)
        axes[0, 1].imshow(well_image)
        # mark position of correlation maximum. x and y are reversed
        # because we display on a numpy array
        axes[0, 1].plot(corr_y, corr_x, "wx", markersize=20)
        #         centerX=offsetX+correlation.shape[0]/2
        #         centerY=offsetY+correlation.shape[1]/2

        #         axes[0,1].plot(centerY, centerX, 'b+', markersize=20)
        axes[1, 0].imshow(correlation)
        # mark position of correlation maximum. x and y are reversed
        # because we display on a numpy array
        axes[1, 0].plot(corr_y, corr_x, "wx", markersize=20)

        # overlay original image over template for well
        #         overlay=np.zeros((well_image.shape[0],well_image.shape[1]))
        overlay = numpy.copy(well_image)
        insert = 1 + numpy.copy(
            overlay[
                corr_x - image.shape[0] / 2 : corr_x + image.shape[0] / 2,
                corr_y - image.shape[0] / 2 : corr_y + image.shape[0] / 2,
            ]
        )
        image_scaled = image / image.max()
        insert = insert + image_scaled
        overlay[
            corr_x - image.shape[0] / 2 : corr_x + image.shape[0] / 2,
            corr_y - image.shape[0] / 2 : corr_y + image.shape[0] / 2,
        ] = insert
        axes[1, 1].imshow(overlay)

        axes[0, 2].imshow(t_image)

        plt.show()


def create_well_image(diameter):
    """Create mask for whole well. Using the whole well for alignment will
    improve accuracy on the cost of speed.
    We recommend to use create_edge_image if possible

    Input:
     diameter: well diameter in pixels

    Return:
     well_image: numpy array for well with well set to 1 and background set to 0
    """

    im = numpy.zeros((diameter, diameter))
    rr, cc = draw.circle(diameter / 2, diameter / 2, diameter / 2.0, im.shape)
    im[rr, cc] = 1
    show_debug_image(im)
    return im


def create_edge_image(diameter, length, r, phi, add_noise=False):
    """Create ImageAICS for well edge used for alignment and test purposes.

    Input:
     diameter: Well diameter in pixels

     length: size of image in pixels

     r: distance of image from circle center in pixels.

     phi: direction of image

     addNoise: add noise for test purposes. Default is False.

    Output:
     im: well edge image to be used for alignment
    """

    im = numpy.zeros((int(length), int(length)))

    # center of ImageAICS
    xc = length / 2
    yc = length / 2
    # center of circle relative to ImageAICS center based on radial coordinates
    phi_r = math.radians(phi)
    radius = diameter / 2.0
    x = xc - r * math.sin(phi_r)
    y = yc - r * math.cos(phi_r)
    # draw circle segment
    rr, cc = draw.circle(x, y, radius, im.shape)
    im[rr, cc] = 1
    # remove center
    # draw circle segment
    rr, cc = draw.circle(x, y, radius - 200, im.shape)
    im[rr, cc] = 0

    # add Gauss noise
    if add_noise:
        im = im + (numpy.random.random(im.shape) - 0.5) * 0.2
    show_debug_image(im)
    return im


def find_well_center(image, well_diameter, percentage, phi):
    """Find center of well based on edge ImageAICS.

    Input:
     image: image with well edge

     well_diameter: diameter of well in pixels

     percentage: percentage of whole well used for convolution.
     Large numbers increase accuracy, smaller speed.
     well_diameter*percentage/100 has to be larger than size of ImageAICS

     phi: direction of image from center

    Return:
     x_center, y_center: expected center of well
    """
    # create image of well section, well_image has to be larger than image
    well_image_size = max(
        well_diameter + 2 * max(image.shape) * percentage / 100,
        image.shape[0],
        image.shape[1],
    )
    well_image = create_edge_image(well_diameter, well_image_size, 0, phi)

    # We take images of well edges with a 1.25x objective.
    # The transmitted light illumination field does not cover the whole FOV
    # of the objective (esp. if the well is filled with buffer),
    # thus the images have a bright center that is smaller than the well
    # and a dim ring for the rest of the well. We will remove the bright center
    # to ensure proper working of the cross-correlation below.
    # imagef=gaussian(image, sigma=4)
    img = image / image.max()
    img_filter = ndimage.median_filter(img, 3)
    thresh = threshold_otsu(img_filter)
    img_filter[img_filter > thresh] = img_filter.min()

    # selem=skimorph.disk(10)
    # img_top=skimorph.white_tophat(img, selem)
    # img_top[img_filter>thresh]=img_top.min()

    img_equal = ndimage.median_filter(exposure.equalize_hist(img_filter, 200), 30)
    thresh2 = threshold_otsu(img_equal)  # noqa
    img_mask = numpy.zeros(img.shape)
    img_mask[img_equal > 0.7] = 1
    # img_mask[img>thresh]=1
    img_mask = skimorph.binary_closing(img_mask)

    # calculate cross correlation between well ImageAICS and edge ImageAICS
    # from http://scikit-image.org/docs/dev/api/skimage.feature.html?highlight=match_template#skimage.feature.match_template:  # noqa
    # Match a template to a 2-D or 3-D image using normalized correlation.
    # The output is an array with values between -1.0 and 1.0. The value at a given
    # position corresponds to the correlation coefficient between the image and the
    # template. For pad_input=True matches correspond to the center and otherwise to the
    # top-left corner of the template. To find the best match you must search for peaks
    #  in the response (output) image.

    corr = feature.match_template(well_image, img_mask, pad_input=True)

    # find maximum of correlation
    x, y = numpy.unravel_index(corr.argmax(), corr.shape)
    # we use complex numbers to calculate the offest between the image center
    # and the well radius calculations are simplified in polar coordinates
    # offCompl=complex(x-corr.shape[0]/2,y-corr.shape[1]/2)
    # r_offset=cmath.polar(offCompl)[0]-wellDiameter/2
    # phi_offset=cmath.phase(offCompl)
    # offset=cmath.rect(r_offset, phi_offset)
    # convert to coordinate system with origin in center of simulated well
    x_center = x - corr.shape[0] / 2
    y_center = y - corr.shape[1] / 2
    # offsetX=offset.real
    # offsetY=offset.imag
    show_debug_summary(image, well_image, img_mask, corr, x, y, x_center, y_center)
    return x_center, y_center


def find_well_center_fine(image, direction, test=False):
    """Find edge of well in image in selected direction.

    Input:
     image: image with well edge

     direction: direction to search for edge. String of form '-x', 'x', '-y', or 'y'

     test: returns 1 if True since test images may not have data (Default: False)

    Return:
     edge_pos: coordinate of well edge in selected direction in pixels
     with origin in center of image
    """
    if test:
        return 1

    # scikit-image assumes floating point images to be in the range [-1,1] or [0, 1]
    img = img_as_float(image)

    if direction == "-x" or direction == "x":
        median_size = (1, 30)
        sobel_axis = 0
    elif direction == "-y" or direction == "y":
        median_size = (30, 1)
        sobel_axis = 1
    else:
        print("Not implemented")

    if direction == "x":
        img = numpy.flipud(img)
    elif direction == "y":
        img = numpy.fliplr(img)

    img_filter = ndimage.median_filter(img, size=median_size)
    img_edges = ndimage.sobel(img_filter, axis=sobel_axis)

    mask = numpy.zeros(img.shape)
    mask[img_edges > numpy.percentile(img_edges, 99.5)] = 1

    pos_xy = numpy.nonzero(mask)
    if direction == "x" or direction == "y":
        edge_pos = img.shape[sobel_axis] / 2 - pos_xy[sobel_axis].min()
    else:
        edge_pos = pos_xy[sobel_axis].min() - img.shape[sobel_axis] / 2
    print(pos_xy[sobel_axis].min(), edge_pos)
    return edge_pos
