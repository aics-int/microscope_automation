"""
Test samples Classes
Created on October 5, 2020

@author: fletcher.chapin
"""

import pytest
from mock import patch
from microscope_automation.samples import samples
import os

os.chdir(os.path.dirname(__file__))

# set skip_all_tests = True to focus on single test
skip_all_tests = False

###############################################################################
#
# Tests for the helper functions
#
###############################################################################


@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    ("plate_format, expected"),
    [
        (
            "12",
            {
                "A1": (0, 0, 104),
                "A2": (26000, 0, 104),
                "A3": (52000, 0, 104),
                "A4": (78000, 0, 104),
                "B1": (0, 26000, 104),
                "B2": (26000, 26000, 104),
                "B3": (52000, 26000, 104),
                "B4": (78000, 26000, 104),
                "C1": (0, 52000, 104),
                "C2": (26000, 52000, 104),
                "C3": (52000, 52000, 104),
                "C4": (78000, 52000, 104),
                "name": "12",
                "well_diameter": 22050,
            },
        ),
        (
            "24",
            {
                "A1": (0, 0, 104),
                "A2": (19300, 0, 104),
                "A3": (38600, 0, 104),
                "A4": (57900, 0, 104),
                "A5": (77200, 0, 104),
                "A6": (96500, 0, 104),
                "B1": (0, 19300, 104),
                "B2": (19300, 19300, 104),
                "B3": (38600, 19300, 104),
                "B4": (57900, 19300, 104),
                "B5": (77200, 19300, 104),
                "B6": (96500, 19300, 104),
                "C1": (0, 38600, 104),
                "C2": (19300, 38600, 104),
                "C3": (38600, 38600, 104),
                "C4": (57900, 38600, 104),
                "C5": (77200, 38600, 104),
                "C6": (96500, 38600, 104),
                "D1": (0, 57900, 104),
                "D2": (19300, 57900, 104),
                "D3": (38600, 57900, 104),
                "D4": (57900, 57900, 104),
                "D5": (77200, 57900, 104),
                "D6": (96500, 57900, 104),
                "name": "24",
                "well_diameter": 15540,
            },
        ),
        (
            "96",
            {
                "A1": (0, 0, 104),
                "A10": (81000, 0, 104),
                "A11": (90000, 0, 104),
                "A12": (99000, 0, 104),
                "A2": (9000, 0, 104),
                "A3": (18000, 0, 104),
                "A4": (27000, 0, 104),
                "A5": (36000, 0, 104),
                "A6": (45000, 0, 104),
                "A7": (54000, 0, 104),
                "A8": (63000, 0, 104),
                "A9": (72000, 0, 104),
                "B1": (0, 9000, 104),
                "B10": (81000, 9000, 104),
                "B11": (90000, 9000, 104),
                "B12": (99000, 9000, 104),
                "B2": (9000, 9000, 104),
                "B3": (18000, 9000, 104),
                "B4": (27000, 9000, 104),
                "B5": (36000, 9000, 104),
                "B6": (45000, 9000, 104),
                "B7": (54000, 9000, 104),
                "B8": (63000, 9000, 104),
                "B9": (72000, 9000, 104),
                "C1": (0, 18000, 104),
                "C10": (81000, 18000, 104),
                "C11": (90000, 18000, 104),
                "C12": (99000, 18000, 104),
                "C2": (9000, 18000, 104),
                "C3": (18000, 18000, 104),
                "C4": (27000, 18000, 104),
                "C5": (36000, 18000, 104),
                "C6": (45000, 18000, 104),
                "C7": (54000, 18000, 104),
                "C8": (63000, 18000, 104),
                "C9": (72000, 18000, 104),
                "D1": (0, 27000, 104),
                "D10": (81000, 27000, 104),
                "D11": (90000, 27000, 104),
                "D12": (99000, 27000, 104),
                "D2": (9000, 27000, 104),
                "D3": (18000, 27000, 104),
                "D4": (27000, 27000, 104),
                "D5": (36000, 27000, 104),
                "D6": (45000, 27000, 104),
                "D7": (54000, 27000, 104),
                "D8": (63000, 27000, 104),
                "D9": (72000, 27000, 104),
                "E1": (0, 36000, 104),
                "E10": (81000, 36000, 104),
                "E11": (90000, 36000, 104),
                "E12": (99000, 36000, 104),
                "E2": (9000, 36000, 104),
                "E3": (18000, 36000, 104),
                "E4": (27000, 36000, 104),
                "E5": (36000, 36000, 104),
                "E6": (45000, 36000, 104),
                "E7": (54000, 36000, 104),
                "E8": (63000, 36000, 104),
                "E9": (72000, 36000, 104),
                "F1": (0, 45000, 104),
                "F10": (81000, 45000, 104),
                "F11": (90000, 45000, 104),
                "F12": (99000, 45000, 104),
                "F2": (9000, 45000, 104),
                "F3": (18000, 45000, 104),
                "F4": (27000, 45000, 104),
                "F5": (36000, 45000, 104),
                "F6": (45000, 45000, 104),
                "F7": (54000, 45000, 104),
                "F8": (63000, 45000, 104),
                "F9": (72000, 45000, 104),
                "G1": (0, 54000, 104),
                "G10": (81000, 54000, 104),
                "G11": (90000, 54000, 104),
                "G12": (99000, 54000, 104),
                "G2": (9000, 54000, 104),
                "G3": (18000, 54000, 104),
                "G4": (27000, 54000, 104),
                "G5": (36000, 54000, 104),
                "G6": (45000, 54000, 104),
                "G7": (54000, 54000, 104),
                "G8": (63000, 54000, 104),
                "G9": (72000, 54000, 104),
                "H1": (0, 63000, 104),
                "H10": (81000, 63000, 104),
                "H11": (90000, 63000, 104),
                "H12": (99000, 63000, 104),
                "H2": (9000, 63000, 104),
                "H3": (18000, 63000, 104),
                "H4": (27000, 63000, 104),
                "H5": (36000, 63000, 104),
                "H6": (45000, 63000, 104),
                "H7": (54000, 63000, 104),
                "H8": (63000, 63000, 104),
                "H9": (72000, 63000, 104),
                "name": "96",
                "well_diameter": 6134,
            },
        ),
    ],
)
def test_create_plate(plate_format, expected):
    assert samples.create_plate(plate_format) == expected


@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    ("n_col, n_row, x_pitch, y_pitch, z_pos, expected"),
    [
        (
            2,
            2,
            0.1,
            0.1,
            0,
            [(-0.05, -0.05, 0), (-0.05, 0.05, 0), (0.05, -0.05, 0), (0.05, 0.05, 0)],
        ),
        (
            5,
            10,
            0.5,
            0.1,
            2,
            [
                (-1.0, -0.45, 2),
                (-1.0, -0.35000000000000003, 2),
                (-1.0, -0.25, 2),
                (-1.0, -0.15000000000000002, 2),
                (-1.0, -0.05, 2),
                (-1.0, 0.05, 2),
                (-1.0, 0.15000000000000002, 2),
                (-1.0, 0.25, 2),
                (-1.0, 0.35000000000000003, 2),
                (-1.0, 0.45, 2),
                (-0.5, -0.45, 2),
                (-0.5, -0.35000000000000003, 2),
                (-0.5, -0.25, 2),
                (-0.5, -0.15000000000000002, 2),
                (-0.5, -0.05, 2),
                (-0.5, 0.05, 2),
                (-0.5, 0.15000000000000002, 2),
                (-0.5, 0.25, 2),
                (-0.5, 0.35000000000000003, 2),
                (-0.5, 0.45, 2),
                (0.0, -0.45, 2),
                (0.0, -0.35000000000000003, 2),
                (0.0, -0.25, 2),
                (0.0, -0.15000000000000002, 2),
                (0.0, -0.05, 2),
                (0.0, 0.05, 2),
                (0.0, 0.15000000000000002, 2),
                (0.0, 0.25, 2),
                (0.0, 0.35000000000000003, 2),
                (0.0, 0.45, 2),
                (0.5, -0.45, 2),
                (0.5, -0.35000000000000003, 2),
                (0.5, -0.25, 2),
                (0.5, -0.15000000000000002, 2),
                (0.5, -0.05, 2),
                (0.5, 0.05, 2),
                (0.5, 0.15000000000000002, 2),
                (0.5, 0.25, 2),
                (0.5, 0.35000000000000003, 2),
                (0.5, 0.45, 2),
                (1.0, -0.45, 2),
                (1.0, -0.35000000000000003, 2),
                (1.0, -0.25, 2),
                (1.0, -0.15000000000000002, 2),
                (1.0, -0.05, 2),
                (1.0, 0.05, 2),
                (1.0, 0.15000000000000002, 2),
                (1.0, 0.25, 2),
                (1.0, 0.35000000000000003, 2),
                (1.0, 0.45, 2),
            ],
        ),
    ],
)
def test_create_rect_tile(n_col, n_row, x_pitch, y_pitch, z_pos, expected):
    print(samples.create_rect_tile(n_col, n_row, x_pitch, y_pitch, z_pos))
    assert samples.create_rect_tile(n_col, n_row, x_pitch, y_pitch, z_pos) == expected


###############################################################################
#
# Tests for the ImagingSystem class
#
###############################################################################


@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    ("stage_id_init, stage_id_change"), [(None, ""), ("stage_init", "stage_final")]
)
def test_set_hardware(stage_id_init, stage_id_change, helpers):
    img_sys = helpers.setup_local_imaging_system(helpers, stage_id=stage_id_init)
    assert img_sys.stage_id == stage_id_init

    img_sys.set_hardware(stage_id=stage_id_change)
    assert img_sys.stage_id == stage_id_change


@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    ("name_get, name_set"), [(None, ""), ("test_name", "new_test_name")]
)
def test_get_set_name(name_get, name_set, helpers):
    img_sys = helpers.setup_local_imaging_system(helpers, name=name_get)
    assert img_sys.get_name() == name_get

    img_sys.set_name(name_set)
    assert img_sys.get_name() == name_set


@patch("pyqtgraph.TextItem")
@patch(
    "microscope_automation.samples.interactive_location_picker_pyqtgraph.ImageLocationPicker.plot_points"
)  # noqa
@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    ("location_list, expected"), [(None, "TypeError"), ([], []), ([(1, 2)], [(1, 0)])]
)
def test_set_interactive_positions_img_system(
    mock0, mock1, location_list, expected, helpers
):
    img_sys = helpers.setup_local_imaging_system(helpers)
    image_data = [[0, 0]]

    try:
        result = img_sys.set_interactive_positions(image_data, location_list)
    except Exception as err:
        result = type(err).__name__

    assert result == expected


@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    ("name_get, name_set"), [(None, ""), ("test_name", "new_test_name")]
)
def test_get_set_ref_object(name_get, name_set, helpers):
    ref_obj_get = helpers.setup_local_imaging_system(helpers, name=name_get)
    img_sys = helpers.setup_local_imaging_system(helpers, reference_object=ref_obj_get)
    assert img_sys.get_reference_object().get_name() == name_get

    ref_obj_set = helpers.setup_local_imaging_system(helpers, name=name_set)
    img_sys.set_reference_object(ref_obj_set)
    assert img_sys.get_reference_object().get_name() == name_set


@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    ("x_set, y_set, z_set, x_get, y_get, z_get, ref_obj_name"),
    [
        (None, 1, 2, None, None, None, None),
        (-1, 1, 0, -1, 1, 0, None),
        (0, 1, 2, None, None, None, "test_ref_obj")
    ]
)
def test_get_set_ref_position(x_set, y_set, z_set, x_get, y_get, z_get,
                              ref_obj_name, helpers):
    if ref_obj_name:
        ref_obj = helpers.setup_local_imaging_system(helpers, name=ref_obj_name)
    else:
        ref_obj = None

    img_sys = helpers.setup_local_imaging_system(helpers, reference_object=ref_obj,
                                                 x_ref=x_set, y_ref=y_set, z_ref=z_set)
    assert img_sys.get_reference_position() == (x_get, y_get, z_get)
