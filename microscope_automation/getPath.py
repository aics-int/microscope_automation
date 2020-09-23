'''
Collection of functions to return path for settings, logfile, and data
Created on Aug 8, 2016

@author: winfriedw
'''
# import Python modules
import datetime
import time
from datetime import date
import os
from pathlib import Path
# import modules that are part of package MicroscopeAutomation
# module to read preference files
# from .preferences import Preferences
from preferences import Preferences

pref_path = None

def set_pref_file(prefs):
    """
    Set the preferences file location for the application during runtime
    TODO: This should be an object
    :param prefs: file location
    :return:
    """
    global pref_path
    pref_path = prefs


def get_valid_path_from_prefs(prefs, key, searchDir=True, validate=False):
    '''Read list of paths from prefs and return first valid match.
    
    Input:
     prefs:  Dictionary with preferences 
     key: key for pathlist in preferences.yml
     searchDir: if True search for directory, otherwise for file
     
    Output:
     returnPath: path to valid file or directory
    '''
    pathList = prefs.getPref(key)
    # To catch non-list inputs
    if type(pathList) is not list:
        if type(pathList) is str:
            pathList = [pathList]
        else:
            raise ValueError("No valid path found in preferences for key: " + key)

    returnPath = ''
    for path in pathList:
        # For Zen Black implementation, there is no experiment path, hence it is left as "NA"
        if path == 'NA':
            return path
        if os.path.exists(path):
            if searchDir:
                if os.path.isdir(path):
                    returnPath = path
                    break
            else:
                if os.path.isfile(path):
                    returnPath = path
                    break
    if validate:
        assert returnPath is not None, "No valid path found in preferences for key: " + key
    return returnPath


def set_up_subfolders(parent_folder_path, subfolder):
    """
    Set the Subfolders for imaging folder - eg. TapeOnly and Failed QC
    :param parent_folder_path: Image Folder Path
    :param subfolder: folder to create, can be list of multiple folders
    :return: sub_folder_path: full path of subfolder
    """
    if not isinstance(subfolder, list):
        subfolder = list(subfolder)
    
    for folder in subfolder:
        sub_folder_path = os.path.normpath(os.path.join(parent_folder_path, folder))
        # test if folder exists, if not, create folder
        if not os.path.isdir(sub_folder_path):
            os.makedirs(sub_folder_path)
    return sub_folder_path

    
def get_daily_folder(prefs, barcode=None):
    '''Find folder for daily settings and results. Create folder if not existing.
    
    Input:
     prefs: Dictionary with preferences 
     barcode: Use the plate barcode to make the folder
    Output:
     folderPath: path to daily folder. No '/' at end.
    '''
    # Add the microscope name level in the folder structure ot make it more aligned with pipeline & FMS standard
    try:
        microscope_name = prefs.getPref('Info')['System']
    except:
        microscope_name = "000"
    if barcode is None:
        # get today's date and construct folder name
        today=date.today()
        folderName=str(today.year) +'_'+str(today.month)+'_'+str(today.day)
    else:
        folderName = str(barcode)

    # find path to daily folder. Should reside in settings file.
    # read list with possible paths for daily folder from preferences.yml
    dailyFolder = get_valid_path_from_prefs(prefs, 'PathDailyFolder')
    dailyPath=os.path.normpath(os.path.join(dailyFolder, folderName, microscope_name))

    # test if folder exists, if not, create folder
    if not os.path.isdir(dailyPath):
        os.makedirs(dailyPath)
    global daily_folder_path
    daily_folder_path= dailyPath
    return dailyPath


def get_position_csv_path(prefs):
    """
    Function to get the file path for the csv files where all the positions are stored after segmentation
    :param prefs: preferences
    :return: filepaths for the files
    """
    # 1. To store the list of positions in the format specific to Zen Blue software for 100X imaging.
    filename_pos = Path(prefs.getPref('PositionCsv'))
    filename_wellid = Path(filename_pos.stem + '_wellid.csv')
    filename_failed = Path('failed_wells.csv')
    position_csv_path = daily_folder_path / filename_pos
    failed_csv_path = daily_folder_path / filename_failed
    # 2. To store positions and respective well IDs for post processing (splitting and aligning)
    position_wellid_csv_path = daily_folder_path / filename_wellid
    return position_csv_path, position_wellid_csv_path, failed_csv_path

def get_log_file_path(prefs):
    '''Return path to log file.
    
    Input:
     prefs: Dictionary with preferences 
     
    Output:
     logFile: path to log file
    '''

    # get today's date and construct folder name
    today=date.today()
    file_name = str(today.year)+'_'+str(today.month)+'_'+str(today.day)+'.log'
    if prefs.getPref('LogFilePath') is None:
        raise ValueError("No valid path found in preferences for key: LogFilePath")
    logFilePath = os.path.normpath(os.path.join(prefs.getPref('LogFilePath'), file_name))
    folderPath = os.path.dirname(logFilePath)
    # test if folder exists, if not, create folder
    if not os.path.isdir(folderPath):
        os.makedirs(folderPath)
    return logFilePath


def get_meta_data_path(prefs):
    '''Return path for meta data.
    
    Input:
     prefs: Dictionary with preferences 
     
    Output:
     metaDataFile: path to log file
    '''        
    metaDataFile = os.path.normpath(os.path.join(daily_folder_path, prefs.getPref('MetaDataPath')))
    folderPath = os.path.dirname(metaDataFile)
    # test if folder exists, if not, create folder
    if not os.path.isdir(folderPath):
        os.makedirs(folderPath)
    return metaDataFile

def get_experiment_path(prefs, dir = False):
    '''Return path to experiment.
    
    Input:
     prefs: Dictionary with preferences 
     dir: if true return path to experiments directory, otherwise to experiment file
          default: False
     
    Output:
     experiment_path: path to experiment
    '''
    
    experiment_dir_path = get_valid_path_from_prefs(prefs, 'PathExperiments', searchDir=True, validate = False)
    # For Zen Black implementation, there is no experiment path, hence it is left as "NA"
    if experiment_dir_path =='NA':
        return experiment_dir_path
    if dir: 
        experiment_path = os.path.normpath(experiment_dir_path)
    else:
        experiment_name = prefs.getPref('Experiment')
        experiment_path = os.path.normpath(os.path.join(experiment_dir_path, experiment_name))

    return experiment_path

def get_prefs_path():
    '''Return path to preferences file.
    
    Input:
     none
     
    Output:
     prefsFile: path to preferences file
    '''

    return pref_path


def get_recovery_settings_path(file_dir):
    """
    Returns the file path to save the pickled dictionary after interruption
    :param prefs: Dictionary with preferences
    :return: file path
    """
    if file_dir is None:
        raise ValueError("No valid path found in preferences for key: RecoverySettingsFilePath")
    time_stamp = time.time()
    formatted_time_stamp = datetime.datetime.fromtimestamp(time_stamp).strftime('%Y-%m-%d_%H-%M-%S')
    filename = 'Plate_' + formatted_time_stamp + '.pickle'
    file_path = os.path.normpath(os.path.join(file_dir, filename))
    return file_path

def get_colony_dir_path(prefs):
    '''Return path to directory with .csv file with colony positions and features.
    
    Input:
     prefs: Dictionary with preferences 
     
    Output:
     colonyDir: path to log file
    '''
    ColonyDirPath = prefs.getPref('ColonyDirPath')
    if ColonyDirPath is None:
        ColonyDirPath = ''
    
    folderPath = os.path.normpath(os.path.join (daily_folder_path, ColonyDirPath))
    # test if folder exists, if not, create folder
    if not os.path.isdir(folderPath):
        os.makedirs(folderPath)

    return folderPath


def get_colony_remote_dir_path(prefs):
    '''Return path to directory with .csv file with colony positions and features on network.
    
    Input:
     prefs: Dictionary with preferences 
     
    Output:
     colonyRemoteDir: path to log file
    '''
    ColonyDirPath = get_valid_path_from_prefs(prefs, 'ColonyFileFolder', searchDir=True)
    if ColonyDirPath is None:
        ColonyDirPath = ''
#     return os.path.normpath(os.path.join (get_daily_folder(prefs), ColonyDirPath))
    return ColonyDirPath


def get_colony_file_path(prefs, colonyFile):
    '''Return path to file with colony information typically produced by CellProfiler based on Celigo platescanner data.
    
    Input:
     prefs: Dictionary with preferences 
     colonyFile: path to .csv file with colony data
     
    Output:
     colonyFilePath: complete path to colony file
    '''
    dirPath = get_colony_dir_path(prefs)
    colonyFilePath = os.path.normpath(os.path.join(dirPath, colonyFile))
    
    return colonyFilePath
    

def get_hardware_settings_path(prefs):
    '''Return path to .yml file with microscope specifications from preferences file.
    
    Input:
     prefs: Dictionary with preferences 
     
    Output:
     hardwarePath: path to layout file
    '''
    return get_valid_path_from_prefs(prefs, 'PathMicroscopeSpecs', searchDir=False, validate=True)


def get_references_path(prefs):
    '''Return path to directory for reference images. Create directory if not available
    
    Input:
     prefs: Dictionary with preferences 
     
    Output:
     referencesPath: path to directory for reference images for specific well
    '''
    referencesPath = os.path.normpath(os.path.join(daily_folder_path, prefs.getPref('ReferenceDirPath')))
    # create directory if not existent
    if not os.path.isdir(referencesPath):
        os.makedirs(referencesPath)
    return referencesPath   


def get_images_path(prefs, subDir=None):
    '''Return path to directory for images. Create directory if not available
    
    Input:
     subDir: Sub-directory for images. Will create folder with this name
     
    Output:
     referencesPath: path to directory for reference images for specific well
    '''
    if subDir:
        referencesPath = os.path.join(daily_folder_path, subDir)
    else:
        referencesPath = daily_folder_path

    # create directory if not existent
    if not os.path.isdir(referencesPath):
        os.makedirs(referencesPath)
    return referencesPath


def get_calibration_path(prefs):
    '''Return path to calibration information e.g. blackreference images
    
    Input:
     prefs: dictionary with preferences
     
    Output
     calibrationPath: path to calibration directory
    '''
    calibrationPath = get_valid_path_from_prefs(prefs, key = 'PathCalibration', searchDir=True)
    return calibrationPath


def add_suffix(filePath, suffix):
    '''Add suffix to end of file name.
    
    Input:
     filePath: path to file name
     suffix: suffix to put between end of filename and file extension
     
    Output:
     newFilePath: filePath with suffix
    '''
    splitPath = os.path.splitext(filePath)
    newFilePath = splitPath[0] + '_' +  suffix + splitPath[1]
    return newFilePath
         
if __name__ == '__main__':
    prefsPath = get_prefs_path()
    print prefsPath
    prefs=Preferences(prefsPath)

    print get_daily_folder(prefs)
    print get_log_file_path(prefs)
    print get_colony_dir_path(prefs)
#     print get_plate_layout_path(prefs)
    print get_hardware_settings_path(prefs)
    print get_references_path(prefs)   
    imagesPath = get_images_path(prefs)
    print imagesPath
    print add_suffix(imagesPath + 'image.czi', suffix = 'top')