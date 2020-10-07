import pytest
import pathlib
import os
from microscope_automation.slidebook.slidebook_experiment_info import (
    SlidebookExperiment,
)  # noqa

experiment_name = "test_communication.exp.prefs"


@pytest.fixture()
def experiment_path():
    exp = os.path.join(
        os.path.dirname(os.path.realpath(__file__)), "data", experiment_name
    )
    return str(exp)


@pytest.fixture()
def exp_class(experiment_path):
    return SlidebookExperiment(experiment_path, experiment_name)


def test_class_init(experiment_path):
    SlidebookExperiment(experiment_path, experiment_name)


def test_experiment_exists(experiment_path):
    slidebook_experiment = SlidebookExperiment(experiment_path, experiment_name)
    assert slidebook_experiment.experiment_exists()


def test_experiment_exists_fail(experiment_path):
    with pytest.raises(AssertionError):
        p = pathlib.Path(experiment_path).parent / "NotExistingExperiment.czexp"
        slidebook_experiment = SlidebookExperiment(str(p), experiment_name)
        assert slidebook_experiment.experiment_exists()
