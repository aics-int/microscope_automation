import pytest
import pathlib
import os
os.chdir(os.path.dirname(__file__))

from microscope_automation.zeiss.zen_experiment_info import ZenExperiment


experiment_name = 'WellTile_10x.czexp'


@pytest.fixture()
def experiment_path():
    exp = 'data/Experiment Setup/' + experiment_name
    return str(exp)


@pytest.fixture()
def exp_class(experiment_path):
    return ZenExperiment(experiment_path, experiment_name)


def test_class_init(experiment_path):
    ZenExperiment(experiment_path, experiment_name)


def test_experiment_exists(experiment_path):
    zen_experiment = ZenExperiment(experiment_path, experiment_name)
    assert zen_experiment.experiment_exists()


def test_experiment_exists_fail(experiment_path):
    with pytest.raises(AssertionError):
        p = pathlib.Path(experiment_path).parent / 'NotExistingExperiment.czexp'
        zen_experiment = ZenExperiment(str(p), experiment_name)
        assert zen_experiment.experiment_exists()


def test_get_tag_value_default(exp_class):
    assert '5000,7800' == exp_class.get_tag_value(exp_class.TAG_PATH_TILE_CENTER_XY)
    assert '4' == exp_class.get_tag_value(exp_class.TAG_PATH_TILE_CENTER_Z)


def test_get_tag_value_invalid(exp_class):
    with pytest.raises(ValueError):
        exp_class.get_tag_value(exp_class.TAG_PATH_TILE_CENTER_XY + '/badpath')
