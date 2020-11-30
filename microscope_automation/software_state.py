"""File to keep track of the state of the software.
@author: winfriedw
"""
import pickle
import sys
import samples
from collections import OrderedDict

REFERENCE_OBJECT = 'reference_object'
NEXT_EXP_OBJECTS = 'next_objects_dict'
LAST_EXP_OBJECTS = 'last_exp_objects_list'
HARDWARE_STATUS = 'hardware_status_dict'


# When pickling fails, this method prints out objects it pickled
# It helps pinpoint what exactly could not be pickled.
class DiagnosticPickler (pickle.Pickler):
    def save(self, obj):
        print ('pickling object' + obj + 'of type' + type(obj))
        pickle.Pickler.save(self, obj)


class State(object):

    def __init__(self, recovery_file_path=None):
        """
        Function to initialize the object
        :param: recovery_file_path =  full file path+name of the recovery file for the experiment
        """
        self.workflow_pos = []
        self.reference_object = None
        # List of wells/cells names that have already been imaged, to be able to continue right where we left off
        self.last_experiment_objects = []
        self.next_experiment_objects = OrderedDict()  # {Function Name: list of objects acquired for the next experiment}
        self.hardware_status_dict = {}     # If the objectives were already initialized
        self.recovery_file_path = recovery_file_path

        # Kruft
        self.zen_instance = None
        self.ref_image = None

    def save_state_and_exit(self):
        """
        Function to process the objects and save them by pickling and exiting the software.
        :param
        :return:
        """
        self.save_state()
        sys.exit(0)

    def save_state(self):
        """
        Function to process the objects and save them by pickling.
        :param
        :return:
        """
        pickle_dict = {}
        self.prune_object_dict()
        pickle_dict[NEXT_EXP_OBJECTS] = self.next_experiment_objects
        pickle_dict[REFERENCE_OBJECT] = self.reference_object
        # No need to prune last experiment objects because it's just a list of names (string)
        pickle_dict[LAST_EXP_OBJECTS] = self.last_experiment_objects
        pickle_dict[HARDWARE_STATUS] = self.hardware_status_dict
        # Generate the file name for the particular interrupt
        try:
            with open(self.recovery_file_path, 'wb') as f:
                pickle.dump(pickle_dict, f, pickle.HIGHEST_PROTOCOL)
                print("State was saved in the recovery file")
                f.close()
        except:
            print("State was NOT saved.")

        # Need to rehydrate the removed references
        self.rehydrate_removed_references()

    def rehydrate_removed_references(self):
        """
        In case of auto save, we need the Zen object to be added back (it was removed before pickling)
        :return:
        """
        for object in self.next_experiment_objects.values():
            for item in object:
                self.add_unpickled_objects(item)

        if self.reference_object and self.reference_object.container is not None:
            self.add_unpickled_objects(self.reference_object)

    def add_unpickled_objects(self, base_object):
        """
        Function to add Zen object back
        :param base_object: The reference object or next experiment object to rehydrate
        :return:
        """
        current_object = base_object
        if current_object.microscope is not None:
            current_object.microscope.get_control_software().connection.Zen = self.zen_instance
        while current_object.container is not None:
            if isinstance(current_object.container, samples.PlateHolder):
                current_object.container.microscope.get_control_software().connection.Zen = self.zen_instance
                current_object.container.microscope.get_control_software().connection.image = self.ref_image
            current_object = current_object.container

    def prune_object_dict(self):
        """
        Function to strip away the Zen microscope object from each level of the sample object tree.
        Reason - there are some objects in microscope class (communication object) that can't be pickled.
        :param object_dict: The dictionary that needs to be filtered.
        :return: object_dict: The filtered dictionary.
        """

        for object in self.next_experiment_objects.values():
            for item in object:
                self.eliminate_unpickled_objects(item)

        if self.reference_object and self.reference_object.container is not None:
            self.eliminate_unpickled_objects(self.reference_object)

    def eliminate_unpickled_objects(self, base_object):
        """
        base_object: Object that needs to be pruned
        :return:
        """
        current_object = base_object
        if current_object.microscope is not None:
            self.zen_instance = current_object.microscope.get_control_software().connection.Zen
            current_object.microscope.get_control_software().connection.Zen = None
        while current_object.container is not None:
            if isinstance(current_object.container, samples.PlateHolder):
                if self.zen_instance is None:
                    self.zen_instance = current_object.container.microscope.get_control_software().connection.Zen
                current_object.container.microscope.get_control_software().connection.Zen = None
                self.ref_image = current_object.container.microscope.get_control_software().connection.image
                current_object.container.microscope.get_control_software().connection.image = None
            current_object = current_object.container


    def add_next_experiment_object(self, experiment_name, exp_object_list):
        """
        Add objects to the list for next experiment objects.
        :param exp_object_list:
        :return:
        """
        self.next_experiment_objects.update({experiment_name: exp_object_list})

    def recover_objects(self, file_path):
        """
        Function to return next objects dictionary and the reference object by unpickling the file
        :param filepath: path to the pickled file
        :return: (object_dict, reference_object)
        """
        with open(file_path, 'rb') as handle:
            pickle_dict = pickle.load(handle)
            self.last_experiment_objects = []
            self.next_experiment_objects = OrderedDict()
        # Restore the state
        self.next_experiment_objects = pickle_dict[NEXT_EXP_OBJECTS]
        self.reference_object = pickle_dict[REFERENCE_OBJECT]
        self.last_experiment_objects = pickle_dict[LAST_EXP_OBJECTS]
        self.hardware_status_dict = pickle_dict[HARDWARE_STATUS]
        return (self.next_experiment_objects, self.reference_object, self.last_experiment_objects,
                self.hardware_status_dict)

    def add_last_experiment_object(self, exp_object_name):
        """
        Add objects to the list for last experiment objects to keep track of which cells have already been imaged
        To be able to pick up exactly where we left off
        :param exp_object_list:
        :return:
        """
        self.last_experiment_objects.append(exp_object_name)
