"""
Test connect_slidebook and it's connections to command and data servers
Created on Jan 27, 2020

@author: winfriedw
"""
import pytest
import requests
import numpy as np
import skimage

# Import the resource/controllers we're testing
from microscope_automation.util.automation_exceptions import (
    HardwareCommandNotDefinedError,
)
from microscope_automation.util.image_AICS import ImageAICS
from microscope_automation.slidebook.connect_slidebook import ConnectMicroscope


# Set to True if you want to skip all tests, e.g. when developing a new function
skip_all_functions = True


@pytest.fixture
def connection_object(
    cmd_url="http://127.0.0.1:5000",
    data_url="http://127.0.0.1:5100",
    microscopes="3iW1-0",
):
    """Return connection object to servers and test if connection was established"""
    connection = ConnectMicroscope(cmd_url, data_url, microscopes)
    return connection


@pytest.fixture
def image():
    """Image for testing"""
    caller = getattr(skimage.data, "camera")
    image = caller()
    return image


@pytest.fixture
def meta_data():
    """Meta data for image"""
    meta_data = {
        "data_id": 123,
        "microscope": "3iW1-0",
        "stage_location": [100, 100, 100],
        "xy_pixel_size": 0.1,
        "z_spacing": 1.0,
        "x_stage_direction": 1,
        "y_stage_direction": 1,
        "z_stage_direction": 1,
        "is_montage": False,
        "time_stamp": "2019-10-19:12:24;12",
    }
    return meta_data


@pytest.fixture
def experiment():
    """Standard experiment"""
    experiment = {
        "experiment_id": "",
        "microscope": "3iW1-0",
        "number_positions": 1,
        "stage_locations": [(0, 0, 0)],
        "stage_locations_filter": [True],
        "capture_settings": ["No_experiment"],
        "centers_of_interest": [(0, 0, 0)],
        "objective": "Apo_10x",
        "time_stamp": "",
        "microscope_action": "snap",
        "status": "none",
    }
    return experiment


# Test connection to command and data servers
@pytest.mark.skipif(skip_all_functions, reason="Testing disabled")
def test_init(connection_object):
    """Get information from servers"""
    assert connection_object.cmd_server_info["name"] == "Command_API"
    #     assert connection_object.cmd_server_info['IP'] == '127.0.0.1'
    assert connection_object.cmd_server_info["port"] == 5000
    assert connection_object.data_server_info["name"] == "Data_API"
    #     assert connection_object.data_server_info['IP'] == '127.0.0.1'
    assert connection_object.data_server_info["port"] == 5100


# Methods to get information about command and data services and manipulate queues
@pytest.mark.skipif(skip_all_functions, reason="Testing disabled")
def test_get_about_command_service(connection_object):
    """Retrieve information about data service"""
    about = connection_object.get_about_command_service()
    assert about["name"] == "Command_API"
    #     assert about['IP'] == '127.0.0.1'
    assert about["port"] == 5000


@pytest.mark.skipif(skip_all_functions, reason="Testing disabled")
def test_get_about_data_service(connection_object):
    """Retrieve information about data service"""
    about = connection_object.get_about_data_service()
    assert about["name"] == "Data_API"
    #     assert about['IP'] == '127.0.0.1'
    assert about["port"] == 5100


# Saving and loading images from data service
@pytest.mark.skipif(skip_all_functions, reason="Testing disabled")
def test_save_image(connection_object):
    """Save image through microscope software not supported for Slidebook"""
    with pytest.raises(HardwareCommandNotDefinedError):
        assert connection_object.save_image(fileName="")


@pytest.mark.skipif(skip_all_functions, reason="Testing disabled")
@pytest.mark.parametrize("get_meta_data", [True, False])
@pytest.mark.parametrize("provide_imageAICS", [True, False])
def test_load_image(
    connection_object, image, meta_data, get_meta_data, provide_imageAICS
):
    """Return image from data service"""
    # Load image to data service
    bytestream = image.tobytes()
    # send meta data and return data_id
    meta_data["image_dimensions"] = image.shape
    meta_data["format"] = str(image.dtype)
    response = requests.post(connection_object.data_url + "/meta_data", json=meta_data)
    assert response.status_code == 200
    data_id = response.json()["data_id"]

    # send image to data_id
    response = requests.post(
        connection_object.data_url + "/binary/" + data_id, data=bytestream
    )
    assert response.status_code == 200

    # load image into Automation Software
    if provide_imageAICS:
        aics_image = ImageAICS(meta={"aics_experiment": experiment})
    else:
        aics_image = None
    return_image = connection_object.load_image(
        image=aics_image, get_meta_data=get_meta_data
    )
    assert np.array_equal(return_image.data, image)


# Methods to manipulate data queue
@pytest.mark.skipif(skip_all_functions, reason="Testing disabled")
def test_experiment_queue(connection_object, experiment):
    """Get manipulations of experiment in queue"""
    # clear experiment queue
    _ = connection_object.clear_experiments()

    # Now there should be no more experiments in queue
    response = connection_object.count_experiments()
    assert response == 0

    response = connection_object.get_experiment_dict()
    assert response == {}

    # Add 5 experiments
    for i in range(4):
        response = connection_object.post_experiment(experiment)
        response = connection_object.count_experiments()
        assert response == i + 1

    # Retrieve experiments and remove from queue
    for i in range(4):
        next_experiment = connection_object.get_next_experiment()
        experiment_by_id = connection_object.get_experiment(
            next_experiment["experiment_id"]
        )
        assert next_experiment == experiment_by_id
        remaining_experiments_1 = connection_object.delete_experiment(
            next_experiment["experiment_id"]
        )
        remaining_experiments_2 = connection_object.delete_experiment(
            next_experiment["experiment_id"]
        )
        assert remaining_experiments_1 == remaining_experiments_2
        response = connection_object.count_experiments()
        assert response == max(0, 3 - i)
        experiment_by_id = connection_object.get_experiment(
            next_experiment["experiment_id"]
        )
        assert experiment_by_id == {}


# Acquire images
@pytest.mark.skipif(skip_all_functions, reason="Testing disabled")
def test_snap_image(connection_object):
    """Acquire image without moving stage"""
    success = connection_object.snap_image(capture_settings="test_communication")
    assert success


@pytest.mark.skipif(skip_all_functions, reason="Testing disabled")
def test_execute_experiment(connection_object):
    """Acuqire image without moving stage"""
    success = connection_object.execute_experiment(
        capture_settings="test_communication",
        locations=[(100, 100, 100), (200, 200, 200)],
    )
    assert success


@pytest.mark.skipif(skip_all_functions, reason="Testing disabled")
def test_live_mode_start(connection_object):
    """Start live mode not supported for Slidebook"""
    with pytest.raises(HardwareCommandNotDefinedError):
        assert connection_object.live_mode_start("")


@pytest.mark.skipif(skip_all_functions, reason="Testing disabled")
def test_live_mode_stop(connection_object):
    """Start live mode not supported for Slidebook"""
    with pytest.raises(HardwareCommandNotDefinedError):
        assert connection_object.live_mode_stop("")
