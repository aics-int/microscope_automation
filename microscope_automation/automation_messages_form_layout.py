'''
Dialog boxes and other messages for Microscope Automation package based on formlayout
https://pypi.python.org/pypi/formlayout
http://pythonhosted.org/formlayout/index.html#
https://github.com/PierreRaybaut/formlayout
http://pyqt.sourceforge.net/Docs/PyQt4/
https://wiki.qt.io/PySide

Requires PyQt4 or PyQt5, set installed API below

Created on Jun 23, 2016

@author: winfriedw
'''

# select PyQT5 as QT_API
# make sure QT5 is installed on system
import os
import sys
import re

# switch between different versions of PyQt depending on computer system
try:
    os.environ['QT_API'] = 'pyqt5'
    from PyQt5 import QtGui
except ImportError:
    from PyQt4 import QtGui
    os.environ['QT_API'] = 'pyqt'
# from PySide import QtGui
from formlayout import fedit
from os import listdir
import pandas

# create logger
import logging
logger = logging.getLogger('microscopeAutomation')

# get function to abort program
# from microscopeAutomation import stop_script
# TODO: fix circular imports, current implementation has stop_script in this file


def read_string(title, label, default, returnCode=False):
    """Ask for user input and allows option to abort script.

    Input:
     title: Title of dialog box

     label: Text to display in front of sting input field

     default: default input

     returnCode: if True, will return after cancel with code 0,
     otherwise will call sys.exit()

    Return:
     0: User selected to abort script

     1: User pressed ok
    """

    datalist = [(label, default), (None, None),
                (None, "Press ok when done.\nPress cancel to abort script.")]
    result = fedit(datalist, title=title,
                   comment="")
    if result is None:
        if returnCode:
            return 0
        else:
            print('User terminated program')
            sys.exit()
    else:
        return str(result[0])


def information_message(title, message, returnCode=False):
    """Displays information to user and allows option to abort script.

    Input:
     title: Title of dialog box

     message: Message that will be displayed

     returnCode: if True, will return after cancel with code 0,
     otherwise will call sys.exit()

    Return:
     0: User selected to abort script

     1: User pressed ok
    """
    datalist = [(None, None),
                (None, "Press OK when ready.\nPress cancel to abort script.")
                ]
    result = fedit(datalist, title=title,
                   comment=message)
    if result is None:
        if returnCode:
            return 0
        else:
            print('User terminated program')
            sys.exit()
    else:
        return 1


def setup_message(message, returnCode=False):
    """Displays information about setup error and allows option to abort script.

    Input:
     message: Message that will be displayed

     returnCode: if True, will return after cancel with code 0,
     otherwise will call sys.exit()

    Return:
     0: User selected to abort script

     1: User pressed ok
    """
    datalist = [(None, None),
                (None, "Press ok when done.\nPress cancel to abort script.")]
    result = fedit(datalist, title="Error in setup detected",
                   comment=message)
    if result is None:
        if returnCode:
            return 0
        else:
            print('User terminated program')
            sys.exit()
    else:
        return 1


def operate_message(message, returnCode=False):
    """Ask user to operate microscope manually and allows option to abort script.

    Input:
     message: Message that will be displayed

     returnCode: if True, will return after cancel with code 0,
     otherwise will call sys.exit()

    Return:
     0: User selected to abort script

     1: User pressed ok
    """
    datalist = [(None, None),
                (None, "Press ok when done.\nPress cancel to abort script.")
                ]
    result = fedit(datalist, title="Please operate microscope",
                   comment=message)
    if result is None:
        if returnCode:
            return 0
        else:
            print('User terminated program')
            sys.exit()
    else:
        return 1


def check_box_message(message, checkBoxList, returnCode=False):
    """Ask user to operate microscope manually and allows option to abort script.

    Input:
     message: Message that will be displayed

     checkBoxList: list with check box names and settings in form:
      [('Choice 1', True), ('Choice 2', False)

     returnCode: if True, will return after cancel with code 0,
     otherwise will call sys.exit()

    Return:
     0: User selected to abort script

     newCheckBoxList: User pressed ok result is updated checkBoxList
    """
    datalist = checkBoxList + [(None, None),
                               (None, "Press ok when done.\nPress cancel to abort.")]
    # datalist = [(None, None),
    #            (None, '''Press ok when done. \nPress cancel to abort.''')
    #            ] + checkBoxList

    result = fedit(datalist, title="Please select",
                   comment=message)
    if result is None:
        if returnCode:
            return 0
        else:
            print('User terminated program')
            sys.exit()
    else:
        boxLabels = [box[0] for box in checkBoxList]
        newCheckBoxList = list(zip(boxLabels, result))
        return newCheckBoxList


def error_message(message, returnCode=False, blocking=True):
    """Show error message and allows option to abort script.

    Input:
     message: Message that will be displayed

     returnCode: if True, will return after cancel with code 0,
     otherwise will call sys.exit()

     blocking: if True use modal dialog for error reporting, otherwise print(message)

    Return:
     0: User selected to abort script

     1: User pressed ok

     -1: User pressed ok and selected 'Ignore'
    """
    if blocking is False:
        print(message)
        return 1
    else:
        datalist = [(None, None),
                    (None, ("Please perform the action.\nPress ok when done."
                            "\nPress cancel to abort.")),
                    ('Ignore', False)]
        result = fedit(datalist, title="Error",
                       comment=message)
        if result:
            if result[0]:
                return -1
            else:
                return 1
        if result is None:
            if returnCode:
                return 0
            else:
                print('User terminated program')
                sys.exit()
        else:
            return 1


def wait_message(message, returnCode=False):
    """Interrupt script and wait for user to continue.

    Input:
     message: Message that will be displayed

     returnCode: if True, will return after cancel with code 0,
     otherwise will call sys.exit()

    Return:
     0: User selected to abort script

     True: User pressed ok and want's to continue to wait after each image

     False: User pressed ok and want's to cancel wait times
    """
    datalist = [(None, None),
                (None, ("Please perform the action.\nPress ok when done."
                        "\nPress cancel to abort.")),
                ("Continue to wait after next image", True)]
    result = fedit(datalist, title="Continue?",
                   comment=message)
    if result is None:
        if returnCode:
            return 0
        else:
            print('User terminated program')
            sys.exit()
    else:
        return result[0]


def select_message(message, count=None, returnCode=False):
    """Interrupt script and wait for user to continue.

    Input:
     message: Message that will be displayed

     count: number of collected positions

     returnCode: if True, will return after cancel with code 0,
     otherwise will call sys.exit()

    Return:
     0: If user selected to abort script

     resultDict: dictionary of form {'Include': True/False, 'Continue': True/False}
    """
    datalist = [(None, None),
                (None, ("Please perform the action(s) below.\nPress ok when done."
                        "\nPress cancel to abort.")),
                ("Include position in data acquisition.", True),
                (None, None),
                (None, "Number of collected positions: {}".format(count)),
                ("Continue collecting positions.", True)]
    result = fedit(datalist, title="Select",
                   comment=message)
    if result is None:
        if returnCode:
            return 0
        else:
            print("User terminated program")
            sys.exit()
    else:
        resultDict = {'Include': result[0], 'Continue': result[1]}
        return resultDict


def file_select_dialog(directory, filePattern=None, comment=None, returnCode=False):
    """List all files in directory and select one.

    Input:
     directory: path to directory with files

     filePattern: string with regular expression.
     If file matches expression it will be pre-selected.

     returnCode: if True, will return after cancel with code 0,
     otherwise will call sys.exit()

    Output:
     filePath: path to selected file
    """
    # load all file names in directory dirPaht + date
    # check if directory exists
    if not os.path.isdir(directory):
        logger.warning('Directory for .csv file with colony coordinates does not exist')
    allFiles = pandas.Series(listdir(directory))
    try:
        # find all filenames that match
        colFileLocSeries = [re.search(filePattern, singleFile) is not None
                            for singleFile in allFiles]
        colFileLocIndex = [int(allFiles[colFileLocSeries].index.tolist()[0])]
        allFiles = list(allFiles)
    except Exception:
        colFileLocIndex = [0]
        allFiles = [''] + list(allFiles)
    allFiles.sort()
    datalist = [('Files:', colFileLocIndex + allFiles)]
    result = fedit(datalist, title="Select file?",
                   comment=comment)
    print(result)
    if result is None:
        if returnCode:
            return 0
        else:
            print('User terminated program')
            sys.exit()
    return allFiles[result[0]]


def pull_down_select_dialog(itemList, message):
    """Show all items from itemList in pulldown menu and allow user to select one item.

    Input:
     itemList: list of strings to display in pull down menu

     message: string with instructions to user

    Output:
     selectedItem: item selected by user
    """
    # create content of pull down menu
    datalist = [('Selection:', ([0] + [str(i) for i in itemList]))]

    # display dialog bos
    result = fedit(datalist, title="Selection", comment=message)
    if result is None:
        stop_script()
    selectedItem = itemList[result[0]]
    return selectedItem


def value_calibration_form(title, comment, default, *form_fields):
    """Attribute selection dialog for value calibration. Last result value will
    always be True or False for whether the value(s) were acceptable.

    Input:
     title: title for the form

     comment: comment for the form

     form_fields: variable length argument list for all fields to be changed

    Output:
     result: the filled-in form
    """
    data_list = list(form_fields) + [('Correct?', default)]
    result = fedit(data_list, title=title, comment=comment)
    return result


def stop_script(messageText=None, allowContinue=False):
    """Stop processing and ask to leave automation script.
    Script will stop all Microscope action immediately and ask user
    to stop execution of script or to continue.

    Input:
     messageText: Message to user explaining why processing should be stopped.

     allowContinue: if True, allow user to continue. Default: False

    Returns if user selects 'Continue', otherwise calls sys.exit()
    """

    #     Microscope.stop_microscope()
    if allowContinue:
        if messageText is None:
            messageText = 'If you want to abort script press ok.\notherwise Continue'
        con = information_message('Exit script', messageText, returnCode=True)
    else:
        if messageText is None:
            messageText = 'Exit'
        con = information_message('Exit script', messageText, returnCode=False)
        con = 0

    if con == 0:
        # logger.info('User aborted operation')
        print('Operation Aborted')
        # cleanup after image displaying
        os._exit(1)


if __name__ == '__main__':
    from .interactive_location_picker_pyqtgraph import ImageLocationPicker
    import numpy as np
    import pyqtgraph

    image = np.zeros((50, 50))
    app = QtGui.QApplication([])
    input('Continue')
    ImageLocationPicker(image, app=app).plot_points('Test')
    input('Continue')
    print((error_message('Test error message')))
    pyqtgraph.exit()
