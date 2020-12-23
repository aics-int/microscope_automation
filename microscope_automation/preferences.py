"""
Created on Jun 7, 2016
Part of microscope_automation
Will read and return values for different configuration files

@author: winfriedw
"""
import yaml
import logging

# create logger
module_logger = logging.getLogger("microscope_automation")


class Preferences:
    """Reads configuration files and will return Values"""

    def __init__(self, pref_path=None, pref_dict=None, parent_prefs=None):
        """Creates preferences object from .yml preferences file or dictionary.
        Choose pref_path or pref_dict.

        Input:
         pref_path: path to .yml file (Default = None).

         pref_dict: dictionary with preferences (Default = None)

         parent_prefs: Preferences object that was source for pref_dict.
         This will allow access to global preferences, even working with local subset.

        Output:
         Object of class preferences
        """
        # setup logging
        self.logger = logging.getLogger("microscope_automation.preferences.Preferences")

        # check for valid input
        # We should add checking for valid filename etc.
        # Check that either one field is None or the other is None, not both (xor)
        assert (pref_path is None) ^ (
            pref_dict is None
        ), "One and only one preference option must be specified"

        if pref_path is not None:
            self.logger.info("read preferences from " + pref_path)

            with open(pref_path, "r") as prefsFile:
                self.prefs = yaml.load(prefsFile, Loader=yaml.FullLoader)
                print("\nRead preferences from {}\n".format(pref_path))
                prefs_info = self.prefs["Info"]
                for key, value in prefs_info.items():
                    print("{}:\t{}".format(key, value))

        if pref_dict is not None:
            self.logger.info("read preferences from dictionary")
            self.prefs = pref_dict

        self.logger.info("add parent preferences set")
        self.parent_prefs = parent_prefs

    def print_prefs(self):
        print(self.prefs)

    def get_parent_prefs(self):
        """preferences objects that are created from a subset of preferences,
        keep a reference to the original preferences set.

        Input:
         none

        Output:
         parent_prefs: Object of class preferences of preferences that
         were source for current subset of preferences.
        """
        return self.parent_prefs

    def get_pref(self, name, valid_values=None):
        """Return value for key 'name' in preferences.

        Input:
         name: string with key name

         valid_values: list with allowed values. Throw exception if value is not valid.
         Default: do not check.

        Output:
         pref: value for key 'name' in preferences
        """
        from .automation_messages_form_layout import pull_down_select_dialog

        if not isinstance(self.prefs, type(dict())):
            print("\n")
            print(self.prefs)
        pref = self.prefs.get(name)
        if pref is None and self.parent_prefs is not None:
            parentPref = self.parent_prefs.get_pref(name)
            if parentPref is not None:
                return parentPref
            print("Key ", name, " is not defined and there are no parent preferences")

        if valid_values is not None:
            if isinstance(pref, list):
                while not (set(pref) < set(valid_values)):
                    pref = [
                        pull_down_select_dialog(
                            valid_values,
                            "Please select valid value for preference key {},\ninstead of {}\nor exit program by pressing 'Cancel'.".format(  # noqa
                                name, pref
                            ),
                        )
                    ]
            else:
                while pref not in valid_values:
                    pref = pull_down_select_dialog(
                        valid_values,
                        "Please select valid value for preference key {},\ninstead of {}\nor exit program by pressing 'Cancel'.".format(  # noqa
                            name, pref
                        ),
                    )
        return pref

    def get_pref_as_meta(self, name):
        """Return subset of preferences as preferences object.

        Input:
         name: name of meta data dictionary

        Output:
         prefsObject: preferences dictionary as preferences object
        """
        # To return dictionaries as object will help later
        # if we want to implement some pre-processing and error checking of meta data.
        if self.get_pref(name):
            return Preferences(pref_dict=self.get_pref(name), parent_prefs=self)
        else:
            return None

    def set_pref(self, name, value):
        self.prefs[name] = value

    # TODO: Add capacity to save preferences
