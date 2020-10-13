#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Configuration for tests! There are a whole list of hooks you can define in this file to
run before, after, or to mutate how tests run. Commonly for most of our work, we use
this file to define top level fixtures that may be needed for tests throughout multiple
test files.

In this case, while we aren't using this fixture in our tests, the prime use case for
something like this would be when we want to preload a file to be used in multiple
tests. File reading can take time, so instead of re-reading the file for each test,
read the file once then use the loaded content.

Docs: https://docs.pytest.org/en/latest/example/simple.html
      https://docs.pytest.org/en/latest/plugins.html#requiring-loading-plugins-in-a-test-module-or-conftest-file
"""

import pytest
import microscope_automation.hardware.setup_microscope as setup_microscope
import microscope_automation.preferences as preferences
import microscope_automation.hardware.hardware_components as h_comp
import microscope_automation.samples.samples as samples


class Helpers:
    @staticmethod
    def setup_local_microscope(prefs_path):
        """Create microscope object"""
        prefs = preferences.Preferences(prefs_path)
        microscope_object = setup_microscope.setup_microscope(prefs)
        return microscope_object

    def setup_local_experiment(self, name, path, prefs_path):
        """Create Experiment object"""
        microscope_object = self.setup_local_microscope(prefs_path)
        experiment = h_comp.Experiment(path, name, microscope_object)
        return experiment

    @staticmethod
    def setup_local_control_software(software):
        """Create ControlSoftware object"""
        control_software = h_comp.ControlSoftware(software)
        return control_software

    @staticmethod
    def setup_local_safety(safety_id):
        """Create Safety object"""
        safety = h_comp.Safety(safety_id)
        return safety

    @staticmethod
    def setup_local_camera(
        camera_id,
        pixel_size=(None, None),
        pixel_number=(None, None),
        pixel_type=None,
        name=None,
        detector_type="generic",
        manufacturer=None,
        model=None,
    ):
        """Create Camera object"""
        camera = h_comp.Camera(
            camera_id,
            pixel_size,
            pixel_number,
            pixel_type,
            name,
            detector_type,
            manufacturer,
            model,
        )
        return camera

    def setup_local_stage(
        self,
        stage_id,
        safe_area=None,
        safe_position=None,
        objective_changer=None,
        prefs_path=None,
        default_experiment=None,
    ):
        """Create Stage object"""
        if prefs_path:
            microscope_object = self.setup_local_microscope(prefs_path)
        else:
            microscope_object = None

        stage = h_comp.Stage(
            stage_id,
            safe_area,
            safe_position,
            objective_changer,
            microscope_object,
            default_experiment,
        )
        return stage

    def setup_local_autofocus(
        self,
        auto_focus_id,
        default_camera=None,
        obj_changer=None,
        default_reference_position=[[50000, 37000, 6900]],
        prefs_path=None,
    ):
        """Create AutoFocus object"""
        if prefs_path:
            microscope_object = self.setup_local_microscope(prefs_path)
        else:
            microscope_object = None

        autofocus = h_comp.AutoFocus(
            auto_focus_id,
            default_camera,
            obj_changer,
            default_reference_position,
            microscope_object,
        )

        return autofocus

    def setup_local_focus_drive(
        self,
        focus_drive_id,
        max_load_position=0,
        min_work_position=10,
        auto_focus_id=None,
        objective_changer=None,
        prefs_path=None,
    ):
        """Create FocusDrive object"""
        if prefs_path:
            microscope_object = self.setup_local_microscope(prefs_path)
        else:
            microscope_object = None

        focus_drive = h_comp.FocusDrive(
            focus_drive_id,
            max_load_position,
            min_work_position,
            auto_focus_id,
            objective_changer,
            microscope_object,
        )

        return focus_drive

    def setup_local_obj_changer(
        self,
        obj_changer_id,
        n_positions=None,
        objectives=None,
        ref_objective=None,
        prefs_path=None,
        auto_focus_id=None,
    ):
        """Create ObjectiveChanger object"""
        if prefs_path:
            microscope_object = self.setup_local_microscope(prefs_path)
        else:
            microscope_object = None

        obj_changer = h_comp.ObjectiveChanger(
            obj_changer_id, n_positions, objectives, ref_objective, microscope_object
        )

        if microscope_object:
            obj_changer.microscope_object.add_microscope_object(obj_changer)

            if auto_focus_id:
                autofocus = self.setup_local_autofocus(self, auto_focus_id)
                obj_changer.microscope_object.add_microscope_object(autofocus)

        return obj_changer

    @staticmethod
    def setup_local_pump(pump_id, seconds=1, port="COM1", baudrate=19200):
        """Create Pump object"""
        return h_comp.Pump(pump_id, seconds, port, baudrate)

    def setup_local_imaging_system(
        self,
        container=None,
        name="",
        image=True,
        reference_object=None,
        x_ref=None,
        y_ref=None,
        z_ref=None,
        x_safe_position=None,
        y_safe_position=None,
        z_safe_position=None,
        prefs_path=None,
        stage_id=None,
        focus_id=None,
        auto_focus_id=None,
        objective_changer_id=None,
        safety_id=None,
    ):
        """Create ImagingSystem object"""
        if prefs_path:
            microscope_object = self.setup_local_microscope(prefs_path)
        else:
            microscope_object = None

        # TODO: add in other objects like focus drive and safety here

        return samples.ImagingSystem(
            container=container,
            name=name,
            image=image,
            reference_object=reference_object,
            x_ref=x_ref,
            y_ref=y_ref,
            z_ref=z_ref,
            x_safe_position=x_safe_position,
            y_safe_position=y_safe_position,
            z_safe_position=z_safe_position,
            microscope_object=microscope_object,
            stage_id=stage_id,
            focus_id=focus_id,
            auto_focus_id=auto_focus_id,
            objective_changer_id=objective_changer_id,
            safety_id=safety_id,
        )

    def setup_local_well(
        self,
        name="Well",
        center=[0, 0, 0],
        diameter=1,
        plate_name=None,
        well_position_numeric=(1, 1),
        well_position_string=("A", "1"),
        x_flip=1,
        y_flip=1,
        z_flip=1,
    ):
        """Create Well object"""
        if plate_name:
            plate_object = self.setup_local_plate(self)
        else:
            plate_object = None

        return samples.Well(
            name=name,
            center=center,
            diameter=diameter,
            plate_object=plate_object,
            well_position_numeric=well_position_numeric,
            well_position_string=well_position_string,
            x_flip=x_flip,
            y_flip=y_flip,
            z_flip=z_flip,
        )

    def setup_local_plate(
        self,
        name="Plate",
        center=[0, 0, 0],
        plate_holder_name=None,
        x_flip=1,
        y_flip=1,
        z_flip=1,
    ):
        """Create Plate object"""
        if plate_holder_name:
            plate_holder_object = self.setup_local_plate_holder(self)
        else:
            plate_holder_object = None

        return samples.Plate(
            name=name,
            center=center,
            plate_holder_object=plate_holder_object,
            x_flip=x_flip,
            y_flip=y_flip,
            z_flip=z_flip,
        )

    def setup_local_plate_holder(
        self,
        name="PlateHolder",
        prefs_path=None,
        stage_id=None,
        focus_id=None,
        objective_changer_id=None,
        safety_id=None,
        center=[0, 0, 0],
        x_flip=1,
        y_flip=1,
        z_flip=1,
    ):
        """Create PlateHolder object"""
        if prefs_path:
            microscope_object = self.setup_local_microscope(prefs_path)
        else:
            microscope_object = None

        return samples.PlateHolder(
            name=name,
            center=center,
            microscope_object=microscope_object,
            stage_id=stage_id,
            focus_id=focus_id,
            objective_changer_id=objective_changer_id,
            safety_id=safety_id,
            x_flip=x_flip,
            y_flip=y_flip,
            z_flip=z_flip,
        )

    @staticmethod
    def create_sample_object(sample_type, container=None,
                             microscope_obj=None, stage_id=None, focus_id=None,
                             autofocus_id=None, obj_changer_id=None,
                             safety_id=None, ref_obj=None):
        """Create an object of the type passed in, e.g. PlateHolder or Well.

        This method is usually used for simple objects, whereas the other
        setup_local_<object> methods are used for full control over configuration.
        """
        if sample_type == "plate_holder":
            obj = samples.PlateHolder(microscope_object=microscope_obj,
                                      stage_id=stage_id,
                                      auto_focus_id=autofocus_id,
                                      focus_id=focus_id,
                                      objective_changer_id=obj_changer_id,
                                      safety_id=safety_id)
        elif sample_type == "plate":
            obj = samples.Plate(plate_holder_object=container)
        elif sample_type == "well":
            obj = samples.Well(plate_object=container)
        elif sample_type == "img_sys":
            obj = samples.ImagingSystem(container=container,
                                        microscope_object=microscope_obj,
                                        stage_id=stage_id,
                                        auto_focus_id=autofocus_id,
                                        focus_id=focus_id,
                                        objective_changer_id=obj_changer_id,
                                        safety_id=safety_id,
                                        reference_object=ref_obj,)
        elif sample_type is None:
            obj = None

        return obj

    def microscope_for_samples_testing(
        self,
        prefs_path="data/preferences_ZSD_test.yml"
    ):
        stage_id = "Marzhauser"
        focus_id = "MotorizedFocus"
        max_load_position = 500
        min_work_position = 100
        autofocus_id = "DefiniteFocus2"
        obj_changer_id = "6xMotorizedNosepiece"
        safe_verts = [(-1, -1), (108400, -1), (108400, 71200), (-1, 71200)]
        z_max = 9900
        safe_area_id = "StageArea"
        objectives = {
            "Plan-Apochromat 10x/0.45": {
                "x_offset": -19,
                "y_offset": 15,
                "z_offset": 10,
                "magnification": 10,
                "immersion": "air",
                "experiment": "WellTile_10x_true",
                "camera": "Camera1 (back)",
                "autofocus": "DefiniteFocus2",
            }
        }
        safety_id = "ZSD_01_plate"
        control_software = self.setup_local_control_software("ZEN Blue Dummy")
        stage = self.setup_local_stage(self, stage_id,
                                       safe_area=safe_area_id,
                                       objective_changer=obj_changer_id,
                                       prefs_path=prefs_path,)
        autofocus = self.setup_local_autofocus(self, autofocus_id)
        focus_drive = self.setup_local_focus_drive(
            self,
            focus_id,
            max_load_position=max_load_position,
            min_work_position=min_work_position,
            prefs_path=prefs_path,
            objective_changer=obj_changer_id,
        )
        focus_drive.z_load = 500
        focus_drive.initialize(
            control_software.connection,
            action_list=["set_load"],
            verbose=False,
            test=True,
        )
        obj_changer = self.setup_local_obj_changer(self, obj_changer_id,
                                                   objectives=objectives,
                                                   prefs_path=prefs_path)
        safety = self.setup_local_safety(safety_id)
        safety.add_safe_area(safe_verts, safe_area_id, z_max)

        microscope = self.setup_local_microscope(prefs_path)
        microscope.add_control_software(control_software)
        microscope.add_microscope_object([stage, autofocus, focus_drive,
                                          obj_changer, safety])

        return microscope, stage_id, focus_id, autofocus_id, obj_changer_id, safety_id


@pytest.fixture
def helpers():
    return Helpers
