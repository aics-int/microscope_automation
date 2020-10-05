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

        return samples.ImagingSystem(container=container, name=name, image=image,
                                     microscope_object=microscope_object,
                                     stage_id=stage_id,
                                     focus_id=focus_id,
                                     auto_focus_id=auto_focus_id,
                                     objective_changer_id=objective_changer_id,
                                     safety_id=safety_id)


@pytest.fixture
def helpers():
    return Helpers
