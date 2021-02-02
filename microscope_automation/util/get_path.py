"""
Collection of functions to return path for settings, logfile, and data
Created on Aug 8, 2016

@author: winfriedw
"""
# import Python modules
import datetime
import time
from datetime import date
import os
from pathlib import Path


def add_suffix(file_path, suffix):
    """Add suffix to end of file name.

    Input:
     file_path: path to file name

     suffix: suffix to put between end of filename and file extension

    Output:
     new_file_path: file_path with suffix
    """
    split_path = os.path.splitext(file_path)
    new_file_path = split_path[0] + "_" + suffix + split_path[1]
    return new_file_path


def get_valid_path_from_prefs(prefs, key, search_dir=True, validate=False):
    """Read list of paths from prefs and return first valid match.

    Input:
     prefs: Preferences object created from YAML file

     key: key for pathlist in preferences.yml

     search_dir: if True search for directory, otherwise for file

    Output:
     return_path: path to valid file or directory
    """
    path_list = prefs.get_pref(key)
    # To catch non-list inputs
    if type(path_list) is not list:
        if type(path_list) is str:
            path_list = [path_list]
        else:
            raise ValueError("No valid path found in preferences for key: " + key)

    return_path = ""
    for path in path_list:
        # For Zen Black implementation, there is no experiment path, hence left as "NA"
        if path == "NA":
            return path
        if os.path.exists(path):
            if search_dir:
                if os.path.isdir(path):
                    return_path = path
                    break
            else:
                if os.path.isfile(path):
                    return_path = path
                    break
    if validate:
        assert return_path is not None and len(return_path), (
            "No valid path found in preferences for key: " + key
        )
    return return_path


def set_up_subfolders(parent_folder_path, subfolder):
    """Set the Subfolders for imaging folder - e.g. TapeOnly and Failed QC

    Input:
     parent_folder_path: Image Folder Path

     subfolder: folder to create, can be list of multiple folders

    Output:
     subfolders: list of full path of subfolders created
    """
    if not isinstance(subfolder, list):
        subfolder = [subfolder]

    subfolders = []
    for folder in subfolder:
        sub_folder_path = os.path.normpath(os.path.join(parent_folder_path, folder))
        # test if folder exists, if not, create folder
        if not os.path.isdir(sub_folder_path):
            os.makedirs(sub_folder_path)

        subfolders.append(sub_folder_path)
    return subfolders


def get_daily_folder(prefs, barcode=None):
    """Find folder for daily settings and results. Create folder if not existing.

    Input:
     prefs: Preferences object created from YAML file

     barcode: Use the plate barcode to make the folder

    Output:
     daily_path: path to daily folder. No '/' at end.
    """
    # Add the microscope name level in the folder structure to
    # make it more aligned with pipeline & FMS standard
    try:
        microscope_name = prefs.get_pref("Info")["System"]
    except KeyError:
        microscope_name = "000"
    if barcode is None:
        # get today's date and construct folder name
        today = date.today()
        folder_name = str(today.year) + "_" + str(today.month) + "_" + str(today.day)
    else:
        folder_name = str(barcode)

    # find path to daily folder. Should reside in settings file.
    # read list with possible paths for daily folder from preferences.yml
    daily_folder = get_valid_path_from_prefs(prefs, "PathDailyFolder")
    daily_path = os.path.normpath(
        os.path.join(daily_folder, folder_name, microscope_name)
    )

    # test if folder exists, if not, create folder
    if not os.path.isdir(daily_path):
        os.makedirs(daily_path)
    return daily_path


def get_position_csv_path(prefs, barcode=None):
    """Function to get the file path for the csv files where
    all the positions are stored after segmentation.

    Input:
     prefs: preferences

     barcode: Use the plate barcode to make the folder

    Output:
     paths: file paths for the files
    """
    daily_folder_path = get_daily_folder(prefs, barcode)
    # 1. To store the list of positions in the format specific
    # to Zen Blue software for 100X imaging.
    filename_pos = Path(prefs.get_pref("PositionCsv"))
    filename_wellid = Path(filename_pos.stem + "_wellid.csv")
    filename_failed = Path("failed_wells.csv")
    position_csv_path = daily_folder_path / filename_pos
    failed_csv_path = daily_folder_path / filename_failed
    # 2. To store positions and respective well IDs
    # for post processing (splitting and aligning)
    position_wellid_csv_path = daily_folder_path / filename_wellid
    return position_csv_path, position_wellid_csv_path, failed_csv_path


def get_log_file_path(prefs):
    """Return path to log file.

    Input:
     prefs: Preferences object created from YAML file

    Output:
     log_file_path: path to log file
    """
    # get today's date and construct folder name
    today = date.today()
    file_name = str(today.year) + "_" + str(today.month) + "_" + str(today.day) + ".log"
    log_file_folder = get_valid_path_from_prefs(prefs, "LogFilePath", search_dir=True)
    log_file_path = os.path.normpath(os.path.join(log_file_folder, file_name))

    # test if folder exists, if not, create folder
    if not os.path.isdir(log_file_folder):
        os.makedirs(log_file_folder)
    return log_file_path


def get_meta_data_path(prefs, barcode=None):
    """Return path for meta data.

    Input:
     prefs: Preferences object created from YAML file

     barcode: Use the plate barcode to make the folder

    Output:
     meta_data_file: path to log file
    """
    daily_folder_path = get_daily_folder(prefs, barcode)
    meta_data_file = os.path.normpath(
        os.path.join(daily_folder_path, prefs.get_pref("MetaDataPath"))
    )
    folder_path = os.path.dirname(meta_data_file)
    # test if folder exists, if not, create folder
    if not os.path.isdir(folder_path):
        os.makedirs(folder_path)
    return meta_data_file


def get_experiment_path(prefs, dir=False):
    """Return path to experiment.

    Input:
     prefs: Preferences object created from YAML file

     dir: if true return path to experiments directory, otherwise to experiment file.
     Default: False

    Output:
     experiment_path: path to experiment
    """
    experiment_dir_path = get_valid_path_from_prefs(
        prefs, "PathExperiments", search_dir=True, validate=False
    )
    # For Zen Black implementation, there is no experiment path, hence left as "NA"
    if experiment_dir_path == "NA":
        return experiment_dir_path
    if dir:
        experiment_path = os.path.normpath(experiment_dir_path)
    else:
        experiment_name = prefs.get_pref("Experiment")
        experiment_path = os.path.normpath(
            os.path.join(experiment_dir_path, experiment_name)
        )

    return experiment_path


def get_recovery_settings_path(prefs):
    """Returns the file path to save the pickled dictionary after interruption

    Input:
     prefs: Preferences object created from YAML file

    Output:
     file_path: path to recovery settings
    """
    time_stamp = time.time()
    formatted_time_stamp = datetime.datetime.fromtimestamp(time_stamp).strftime(
        "%Y-%m-%d_%H-%M-%S"
    )
    filename = "Plate_" + formatted_time_stamp + ".pickle"
    file_dir = get_valid_path_from_prefs(
        prefs, "RecoverySettingsFilePath", search_dir=True
    )
    file_path = os.path.normpath(os.path.join(file_dir, filename))
    return file_path


def get_colony_dir_path(prefs, barcode=None):
    """Return path to directory with .csv file with colony positions and features.

    Input:
     prefs: Preferences object created from YAML file

     barcode: Use the plate barcode to make the folder

    Output:
     colonyDir: path to log file
    """
    daily_folder_path = get_daily_folder(prefs, barcode)

    colony_dir_path = prefs.get_pref("ColonyDirPath")
    if colony_dir_path is None:
        colony_dir_path = ""

    folder_path = os.path.normpath(os.path.join(daily_folder_path, colony_dir_path))
    # test if folder exists, if not, create folder
    if not os.path.isdir(folder_path):
        os.makedirs(folder_path)

    return folder_path


def get_colony_remote_dir_path(prefs):
    """Return path to directory with .csv file with colony positions
    and features on network.

    Input:
     prefs: Preferences object created from YAML file

    Output:
     colony_dir_path: path to log file
    """
    colony_dir_path = get_valid_path_from_prefs(
        prefs, "ColonyFileFolder", search_dir=True
    )
    if colony_dir_path is None:
        colony_dir_path = ""
    # return os.path.normpath(os.path.join (get_daily_folder(prefs), colony_dir_path))
    return colony_dir_path


def get_colony_file_path(prefs, colony_file, barcode=None):
    """Return path to file with colony information typically produced by
    CellProfiler based on Celigo platescanner data.

    Input:
     prefs: Preferences object created from YAML file

     colony_file: path to .csv file with colony data

     barcode: Use the plate barcode to make the folder

    Output:
     colony_file_path: complete path to colony file
    """
    dir_path = get_colony_dir_path(prefs, barcode=barcode)
    colony_file_path = os.path.normpath(os.path.join(dir_path, colony_file))

    return colony_file_path


def get_hardware_settings_path(prefs):
    """Return path to .yml file with microscope specifications from preferences file.

    Input:
     prefs: Preferences object created from YAML file

    Output:
     hardwarePath: path to layout file
    """
    return get_valid_path_from_prefs(
        prefs, "PathMicroscopeSpecs", search_dir=False, validate=True
    )


def get_references_path(prefs, barcode=None):
    """Return path to directory for reference images. Create directory if not available

    Input:
     prefs: Preferences object created from YAML file

     barcode: Use the plate barcode to make the folder

    Output:
     references_path: path to directory for reference images for specific well
    """
    daily_folder_path = get_daily_folder(prefs, barcode)
    references_path = os.path.normpath(
        os.path.join(daily_folder_path, prefs.get_pref("ReferenceDirPath"))
    )
    # create directory if not existent
    if not os.path.isdir(references_path):
        os.makedirs(references_path)
    return references_path


def get_images_path(prefs, sub_dir=None, barcode=None):
    """Return path to directory for images. Create directory if not available

    Input:
     prefs: Preferences object created from YAML file

     sub_dir: Sub-directory for images. Will create folder with this name

     barcode: Use the plate barcode to make the folder

    Output:
     references_path: path to directory for reference images for specific well
    """
    daily_folder_path = get_daily_folder(prefs, barcode)
    if sub_dir:
        references_path = os.path.join(daily_folder_path, sub_dir)
    else:
        references_path = daily_folder_path

    # create directory if not existent
    if not os.path.isdir(references_path):
        os.makedirs(references_path)
    return references_path


def get_calibration_path(prefs):
    """Return path to calibration information e.g. blackreference images

    Input:
     prefs: Preferences object created from YAML file

    Output:
     calibration_path: path to calibration directory
    """
    calibration_path = get_valid_path_from_prefs(
        prefs, key="PathCalibration", search_dir=True
    )
    return calibration_path


def get_well_edge_path(prefs, barcode=None):
    """Return path to folder where well edge images are saved.
    Used to determine the well's center.

    Input:
     prefs: Preferences object created from YAML file

    Output:
     well_edge_path: path to calibration directory
    """
    daily_folder_path = get_daily_folder(prefs, barcode)
    relative_path = prefs.get_pref("WellEdgeDirPath")
    well_edge_path = os.path.join(daily_folder_path, relative_path)
    return well_edge_path
