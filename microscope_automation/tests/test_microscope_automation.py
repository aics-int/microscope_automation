"""
Test microscope automation's main module, which orchestrates workflows.
Created on December 1, 2020

@author: fletcher.chapin
"""

import pytest
import os
from mock import patch
from collections import Mapping
from microscope_automation.image_AICS import ImageAICS
from microscope_automation.preferences import Preferences
from microscope_automation.samples import samples
from microscope_automation import microscope_automation

os.chdir(os.path.dirname(__file__))

# set skip_all_tests = True to focus on single test
skip_all_tests = False


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
        result = microscope_automation.stop_script(
            message_text=text, allow_continue=allow_continue
        )
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
def test_get_well_object(prefs_path, plate_holder_name, plate_name,
                         well, helpers):
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


@patch(
    "microscope_automation.samples.samples.PlateHolder.execute_experiment"
)
@patch("microscope_automation.automation_messages_form_layout.operate_message")
@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    ("prefs_path, pref_name, plate_holder_name, plate_name, "
     "well_name, barcode_name, expected"),
    [
        ("data/preferences_ZSD_2_test.yml", "ImageBarcode", "Plateholder",
         "96-well", "A1", "1234", "Not implemented"),
        ("data/preferences_ZSD_2_test.yml", "ImageBarcode", "Plateholder",
         "96-well", None, None, "AttributeError"),
    ],
)
def test_read_barcode(mock_message, mock_execute, prefs_path, pref_name,
                      plate_holder_name, plate_name, well_name, barcode_name,
                      expected, helpers):
    mic_auto = helpers.setup_local_microscope_automation(prefs_path)
    well_object = helpers.setup_local_well(helpers, name=well_name,
                                           plate_name=plate_name)
    plate_holder_object = helpers.setup_local_plate_holder(
        helpers,
        name=plate_holder_name,
        prefs_path=prefs_path
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
            barcode_name
        )
    except Exception as err:
        result = type(err).__name__

    assert result == expected


@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    ("prefs_path, pref_name, plate_holder_name, plate_name, "
     "well_names, well_diameter, expected"),
    [
        ("data/preferences_ZSD_2_test.yml", "CalibrateWellDiameter", "Plateholder",
         "96-well", ["B2", "B11", "G11"], None, "TypeError"),
        ("data/preferences_ZSD_2_test.yml", "CalibrateWellDiameter", "Plateholder",
         "96-well", ["B2", "B11", "G11"], 6134, None),
        ("data/preferences_ZSD_2_test.yml", "ImageBarcode", "Plateholder",
         "96-well", [], None, "AttributeError"),
    ],
)
def test_calculate_all_wells_correction(prefs_path, pref_name,
                                        plate_holder_name, plate_name, well_names,
                                        well_diameter, expected, helpers):
    mic_auto = helpers.setup_local_microscope_automation(prefs_path)
    plate_object = helpers.setup_local_plate(helpers, name=plate_name)
    plate_holder_object = helpers.setup_local_plate_holder(
        helpers,
        name=plate_holder_name,
        prefs_path=prefs_path
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
            None
        )
    except Exception as err:
        result = type(err).__name__

    assert result == expected


@patch(
    "microscope_automation.samples.samples.PlateHolder.execute_experiment"
)
@patch("microscope_automation.hardware.hardware_components.Safety.show_safe_areas")
@patch("microscope_automation.automation_messages_form_layout.operate_message")
@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    ("prefs_path, pref_name, plate_holder_name, immersion_name, expected"),
    [
        (None, "SetupImmersionSystem", "Plateholder",
         "ImmersionDelivery", "AssertionError"),
        ("data/preferences_ZSD_2_test.yml", "SetupImmersionSystem", "Plateholder",
         "ImmersionDelivery", None),
    ],
)
def test_setup_immersion_system(mock_execute, mock_show_safe, mock_message,
                                prefs_path, pref_name, plate_holder_name,
                                immersion_name, expected, helpers):
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
        helpers,
        name=immersion_name
    )
    plate_holder.immersion_delivery_system.container = plate_holder

    try:
        mic_auto = helpers.setup_local_microscope_automation(prefs_path)
        prefs = Preferences(prefs_path).get_pref_as_meta(pref_name)
        result = mic_auto.setup_immersion_system(
            prefs,
            plate_holder,
        )

        assert (prefs.get_pref("MaginificationImmersionSystem")
                == plate_holder.immersion_delivery_system.magnification)
    except Exception as err:
        result = type(err).__name__

    assert result == expected


@patch(
    "microscope_automation.zeiss.connect_zen_blue.ConnectMicroscope.get_all_objectives"
)
@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    ("prefs_path, plate_holder_name, expected"),
    [
        ("data/preferences_ZSD_2_test.yml", "Plateholder", None),
    ],
)
def test_set_up_objectives_and_offset(mock_get_obj, prefs_path,
                                      plate_holder_name, expected, helpers):
    mock_get_obj.return_value = {'10': {'Position': 6,
                                        'Name': 'Plan-Apochromat 10x/0.45'}}
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
        ("data/preferences_ZSD_2_test.yml", "Koehler", "Plateholder", "E7",
         "Camera1 (back)", None),
    ],
)
def test_set_up_koehler(mock_message, prefs_path, pref_name, plate_holder_name,
                        well_name, camera_id, expected, helpers):
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
    well_object = helpers.create_sample_object(
        "well",
        container=plate_object
    )
    plate_object.add_wells({well_name: well_object})

    mic_auto = helpers.setup_local_microscope_automation(prefs_path)
    result = mic_auto.set_up_koehler(
        Preferences(prefs_path).get_pref_as_meta(pref_name),
        plate_object
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
def test_initialize_microscope(mock_message, mock_koehler, mock_file_dialog,
                               prefs_path, pref_name, expected, helpers):
    mock_file_dialog.return_value = 'data/PlateSpecifications/PipelineData_Celigo.csv'
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
        ("data/preferences_ZSD_2_test.yml", "UpdatePlateWellZero",
         {'Experiment': 'UpdatePlateWellZero', 'Repetitions': 1,
          'Input': None, 'Output': {}}, "Well", "AttributeError"),
        ("data/preferences_ZSD_2_test.yml", "UpdatePlateWellZero",
         {'Experiment': 'UpdatePlateWellZero', 'Repetitions': 1,
          'Input': None, 'Output': {}, 'OriginalWorkflow':
          [{'Experiment': 'Koehler', 'Repetitions': 1, 'Input': None, 'Output': {}},
           {'Experiment': 'UpdatePlateWellZero', 'Repetitions': 1,
            'Input': None, 'Output': {}},
           {'Experiment': 'RunMacro', 'Repetitions': 1, 'Input': None,
            'Output': {}},
           ], 'WorkflowList': ['Koehler', 'UpdatePlateWellZero', 'RunMacro']
          }, "E7", None),
    ],
)
def test_update_plate_z_zero(mock_message, prefs_path, pref_name, experiment,
                             well_name, expected, helpers):
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
        ("data/preferences_ZSD_2_test.yml", "CalibrateWellDistance", "96-well",
         ["B2", "B11", "G11"], [(0, 0, 0), (6134, 0, 0), (12268, 0, 0)],
         "ZeroDivisionError"),
        ("data/preferences_ZSD_2_test.yml", "CalibrateWellDistance", "96-well",
         ["B2", "B11", "G11"], [(0, 0, 0), (6134, 6134, 0), (12268, 12268, 0)],
         None),
    ],
)
def test_calculate_plate_correction(mock_reference, mock_message, mock_close, mock_save,
                                    mock_load, mock_find_center, prefs_path, pref_name,
                                    plate_name, well_names, well_centers, expected,
                                    helpers):
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
        ("data/preferences_ZSD_2_test.yml", "ScanWellsZero", ["B3"],
         "AttributeError"),
        ("data/preferences_ZSD_2_test.yml", "ScanWellsZero",
         ["B3", "C3", "D3", "B4", "C4", "D4"], None),
    ],
)
def test_scan_wells_zero(mock_message, mock_close, mock_save, mock_show_safe,
                         prefs_path, pref_name, well_names, expected, helpers):
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
        # well.set_measured_diameter(well_diameter)
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
    ("prefs_path, pref_name, experiment, sample_type, reference_type, "
     "image_path, meta_dict, repetition, expected"),
    [
        ("data/preferences_ZSD_2_test.yml", "PreScanPlate",
         {'Experiment': 'UpdatePlateWellZero', 'Repetitions': 1,
          'Input': None, 'Output': {}, 'OriginalWorkflow':
          [{'Experiment': 'Koehler', 'Repetitions': 1, 'Input': None, 'Output': {}},
           {'Experiment': 'UpdatePlateWellZero', 'Repetitions': 1,
            'Input': None, 'Output': {}},
           {'Experiment': 'RunMacro', 'Repetitions': 1, 'Input': None,
            'Output': {}},
           ], 'WorkflowList': ['Koehler', 'UpdatePlateWellZero', 'RunMacro']
          }, "plate", "well", None, None, 0,
         {'Image': [ImageAICS()], 'Continue': True}),
        ("data/preferences_ZSD_2_test.yml", "PreScanPlate",
         {'Experiment': 'UpdatePlateWellZero', 'Repetitions': 1,
          'Input': None, 'Output': {}, 'OriginalWorkflow':
          [{'Experiment': 'Koehler', 'Repetitions': 1, 'Input': None, 'Output': {}},
           {'Experiment': 'UpdatePlateWellZero', 'Repetitions': 1,
            'Input': None, 'Output': {}},
           {'Experiment': 'RunMacro', 'Repetitions': 1, 'Input': None,
            'Output': {}},
           ], 'WorkflowList': ['Koehler', 'UpdatePlateWellZero', 'RunMacro']
          }, "plate", "well", None, None, 1,
         {'Image': [ImageAICS()], 'Continue': True}),
        ("data/preferences_ZSD_2_test.yml", "ScanPlate",
         {'Experiment': 'UpdatePlateWellZero', 'Repetitions': 1,
          'Input': None, 'Output': {}, 'OriginalWorkflow':
          [{'Experiment': 'Koehler', 'Repetitions': 1, 'Input': None, 'Output': {}},
           {'Experiment': 'UpdatePlateWellZero', 'Repetitions': 1,
            'Input': None, 'Output': {}},
           {'Experiment': 'RunMacro', 'Repetitions': 1, 'Input': None,
            'Output': {}},
           ], 'WorkflowList': ['Koehler', 'UpdatePlateWellZero', 'RunMacro']
          }, "plate", None, None, None, 1, "HardwareError"),
    ],
)
def test_scan_single_ROI(mock_select, mock_message, mock_show_safe, mock_close,
                         prefs_path, pref_name, experiment, sample_type,
                         reference_type, image_path, meta_dict, repetition,
                         expected, helpers):
    if isinstance(expected, Mapping):
        mock_select.return_value = {'Continue': expected['Continue'], 'Include': True}
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
        assert result['Continue'] == expected['Continue']
        assert result['Image'].__class__ == expected['Image'].__class__
    except Exception as err:
        result = type(err).__name__
        assert result == expected
