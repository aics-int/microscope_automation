'''
Created on Jun 7, 2016
Part of microscopeAutomation
Will read and return values for different configuration files

@author: winfriedw
'''
import yaml
import logging

# create logger
module_logger = logging.getLogger('microscopeAutomation')


class Preferences:
    '''Reads configuration files and will return Values'''
    def __init__(self, prefPath=None, prefDict=None, parentPrefs=None):
        ''''Creates preferences object from .yml preferences file or dictionary.
        Choose prefPath or prefDict.

        Input:
         prefPath: path to .yml file (Default = None).

         prefDict: dictionary with preferences (Default = None)

         parentPrefs: Preferences object that was source for prefDict.
         This will allow access to global preferences, even working with local subset.

        Output:
         Object of class preferences
        '''
        # setup logging
        self.logger = logging.getLogger('microscopeAutomation.MetaData.preferences')

        # check for valid input
        # We should add checking for valid filename etc.
        # Check that either one field is None or the other is None, not both (xor)
        assert (prefPath is None) ^ (prefDict is None), \
            'One and only one preference option must be specified'

        if prefPath is not None:
            self.logger.info('read preferences from ' + prefPath)

            with open(prefPath, 'r') as prefsFile:
                self.prefs = yaml.load(prefsFile, Loader=yaml.FullLoader)
                print(('\nRead preferences from {}\n'.format(prefPath)))
                prefs_info = self.prefs['Info']
                for key, value in prefs_info.items():
                    print(('{}:\t{}'.format(key, value)))

        if prefDict is not None:
            self.logger.info('read preferences from dictionary')
            self.prefs = prefDict

        self.logger.info('add parent preferences set')
        self.parentPrefs = parentPrefs

    def printPrefs(self):
        print((self.prefs))

    def getParentPrefs(self):
        '''preferences objects that are created from a subset of preferences,
        keep a reference to the original preferences set.

        Input:
         none

        Output:
         parentPrefs: Object of class preferences of preferences that where
         source for current subset of preferences.
        '''
        return self.parentPrefs

    def getPref(self, name, validValues=None):
        '''Return value for key 'name' in preferences.

        Input:
         name: string with key name

         validValues: list with allowed values. Throw exception if value is not valid.
         Default: do not check.

        Output:
         pref: value for key 'name' in preferences
        '''
#         from .automation_messages_form_layout import pull_down_select_dialog
        from .automation_messages_form_layout import pull_down_select_dialog

        pref = self.prefs.get(name)
        if pref is None and self.parentPrefs is not None:
            parentPref = self.parentPrefs.getPref(name)
            if parentPref is not None:
                return parentPref
            print(('Key ', name, ' is not defined and there are no parent preferences'))

        if validValues is not None:
            if isinstance(pref, list):
                while not (set(pref) < set(validValues)):
                    pref = [pull_down_select_dialog(validValues, "Please select valid value for preference key {},\ninstead of {}\nor exit program by pressing 'Cancel'.".format(name, pref))]  # noqa
            else:
                while pref not in validValues:
                    pref = pull_down_select_dialog(validValues, "Please select valid value for preference key {},\ninstead of {}\nor exit program by pressing 'Cancel'.".format(name, pref))  # noqa
        return pref

    def getPrefAsMeta(self, name):
        '''Return subset of preferences as preferences object.

        Input:
         name: name of meta data dictionary

        Output:
         prefsObject: preferences dictionary as preferences object
        '''
        # To return dictionaries as object will help later
        # if we want to implement some pre-processing and error checking of meta data.
        if self.getPref(name):
            return Preferences(prefDict=self.getPref(name), parentPrefs=self)
        else:
            return None

    def setPref(self, name, value):
        self.prefs[name] = value

    # TODO: Add capacity to save preferences


if __name__ == '__main__':
    prefPath = '../GeneralSettings/preferences.yml'
    meta = Preferences(prefPath)
    print((meta.getPref('PathMicroscopeSpecs')))
    print((meta.getPref('ExperimentsScanBackground')))

    metaObject = meta.getPrefAsMeta('ScanColonies')
    print((metaObject.getPref('Execute')))
    print((metaObject.getParentPrefs()))
    print((metaObject.getPref('PathDailyFolder')))
    print((metaObject.getPref('Tile', validValues=['None', 'Fixed', 'Size'])))
    print((metaObject.getPref('Tile', validValues=['ThrowError'])))
    print('Done')
