import os
import microscope_automation.zeiss.write_zen_tiles_experiment as write_zen

os.chdir(os.path.dirname(__file__))
testclass = write_zen.PositionWriter(zsd="testZsd", plate=1234, production_path="data")


def test_init():
    # Check Type conversion
    assert isinstance(testclass.plate, str)
    # Check data fed into next step
    assert testclass.path == "data" + os.path.sep + "1234" + os.path.sep + "testZsd"
    assert testclass.zsd == "testZsd"


sample_coords_no_header = [
    ["name0", 0.1, 0.1, 0.1],
    ["name1", 100.0, 100.0, 100.0],
    ["name2", 200.5, 200.5, 200.5],
]
converted_list_no_header = testclass.convert_to_stage_coords(
    offset_x=1.0, offset_y=1.0, positions_list=sample_coords_no_header, header=False
)

sample_coords_with_header = [
    ["Name", "X", "Y", "Z"],
    ["name0", 0.1, 0.1, 0.1],
    ["name1", 100.0, 100.0, 100.0],
    ["name2", 200.5, 200.5, 200.5],
]
converted_list_header = testclass.convert_to_stage_coords(
    offset_x=1.0, offset_y=1.0, positions_list=sample_coords_with_header, header=True
)


def test_convert_to_stage_coords():
    # list returns correct size
    assert len(converted_list_no_header) == len(sample_coords_no_header)
    assert len(converted_list_header)

    # see if conversion (offset addition) is working okay using floats.
    # Automation software passes floats
    assert converted_list_no_header[0] == {
        "name": "name0",
        "actual_x": 1.1,
        "actual_y": 1.1,
        "actual_z": 0.1,
    }
    assert converted_list_no_header[1] == {
        "name": "name1",
        "actual_x": 101.0,
        "actual_y": 101.0,
        "actual_z": 100.0,
    }
    assert converted_list_no_header[2] == {
        "name": "name2",
        "actual_x": 201.5,
        "actual_y": 201.5,
        "actual_z": 200.5,
    }

    # addition of offset still results in a float value
    assert isinstance(converted_list_no_header[0]["actual_x"], float)
    assert isinstance(converted_list_no_header[1]["actual_y"], float)
    assert isinstance(converted_list_no_header[2]["actual_z"], float)


def test_write():
    # was convert_to_stage_coords called?
    assert len(converted_list_header) != 0

    # Test by attempting to write with empty dummy file, so error is expected.
    try:
        testclass.write(
            converted_list_header,
            dummy=os.path.join("data", "1234", "testZsd", "positions_output_a.czsh"),
        )
    except Exception as err:
        assert type(err).__name__ == "ParseError"

    testclass2 = write_zen.PositionWriter(zsd="testZsd", plate=1234, production_path="data")
    testclass2.write(
        converted_list_header,
        dummy=os.path.join("data", "1234", "testZsd", "dummy_tile_positions.czsh"),
    )


def test_get_next_pos_name():
    testclass = write_zen.PositionWriter(
        zsd="testZsd", plate=1234, production_path="data"
    )
    assert (
        testclass.get_next_pos_name(
            test_mode=True, test_file_names=["positions_output_a"]
        )
        == "b"
    )

    testclass = write_zen.PositionWriter(
        zsd="testZsd", plate=1234, production_path="data"
    )
    assert (
        testclass.get_next_pos_name(
            test_mode=True, test_file_names=["positions_output_aa"]
        )
        == "ab"
    )

    testclass = write_zen.PositionWriter(
        zsd="testZsd", plate=1234, production_path="data"
    )
    assert (
        testclass.get_next_pos_name(
            test_mode=True,
            test_file_names=[
                "positions_output_a",
                "positions_output_c",
                "positions_output_z",
            ],
        )
        == "aa"
    )

    testclass = write_zen.PositionWriter(
        zsd="testZsd", plate=1234, production_path="data"
    )
    assert (testclass.get_next_pos_name(test_mode=True, test_file_names=[]) == "a")

    # assert testclass.get_next_pos_name(test_mode=False) == "b"
