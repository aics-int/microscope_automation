"""
Test get_path module, which returns path for settings, logfile, and data
based on preferences file
Created on Nov 17, 2020

@author: fletcher.chapin
"""
import os
import pytest
import numpy as np
from microscope_automation.util.image_AICS import ImageAICS
from microscope_automation.samples import correct_background

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


@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    "image, black_reference, expected",
    [
        (
            "test_image_all_white",
            "test_image_all_black",
            [
                [-1, -1, -1, -1, -1],
                [-1, -1, -1, -1, -1],
                [-1, -1, -1, -1, -1],
                [-1, -1, -1, -1, -1],
                [-1, -1, -1, -1, -1],
            ],
        ),
        (
            "test_image_all_black",
            "test_image_all_white",
            [
                [1, 1, 1, 1, 1],
                [1, 1, 1, 1, 1],
                [1, 1, 1, 1, 1],
                [1, 1, 1, 1, 1],
                [1, 1, 1, 1, 1],
            ],
        ),
        (
            "test_image_all_black",
            "test_image_black_reference",
            [
                [1, 1, 1, 0.25, 1],
                [0.25, 0.25, 0.25, 0.25, 0.25],
                [0.25, 0.25, 0.25, 0.25, 0.25],
                [0.25, 0.25, 0.25, 0.25, 0.25],
                [0.25, 0.25, 0.25, 0.25, 0.25],
            ],
        ),
    ],
)
def test_fixed_pattern_correction(
    image,
    black_reference,
    expected,
    test_image_all_black,
    test_image_all_white,
    test_image_black_reference,
):
    image = select_image(image, test_image_all_black, test_image_all_white)
    black_reference = select_image(
        black_reference,
        test_image_all_black,
        test_image_all_white,
        test_image_black_reference=test_image_black_reference,
    )

    result = correct_background.fixed_pattern_correction(
        image.get_data(), black_reference.get_data()
    )

    assert len(result) == len(expected)
    i = 0
    for row in result:
        assert all([a == b for a, b in zip(row, expected[i])])
        i += 1


@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    "image, black_reference, illumination_reference, expected",
    [
        (
            "test_image_all_white",
            "test_image_all_black",
            "test_image_illumination_reference",
            [
                [2, 2, 2, 2, 2],
                [2, 2, 2, 2, 2],
                [1, 2, 1, 1, 1.3333333333333333],
                [1, 2, 1, 1, 1],
                [2, 2, 2, 2, 2],
            ],
        ),
        (
            "test_image_all_black",
            "test_image_all_white",
            "test_image_illumination_reference",
            [
                [2, 2, 2, 2, 2],
                [2, 2, 2, 2, 2],
                [np.inf, 2, np.inf, np.inf, 4],
                [np.inf, 2, np.inf, np.inf, np.inf],
                [2, 2, 2, 2, 2],
            ],
        ),
        (
            "test_image_black_reference",
            "test_image_all_black",
            "test_image_illumination_reference",
            [
                [2, 2, 2, 0.5, 2],
                [0.5, 0.5, 0.5, 0.5, 0.5],
                [0.25, 0.5, 0.25, 0.25, 0.3333333333333333],
                [0.25, 0.5, 0.25, 0.25, 0.25],
                [0.5, 0.5, 0.5, 0.5, 0.5],
            ],
        ),
    ],
)
def test_illumination_correction(
    image,
    black_reference,
    illumination_reference,
    expected,
    test_image_all_black,
    test_image_all_white,
    test_image_illumination_reference,
    test_image_black_reference,
):
    image = select_image(
        image,
        test_image_all_black,
        test_image_all_white,
        test_image_illumination_reference,
        test_image_black_reference,
    )
    black_reference = select_image(
        black_reference,
        test_image_all_black,
        test_image_all_white,
        test_image_illumination_reference,
        test_image_black_reference,
    )
    illumination_reference = select_image(
        illumination_reference,
        test_image_all_black,
        test_image_all_white,
        test_image_illumination_reference,
        test_image_black_reference,
    )

    result = correct_background.illumination_correction(
        image.get_data(), black_reference.get_data(), illumination_reference.get_data()
    )

    assert len(result) == len(expected)
    i = 0
    for row in result:
        assert all([a == b for a, b in zip(row, expected[i])])
        i += 1
