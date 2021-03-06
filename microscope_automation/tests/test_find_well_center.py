"""
Test find_well_center module
Created on Nov 24, 2020

@author: fletcher.chapin
"""

import os
import pytest
from mock import patch
from microscope_automation.util.image_AICS import ImageAICS
from microscope_automation.samples import find_well_center

os.chdir(os.path.dirname(__file__))

# set skip_all_tests = True to focus on single test
skip_all_tests = False


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
