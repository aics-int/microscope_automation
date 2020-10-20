"""
Test samples Classes
Created on October 5, 2020

@author: fletcher.chapin
"""

import pytest
import numpy as np
from mock import patch
from microscope_automation.image_AICS import ImageAICS
from microscope_automation.preferences import Preferences
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


@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    ("prefs_path, expected_cell_count, expected_name"),
    [("data/preferences_ZSD_test.yml", 1, "C1D5")]
)
def test_create_plate_holder_manually(prefs_path, expected_cell_count,
                                      expected_name, helpers):
    m = helpers.setup_local_microscope(prefs_path)
    prefs = Preferences(prefs_path)

    result = samples.create_plate_holder_manually(m, prefs)

    assert result.name == expected_name
    assert result.number_cells() == expected_cell_count

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
    ("name_get, name_set, repr"),
    [
        (None, "", "<class ImagingSystem: ''>"),
        ("test_name", "new_test_name", "<class ImagingSystem: 'new_test_name'>"),
    ],
)
def test_get_set_name(name_get, name_set, repr, helpers):
    img_sys = helpers.setup_local_imaging_system(helpers, name=name_get)
    assert img_sys.get_name() == name_get

    img_sys.set_name(name_set)
    assert img_sys.get_name() == name_set

    assert img_sys.__repr__() == repr


@patch("pyqtgraph.TextItem")
@patch(
    "microscope_automation.samples.interactive_location_picker_pyqtgraph.ImageLocationPicker.plot_points"  # noqa
)
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
        (0, 1, 2, None, None, None, "test_ref_obj"),
    ],
)
def test_get_set_ref_position(
    x_set, y_set, z_set, x_get, y_get, z_get, ref_obj_name, helpers
):
    if ref_obj_name:
        ref_obj = helpers.setup_local_imaging_system(helpers, name=ref_obj_name)
    else:
        ref_obj = None

    img_sys = helpers.setup_local_imaging_system(
        helpers, reference_object=ref_obj, x_ref=x_set, y_ref=y_set, z_ref=z_set
    )
    assert img_sys.get_reference_position() == (x_get, y_get, z_get)


@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    ("img_sys_name, sample_obj_name"),
    [
        (None, None),
        ("test_sys", "test_sample"),
    ],
)
def test_add_samples_img_sys(img_sys_name, sample_obj_name, helpers):
    sample_obj = helpers.setup_local_imaging_system(helpers, name=sample_obj_name)
    img_sys = helpers.setup_local_imaging_system(helpers, name=img_sys_name)

    img_sys.add_samples({sample_obj_name: sample_obj})

    assert img_sys.samples == {sample_obj_name: sample_obj}


@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    ("img_sys_name, well_obj_name, expected"),
    [
        (None, None, "AttributeError"),
        ("test_sys", "test_well", "test_well"),
    ],
)
def test_get_well_object_img_sys(img_sys_name, well_obj_name, expected, helpers):
    if well_obj_name:
        well_obj = helpers.setup_local_well(helpers, name=well_obj_name)
    else:
        well_obj = None

    try:
        img_sys = helpers.setup_local_imaging_system(helpers, name=img_sys_name,
                                                     container=well_obj)
        result = img_sys.get_well_object().name
    except Exception as err:
        result = type(err).__name__

    assert expected == result


@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    ("image_set, image_get"),
    [
        (None, True),
        (True, True),
        (False, True),
    ],
)
def test_get_set_image(image_set, image_get, helpers):
    if image_set:
        img_sys = helpers.setup_local_imaging_system(helpers, image=image_set)
    else:
        img_sys = helpers.setup_local_imaging_system(helpers)

    assert img_sys.get_image() == image_get


@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    ("list_name, sample_object_types, position, expected"),
    [
        ("test_dir", None, None, []),
        ("test_dir", "well", None, ["Well"]),
        ("test_dir", "well", 0, ["Well"]),
        ("test_dir", "well", 3, ["Well"]),
        ("test_dir", ["well", "well"], None, ["Well", "Well"]),
        ("test_dir", ["well", "plate", "plate_holder"], None,
         ["Well", "Plate", "PlateHolder"])
    ],
)
def test_add_to_get_from_image_dir(list_name, sample_object_types, position,
                                   expected, helpers):
    img_sys = helpers.setup_local_imaging_system(helpers)

    if sample_object_types:
        if isinstance(sample_object_types, list):
            sample_objects = []
            for t in sample_object_types:
                obj = helpers.create_sample_object(t)
                sample_objects.append(obj)
        else:
            sample_objects = helpers.create_sample_object(sample_object_types)
    else:
        sample_objects = None

    img_sys.add_to_image_dir(list_name, sample_objects, position)
    result = img_sys.get_from_image_dir(list_name)

    if result:
        result2 = []
        for sample in result:
            result2.append(sample.name)

        result = result2

    assert result == expected


@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    ("plate_obj_name, barcode, expected"),
    [
        (None, None, "AttributeError"),
        ("test_plate", None, None),
        ("test_plate", "1234", "1234"),
    ],
)
def test_get_set_barcode_img_sys(plate_obj_name, barcode, expected, helpers):
    if plate_obj_name:
        well_obj = helpers.setup_local_plate(helpers, name=plate_obj_name)
    else:
        well_obj = None

    try:
        img_sys = helpers.setup_local_imaging_system(helpers, container=well_obj)

        img_sys.set_barcode(barcode)
        result = img_sys.get_barcode()
    except Exception as err:
        result = type(err).__name__

    assert result == expected


@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    ("sample_type, expected"),
    [
        ("plate_holder", "PlateHolder"),
        ("plate", "Plate"),
        ("well", "Well"),
        ("img_sys", "ImagingSystem"),
    ],
)
def test_get_sample_type(sample_type, expected, helpers):
    obj = helpers.create_sample_object(sample_type)
    result = obj.get_sample_type()

    assert result == expected


@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    ("sample_type, container_type, prefs_path, x, y, z, verbose, expected"),
    [
        ("img_sys", None, None, None, None, None, True, "AttributeError"),
        ("img_sys", "well", None, None, None, None, True, "AttributeError"),
        ("img_sys", "plate_holder", None, None, None, None, True, "AttributeError"),
        ("plate_holder", None, None, None, None, None, True, "AttributeError"),
        ("img_sys", "plate_holder", "data/preferences_ZSD_test.yml", None,
         None, None, True, "TypeError"),
        ("plate_holder", None, "data/preferences_ZSD_test.yml",
         None, None, None, True, (None, None, 500)),
        ("img_sys", "well", None, 1, 2, 3, False, (1, 2, 3)),
    ],
)
def test_set_zero(sample_type, container_type, prefs_path, x, y, z, verbose,
                  expected, helpers):
    if prefs_path:
        stage = helpers.setup_local_stage(helpers, "Marzhauser")
        autofocus = helpers.setup_local_autofocus(helpers, "DefiniteFocus2")
        focus_drive = helpers.setup_local_focus_drive(helpers, "MotorizedFocus")

        microscope_obj = helpers.setup_local_microscope(prefs_path)
        microscope_obj.add_microscope_object([stage, autofocus, focus_drive])
    else:
        microscope_obj = None

    container_obj = helpers.create_sample_object(container_type,
                                                 microscope_obj=microscope_obj,
                                                 stage_id="Marzhauser",
                                                 autofocus_id="DefiniteFocus2",
                                                 focus_id="MotorizedFocus")
    sample_obj = helpers.create_sample_object(sample_type, container=container_obj,
                                              microscope_obj=microscope_obj,
                                              stage_id="Marzhauser",
                                              autofocus_id="DefiniteFocus2",
                                              focus_id="MotorizedFocus")

    try:
        result = sample_obj.set_zero(x, y, z, verbose)
    except Exception as err:
        result = type(err).__name__

    assert result == expected


@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    ("x, y, z, expected"),
    [
        (None, None, None, (0, 0, 0)),
        (None, -5, None, (0, -5, 0)),
        (3, 2, 1, (3, 2, 1)),
    ],
)
def test_get_update_zero(x, y, z, expected, helpers):
    img_sys = helpers.setup_local_imaging_system(helpers)
    img_sys.update_zero(x, y, z)
    result = img_sys.get_zero()

    assert result == expected


@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    ("sample_type, expected"),
    [
        ("img_sys", "ZeroDivisionError"),
        ("plate_holder", (0.0, 0.0, 0.0))
    ],
)
def test_get_abs_zero(sample_type, expected, helpers):
    sample = helpers.create_sample_object(sample_type)

    try:
        result = sample.get_abs_zero()
    except Exception as err:
        result = type(err).__name__

    assert result == expected


@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    ("container_type, x, y, z, expected"),
    [
        (None, 0, 0, None, (0, 0, None)),
        (None, 1, -3, 2, (1, -3, 2)),
        (None, None, None, None, "AttributeError"),
        ("plate_holder", None, None, None, (55600, 31800, 0)),
    ],
)
def test_get_set_safe(container_type, x, y, z, expected, helpers):
    container_obj = helpers.create_sample_object(container_type)
    img_sys = helpers.setup_local_imaging_system(helpers, container=container_obj)

    try:
        img_sys.set_safe(x, y, z)
        result = img_sys.get_safe()
    except Exception as err:
        result = type(err).__name__

    assert result == expected


@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    ("x, y, z, expected"),
    [
        (None, -5, None, "TypeError"),
        (1, 1, 1, (1, 1, 1)),
        (1, -1, -1, (1, -1, -1)),
    ],
)
def test_get_update_flip(x, y, z, expected, helpers):
    img_sys = helpers.setup_local_imaging_system(helpers)

    try:
        img_sys.update_flip(x, y, z)
        result = img_sys.get_flip()
    except Exception as err:
        result = type(err).__name__

    assert result == expected


@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    ("sample_type, x_correction, y_correction, z_correction, z_correction_x_slope, "
     "z_correction_y_slope, xyz_correction_x_zero, xyz_correction_y_zero, expected"),
    [
        (
            "img_sys",
            1, 1, 1, 1, 1, 1, 1,
            {
                "x_correction": 0,
                "y_correction": 0,
                "z_correction": 0,
                "z_correction_x_slope": 0,
                "z_correction_y_slope": 0,
                "z_correction_z_slope": 0,
                "z_correction_offset": 0,
            }
        ),
        (
            "plate_holder",
            1, 1, 1, 1, 1, 1, 1,
            {
                "x_correction": 1,
                "y_correction": 1,
                "z_correction": 1,
                "z_correction_x_slope": 0,
                "z_correction_y_slope": 0,
                "z_correction_z_slope": 0,
                "z_correction_offset": 0,
            }
        ),
    ],
)
def test_get_update_correction(sample_type, x_correction, y_correction, z_correction,
                               z_correction_x_slope, z_correction_y_slope,
                               xyz_correction_x_zero, xyz_correction_y_zero,
                               expected, helpers):
    sample = helpers.create_sample_object(sample_type)

    try:
        sample.update_correction(x_correction, y_correction, z_correction,
                                 z_correction_x_slope, z_correction_y_slope,
                                 xyz_correction_x_zero, xyz_correction_y_zero)
        result = sample.get_correction()
    except Exception as err:
        result = type(err).__name__

    assert result == expected


@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    ("prefs_path, experiment, use_reference, use_auto_focus, auto_focus_id, expected"),
    [
        (None, "WellTile_10x_true.czexp", False, False, None, "AttributeError"),
        ("data/preferences_3i_test.yml", "test_communication.exp.prefs",
         False, False, None, True),
        ("data/preferences_3i_test.yml", "test_communication.exp.prefs",
         False, True, "DefiniteFocus2", True),
    ]
)
def test_microscope_is_ready(prefs_path, experiment, use_reference,
                             use_auto_focus, auto_focus_id, expected, helpers):
    if prefs_path:
        microscope = helpers.setup_local_microscope(prefs_path)
    else:
        microscope = None

    if auto_focus_id:
        autofocus = helpers.setup_local_autofocus(
            helpers, auto_focus_id, prefs_path=prefs_path
        )
        microscope.add_microscope_object(autofocus)

    img_sys = helpers.create_sample_object("img_sys",
                                           microscope_obj=microscope,
                                           autofocus_id=auto_focus_id)

    try:
        result = img_sys.microscope_is_ready(experiment,
                                             use_reference=use_reference,
                                             use_auto_focus=use_auto_focus)
    except Exception as err:
        result = type(err).__name__

    assert result == expected


@patch(
    "microscope_automation.zeiss.hardware_control_zeiss.SpinningDiskZeiss.recover_hardware"  # noqa
)
@patch("microscope_automation.hardware.hardware_components.Safety.show_safe_areas")
@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    ("sample_type, container_type, x, y, z, ref_obj_type, prefs_path, expected"),
    [
        ("img_sys", None, None, None, None, None, None, "AttributeError"),
        ("img_sys", "plate_holder", None, None, None, None, None, "AttributeError"),
        ("img_sys", "plate_holder", None, None, None, None,
         "data/preferences_ZSD_test.yml", (0, 0, 500),),
    ]
)
def test_move_to_abs_position(mock_show, mock_recover, sample_type, container_type,
                              x, y, z, ref_obj_type, prefs_path, expected, helpers):
    if prefs_path:
        microscope, stage_id, focus_id, autofocus_id, obj_changer_id, safety_id = helpers.microscope_for_samples_testing(helpers, prefs_path)  # noqa
    else:
        microscope = None
        stage_id = None
        focus_id = None
        autofocus_id = None
        obj_changer_id = None
        safety_id = None

    if container_type:
        container = helpers.create_sample_object(container_type,
                                                 microscope_obj=microscope,
                                                 stage_id=stage_id,
                                                 focus_id=focus_id,
                                                 autofocus_id=autofocus_id,
                                                 obj_changer_id=obj_changer_id,
                                                 safety_id=safety_id)
    else:
        container = None

    if ref_obj_type:
        ref_obj = helpers.create_sample_object(ref_obj_type)
    else:
        ref_obj = None

    sample = helpers.create_sample_object(sample_type, container=container,
                                          microscope_obj=microscope,
                                          stage_id=stage_id,
                                          focus_id=focus_id,
                                          autofocus_id=autofocus_id,
                                          obj_changer_id=obj_changer_id,
                                          safety_id=safety_id,
                                          ref_obj=ref_obj)
    try:
        result = sample.move_to_abs_position(x, y, z, ref_obj)
    except Exception as err:
        result = type(err).__name__

    assert result == expected


@patch(
    "microscope_automation.zeiss.hardware_control_zeiss.SpinningDiskZeiss.recover_hardware"  # noqa
)
@patch("microscope_automation.hardware.hardware_components.Safety.show_safe_areas")
@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    ("sample_type, prefs_path, expected"),
    [
        ("img_sys", None, "ZeroDivisionError"),
        ("plate_holder", None, "AttributeError"),
        ("plate_holder", "data/preferences_ZSD_test.yml", (0, 0, 0)),
    ]
)
def test_move_to_zero(mock_show, mock_recover, sample_type, prefs_path, expected,
                      helpers):
    if prefs_path:
        microscope, stage_id, focus_id, autofocus_id, obj_changer_id, safety_id = helpers.microscope_for_samples_testing(helpers, prefs_path)  # noqa
    else:
        microscope = None
        stage_id = None
        focus_id = None
        autofocus_id = None
        obj_changer_id = None
        safety_id = None

    sample = helpers.create_sample_object(sample_type,
                                          microscope_obj=microscope,
                                          stage_id=stage_id,
                                          focus_id=focus_id,
                                          autofocus_id=autofocus_id,
                                          obj_changer_id=obj_changer_id,
                                          safety_id=safety_id)

    try:
        result = sample.move_to_zero()
    except Exception as err:
        result = type(err).__name__

    assert result == expected


@patch(
    "microscope_automation.zeiss.hardware_control_zeiss.SpinningDiskZeiss.recover_hardware"  # noqa
)
@patch("microscope_automation.hardware.hardware_components.Safety.show_safe_areas")
@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    ("sample_type, prefs_path, x_safe, y_safe, z_safe, expected"),
    [
        ("img_sys", None, None, None, None, "AttributeError"),
        ("plate_holder", None, None, None, None, "AttributeError"),
        ("plate_holder", "data/preferences_ZSD_test.yml", None, None, None,
         (55600.0, 31800.0, 0.0)),
        ("img_sys", "data/preferences_ZSD_test.yml", 55600, 31800, None,
         "AttributeError"),
        ("plate_holder", "data/preferences_ZSD_test.yml", 55600, 31800, None,
         (55600.0, 31800.0, 500)),
    ]
)
def test_move_to_safe(mock_show, mock_recover, sample_type,
                      prefs_path, x_safe, y_safe, z_safe, expected, helpers):
    if prefs_path:
        microscope, stage_id, focus_id, autofocus_id, obj_changer_id, safety_id = helpers.microscope_for_samples_testing(helpers, prefs_path)  # noqa
    else:
        microscope = None
        stage_id = None
        focus_id = None
        autofocus_id = None
        obj_changer_id = None
        safety_id = None

    sample = helpers.create_sample_object(sample_type,
                                          microscope_obj=microscope,
                                          stage_id=stage_id,
                                          focus_id=focus_id,
                                          autofocus_id=autofocus_id,
                                          obj_changer_id=obj_changer_id,
                                          safety_id=safety_id)

    try:
        if x_safe or y_safe or z_safe:
            sample.set_safe(x_safe, y_safe, z_safe)
        result = sample.move_to_safe()
    except Exception as err:
        result = type(err).__name__

    assert result == expected


@patch(
    "microscope_automation.zeiss.hardware_control_zeiss.SpinningDiskZeiss.recover_hardware"  # noqa
)
@patch("microscope_automation.hardware.hardware_components.Safety.show_safe_areas")
@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    ("sample_type, prefs_path, x, y, z, expected"),
    [
        ("img_sys", None, 0, 0, 0, "ZeroDivisionError"),
        ("plate_holder", None, 0, 0, 0, "AttributeError"),
        ("plate_holder", "data/preferences_ZSD_test.yml", 1, 1, None, (1.0, 1.0, 500)),
        ("plate_holder", "data/preferences_ZSD_test.yml", 1, 1, 2, (1.0, 1.0, 2.0)),
    ]
)
def test_move_to_xyz(mock_show, mock_recover, sample_type, prefs_path,
                     x, y, z, expected, helpers):
    if prefs_path:
        microscope, stage_id, focus_id, autofocus_id, obj_changer_id, safety_id = helpers.microscope_for_samples_testing(helpers, prefs_path)  # noqa
    else:
        microscope = None
        stage_id = None
        focus_id = None
        autofocus_id = None
        obj_changer_id = None
        safety_id = None

    sample = helpers.create_sample_object(sample_type,
                                          microscope_obj=microscope,
                                          stage_id=stage_id,
                                          focus_id=focus_id,
                                          autofocus_id=autofocus_id,
                                          obj_changer_id=obj_changer_id,
                                          safety_id=safety_id)

    try:
        result = sample.move_to_xyz(x, y, z)
    except Exception as err:
        result = type(err).__name__

    assert result == expected


@patch(
    "microscope_automation.zeiss.hardware_control_zeiss.SpinningDiskZeiss.recover_hardware"  # noqa
)
@patch("microscope_automation.hardware.hardware_components.Safety.show_safe_areas")
@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    ("sample_type, prefs_path, r, phi, expected"),
    [
        ("img_sys", None, 0, 0, "ZeroDivisionError"),
        ("plate_holder", None, 0, 0, "AttributeError"),
        ("plate_holder", "data/preferences_ZSD_test.yml", 0, 0, (0.0, 0.0, 500)),
        ("plate_holder", "data/preferences_ZSD_test.yml", 1, 2 * np.pi,
         (0.10944260690631982, 0.9939931165725187, 500)),
    ]
)
def test_move_to_r_phi(mock_show, mock_recover, sample_type, prefs_path,
                       r, phi, expected, helpers):
    if prefs_path:
        microscope, stage_id, focus_id, autofocus_id, obj_changer_id, safety_id = helpers.microscope_for_samples_testing(helpers, prefs_path)  # noqa
    else:
        microscope = None
        stage_id = None
        focus_id = None
        autofocus_id = None
        obj_changer_id = None
        safety_id = None

    sample = helpers.create_sample_object(sample_type,
                                          microscope_obj=microscope,
                                          stage_id=stage_id,
                                          focus_id=focus_id,
                                          autofocus_id=autofocus_id,
                                          obj_changer_id=obj_changer_id,
                                          safety_id=safety_id)

    try:
        result = sample.move_to_r_phi(r, phi)
    except Exception as err:
        result = type(err).__name__

    assert result == expected


@patch(
    "microscope_automation.zeiss.hardware_control_zeiss.SpinningDiskZeiss.recover_hardware"  # noqa
)
@patch("microscope_automation.hardware.hardware_components.Safety.show_safe_areas")
@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    ("sample_type, prefs_path, x, y, z, expected"),
    [
        ("img_sys", None, 0, 0, 0, "AttributeError"),
        ("plate_holder", "data/preferences_ZSD_test.yml", 1, 1, None, "TypeError"),
        ("plate_holder", "data/preferences_ZSD_test.yml", 1, 1, 2, (1, 1, 502)),
    ]
)
def test_move_delta_xyz(mock_show, mock_recover, sample_type, prefs_path,
                        x, y, z, expected, helpers):
    if prefs_path:
        microscope, stage_id, focus_id, autofocus_id, obj_changer_id, safety_id = helpers.microscope_for_samples_testing(helpers, prefs_path)  # noqa
    else:
        microscope = None
        stage_id = None
        focus_id = None
        autofocus_id = None
        obj_changer_id = None
        safety_id = None

    sample = helpers.create_sample_object(sample_type,
                                          microscope_obj=microscope,
                                          stage_id=stage_id,
                                          focus_id=focus_id,
                                          autofocus_id=autofocus_id,
                                          obj_changer_id=obj_changer_id,
                                          safety_id=safety_id)

    try:
        result = sample.move_delta_xyz(x, y, z)
    except Exception as err:
        result = type(err).__name__

    assert result == expected


@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    ("sample_type, container_type, prefs_path, stage_id, focus_id, expected"),
    [
        ("img_sys", None, None, None, None, "AttributeError"),
        ("img_sys", None, "data/preferences_ZSD_test.yml", "Marzhauser",
         "MotorizedFocus", "AttributeError"),
        ("plate_holder", None, "data/preferences_ZSD_test.yml", "Marzhauser",
         "MotorizedFocus", (None, None, None)),
        ("img_sys", "plate_holder", "data/preferences_ZSD_test.yml", "Marzhauser",
         "MotorizedFocus", (None, None, None)),
    ]
)
def test_get_abs_position(sample_type, container_type, prefs_path, stage_id,
                          focus_id, expected, helpers):
    if prefs_path:
        stage = helpers.setup_local_stage(helpers, stage_id)
        focus_drive = helpers.setup_local_focus_drive(helpers, focus_id)
        microscope = helpers.setup_local_microscope(prefs_path)
        microscope.add_microscope_object([stage, focus_drive])
    else:
        microscope = None

    if container_type:
        container = helpers.create_sample_object(container_type,
                                                 microscope_obj=microscope,
                                                 stage_id=stage_id,
                                                 focus_id=focus_id)
    else:
        container = None

    sample = helpers.create_sample_object(sample_type, container=container,
                                          microscope_obj=microscope,
                                          stage_id=stage_id,
                                          focus_id=focus_id)

    try:
        result = sample.get_abs_position(stage_id, focus_id)
    except Exception as err:
        result = type(err).__name__

    assert result == expected


@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    ("z_slope_z_correction, x, y, expected"),
    [
        (0, None, None, 0),
        (1, 0, 0, 0),
        (-1, 1, 1, 0),
    ]
)
def test_calculate_slope_correction(z_slope_z_correction, x, y, expected, helpers):
    img_sys = helpers.setup_local_imaging_system(helpers)
    img_sys.z_correction_z_slope = z_slope_z_correction

    result = img_sys.calculate_slope_correction(x, y)
    assert result == expected


@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    ("sample_type, container_type, x_container, y_container, z_container, expected"),
    [
        ("img_sys", None, 0, 0, 0, (0, 0, 0)),
        ("img_sys", None, 3, 2, 1, (0, 0, 0)),
        ("plate_holder", None, 3, 2, 1, (3, 2, 1)),
        ("img_sys", "plate_holder", 0, 0, 0, (0, 0, 0)),
        ("img_sys", "plate_holder", 1, 2, 3, (0, 0, 0)),
    ]
)
def test_get_obj_pos_from_container_pos(sample_type, container_type, x_container,
                                        y_container, z_container, expected, helpers):
    if container_type:
        container = helpers.create_sample_object(container_type)
    else:
        container = None

    sample = helpers.create_sample_object(sample_type, container=container)
    result = sample.get_obj_pos_from_container_pos(x_container,
                                                   y_container, z_container)

    assert result == expected


@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    ("sample_type, container_type, prefs_path, x, y, z, expected"),
    [
        ("img_sys", None, None, 0, 0, 0, (0, 0, 0)),
        ("img_sys", None, None, None, None, None, "AttributeError"),
        ("plate_holder", None, None, None, None, None, "AttributeError"),
        ("plate_holder", None, "data/preferences_ZSD_test.yml", None, None, None,
         (0, 0, 500)),
        ("plate_holder", None, "data/preferences_ZSD_test.yml", 50000, 10000, None,
         (50000, 10000, 500)),
        ("img_sys", "plate_holder", None, 2, 3, 1, (0, 0, 0)),
        ("plate_holder", "img_sys", None, 2, 3, 1, (2, 3, 1)),
    ]
)
def test_get_pos_from_abs_pos(sample_type, container_type, prefs_path, x, y, z,
                              expected, helpers):
    if prefs_path:
        microscope, stage_id, focus_id, autofocus_id, obj_changer_id, safety_id = helpers.microscope_for_samples_testing(helpers, prefs_path)  # noqa
    else:
        microscope = None
        stage_id = None
        focus_id = None

    if container_type:
        container = helpers.create_sample_object(container_type,
                                                 microscope_obj=microscope,
                                                 stage_id=stage_id,
                                                 focus_id=focus_id)
    else:
        container = None

    sample = helpers.create_sample_object(sample_type, container=container,
                                          microscope_obj=microscope,
                                          stage_id=stage_id,
                                          focus_id=focus_id)
    try:
        result = sample.get_pos_from_abs_pos(x, y, z)
    except Exception as err:
        result = type(err).__name__

    assert result == expected


@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    ("sample_type, container_type, prefs_path, x, y, z, expected"),
    [
        ("img_sys", None, None, 0, 0, 0, "ZeroDivisionError"),
        ("img_sys", None, None, None, None, None, "TypeError"),
        ("plate_holder", None, None, None, None, None, "TypeError"),
        ("plate_holder", None, "data/preferences_ZSD_test.yml", None, None, None,
         "TypeError"),
        ("plate_holder", None, "data/preferences_ZSD_test.yml", 50000, 10000, None,
         (50000.0, 10000.0, None)),
        ("img_sys", "plate_holder", None, 2, 3, 1, "ZeroDivisionError"),
        ("plate", "plate_holder", None, 2, 3, 1, (2.0, 3.0, 1.0)),
    ]
)
def test_get_abs_pos_from_obj_pos(sample_type, container_type, prefs_path, x, y, z,
                                  expected, helpers):
    if prefs_path:
        microscope, stage_id, focus_id, autofocus_id, obj_changer_id, safety_id = helpers.microscope_for_samples_testing(helpers, prefs_path)  # noqa
    else:
        microscope = None
        stage_id = None
        focus_id = None

    if container_type:
        container = helpers.create_sample_object(container_type,
                                                 microscope_obj=microscope,
                                                 stage_id=stage_id,
                                                 focus_id=focus_id)
    else:
        container = None

    sample = helpers.create_sample_object(sample_type, container=container,
                                          microscope_obj=microscope,
                                          stage_id=stage_id,
                                          focus_id=focus_id)
    try:
        result = sample.get_abs_pos_from_obj_pos(x, y, z)
    except Exception as err:
        result = type(err).__name__

    assert result == expected


@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    ("sample_type, container_type, prefs_path, x, y, z, expected"),
    [
        ("img_sys", None, None, 0, 0, 0, "ZeroDivisionError"),
        ("img_sys", None, None, None, None, None, "TypeError"),
        ("plate_holder", None, None, None, None, None, "TypeError"),
        ("plate_holder", None, "data/preferences_ZSD_test.yml", None, None, None,
         "TypeError"),
        ("plate_holder", None, "data/preferences_ZSD_test.yml", 50000, 10000, None,
         (50000.0, 10000.0, None)),
        ("img_sys", "plate_holder", None, 2, 3, 1, "ZeroDivisionError"),
        ("plate", "plate_holder", None, 2, 3, 1, (2.0, 3.0, 1.0)),
    ]
)
def test_get_container_pos_from_obj_pos(sample_type, container_type, prefs_path,
                                        x, y, z, expected, helpers):
    if prefs_path:
        microscope, stage_id, focus_id, autofocus_id, obj_changer_id, safety_id = helpers.microscope_for_samples_testing(helpers, prefs_path)  # noqa
    else:
        microscope = None
        stage_id = None
        focus_id = None

    if container_type:
        container = helpers.create_sample_object(container_type,
                                                 microscope_obj=microscope,
                                                 stage_id=stage_id,
                                                 focus_id=focus_id)
    else:
        container = None

    sample = helpers.create_sample_object(sample_type, container=container,
                                          microscope_obj=microscope,
                                          stage_id=stage_id,
                                          focus_id=focus_id)

    try:
        result = sample.get_container_pos_from_obj_pos(x, y, z)
    except Exception as err:
        result = type(err).__name__

    assert result == expected


@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    ("container_type, prefs_path, flag, expected"),
    [
        (None, None, None, "AttributeError"),
        ("plate_holder", "data/preferences_ZSD_test.yml", False, False),
        ("plate_holder", "data/preferences_ZSD_test.yml", True, True),
    ]
)
def test_get_set_autofocus(container_type, prefs_path, flag,
                           expected, helpers):
    if prefs_path:
        microscope, stage_id, focus_id, autofocus_id, obj_changer_id, safety_id = helpers.microscope_for_samples_testing(helpers, prefs_path)  # noqa
    else:
        microscope = None
        autofocus_id = None
        obj_changer_id = None

    if container_type:
        container = helpers.create_sample_object(container_type,
                                                 microscope_obj=microscope,
                                                 autofocus_id=autofocus_id,
                                                 obj_changer_id=obj_changer_id)
    else:
        container = None

    sample = helpers.setup_local_imaging_system(helpers, container,
                                                prefs_path=prefs_path,
                                                auto_focus_id=autofocus_id,
                                                objective_changer_id=obj_changer_id)
    try:
        if flag:
            sample.set_use_autofocus(flag)
        result = sample.get_use_autofocus()
    except Exception as err:
        result = type(err).__name__

    assert result == expected


@patch("microscope_automation.zeiss.hardware_control_zeiss.SpinningDiskZeiss.setup_microscope_for_initialization")  # noqa
@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    ("container_type, ref_object_type, prefs_path, expected"),
    [
        (None, None, None, "AttributeError"),
        ("plate_holder", None, "data/preferences_ZSD_test.yml",
         {'DefiniteFocus2': {'initial_focus': 9000, 'use': False,
          'experiment': 'Not defined', 'camera': None, 'live_mode': True,
          'reference_object_id': None, 'delta_z': None}}),
        ("plate_holder", "plate", "data/preferences_ZSD_test.yml",
         "HardwareCommandNotDefinedError"),
    ]
)
def test_find_surface(mock_setup, container_type, ref_object_type, prefs_path,
                      expected, helpers):
    if prefs_path:
        microscope, stage_id, focus_id, autofocus_id, obj_changer_id, safety_id = helpers.microscope_for_samples_testing(helpers, prefs_path)  # noqa
    else:
        microscope = None
        autofocus_id = None

    if ref_object_type:
        ref_object = helpers.create_sample_object(ref_object_type)
    else:
        ref_object = None

    if container_type:
        container = helpers.create_sample_object(container_type,
                                                 microscope_obj=microscope,
                                                 autofocus_id=autofocus_id)
    else:
        container = None

    sample = helpers.setup_local_imaging_system(helpers, container,
                                                prefs_path=prefs_path,
                                                auto_focus_id=autofocus_id,
                                                reference_object=ref_object)

    try:
        result = sample.find_surface()
    except Exception as err:
        result = type(err).__name__

    assert result == expected


@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    ("container_type, ref_object_type, prefs_path, expected"),
    [
        (None, None, None, "AttributeError"),
        ("plate_holder", None, "data/preferences_ZSD_test.yml",
         {'DefiniteFocus2':
          {'initial_focus': 500, 'use': False,
           'experiment': 'Not defined', 'camera': None, 'live_mode': True,
           'reference_object_id': '', 'delta_z': None}}),
        ("plate_holder", "plate", "data/preferences_ZSD_test.yml",
         {'DefiniteFocus2':
          {'initial_focus': 500, 'use': False,
           'experiment': 'Not defined', 'camera': None, 'live_mode': True,
           'reference_object_id': 'Plate', 'delta_z': None}}),
    ]
)
def test_store_focus(container_type, ref_object_type, prefs_path,
                     expected, helpers):
    if prefs_path:
        microscope, stage_id, focus_id, autofocus_id, obj_changer_id, safety_id = helpers.microscope_for_samples_testing(helpers, prefs_path)  # noqa
    else:
        microscope = None
        autofocus_id = None

    if ref_object_type:
        ref_object = helpers.create_sample_object(ref_object_type)
    else:
        ref_object = None

    if container_type:
        container = helpers.create_sample_object(container_type,
                                                 microscope_obj=microscope,
                                                 autofocus_id=autofocus_id)
    else:
        container = None

    sample = helpers.setup_local_imaging_system(helpers, container,
                                                prefs_path=prefs_path,
                                                auto_focus_id=autofocus_id,
                                                reference_object=ref_object)

    try:
        result = sample.store_focus(focus_reference_obj=ref_object)
    except Exception as err:
        result = type(err).__name__

    assert result == expected


@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    ("container_type, camera_id, experiment, prefs_path, expected"),
    [
        (None, None, None, None, "AttributeError"),
        ("plate_holder", "Camera1 (back)", "WellTile_10x_true.czexp",
         "data/preferences_ZSD_test.yml", "AttributeError"),
    ]
)
def test_recall_focus(container_type, camera_id, experiment, prefs_path,
                      expected, helpers):
    if prefs_path:
        microscope = helpers.setup_local_microscope(prefs_path)
        microscope.add_microscope_object(helpers.setup_local_camera(camera_id))
    else:
        microscope = None

    if container_type:
        container = helpers.create_sample_object(container_type,
                                                 microscope_obj=microscope)
    else:
        container = None

    sample = helpers.setup_local_imaging_system(helpers, container,
                                                prefs_path=prefs_path)

    try:
        result = sample.recall_focus(camera_id, experiment)
    except Exception as err:
        result = type(err).__name__

    assert result == expected


@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    ("container_type, camera_id, experiment, prefs_path, expected"),
    [
        (None, "Camera1 (back)", "WellTile_10x_true.czexp",
         "data/preferences_ZSD_test.yml", "AttributeError"),
        ("plate_holder", "Camera1 (back)",
         "WellTile_10x_true.czexp", "data/preferences_ZSD_test.yml", None),
    ]
)
def test_live_mode_start_stop(container_type, camera_id, experiment, prefs_path,
                              expected, helpers):
    if prefs_path:
        microscope = helpers.setup_local_microscope(prefs_path)
        microscope.add_microscope_object(helpers.setup_local_camera(camera_id))
    else:
        microscope = None

    if container_type:
        container = helpers.create_sample_object(container_type,
                                                 microscope_obj=microscope)
    else:
        container = None

    sample = helpers.setup_local_imaging_system(helpers, container,
                                                prefs_path=prefs_path)

    try:
        result = sample.live_mode_start(camera_id, experiment)
        result = sample.live_mode_stop(camera_id, experiment)
    except Exception as err:
        result = type(err).__name__

    assert result == expected


@patch("microscope_automation.zeiss.connect_zen_blue.ConnectMicroscope.save_image")
@patch(
    "microscope_automation.zeiss.connect_zen_blue.ConnectMicroscope.close_experiment"
)  # noqa
@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    ("container_type, ref_object_type, camera_id, experiment, file_path, "
     "meta_dict, prefs_path, expected"),
    [
        (None, None, "Camera1 (back)", "WellTile_10x_true.czexp", None, None,
         "data/preferences_ZSD_test.yml", "AttributeError"),
        ("plate_holder", None, "Camera1 (back)", "WellTile_10x_true.czexp", None,
         {}, "data/preferences_ZSD_test.yml", ImageAICS),
        ("plate_holder", "plate", "Camera1 (back)", "WellTile_10x_true.czexp",
         "data/test_sample_image.czi", None, "data/preferences_ZSD_test.yml",
         ImageAICS),
    ]
)
def test_execute_experiment(mock_close, mock_save, container_type, ref_object_type,
                            camera_id, experiment, file_path, meta_dict,
                            prefs_path, expected, helpers):
    if prefs_path:
        microscope, stage_id, focus_id, autofocus_id, obj_changer_id, safety_id = helpers.microscope_for_samples_testing(helpers, prefs_path)  # noqa
        microscope.add_microscope_object(helpers.setup_local_camera(camera_id))
    else:
        microscope = None
        focus_id = None

    if ref_object_type:
        ref_object = helpers.create_sample_object(ref_object_type)
    else:
        ref_object = None

    if container_type:
        container = helpers.create_sample_object(container_type,
                                                 microscope_obj=microscope,
                                                 focus_id=focus_id,
                                                 stage_id=stage_id,
                                                 autofocus_id=autofocus_id)
    else:
        container = None

    sample = helpers.setup_local_imaging_system(helpers, container,
                                                reference_object=ref_object,
                                                prefs_path=prefs_path,
                                                focus_id=focus_id,
                                                stage_id=stage_id,
                                                auto_focus_id=autofocus_id)

    try:
        result = sample.execute_experiment(experiment, camera_id,
                                           reference_object=ref_object,
                                           file_path=file_path,
                                           meta_dict=meta_dict)
        result = result.__class__
    except Exception as err:
        result = type(err).__name__

    assert result == expected


@patch("microscope_automation.hardware.hardware_components.ObjectiveChanger.initialize")
@patch(
    "microscope_automation.hardware.hardware_control.BaseMicroscope.recover_hardware"
)  # noqa
@patch("microscope_automation.hardware.hardware_components.Safety.show_safe_areas")
@patch("microscope_automation.zeiss.connect_zen_blue.ConnectMicroscope.save_image")
@patch(
    "microscope_automation.zeiss.connect_zen_blue.ConnectMicroscope.close_experiment"
)  # noqa
@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    ("container_type, ref_object_type, camera_id, experiment, file_path, "
     "pos_list, meta_dict, use_reference, prefs_path, expected"),
    [
        (None, None, "Camera1 (back)", "WellTile_10x_true.czexp", None, None, None,
         False, "data/preferences_ZSD_test.yml", "AttributeError"),
        ("plate_holder", None, "Camera1 (back)", "WellTile_10x_true.czexp", None, {},
         None, False, "data/preferences_ZSD_test.yml", []),
        ("plate_holder", "plate", "Camera1 (back)", "WellTile_10x_true.czexp",
         "data/test_sample_image.czi", None, None, True,
         "data/preferences_ZSD_test.yml", [ImageAICS]),
        ("plate_holder", "plate", "Camera1 (back)", "WellTile_10x_true.czexp",
         "data/test_sample_image.czi", None, {}, True,
         "data/preferences_ZSD_test.yml", [ImageAICS]),
        ("plate_holder", "plate", "Camera1 (back)", "WellTile_10x_true.czexp",
         "data/test_sample_image.czi", [(1, 2, 3)], {}, True,
         "data/preferences_ZSD_test.yml", [ImageAICS]),
    ]
)
def test_acquire_images(mock_close, mock_save, mock_show, mock_recover, mock_init,
                        container_type, ref_object_type, camera_id, experiment,
                        file_path, pos_list, meta_dict, use_reference,
                        prefs_path, expected, helpers):
    if prefs_path:
        microscope, stage_id, focus_id, autofocus_id, obj_changer_id, safety_id = helpers.microscope_for_samples_testing(helpers, prefs_path)  # noqa
        microscope.add_microscope_object(helpers.setup_local_camera(camera_id))
    else:
        microscope = None
        focus_id = None
        obj_changer_id = None
        focus_id = None
        stage_id = None
        autofocus_id = None
        safety_id = None

    if ref_object_type:
        ref_object = helpers.create_sample_object(ref_object_type)
    else:
        ref_object = None

    if container_type:
        container = helpers.create_sample_object(container_type,
                                                 microscope_obj=microscope,
                                                 focus_id=focus_id,
                                                 stage_id=stage_id,
                                                 autofocus_id=autofocus_id,
                                                 obj_changer_id=obj_changer_id,
                                                 safety_id=safety_id)
    else:
        container = None

    sample = helpers.create_sample_object("img_sys", container=container,
                                          microscope_obj=microscope,
                                          ref_obj=ref_object,
                                          focus_id=focus_id,
                                          stage_id=stage_id,
                                          autofocus_id=autofocus_id,
                                          obj_changer_id=obj_changer_id,
                                          safety_id=safety_id)

    try:
        results = sample.acquire_images(experiment, camera_id,
                                        reference_object=ref_object,
                                        file_path=file_path,
                                        pos_list=pos_list)
        final_result = []
        for r in results:
            final_result.append(r.__class__)
    except Exception as err:
        final_result = type(err).__name__

    assert final_result == expected


@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    ("sample_type, prefs_path, pref_name, tile_obj, expected"),
    [
        ("img_sys", None, None, None, "ZeroDivisionError"),
        ("plate_holder", None, None, None, "ValueError"),
        ("plate_holder", None, None, "NoTiling",
            {'center': (0.0, 0.0, 0.0),
             'degrees': None,
             'percentage': 100,
             'tile_number': (1, 1),
             'tile_size': (None, None),
             'tile_type': 'none'}),
        ("plate_holder", None, None, "Fixed", "AttributeError"),
        ("plate_holder", "data/preferences_ZSD_test.yml", "ScanPlate", "Fixed",
         {'center': (0.0, 0.0, 0.0),
          'degrees': 0,
          'percentage': 100,
          'tile_number': (2, 2),
          'tile_size': (1000, 756.17),
          'tile_type': 'rectangle'}),
        ("well", "data/preferences_ZSD_test.yml", "ScanCells", "Well", "TypeError"),
        ("well", "data/preferences_ZSD_test.yml", "ScanPlate", "Well",
         {'center': (0.0, 0.0, 0.0),
          'degrees': 0,
          'percentage': 20,
          'tile_number': (1, 1),
          'tile_size': (1000, 756.17),
          'tile_type': 'ellipse'}),
        ("colony", "data/preferences_ZSD_test.yml", "ScanCells", "ColonySize",
         {'center': (0.0, 0.0, 0.0),
          'degrees': None,
          'percentage': 100,
          'tile_number': (None, None),
          'tile_size': (100.32, 75.62),
          'tile_type': 'ellipse'}),
    ]
)
def test_get_tile_params(sample_type, prefs_path, pref_name, tile_obj,
                         expected, helpers):
    if prefs_path:
        prefs = Preferences(pref_path=prefs_path)
        image_settings = prefs.get_pref_as_meta(pref_name)
    else:
        image_settings = None

    sample = helpers.create_sample_object(sample_type)
    try:
        result = sample._get_tile_params(image_settings, tile_obj)
    except Exception as err:
        result = type(err).__name__

    assert result == expected


@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    ("tile_params, expected"),
    [
        ({}, "KeyError"),
        ({'center': (0.0, 0.0, 0.0),
          'degrees': None,
          'percentage': 100,
          'tile_number': (None, None),
          'tile_size': (100.32, 75.62),
          'tile_type': 'ellipse'}, "TypeError"),
        ({'center': (0.0, 0.0, 0.0),
          'degrees': None,
          'percentage': 100,
          'tile_number': (2, 2),
          'tile_size': (100.32, 75.62),
          'tile_type': 'ellipse'}, [(-50.16, -37.81, 0.0), (-50.16, 37.81, 0.0),
                                    (50.16, -37.81, 0.0), (50.16, 37.81, 0.0)]),
    ]
)
def test_compute_tile_positions_list(tile_params, expected, helpers):
    img_sys = helpers.setup_local_imaging_system(helpers)

    try:
        result = img_sys._compute_tile_positions_list(tile_params)
    except Exception as err:
        result = type(err).__name__

    assert result == expected


@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    ("sample_type, prefs_path, pref_name, tile_object, expected"),
    [
        ("img_sys", None, None, "NoTiling", "ZeroDivisionError"),
        ("colony", None, None, "NoTiling", [(0.0, 0.0, 0.0)]),
        ("colony", "data/preferences_ZSD_test.yml", "ScanCells", "ColonySize",
         "TypeError"),
        ("well", "data/preferences_ZSD_test.yml", "ScanCells", "Well",
         None),
        ("well", "data/preferences_ZSD_test.yml", "ScanPlate", "Well",
         [(0.0, 0.0, 0.0)]),
        ("plate_holder", "data/preferences_ZSD_test.yml", "ScanPlate", "Well",
         "AttributeError"),
        ("plate_holder", "data/preferences_ZSD_test.yml", "ScanPlate", "Fixed",
         [(-500.0, -378.085, 0.0), (-500.0, 378.085, 0.0),
          (500.0, -378.085, 0.0), (500.0, 378.085, 0.0)]),
    ]
)
def test_get_tile_positions_list(sample_type, prefs_path, pref_name,
                                 tile_object, expected, helpers):
    if prefs_path:
        prefs = Preferences(pref_path=prefs_path)
        image_settings = prefs.get_pref_as_meta(pref_name)
    else:
        image_settings = None

    sample = helpers.create_sample_object(sample_type)

    try:
        result = sample.get_tile_positions_list(image_settings, tile_object)
    except Exception as err:
        result = type(err).__name__

    assert result == expected


@patch("microscope_automation.zeiss.connect_zen_blue.ConnectMicroscope.load_image")
@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    ("container_type, prefs_path, image, get_meta, expected"),
    [
        (None, "data/preferences_ZSD_test.yml", ImageAICS(), False, "AttributeError"),
        ("plate_holder", "data/preferences_ZSD_test.yml", ImageAICS(), True,
         "<class 'mock.mock.MagicMock'>")
    ]
)
def test_load_image(mock_load, container_type, prefs_path, image, get_meta,
                    expected, helpers):
    if prefs_path:
        microscope = helpers.setup_local_microscope(prefs_path)
    else:
        microscope = None

    if container_type:
        container = helpers.create_sample_object(container_type,
                                                 microscope_obj=microscope)
    else:
        container = None

    sample = helpers.create_sample_object("img_sys", container=container,
                                          microscope_obj=microscope)

    try:
        result = sample.load_image(image, get_meta)
        result = str(result.__class__)
    except Exception as err:
        result = type(err).__name__

    assert result == expected

###############################################################################
#
# Tests for the PlateHolder class
#
###############################################################################
