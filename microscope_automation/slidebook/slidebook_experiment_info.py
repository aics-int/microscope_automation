# module to extract and update information from the slidebook software experiment files
try:
    from pathlib import Path
except ImportError:
    from pathlib2 import Path

import logging


log = logging.getLogger(__name__)


class SlidebookExperiment(object):
    def __init__(self, experiment_path, experiment_name):
        """
        Initializing the experiment class

        Input:
         experiment_name: Name of the experiment as defined in the Zen software
         & preference file

         prefs: the preference file for the workflow

        Output:
         none
        """
        self.experiment_path = experiment_path
        self.experiment_name = experiment_name

    def experiment_exists(self):
        """Function to check if the experiment name provided in the preference
        file exists in the Slidebook software

        Input:
         none

        Output:
         a boolean indicating if the experiment exists or not
        """
        # log.debug("Experiment path: {}".format(self.experiment_path))
        experiment_exists = Path(self.experiment_path).exists()
        return experiment_exists
