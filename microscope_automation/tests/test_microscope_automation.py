"""
Test microscope automation's main module, which orchestrates workflows.
Created on December 1, 2020

@author: fletcher.chapin
"""

import pytest
import os
import datetime
from shutil import copyfile
from mock import patch
from collections import Mapping
from microscope_automation.image_AICS import ImageAICS
from microscope_automation.preferences import Preferences
from microscope_automation.samples import samples
from microscope_automation.automation_messages_form_layout import stop_script

os.chdir(os.path.dirname(__file__))

# set skip_all_tests = True to focus on single test
skip_all_tests = False

today = datetime.date.today()
DATE_STR = str(today.year) + "_" + str(today.month) + "_" + str(today.day)


@patch("microscope_automation.automation_messages_form_layout.information_message")
@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    ("text, allow_continue, expected"),
    [
        (None, False, "SystemExit"),
        (None, True, None),
    ],
)
def test_stop_script(mock_message, text, allow_continue, expected):
    try:
        result = stop_script(message_text=text, allow_continue=allow_continue)
    except SystemExit as err:
        result = type(err).__name__
    assert result == expected


@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    ("prefs_path, plate_holder_name, plate_name, well"),
    [
        ("data/preferences_ZSD_test.yml", "Plateholder", "96-well", "A1"),
    ],
)
def test_get_well_object(prefs_path, plate_holder_name, plate_name, well, helpers):
    mic_auto = helpers.setup_local_microscope_automation(prefs_path)
    well_object = helpers.setup_local_well(helpers, name=well, plate_name=plate_name)
    plate_holder_object = helpers.setup_local_plate_holder(helpers, plate_holder_name)
    plate_object = well_object.container
    plate_object.set_container(plate_holder_object)
    plate_object.add_wells({well: well_object})
    plate_holder_object.add_plates({plate_name: plate_object})

    result = mic_auto.get_well_object(plate_holder_object, plate_name, well)

    assert result.name == well
    assert result.__class__ == samples.Well


@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    ("prefs_path, well_name, barcode_name"),
    [
        ("data/preferences_ZSD_test.yml", "A1", "1234"),
    ],
)
def test_get_barcode_object(prefs_path, well_name, barcode_name, helpers):
    mic_auto = helpers.setup_local_microscope_automation(prefs_path)
    well_object = helpers.setup_local_well(helpers, name=well_name)
    barcode_object = samples.Barcode(name=barcode_name)
    well_object.add_barcode({barcode_name: barcode_object})

    result = mic_auto.get_barcode_object(well_object, barcode_name)

    assert result.name == barcode_name
    assert result.__class__ == samples.Barcode


@patch("microscope_automation.samples.samples.PlateHolder.execute_experiment")
@patch("microscope_automation.automation_messages_form_layout.operate_message")
@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    (
        "prefs_path, pref_name, plate_holder_name, plate_name, "
        "well_name, barcode_name, expected"
    ),
    [
        (
            "data/preferences_ZSD_2_test.yml",
            "ImageBarcode",
            "Plateholder",
            "96-well",
            "A1",
            "1234",
            "Not implemented",
        ),
        (
            "data/preferences_ZSD_2_test.yml",
            "ImageBarcode",
            "Plateholder",
            "96-well",
            None,
            None,
            "AttributeError",
        ),
    ],
)
def test_read_barcode(
    mock_message,
    mock_execute,
    prefs_path,
    pref_name,
    plate_holder_name,
    plate_name,
    well_name,
    barcode_name,
    expected,
    helpers,
):
    mic_auto = helpers.setup_local_microscope_automation(prefs_path)
    well_object = helpers.setup_local_well(
        helpers, name=well_name, plate_name=plate_name
    )
    plate_holder_object = helpers.setup_local_plate_holder(
        helpers, name=plate_holder_name, prefs_path=prefs_path
    )
    plate_object = well_object.container
    plate_object.set_container(plate_holder_object)
    plate_object.add_wells({well_name: well_object})
    plate_holder_object.add_plates({plate_name: plate_object})
    barcode_object = samples.Barcode(name=barcode_name)
    barcode_object.set_container(well_object)
    well_object.add_barcode({barcode_name: barcode_object})

    try:
        result = mic_auto.read_barcode(
            Preferences(prefs_path).get_pref_as_meta(pref_name),
            plate_holder_object,
            plate_name,
            well_name,
            barcode_name,
        )
    except Exception as err:
        result = type(err).__name__

    assert result == expected


@patch(
    "microscope_automation.automation_messages_form_layout.read_string", return_value=""
)
@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    (
        "prefs_path, pref_name, plate_holder_name, plate_name, "
        "well_names, well_diameter, expected"
    ),
    [
        (
            "data/preferences_ZSD_2_test.yml",
            "CalibrateWellDiameter",
            "Plateholder",
            "96-well",
            ["B2", "B11", "G11"],
            None,
            "TypeError",
        ),
        (
            "data/preferences_ZSD_2_test.yml",
            "CalibrateWellDiameter",
            "Plateholder",
            "96-well",
            ["B2", "B11", "G11"],
            6134,
            None,
        ),
        (
            "data/preferences_ZSD_2_test.yml",
            "ImageBarcode",
            "Plateholder",
            "96-well",
            [],
            None,
            "AttributeError",
        ),
    ],
)
def test_calculate_all_wells_correction(
    mock_read,
    prefs_path,
    pref_name,
    plate_holder_name,
    plate_name,
    well_names,
    well_diameter,
    expected,
    helpers,
):
    mic_auto = helpers.setup_local_microscope_automation(prefs_path)
    plate_object = helpers.setup_local_plate(helpers, name=plate_name)
    plate_holder_object = helpers.setup_local_plate_holder(
        helpers, name=plate_holder_name, prefs_path=prefs_path
    )
    plate_object.set_container(plate_holder_object)
    plate_holder_object.add_plates({plate_name: plate_object})
    for name in well_names:
        well = helpers.setup_local_well(helpers, name=name)
        well.set_measured_diameter(well_diameter)
        well.container = plate_object
        plate_object.add_wells({name: well})

    try:
        result = mic_auto.calculate_all_wells_correction(
            Preferences(prefs_path).get_pref_as_meta(pref_name),
            plate_holder_object,
            None,
        )
    except Exception as err:
        result = type(err).__name__

    assert result == expected


@patch(
    "microscope_automation.automation_messages_form_layout.read_string", return_value=""
)
@patch("microscope_automation.automation_messages_form_layout.operate_message")
@patch("microscope_automation.hardware.hardware_components.Safety.show_safe_areas")
@patch("microscope_automation.samples.samples.PlateHolder.execute_experiment")
@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    ("prefs_path, pref_name, plate_holder_name, immersion_name, expected"),
    [
        (
            None,
            "SetupImmersionSystem",
            "Plateholder",
            "ImmersionDelivery",
            "AssertionError",
        ),
        (
            "data/preferences_ZSD_2_test.yml",
            "SetupImmersionSystem",
            "Plateholder",
            "ImmersionDelivery",
            None,
        ),
    ],
)
def test_setup_immersion_system(
    mock_execute,
    mock_show_safe,
    mock_message,
    mock_read,
    prefs_path,
    pref_name,
    plate_holder_name,
    immersion_name,
    expected,
    helpers,
):
    if prefs_path:
        (
            microscope,
            stage_id,
            focus_id,
            autofocus_id,
            obj_changer_id,
            safety_id,
        ) = helpers.microscope_for_samples_testing(helpers, prefs_path)
    else:
        microscope = None
        focus_id = None
        stage_id = None
        autofocus_id = None
        obj_changer_id = None
        safety_id = None

    plate_holder = helpers.create_sample_object(
        "plate_holder",
        microscope_obj=microscope,
        focus_id=focus_id,
        stage_id=stage_id,
        autofocus_id=autofocus_id,
        obj_changer_id=obj_changer_id,
        safety_id=safety_id,
    )
    plate_holder.immersion_delivery_system = helpers.setup_local_immersion_delivery(
        helpers, name=immersion_name
    )
    plate_holder.immersion_delivery_system.container = plate_holder

    try:
        mic_auto = helpers.setup_local_microscope_automation(prefs_path)
        prefs = Preferences(prefs_path).get_pref_as_meta(pref_name)
        result = mic_auto.setup_immersion_system(
            prefs,
            plate_holder,
        )

        assert (
            prefs.get_pref("MagnificationImmersionSystem")
            == plate_holder.immersion_delivery_system.magnification
        )
    except Exception as err:
        result = type(err).__name__

    assert result == expected


@patch("microscope_automation.automation_messages_form_layout.operate_message")
@patch(
    "microscope_automation.zeiss.connect_zen_blue.ConnectMicroscope.get_all_objectives"
)
@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    ("objective_dict, prefs_path, plate_holder_name, expected"),
    [
        (
            {"10": {"Position": 6, "Name": "Plan-Apochromat 10x/0.45"}},
            "data/preferences_ZSD_2_test.yml",
            "Plateholder",
            None,
        ),
    ],
)
def test_set_up_objectives_and_offset(
    mock_get_obj,
    mock_operate,
    objective_dict,
    prefs_path,
    plate_holder_name,
    expected,
    helpers,
):
    mock_get_obj.return_value = objective_dict
    (
        microscope,
        stage_id,
        focus_id,
        autofocus_id,
        obj_changer_id,
        safety_id,
    ) = helpers.microscope_for_samples_testing(helpers, prefs_path)

    plate_holder = helpers.create_sample_object(
        "plate_holder",
        microscope_obj=microscope,
        focus_id=focus_id,
        stage_id=stage_id,
        autofocus_id=autofocus_id,
        obj_changer_id=obj_changer_id,
        safety_id=safety_id,
    )
    plate_object = helpers.create_sample_object(
        "plate",
        container=plate_holder,
    )
    plate_holder.add_plates({"Plate": plate_object})
    plate_object.set_reference_object(plate_holder)

    mic_auto = helpers.setup_local_microscope_automation(prefs_path)
    result0 = mic_auto.set_up_objectives(
        Preferences(prefs_path).get_pref_as_meta("SetUpObjectives"),
        plate_holder,
        None,
    )

    result1 = mic_auto.set_objective_offset(
        Preferences(prefs_path).get_pref_as_meta("ObjectiveOffsets"),
        plate_holder,
        None,
    )

    assert result0 == expected and result1 == expected


@patch("microscope_automation.automation_messages_form_layout.operate_message")
@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    ("prefs_path, pref_name, plate_holder_name, well_name, camera_id, expected"),
    [
        (
            "data/preferences_ZSD_2_test.yml",
            "Koehler",
            "Plateholder",
            "E7",
            "Camera1 (back)",
            None,
        ),
    ],
)
def test_set_up_koehler(
    mock_message,
    prefs_path,
    pref_name,
    plate_holder_name,
    well_name,
    camera_id,
    expected,
    helpers,
):
    (
        microscope,
        stage_id,
        focus_id,
        autofocus_id,
        obj_changer_id,
        safety_id,
    ) = helpers.microscope_for_samples_testing(helpers, prefs_path)
    microscope.add_microscope_object(helpers.setup_local_camera(camera_id))

    plate_holder_object = helpers.create_sample_object(
        "plate_holder",
        microscope_obj=microscope,
        camera_ids=[camera_id],
        focus_id=focus_id,
        stage_id=stage_id,
        autofocus_id=autofocus_id,
        obj_changer_id=obj_changer_id,
        safety_id=safety_id,
    )
    plate_object = helpers.create_sample_object(
        "plate",
        container=plate_holder_object,
    )
    well_object = helpers.create_sample_object("well", container=plate_object)
    plate_object.add_wells({well_name: well_object})

    mic_auto = helpers.setup_local_microscope_automation(prefs_path)
    result = mic_auto.set_up_koehler(
        Preferences(prefs_path).get_pref_as_meta(pref_name), plate_object
    )

    assert result == expected


@patch("microscope_automation.automation_messages_form_layout.file_select_dialog")
@patch(
    "microscope_automation.microscope_automation.MicroscopeAutomation.set_up_koehler"
)
@patch("microscope_automation.automation_messages_form_layout.operate_message")
@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    ("prefs_path, pref_name, expected"),
    [
        ("data/preferences_ZSD_2_test.yml", "InitializeMicroscope", None),
        ("data/preferences_ZSD_2_test.yml", "Koehler", None),
    ],
)
def test_initialize_microscope(
    mock_message,
    mock_koehler,
    mock_file_dialog,
    prefs_path,
    pref_name,
    expected,
    helpers,
):
    mock_file_dialog.return_value = "data/PlateSpecifications/PipelineData_Celigo.csv"
    camera_id = "Camera1 (back)"
    (
        microscope,
        stage_id,
        focus_id,
        autofocus_id,
        obj_changer_id,
        safety_id,
    ) = helpers.microscope_for_samples_testing(helpers, prefs_path)
    plate_holder_object = helpers.create_sample_object(
        "plate_holder",
        microscope_obj=microscope,
        camera_ids=[camera_id],
        focus_id=focus_id,
        stage_id=stage_id,
        autofocus_id=autofocus_id,
        obj_changer_id=obj_changer_id,
        safety_id=safety_id,
    )
    plate_object = helpers.create_sample_object(
        "plate",
        container=plate_holder_object,
    )
    plate_holder_object.add_plates({"Plate": plate_object})
    plate_object.set_reference_object(plate_holder_object)

    mic_auto = helpers.setup_local_microscope_automation(prefs_path)
    result = mic_auto.initialize_microscope(
        Preferences(prefs_path).get_pref_as_meta(pref_name),
        plate_holder_object,
        None,
    )

    assert result == expected


@patch("microscope_automation.automation_messages_form_layout.operate_message")
@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    ("prefs_path, pref_name, experiment, well_name, expected"),
    [
        (
            "data/preferences_ZSD_2_test.yml",
            "UpdatePlateWellZero",
            {
                "Experiment": "UpdatePlateWellZero",
                "Repetitions": 1,
                "Input": None,
                "Output": {},
            },
            "Well",
            "AttributeError",
        ),
        (
            "data/preferences_ZSD_2_test.yml",
            "UpdatePlateWellZero",
            {
                "Experiment": "UpdatePlateWellZero",
                "Repetitions": 1,
                "Input": None,
                "Output": {},
                "OriginalWorkflow": ["Koehler", "UpdatePlateWellZero", "RunMacro"],
                "WorkflowList": ["Koehler", "UpdatePlateWellZero", "RunMacro"],
                "WorkflowType": "new",
            },
            "E7",
            None,
        ),
    ],
)
def test_update_plate_z_zero(
    mock_message, prefs_path, pref_name, experiment, well_name, expected, helpers
):
    camera_id = "Camera1 (back)"
    (
        microscope,
        stage_id,
        focus_id,
        autofocus_id,
        obj_changer_id,
        safety_id,
    ) = helpers.microscope_for_samples_testing(helpers, prefs_path)

    plate_holder_object = helpers.create_sample_object(
        "plate_holder",
        microscope_obj=microscope,
        camera_ids=[camera_id],
        focus_id=focus_id,
        stage_id=stage_id,
        autofocus_id=autofocus_id,
        obj_changer_id=obj_changer_id,
        safety_id=safety_id,
    )
    plate_object = helpers.create_sample_object(
        "plate",
        container=plate_holder_object,
    )
    plate_holder_object.add_plates({"Plate": plate_object})
    well_object = helpers.create_sample_object(
        "well",
        container=plate_object,
    )
    plate_object.add_wells({well_name: well_object})
    plate_object.set_reference_object(well_object)

    mic_auto = helpers.setup_local_microscope_automation(prefs_path)
    try:
        result = mic_auto.update_plate_z_zero(
            Preferences(prefs_path).get_pref_as_meta(pref_name),
            plate_holder_object,
            experiment,
        )
    except Exception as err:
        result = type(err).__name__

    assert result == expected


@patch("microscope_automation.samples.samples.Well.find_well_center_fine")
@patch("microscope_automation.zeiss.connect_zen_blue.ConnectMicroscope.load_image")
@patch("microscope_automation.zeiss.connect_zen_blue.ConnectMicroscope.save_image")
@patch(
    "microscope_automation.zeiss.connect_zen_blue.ConnectMicroscope.close_experiment"
)
@patch("microscope_automation.automation_messages_form_layout.operate_message")
@patch(
    "microscope_automation.zeiss.hardware_control_zeiss.SpinningDiskZeiss.reference_position"  # noqa
)
@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    ("prefs_path, pref_name, plate_name, well_names, well_centers, expected"),
    [
        (
            "data/preferences_ZSD_2_test.yml",
            "CalibrateWellDistance",
            "96-well",
            ["B2", "B11", "G11"],
            [(0, 0, 0), (6134, 0, 0), (12268, 0, 0)],
            "ZeroDivisionError",
        ),
        (
            "data/preferences_ZSD_2_test.yml",
            "CalibrateWellDistance",
            "96-well",
            ["B2", "B11", "G11"],
            [(0, 0, 0), (6134, 6134, 0), (12268, 12268, 0)],
            None,
        ),
    ],
)
def test_calculate_plate_correction(
    mock_reference,
    mock_message,
    mock_close,
    mock_save,
    mock_load,
    mock_find_center,
    prefs_path,
    pref_name,
    plate_name,
    well_names,
    well_centers,
    expected,
    helpers,
):
    mock_find_center.side_effect = [(0, 0, 0), (6134, 6134, 0), (12268, 12268, 0)]
    mic_auto = helpers.setup_local_microscope_automation(prefs_path)
    camera_id = "Camera1 (back)"
    (
        microscope,
        stage_id,
        focus_id,
        autofocus_id,
        obj_changer_id,
        safety_id,
    ) = helpers.microscope_for_samples_testing(helpers, prefs_path)

    plate_holder_object = helpers.create_sample_object(
        "plate_holder",
        microscope_obj=microscope,
        camera_ids=[camera_id],
        focus_id=focus_id,
        stage_id=stage_id,
        autofocus_id=autofocus_id,
        obj_changer_id=obj_changer_id,
        safety_id=safety_id,
    )

    plate_object = helpers.setup_local_plate(helpers, name=plate_name)
    plate_object.set_container(plate_holder_object)
    plate_holder_object.add_plates({plate_name: plate_object})
    i = 0
    for name in well_names:
        well = helpers.setup_local_well(helpers, name=name, center=well_centers[i])
        well.container = plate_object
        plate_object.add_wells({name: well})
        i += 1

    try:
        result = mic_auto.calculate_plate_correction(
            Preferences(prefs_path).get_pref_as_meta(pref_name),
            plate_holder_object,
            None,
        )
    except Exception as err:
        result = type(err).__name__

    assert result == expected


@patch("microscope_automation.hardware.hardware_components.Safety.show_safe_areas")
@patch("microscope_automation.zeiss.connect_zen_blue.ConnectMicroscope.save_image")
@patch(
    "microscope_automation.zeiss.connect_zen_blue.ConnectMicroscope.close_experiment"
)
@patch("microscope_automation.automation_messages_form_layout.operate_message")
@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    ("prefs_path, pref_name, well_names, expected"),
    [
        ("data/preferences_ZSD_2_test.yml", "ScanWellsZero", ["B3"], "AttributeError"),
        (
            "data/preferences_ZSD_2_test.yml",
            "ScanWellsZero",
            ["B3", "C3", "D3", "B4", "C4", "D4"],
            None,
        ),
    ],
)
def test_scan_wells_zero(
    mock_message,
    mock_close,
    mock_save,
    mock_show_safe,
    prefs_path,
    pref_name,
    well_names,
    expected,
    helpers,
):
    camera_id = "Camera1 (back)"
    (
        microscope,
        stage_id,
        focus_id,
        autofocus_id,
        obj_changer_id,
        safety_id,
    ) = helpers.microscope_for_samples_testing(helpers, prefs_path)

    plate_holder_object = helpers.create_sample_object(
        "plate_holder",
        microscope_obj=microscope,
        camera_ids=[camera_id],
        focus_id=focus_id,
        stage_id=stage_id,
        autofocus_id=autofocus_id,
        obj_changer_id=obj_changer_id,
        safety_id=safety_id,
    )
    plate_object = helpers.create_sample_object(
        "plate",
        container=plate_holder_object,
    )
    plate_holder_object.add_plates({"Plate": plate_object})
    well_object = helpers.create_sample_object(
        "well",
        container=plate_object,
    )
    for name in well_names:
        well = helpers.setup_local_well(helpers, name=name)
        well.container = plate_object
        plate_object.add_wells({name: well})
        well_object.set_reference_object(plate_object)

    mic_auto = helpers.setup_local_microscope_automation(prefs_path)
    try:
        result = mic_auto.scan_wells_zero(
            Preferences(prefs_path).get_pref_as_meta(pref_name),
            plate_holder_object,
            "Plate",
        )
    except Exception as err:
        result = type(err).__name__

    assert result == expected


@patch(
    "microscope_automation.zeiss.connect_zen_blue.ConnectMicroscope.close_experiment"
)
@patch("microscope_automation.hardware.hardware_components.Safety.show_safe_areas")
@patch("microscope_automation.automation_messages_form_layout.operate_message")
@patch("microscope_automation.automation_messages_form_layout.select_message")
@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    (
        "prefs_path, pref_name, experiment, sample_type, reference_type, "
        "image_path, meta_dict, repetition, expected"
    ),
    [
        (
            "data/preferences_ZSD_2_test.yml",
            "PreScanPlate",
            {
                "Experiment": "UpdatePlateWellZero",
                "Repetitions": 1,
                "Input": None,
                "Output": {},
                "OriginalWorkflow": ["Koehler", "UpdatePlateWellZero", "RunMacro"],
                "WorkflowList": ["Koehler", "UpdatePlateWellZero", "RunMacro"],
                "WorkflowType": "new",
            },
            "plate",
            "well",
            None,
            None,
            0,
            {"Image": [ImageAICS()], "Continue": True},
        ),
        (
            "data/preferences_ZSD_2_test.yml",
            "PreScanPlate",
            {
                "Experiment": "UpdatePlateWellZero",
                "Repetitions": 1,
                "Input": None,
                "Output": {},
                "OriginalWorkflow": ["Koehler", "UpdatePlateWellZero", "RunMacro"],
                "WorkflowList": ["Koehler", "UpdatePlateWellZero", "RunMacro"],
                "WorkflowType": "new",
            },
            "plate",
            "well",
            None,
            None,
            1,
            {"Image": [ImageAICS()], "Continue": True},
        ),
        (
            "data/preferences_ZSD_2_test.yml",
            "ScanPlate",
            {
                "Experiment": "UpdatePlateWellZero",
                "Repetitions": 1,
                "Input": None,
                "Output": {},
                "OriginalWorkflow": ["Koehler", "UpdatePlateWellZero", "RunMacro"],
                "WorkflowList": ["Koehler", "UpdatePlateWellZero", "RunMacro"],
                "WorkflowType": "new",
            },
            "plate",
            None,
            None,
            None,
            1,
            "AttributeError",
        ),
    ],
)
def test_scan_single_ROI(
    mock_select,
    mock_message,
    mock_show_safe,
    mock_close,
    prefs_path,
    pref_name,
    experiment,
    sample_type,
    reference_type,
    image_path,
    meta_dict,
    repetition,
    expected,
    helpers,
):
    if isinstance(expected, Mapping):
        mock_select.return_value = {"Continue": expected["Continue"], "Include": True}
    camera_id = "Camera1 (back)"
    (
        microscope,
        stage_id,
        focus_id,
        autofocus_id,
        obj_changer_id,
        safety_id,
    ) = helpers.microscope_for_samples_testing(helpers, prefs_path)

    plate_holder_object = helpers.create_sample_object(
        "plate_holder",
        microscope_obj=microscope,
        camera_ids=[camera_id],
        focus_id=focus_id,
        stage_id=stage_id,
        autofocus_id=autofocus_id,
        obj_changer_id=obj_changer_id,
        safety_id=safety_id,
    )
    sample_object = helpers.create_sample_object(
        sample_type,
        container=plate_holder_object,
    )
    reference_object = helpers.create_sample_object(reference_type)
    sample_object.set_reference_object(reference_object)

    mic_auto = helpers.setup_local_microscope_automation(prefs_path)
    try:
        result = mic_auto.scan_single_ROI(
            Preferences(prefs_path).get_pref_as_meta(pref_name),
            experiment,
            sample_object,
            reference_object,
            image_path,
            meta_dict,
            repetition=repetition,
        )
        assert result["Continue"] == expected["Continue"]
        assert result["Image"].__class__ == expected["Image"].__class__
    except Exception as err:
        result = type(err).__name__
        assert result == expected


@patch("microscope_automation.zeiss.connect_zen_blue.ConnectMicroscope.load_image")
@patch("microscope_automation.zeiss.connect_zen_blue.ConnectMicroscope.save_image")
@patch(
    "microscope_automation.zeiss.connect_zen_blue.ConnectMicroscope.close_experiment"
)
@patch("microscope_automation.hardware.hardware_components.Safety.show_safe_areas")
@patch(
    "microscope_automation.automation_messages_form_layout.read_string", return_value=""
)
@patch("microscope_automation.automation_messages_form_layout.wait_message")
@patch("microscope_automation.automation_messages_form_layout.information_message")
@patch("microscope_automation.automation_messages_form_layout.operate_message")
@patch("microscope_automation.automation_messages_form_layout.select_message")
@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    (
        "prefs_path, pref_name, experiment, sample_dict, repetition, wait_after_image,"
        "load_error, less_dialog, expected"
    ),
    [
        (
            "data/preferences_ZSD_2_test.yml",
            "ScanPlate",
            {
                "Experiment": "UpdatePlateWellZero",
                "Repetitions": 1,
                "Input": None,
                "Output": {},
                "OriginalWorkflow": ["Koehler", "UpdatePlateWellZero", "RunMacro"],
                "WorkflowList": ["Koehler", "UpdatePlateWellZero", "RunMacro"],
                "WorkflowType": "new",
            },
            {"E7": "well"},
            0,
            None,
            False,
            False,
            "TypeError",
        ),
        (
            "data/preferences_ZSD_2_test.yml",
            "ScanPlate",
            {
                "Experiment": "UpdatePlateWellZero",
                "Repetitions": 1,
                "Input": None,
                "Output": {},
                "OriginalWorkflow": ["Koehler", "UpdatePlateWellZero", "RunMacro"],
                "WorkflowList": ["Koehler", "UpdatePlateWellZero", "RunMacro"],
                "WorkflowType": "new",
            },
            {"E7": "well"},
            0,
            {"Status": True},
            False,
            False,
            None,
        ),
        (
            "data/preferences_ZSD_2_test.yml",
            "ScanPlate",
            {
                "Experiment": "UpdatePlateWellZero",
                "Repetitions": 1,
                "Input": None,
                "Output": {},
                "OriginalWorkflow": ["Koehler", "UpdatePlateWellZero", "RunMacro"],
                "WorkflowList": ["Koehler", "UpdatePlateWellZero", "RunMacro"],
                "WorkflowType": "new",
            },
            {"E7": "well"},
            0,
            {"Status": True},
            False,
            True,
            None,
        ),
        (
            "data/preferences_ZSD_2_test.yml",
            "ScanPlate",
            {
                "Experiment": "UpdatePlateWellZero",
                "Repetitions": 1,
                "Input": None,
                "Output": {},
                "OriginalWorkflow": ["Koehler", "UpdatePlateWellZero", "RunMacro"],
                "WorkflowList": ["Koehler", "UpdatePlateWellZero", "RunMacro"],
                "WorkflowType": "new",
            },
            {"E7": "well"},
            0,
            {"Status": True},
            True,
            False,
            "FileNotFoundError",
        ),
        (
            "data/preferences_ZSD_2_test.yml",
            "ScanPlate",
            {
                "Experiment": "UpdatePlateWellZero",
                "Repetitions": 1,
                "Input": None,
                "Output": {},
                "OriginalWorkflow": ["Koehler", "UpdatePlateWellZero", "RunMacro"],
                "WorkflowList": ["Koehler", "UpdatePlateWellZero", "RunMacro"],
                "WorkflowType": "new",
            },
            {},
            0,
            None,
            False,
            False,
            "IndexError",
        ),
    ],
)
def test_scan_all_objects(
    mock_select,
    mock_message,
    mock_info,
    mock_wait,
    mock_read,
    mock_show_safe,
    mock_close,
    mock_save,
    mock_load,
    prefs_path,
    pref_name,
    experiment,
    sample_dict,
    repetition,
    wait_after_image,
    load_error,
    less_dialog,
    expected,
    helpers,
):
    mock_load.side_effect = FileNotFoundError if load_error else None
    camera_id = "Camera1 (back)"
    (
        microscope,
        stage_id,
        focus_id,
        autofocus_id,
        obj_changer_id,
        safety_id,
    ) = helpers.microscope_for_samples_testing(helpers, prefs_path)

    plate_holder_object = helpers.create_sample_object(
        "plate_holder",
        microscope_obj=microscope,
        camera_ids=[camera_id],
        focus_id=focus_id,
        stage_id=stage_id,
        autofocus_id=autofocus_id,
        obj_changer_id=obj_changer_id,
        safety_id=safety_id,
    )
    plate_object = helpers.create_sample_object(
        "plate",
        container=plate_holder_object,
    )

    sample_list = []
    for name, sample_type in sample_dict.items():
        sample = helpers.create_sample_object(sample_type, container=plate_object)
        sample.set_name(name)
        sample.set_reference_object(plate_object)
        plate_object.add_wells({name: sample})
        sample_list.append(sample)

    mic_auto = helpers.setup_local_microscope_automation(prefs_path)
    mic_auto.less_dialog = less_dialog
    try:
        result = mic_auto.scan_all_objects(
            Preferences(prefs_path).get_pref_as_meta(pref_name),
            sample_list,
            plate_object,
            experiment,
            repetition=repetition,
            wait_after_image=wait_after_image,
        )
    except Exception as err:
        result = type(err).__name__

    assert result == expected


@patch(
    "microscope_automation.automation_messages_form_layout.read_string", return_value=""
)
@patch("microscope_automation.zeiss.write_zen_tiles_experiment.PositionWriter.write")
@patch(
    "microscope_automation.zeiss.write_zen_tiles_experiment.PositionWriter.convert_to_stage_coords"  # noqa
)
@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    (
        "prefs_path, pref_name, experiment, well_names, repetition, wait_after_image,"
        "barcode, expected"
    ),
    [
        (
            "data/preferences_ZSD_2_test.yml",
            "ScanPlate",
            {
                "Experiment": "UpdatePlateWellZero",
                "Repetitions": 1,
                "Input": None,
                "Output": {},
                "OriginalWorkflow": ["Koehler", "UpdatePlateWellZero", "RunMacro"],
                "WorkflowList": ["Koehler", "UpdatePlateWellZero", "RunMacro"],
                "WorkflowType": "new",
            },
            ["E7"],
            0,
            {"Status": True},
            1234,
            "TypeError",
        ),
        (
            "data/preferences_ZSD_2_test.yml",
            "SegmentWells",
            {
                "Experiment": "UpdatePlateWellZero",
                "Repetitions": 1,
                "Input": None,
                "Output": {},
                "OriginalWorkflow": ["Koehler", "UpdatePlateWellZero", "RunMacro"],
                "WorkflowList": ["Koehler", "UpdatePlateWellZero", "RunMacro"],
                "WorkflowType": "new",
            },
            ["B2", "B11", "G11"],
            0,
            {"Status": True},
            None,
            "ValueError",
        ),
        (
            "data/preferences_ZSD_2_test.yml",
            "SegmentWells",
            {
                "Experiment": "UpdatePlateWellZero",
                "Repetitions": 1,
                "Input": None,
                "Output": {},
                "OriginalWorkflow": ["Koehler", "UpdatePlateWellZero", "RunMacro"],
                "WorkflowList": ["Koehler", "UpdatePlateWellZero", "RunMacro"],
                "WorkflowType": "new",
            },
            ["B2", "B11", "G11"],
            0,
            {"Status": True},
            "invalid_barcode",
            "OSError",
        ),
        (
            "data/preferences_ZSD_2_test.yml",
            "SegmentWells",
            {
                "Experiment": "UpdatePlateWellZero",
                "Repetitions": 1,
                "Input": None,
                "Output": {},
                "OriginalWorkflow": ["Koehler", "UpdatePlateWellZero", "RunMacro"],
                "WorkflowList": ["Koehler", "UpdatePlateWellZero", "RunMacro"],
                "WorkflowType": "new",
            },
            ["B2", "B11", "G11"],
            0,
            {"Status": True},
            1234,
            None,
        ),
        (
            "data/preferences_ZSD_test.yml",
            "SegmentWells",
            {
                "Experiment": "UpdatePlateWellZero",
                "Repetitions": 1,
                "Input": None,
                "Output": {},
                "OriginalWorkflow": ["Koehler", "UpdatePlateWellZero", "RunMacro"],
                "WorkflowList": ["Koehler", "UpdatePlateWellZero", "RunMacro"],
                "WorkflowType": "new",
            },
            ["B2", "B11", "G11", "C2"],
            0,
            {"Status": True},
            1234,
            "NameError",
        ),
    ],
)
def test_segment_wells(
    mock_convert,
    mock_write,
    mock_read,
    prefs_path,
    pref_name,
    experiment,
    well_names,
    repetition,
    wait_after_image,
    barcode,
    expected,
    helpers,
):
    basepath = os.path.join("data", "Production", "Daily")
    src = os.path.join(basepath, "WellEdge_0_1_C2.czi")
    dst = os.path.join(
        basepath, DATE_STR, "Zeiss SD 1", "10XwellScan", "WellEdge_0_1_C2.czi"
    )
    try:
        copyfile(src, dst)
    except FileNotFoundError:
        os.makedirs(os.path.dirname(dst))
        copyfile(src, dst)

    camera_id = "Camera1 (back)"
    (
        microscope,
        stage_id,
        focus_id,
        autofocus_id,
        obj_changer_id,
        safety_id,
    ) = helpers.microscope_for_samples_testing(helpers, prefs_path)

    plate_holder_object = helpers.create_sample_object(
        "plate_holder",
        microscope_obj=microscope,
        camera_ids=[camera_id],
        focus_id=focus_id,
        stage_id=stage_id,
        autofocus_id=autofocus_id,
        obj_changer_id=obj_changer_id,
        safety_id=safety_id,
    )
    plate_object = helpers.create_sample_object(
        "plate",
        container=plate_holder_object,
    )
    plate_object.set_barcode(barcode)
    plate_holder_object.add_plates({plate_object.get_name(): plate_object})

    for name in well_names:
        well = helpers.setup_local_well(helpers, name=name)
        well.container = plate_object
        plate_object.add_wells({name: well})

    mic_auto = helpers.setup_local_microscope_automation(prefs_path)
    try:
        result = mic_auto.segment_wells(
            Preferences(prefs_path).get_pref_as_meta(pref_name),
            plate_holder_object,
            experiment,
            repetition=repetition,
            wait_after_image=wait_after_image,
        )
    except Exception as err:
        result = type(err).__name__

    assert result == expected


@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    ("prefs_path, magnification, expected"),
    [
        ("data/preferences_ZSD_test.yml", 10, (20, 15)),
        ("data/preferences_ZSD_test.yml", 100, (0, 0)),
    ],
)
def test_get_objective_offsets(prefs_path, magnification, expected, helpers):
    (
        microscope,
        stage_id,
        focus_id,
        autofocus_id,
        obj_changer_id,
        safety_id,
    ) = helpers.microscope_for_samples_testing(helpers, prefs_path)

    plate_holder_object = helpers.create_sample_object(
        "plate_holder",
        microscope_obj=microscope,
        obj_changer_id=obj_changer_id,
    )

    mic_auto = helpers.setup_local_microscope_automation(prefs_path)
    result = mic_auto.get_objective_offsets(plate_holder_object, magnification)

    assert result == expected


@patch("microscope_automation.zeiss.connect_zen_blue.ConnectMicroscope.load_image")
@patch("microscope_automation.zeiss.connect_zen_blue.ConnectMicroscope.save_image")
@patch(
    "microscope_automation.zeiss.connect_zen_blue.ConnectMicroscope.close_experiment"
)
@patch("microscope_automation.hardware.hardware_components.Safety.show_safe_areas")
@patch("microscope_automation.automation_messages_form_layout.wait_message")
@patch("microscope_automation.automation_messages_form_layout.information_message")
@patch("microscope_automation.automation_messages_form_layout.operate_message")
@patch("microscope_automation.automation_messages_form_layout.select_message")
@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    (
        "prefs_path, pref_name, experiment, well_names, repetition, wait_after_image,"
        "expected"
    ),
    [
        (
            "data/preferences_ZSD_2_test.yml",
            "PreScanPlate",
            {
                "Experiment": "UpdatePlateWellZero",
                "Repetitions": 1,
                "Input": None,
                "Output": {},
                "OriginalWorkflow": ["Koehler", "UpdatePlateWellZero", "RunMacro"],
                "WorkflowList": ["Koehler", "UpdatePlateWellZero", "RunMacro"],
                "WorkflowType": "new",
            },
            ["E5", "E6"],
            0,
            {"Status": True, "Plate": True},
            None,
        ),
        (
            "data/preferences_ZSD_2_test.yml",
            "PreScanPlate",
            {
                "Experiment": "UpdatePlateWellZero",
                "Repetitions": 1,
                "Input": None,
                "Output": {},
                "OriginalWorkflow": ["Koehler", "UpdatePlateWellZero", "RunMacro"],
                "WorkflowList": ["Koehler", "UpdatePlateWellZero", "RunMacro"],
                "WorkflowType": "continue",
                "ObjectsDict": {"Plate": samples.Plate()},
            },
            ["E5", "E6"],
            0,
            {"Status": True, "Plate": True},
            None,
        ),
        (
            "data/preferences_ZSD_2_test.yml",
            "PreScanPlate",
            {
                "Experiment": "UpdatePlateWellZero",
                "Repetitions": 1,
                "Input": None,
                "Output": {},
                "OriginalWorkflow": ["Koehler", "UpdatePlateWellZero", "RunMacro"],
                "WorkflowList": ["Koehler", "UpdatePlateWellZero", "RunMacro"],
                "WorkflowType": "new",
            },
            ["E5", "E6"],
            0,
            {"Status": True},
            "KeyError",
        ),
        (
            "data/preferences_ZSD_test.yml",
            "ScanPlate",
            {
                "Experiment": "UpdatePlateWellZero",
                "Repetitions": 1,
                "Input": None,
                "Output": {},
                "OriginalWorkflow": ["Koehler", "UpdatePlateWellZero", "RunMacro"],
                "WorkflowList": ["Koehler", "UpdatePlateWellZero", "RunMacro"],
                "WorkflowType": "new",
            },
            ["C2"],
            0,
            {"Status": True},
            "ExperimentNotExistError",
        ),
        (
            "data/preferences_ZSD_test.yml",
            "ScanPlate",
            {
                "Experiment": "UpdatePlateWellZero",
                "Repetitions": 1,
                "Input": None,
                "Output": {},
                "OriginalWorkflow": ["Koehler", "UpdatePlateWellZero", "RunMacro"],
                "WorkflowList": ["Koehler", "UpdatePlateWellZero", "RunMacro"],
                "WorkflowType": "new",
            },
            ["E7"],
            0,
            {"Status": True},
            "AttributeError",
        ),
    ],
)
def test_scan_plate(
    mock_select,
    mock_message,
    mock_info,
    mock_wait,
    mock_show_safe,
    mock_close,
    mock_save,
    mock_load,
    prefs_path,
    pref_name,
    experiment,
    well_names,
    repetition,
    wait_after_image,
    expected,
    helpers,
):
    camera_id = "Camera1 (back)"
    (
        microscope,
        stage_id,
        focus_id,
        autofocus_id,
        obj_changer_id,
        safety_id,
    ) = helpers.microscope_for_samples_testing(helpers, prefs_path)

    plate_holder_object = helpers.create_sample_object(
        "plate_holder",
        microscope_obj=microscope,
        camera_ids=[camera_id],
        focus_id=focus_id,
        stage_id=stage_id,
        autofocus_id=autofocus_id,
        obj_changer_id=obj_changer_id,
        safety_id=safety_id,
    )
    plate_object = helpers.create_sample_object(
        "plate",
        container=plate_holder_object,
    )
    plate_holder_object.add_plates({plate_object.get_name(): plate_object})

    objects_dict = experiment.get("ObjectsDict")
    if objects_dict:
        if objects_dict.get(plate_object.get_name()):
            experiment["ObjectsDict"][plate_object.get_name()] = plate_object

    for name in well_names:
        well = helpers.setup_local_well(helpers, name=name)
        well.container = plate_object
        plate_object.add_wells({name: well})

    mic_auto = helpers.setup_local_microscope_automation(prefs_path)
    try:
        result = mic_auto.scan_plate(
            Preferences(prefs_path).get_pref_as_meta(pref_name),
            plate_holder_object,
            experiment,
            repetition=repetition,
            wait_after_image=wait_after_image,
        )
    except Exception as err:
        result = type(err).__name__

    assert result == expected


@patch(
    "microscope_automation.automation_messages_form_layout.read_string", return_value=""
)
@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    ("prefs_path, pref_name, expected"),
    [
        ("data/preferences_ZSD_2_test.yml", "ScanPlate", None),
        ("data/preferences_ZSD_2_test.yml", "RunMacro", None),
    ],
)
def test_run_macro(mock_read, prefs_path, pref_name, expected, helpers):
    (
        microscope,
        stage_id,
        focus_id,
        autofocus_id,
        obj_changer_id,
        safety_id,
    ) = helpers.microscope_for_samples_testing(helpers, prefs_path)

    plate_holder_object = helpers.create_sample_object(
        "plate_holder",
        microscope_obj=microscope,
        obj_changer_id=obj_changer_id,
    )

    mic_auto = helpers.setup_local_microscope_automation(prefs_path)
    result = mic_auto.run_macro(
        Preferences(prefs_path).get_pref_as_meta(pref_name), plate_holder_object
    )

    assert result == expected


# def test_read_first_barcode_from_plateholderobject():


@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    ("prefs_path, experiment, expected"),
    [
        (
            "data/preferences_ZSD_2_test.yml",
            {
                "Experiment": "UpdatePlateWellZero",
                "Repetitions": 1,
                "Input": None,
                "Output": {},
                "OriginalWorkflow": ["Koehler", "UpdatePlateWellZero", "RunMacro"],
                "WorkflowList": ["Koehler", "UpdatePlateWellZero", "RunMacro"],
                "WorkflowType": "new",
            },
            "KeyError",
        ),
        (
            "data/preferences_ZSD_2_test.yml",
            {
                "Experiment": "UpdatePlateWellZero",
                "Repetitions": 1,
                "Input": None,
                "Output": {},
                "OriginalWorkflow": ["Koehler", "UpdatePlateWellZero", "RunMacro"],
                "WorkflowList": ["Koehler", "UpdatePlateWellZero", "RunMacro"],
                "WorkflowType": "new",
                "ObjectsDict": {},
            },
            None,
        ),
        (
            "data/preferences_ZSD_2_test.yml",
            {
                "Experiment": "UpdatePlateWellZero",
                "Repetitions": 1,
                "Input": None,
                "Output": {},
                "OriginalWorkflow": ["Koehler", "UpdatePlateWellZero", "RunMacro"],
                "WorkflowList": ["Koehler", "UpdatePlateWellZero", "RunMacro"],
                "WorkflowType": "new",
                "ObjectsDict": {"Plate": samples.Plate()},
            },
            None,
        ),
    ],
)
def test_recover_previous_settings(prefs_path, experiment, expected, helpers):
    plate_holder_object = helpers.create_sample_object("plate_holder")
    plate_object = helpers.create_sample_object(
        "plate",
        container=plate_holder_object,
    )

    objects_dict = experiment.get("ObjectsDict")
    if objects_dict:
        if objects_dict.get(plate_object.get_name()):
            experiment["ObjectsDict"][plate_object.get_name()] = plate_object

    mic_auto = helpers.setup_local_microscope_automation(prefs_path)
    try:
        result = mic_auto.recover_previous_settings(
            plate_holder_object, plate_object, experiment
        )
    except Exception as err:
        result = type(err).__name__
    assert result == expected


@patch("matplotlib.image.imsave")
@patch(
    "microscope_automation.zeiss.connect_zen_blue.ConnectMicroscope.get_objective_name"
)
@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    ("prefs_path, pref_name, location_list, image, well_name, expected"),
    [
        (
            "data/preferences_ZSD_2_test.yml",
            "ScanPlate",
            [],
            "test_image_all_black",
            "E7",
            None,
        ),
        (
            "data/preferences_ZSD_2_test.yml",
            "ScanPlate",
            [(0, 0), (-1, 1)],
            "test_image_all_black",
            "E7",
            None,
        ),
        (
            "data/preferences_ZSD_2_test.yml",
            "ScanPlate",
            None,
            "test_image_all_black",
            "E7",
            "TypeError",
        ),
    ],
)
def test_save_segmented_image(
    mock_get_obj,
    mock_save,
    prefs_path,
    pref_name,
    location_list,
    image,
    well_name,
    expected,
    helpers,
    test_image_all_black,
    test_image_all_white,
):
    mock_get_obj.return_value = "Plan-Apochromat 10x/0.45"
    if image == "test_image_all_black":
        image = test_image_all_black
    elif image == "test_image_all_white":
        image = test_image_all_white

    (
        microscope,
        stage_id,
        focus_id,
        autofocus_id,
        obj_changer_id,
        safety_id,
    ) = helpers.microscope_for_samples_testing(helpers, prefs_path)

    plate_holder_object = helpers.create_sample_object(
        "plate_holder",
        microscope_obj=microscope,
        obj_changer_id=obj_changer_id,
    )
    plate_object = helpers.create_sample_object(
        "plate",
        container=plate_holder_object,
    )
    well_object = helpers.setup_local_well(helpers, name=well_name)

    mic_auto = helpers.setup_local_microscope_automation(prefs_path)
    try:
        result = mic_auto.save_segmented_image(
            Preferences(prefs_path).get_pref_as_meta(pref_name),
            image.data,
            location_list,
            plate_object,
            well_object,
        )
    except Exception as err:
        result = type(err).__name__

    assert result == expected


@patch(
    "microscope_automation.microscope_automation.MicroscopeAutomation.update_plate_z_zero"  # noqa
)
@patch(
    "microscope_automation.microscope_automation.MicroscopeAutomation.scan_all_objects"
)
@patch(
    "microscope_automation.automation_messages_form_layout.read_string", return_value=""
)
@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    (
        "prefs_path, pref_name, experiment, well_names, repetition, wait_after_image,"
        "expected"
    ),
    [
        (
            "data/preferences_ZSD_2_test.yml",
            "PreScanPlate",
            {
                "Experiment": "UpdatePlateWellZero",
                "Repetitions": 1,
                "Input": None,
                "Output": {},
                "OriginalWorkflow": ["Koehler", "UpdatePlateWellZero", "RunMacro"],
                "WorkflowList": ["Koehler", "UpdatePlateWellZero", "RunMacro"],
                "WorkflowType": "new",
            },
            ["E5", "E6"],
            0,
            {"Status": True, "Plate": True},
            None,
        ),
        (
            "data/preferences_ZSD_2_test.yml",
            "ScanPlate",
            {
                "Experiment": "UpdatePlateWellZero",
                "Repetitions": 1,
                "Input": None,
                "Output": {},
                "OriginalWorkflow": ["Koehler", "UpdatePlateWellZero", "RunMacro"],
                "WorkflowList": ["Koehler", "UpdatePlateWellZero", "RunMacro"],
                "WorkflowType": "continue",
                "ObjectsDict": {"Plate": samples.Plate()},
            },
            ["E5", "E6"],
            0,
            {"Status": True, "Plate": True},
            "IndexError",
        ),
        (
            "data/preferences_ZSD_test.yml",
            "ScanPlate",
            {
                "Experiment": "UpdatePlateWellZero",
                "Repetitions": 1,
                "Input": None,
                "Output": {},
                "OriginalWorkflow": ["Koehler", "UpdatePlateWellZero", "RunMacro"],
                "WorkflowList": ["Koehler", "UpdatePlateWellZero", "RunMacro"],
                "WorkflowType": "continue",
                "ObjectsDict": {"Plate": samples.Plate()},
            },
            ["E5", "E6"],
            0,
            {"Status": True, "Plate": True},
            "KeyError",
        ),
        (
            "data/preferences_ZSD_test.yml",
            "ScanPlate",
            {
                "Experiment": "UpdatePlateWellZero",
                "Repetitions": 1,
                "Input": None,
                "Output": {},
                "OriginalWorkflow": ["Koehler", "UpdatePlateWellZero", "RunMacro"],
                "WorkflowList": ["Koehler", "UpdatePlateWellZero", "RunMacro"],
                "WorkflowType": "continue",
                "ObjectsDict": {"Plate": samples.Plate()},
                "RecoverySettingsFilePath": [
                    "data\\Production\\GeneralSettings\\RecoverySettings",
                    "data/Production/GeneralSettings/RecoverySettings",
                ],
                "LastExpObjects": None,
            },
            ["E5", "E6"],
            0,
            {"Status": True, "Plate": True},
            "TypeError",
        ),
        (
            "data/preferences_ZSD_test.yml",
            "ScanPlate",
            {
                "Experiment": "UpdatePlateWellZero",
                "Repetitions": 1,
                "Input": None,
                "Output": {},
                "OriginalWorkflow": ["Koehler", "UpdatePlateWellZero", "RunMacro"],
                "WorkflowList": ["Koehler", "UpdatePlateWellZero", "RunMacro"],
                "WorkflowType": "continue",
                "ObjectsDict": {"Plate": samples.Plate()},
                "RecoverySettingsFilePath": [
                    "data\\Production\\GeneralSettings\\RecoverySettings",
                    "data/Production/GeneralSettings/RecoverySettings",
                ],
                "LastExpObjects": [],
            },
            ["E5", "E6"],
            0,
            {"Status": True, "Plate": True},
            None,
        ),
        (
            "data/preferences_ZSD_test.yml",
            "ScanPlate",
            {
                "Experiment": "UpdatePlateWellZero",
                "Repetitions": 1,
                "Input": None,
                "Output": {},
                "OriginalWorkflow": ["Koehler", "UpdatePlateWellZero", "RunMacro"],
                "WorkflowList": ["Koehler", "UpdatePlateWellZero", "RunMacro"],
                "WorkflowType": "continue",
                "ObjectsDict": {"Plate": samples.Plate()},
                "RecoverySettingsFilePath": [
                    "data\\Production\\GeneralSettings\\RecoverySettings",
                    "data/Production/GeneralSettings/RecoverySettings",
                ],
                "LastExpObjects": ["Plate"],
            },
            ["E5", "E6"],
            0,
            {"Status": True, "Plate": True},
            None,
        ),
    ],
)
def test_scan_samples(
    mock_read,
    mock_scan,
    mock_update,
    prefs_path,
    pref_name,
    experiment,
    well_names,
    repetition,
    wait_after_image,
    expected,
    helpers,
):
    camera_id = "Camera1 (back)"
    (
        microscope,
        stage_id,
        focus_id,
        autofocus_id,
        obj_changer_id,
        safety_id,
    ) = helpers.microscope_for_samples_testing(helpers, prefs_path)

    plate_holder_object = helpers.create_sample_object(
        "plate_holder",
        microscope_obj=microscope,
        camera_ids=[camera_id],
        focus_id=focus_id,
        stage_id=stage_id,
        autofocus_id=autofocus_id,
        obj_changer_id=obj_changer_id,
        safety_id=safety_id,
    )
    plate_object = helpers.create_sample_object(
        "plate",
        container=plate_holder_object,
    )
    plate_holder_object.add_plates({plate_object.get_name(): plate_object})

    objects_dict = experiment.get("ObjectsDict")
    if objects_dict:
        if objects_dict.get(plate_object.get_name()):
            experiment["ObjectsDict"][plate_object.get_name()] = plate_object

    for name in well_names:
        well = helpers.setup_local_well(helpers, name=name)
        well.container = plate_object
        plate_object.add_wells({name: well})

    mic_auto = helpers.setup_local_microscope_automation(prefs_path)
    try:
        result = mic_auto.scan_samples(
            Preferences(prefs_path).get_pref_as_meta(pref_name),
            plate_holder_object,
            experiment,
            repetition=repetition,
            wait_after_image=wait_after_image,
        )
    except Exception as err:
        result = type(err).__name__

    assert result == expected


@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    ("prefs_path, pref_name, expected"),
    [
        ("data/preferences_ZSD_2_test.yml", "ScanPlate", None),
        ("data/preferences_3i_test.yml", "ScanPlate", "XMLSyntaxError"),
    ],
)
def test_validate_experiment(prefs_path, pref_name, expected, helpers):
    (
        microscope,
        stage_id,
        focus_id,
        autofocus_id,
        obj_changer_id,
        safety_id,
    ) = helpers.microscope_for_samples_testing(helpers, prefs_path)

    mic_auto = helpers.setup_local_microscope_automation(prefs_path)
    try:
        result = mic_auto.validate_experiment(
            Preferences(prefs_path).get_pref_as_meta(pref_name),
            microscope,
        )
    except Exception as err:
        result = type(err).__name__

    assert result == expected


@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    ("prefs_path, pref_name, sample_type, container_type, expected"),
    [
        (
            "data/preferences_ZSD_2_test.yml",
            "ScanPlate",
            "well",
            None,
            "AttributeError",
        ),
        (
            "data/preferences_ZSD_2_test.yml",
            "ScanPlate",
            "well",
            "plate",
            "AttributeError",
        ),
        ("data/preferences_ZSD_2_test.yml", "ScanPlate", "plate", "plate_holder", True),
        ("data/preferences_ZSD_2_test.yml", "RunMacro", "plate", "plate_holder", False),
    ],
)
def test_control_autofocus(
    prefs_path, pref_name, sample_type, container_type, expected, helpers
):
    camera_id = "Camera1 (back)"
    (
        microscope,
        stage_id,
        focus_id,
        autofocus_id,
        obj_changer_id,
        safety_id,
    ) = helpers.microscope_for_samples_testing(helpers, prefs_path)

    if container_type:
        container = helpers.create_sample_object(
            container_type,
            microscope_obj=microscope,
            camera_ids=[camera_id],
            focus_id=focus_id,
            stage_id=stage_id,
            autofocus_id=autofocus_id,
            obj_changer_id=obj_changer_id,
            safety_id=safety_id,
        )
    else:
        container = None
    sample = helpers.create_sample_object(sample_type, container=container)
    mic_auto = helpers.setup_local_microscope_automation(prefs_path)
    try:
        mic_auto.control_autofocus(
            sample,
            Preferences(prefs_path).get_pref_as_meta(pref_name),
        )
        result = sample.get_use_autofocus()
    except Exception as err:
        result = type(err).__name__

    assert result == expected


@patch("microscope_automation.automation_messages_form_layout.read_string")
@patch("microscope_automation.automation_messages_form_layout.check_box_message")
@patch("microscope_automation.automation_messages_form_layout.information_message")
@patch("microscope_automation.automation_messages_form_layout.operate_message")
@patch("microscope_automation.automation_messages_form_layout.pull_down_select_dialog")
@patch("microscope_automation.automation_messages_form_layout.file_select_dialog")
@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    ("file_name, check_box_val, barcode, prefs_path, less_dialog, expected"),
    [
        (
            None,
            [("Start new workflow", False), ("Continue last workflow", False)],
            None,
            "data/preferences_ZSD_2_test.yml",
            None,
            "UnboundLocalError",
        ),
        (
            None,
            [("Start new workflow", True), ("Continue last workflow", False)],
            None,
            "data/preferences_ZSD_2_test.yml",
            None,
            "AttributeError",
        ),
        (
            None,
            [("Start new workflow", True), ("Continue last workflow", False)],
            "1234",
            "data/preferences_ZSD_test.yml",
            False,
            None,
        ),
        (
            None,
            [("Start new workflow", True), ("Continue last workflow", False)],
            "1234",
            "data/preferences_ZSD_test.yml",
            True,
            None,
        ),
        (
            ".gitignore",
            [("Start new workflow", False), ("Continue last workflow", True)],
            "1234",
            "data/preferences_ZSD_test.yml",
            False,
            "UnpicklingError",
        ),
        (
            "test_recovery.pickle",
            [("Start new workflow", False), ("Continue last workflow", True)],
            "1234",
            "data/preferences_ZSD_test.yml",
            False,
            "AttributeError",
        ),
    ],
)
def test_microscope_automation(
    mock_file_dialog,
    mock_pull_down,
    mock_operate,
    mock_info,
    mock_check_box,
    mock_read,
    file_name,
    check_box_val,
    barcode,
    prefs_path,
    less_dialog,
    expected,
    helpers,
):
    mock_file_dialog.return_value = file_name
    mock_pull_down.return_value = "ScanCells"
    mock_check_box.return_value = check_box_val
    mock_read.return_value = barcode

    mic_auto = helpers.setup_local_microscope_automation(prefs_path)
    mic_auto.less_dialog = less_dialog
    try:
        result = mic_auto.microscope_automation()
    except Exception as err:
        result = type(err).__name__

    assert result == expected
