import os
import pytest
from mock import patch
import microscope_automation.zeiss.write_zen_tiles_experiment as write_zen

os.chdir(os.path.dirname(__file__))


def test_init():
    testclass = write_zen.PositionWriter(
        zsd="testZsd", plate=1234, production_path="data"
    )
    # Check Type conversion
    assert isinstance(testclass.plate, str)
    # Check data fed into next step
    assert testclass.path == "data" + os.path.sep + "1234" + os.path.sep + "testZsd"
    assert testclass.zsd == "testZsd"


@pytest.mark.parametrize(
    "sample_coords, header",
    [
        (
            [
                ["Name", "X", "Y", "Z"],
                ["name0", 0.1, 0.1, 0.1],
                ["name1", 100.0, 100.0, 100.0],
                ["name2", 200.5, 200.5, 200.5],
            ],
            True,
        ),
        (
            [
                ["name0", 0.1, 0.1, 0.1],
                ["name1", 100.0, 100.0, 100.0],
                ["name2", 200.5, 200.5, 200.5],
            ],
            False,
        ),
    ],
)
def test_convert_to_stage_coords(sample_coords, header):
    testclass = write_zen.PositionWriter(
        zsd="testZsd", plate=1234, production_path="data"
    )
    converted_list = testclass.convert_to_stage_coords(
        offset_x=1.0, offset_y=1.0, positions_list=sample_coords, header=header
    )

    # list returns correct size
    if header:
        assert len(converted_list) == len(sample_coords) - 1
    else:
        assert len(converted_list) == len(converted_list)

    # see if conversion (offset addition) is working okay using floats.
    assert converted_list[0] == {
        "name": "name0",
        "actual_x": 1.1,
        "actual_y": 1.1,
        "actual_z": 0.1,
    }
    assert converted_list[1] == {
        "name": "name1",
        "actual_x": 101.0,
        "actual_y": 101.0,
        "actual_z": 100.0,
    }
    assert converted_list[2] == {
        "name": "name2",
        "actual_x": 201.5,
        "actual_y": 201.5,
        "actual_z": 200.5,
    }

    # addition of offset still results in a float value
    assert isinstance(converted_list[0]["actual_x"], float)
    assert isinstance(converted_list[1]["actual_y"], float)
    assert isinstance(converted_list[2]["actual_z"], float)


@patch(
    "microscope_automation.automation_messages_form_layout.read_string",
    return_value="invalid.czsh",
)
@pytest.mark.parametrize(
    "converted_list, dummy, expected",
    [
        (
            [
                ["Name", "X", "Y", "Z"],
                ["name0", 0.1, 0.1, 0.1],
                ["name1", 100.0, 100.0, 100.0],
                ["name2", 200.5, 200.5, 200.5],
            ],
            os.path.join("data", "1234", "testZsd", "positions_output_a.czsh"),
            "ParseError",
        ),
        (
            [
                ["Name", "X", "Y", "Z"],
                ["name0", 0.1, 0.1, 0.1],
                ["name1", 100.0, 100.0, 100.0],
                ["name2", 200.5, 200.5, 200.5],
            ],
            "invalid.czsh",
            "FileNotFoundError",
        ),
        (
            [
                {
                    "name": "name0",
                    "actual_x": 1.1,
                    "actual_y": 1.1,
                    "actual_z": 0.1,
                },
                {
                    "name": "name1",
                    "actual_x": 101.0,
                    "actual_y": 101.0,
                    "actual_z": 100.0,
                },
                {
                    "name": "name2",
                    "actual_x": 201.5,
                    "actual_y": 201.5,
                    "actual_z": 200.5,
                },
            ],
            os.path.join("data", "1234", "testZsd", "dummy_tile_positions.czsh"),
            None,
        ),
    ],
)
def test_write(mock_read, converted_list, dummy, expected):
    testclass = write_zen.PositionWriter(
        zsd="testZsd", plate=1234, production_path="data"
    )
    # was convert_to_stage_coords called?
    assert len(converted_list) != 0

    try:
        result = testclass.write(converted_list, dummy=dummy)
    except Exception as err:
        result = type(err).__name__

    assert result == expected


@pytest.mark.parametrize(
    "test_file_names, expected",
    [
        (["positions_output_a"], "b"),
        (["positions_output_aa"], "ab"),
        (["positions_output_a", "positions_output_c", "positions_output_z"], "aa"),
        ([], "a"),
    ],
)
def test_get_next_pos_name(test_file_names, expected):
    testclass = write_zen.PositionWriter(
        zsd="testZsd", plate=1234, production_path="data"
    )
    assert (
        testclass.get_next_pos_name(test_mode=True, test_file_names=test_file_names)
        == expected
    )
