import pytest
import microscope_automation.writeZENTilesExperiment as writeZEN

testclass = writeZEN.save_position_list(zsd="testZsd", plate=1234, production_path="test_data")


def test_init():
    # Check Type conversion
    assert isinstance(testclass.plate, str)
    # Check data fed into next step
    assert testclass.path == "test_data\\1234\\testZsd"
    assert testclass.zsd == "testZsd"
    # Removed below assert statement since attribute no longer exists
    # assert isinstance(testclass.pos_list, list)


sample_coords_from_automation = [["name0", 0.1, 0.1, 0.1],
                                 ["name1", 100.0, 100.0, 100.0],
                                 ["name2", 200.5, 200.5, 200.5]]
converted_list = testclass.convert_to_stage_coords(offset_x=1.0, offset_y=1.0, positions_list=sample_coords_from_automation)


def test_convert_to_stage_coords():
    # list returns correct size
    assert len(converted_list) == len(sample_coords_from_automation)

    # see if conversion (offset addition) is working okay using floats. Automation software passes floats
    assert converted_list[0] == {"name": "name0", "actual_x": 1.1, "actual_y": 1.1, "actual_z": 0.1}
    assert converted_list[1] == {"name": "name1", "actual_x": 101.0, "actual_y": 101.0, "actual_z": 100.0}
    assert converted_list[2] == {"name": "name2", "actual_x": 201.5, "actual_y": 201.5, "actual_z": 200.5}

    # addition of offset still results in a float value
    assert isinstance(converted_list[0]["actual_x"], float)
    assert isinstance(converted_list[1]["actual_y"], float)
    assert isinstance(converted_list[2]["actual_z"], float)


def test_write():
    # was convert_to_stage_coords called?
    assert len(converted_list) != 0

    # Test by reading tree again and checking values.
