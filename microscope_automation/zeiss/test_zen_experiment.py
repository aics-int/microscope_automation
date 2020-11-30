"""
Test settings in ZEN experiment
Created on Aug 17, 2018

@author: winfriedw
"""


def current_z_set(settings):
    """Test if Focus Strategy for z-stack acquisition is set to CurrentZ.
    Input:
     settings: FocusSetup part of ZEN XML settings tree.

    Output:
     is_valid: True if all instances FocusZStackMode are set to CurrentZ
    """
    z_stack_modes = settings.findall(".//FocusZStackMode")
    for setting in z_stack_modes:
        if setting.text != "CurrentZ":
            return False
    return True


def test_FocusSetup(experiment_object, verbose=True):
    """Test if all focus settings are correct.

    Input:
     experiment_object: object of class hardware.Experiment

     verbose: if verbose == True print debug messages

    Output:
     is_valid: True, if focus settings are valid
    """
    is_valid = True
    if not experiment_object.validate_experiment():
        is_valid = False
        if verbose:
            print(
                (
                    "test_FocusSetup: Experiment {} does not exist".format(
                        experiment_object.experiment_path
                    )
                )
            )

    focus_settings = experiment_object.get_focus_settings()
    # test if at least one setup exists
    if not focus_settings:
        is_valid = False
        if verbose:
            print(
                (
                    "test_FocusSetup: Experiment {} has no FocusSetup".format(
                        experiment_object.experiment_path
                    )
                )
            )

    # Test only activated setups
    for settings in focus_settings:
        if not current_z_set(settings):
            is_valid = False
            if verbose:
                print(
                    (
                        "test_FocusSetup: In experiment {} Focus Strategy of at least one z-stack is not set to CurrentZ".format(  # noqa
                            experiment_object.experiment_path
                        )
                    )
                )

    return is_valid
