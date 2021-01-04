"""
Test find_well_center module
Created on Nov 24, 2020

@author: fletcher.chapin
"""

import os
import pytest
import numpy as np
from mock import patch
from scipy import ndimage
from skimage import exposure
import skimage.morphology as skimorph
from skimage.filters import threshold_otsu
from microscope_automation.image_AICS import ImageAICS
from microscope_automation.samples import find_well_center

os.chdir(os.path.dirname(__file__))

# set skip_all_tests = True to focus on single test
skip_all_tests = True


def select_image(
    image,
    test_image_all_black,
    test_image_all_white,
    test_image_illumination_reference=None,
    test_image_black_reference=None,
):
    if image == "test_image_all_black":
        image = test_image_all_black
    elif image == "test_image_all_white":
        image = test_image_all_white
    elif image == "test_image_illumination_reference":
        image = test_image_illumination_reference
    elif image == "test_image_black_reference":
        image = test_image_black_reference
    else:
        image = ImageAICS()

    return image


def make_mask(image):
    """Makes an image mask using the same logic as find_well_center"""
    img = image / image.max()
    img_filter = ndimage.median_filter(img, 3)
    thresh = threshold_otsu(img_filter)
    img_filter[img_filter > thresh] = img_filter.min()
    img_equal = ndimage.median_filter(exposure.equalize_hist(img_filter, 200), 30)
    img_mask = np.zeros(img.shape)
    img_mask[img_equal > 0.7] = 1
    img_mask = skimorph.binary_closing(img_mask)

    return img_mask


@patch("matplotlib.pyplot.show")
@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    "image_name, expected",
    [("test_image_all_black", None), ("test_image_all_white", None)],
)
def test_show_hist(
    mock_show, image_name, expected, test_image_all_black, test_image_all_white
):
    image = select_image(image_name, test_image_all_black, test_image_all_white)
    result = find_well_center.show_hist(image.data)

    assert result == expected


@patch("matplotlib.pyplot.show")
@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    "image_name, debug, expected",
    [("test_image_all_black", True, None), ("test_image_all_white", False, None)],
)
def test_show_debug_image(
    mock_show, image_name, debug, expected, test_image_all_black, test_image_all_white
):
    image = select_image(image_name, test_image_all_black, test_image_all_white)
    result = find_well_center.show_debug_image(image.data, debug)

    assert result == expected


# @patch("matplotlib.pyplot.show")
# @pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
# @pytest.mark.parametrize(
#     "image_name0, image_name1, summary_debug, expected",
#     [("test_image_all_black", "test_image_all_black", True, None),
#      ("test_image_all_white", "test_image_all_black", False, None)],
# )
# def test_show_debug_summary(
#     mock_show, image_name0, image_name1, summary_debug, expected,
#     test_image_all_black, test_image_all_white
# ):
#     image0 = select_image(image_name0, test_image_all_black, test_image_all_white)
#     image1 = select_image(image_name1, test_image_all_black, test_image_all_white)
#     mask = make_mask(image0.data)
#     result = find_well_center.show_debug_summary(image0.data, image1.data, mask,
#                                                  , summary_debug)
#
#     assert result == expected


@patch("matplotlib.pyplot.show")
# @pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    "image_name, debug, expected",
    [("test_image_all_black", True, None), ("test_image_all_white", False, None)],
)
def test_find_well_center(
    mock_show, image_name, debug, expected, test_image_all_black, test_image_all_white
):
    image = select_image(image_name, test_image_all_black, test_image_all_white)
    result = find_well_center.find_well_center(image.data, 25, 50, 0, summary_debug=False)

    # assert result == expected
    assert False
