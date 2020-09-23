'''
Tests to recreate com error:
com_error: (-2146233079, 'OLE error 0x80131509', (0, None, u'This type has a ComVisible(false) parent in its hierarchy, therefore QueryInterface calls for IDispatch or class interfaces are disallowed.', None, 0, -2146233079), None)

Created on Feb 19, 2019

@author: winfriedw
'''

# Use win32com form pywind32 library to connect to Windows com objects
import win32com.client as microscopeConnection

############################################################################################
#
# Connect to Carl Zeiss ZEN blue OAD API
# 
# To be able to use ZEN services in a COM environment, 
#     the ZEN functionality must be registered as follows as administrator (right click when opening command prompt to run as administrator)
#     (you might have to update versions):
#     pushd "C:\Windows\Microsoft.NET\Framework64\v4.0.30319"
#     SET dll-1="C:\Program Files\Carl Zeiss\ZEN 2\ZEN 2 (blue edition)\Zeiss.Micro.Scripting.dll"
#     regasm /u /codebase /tlb %dll-1%
#     regasm /codebase /tlb %dll-1%
#     
#     SET dll-2="C:\Program Files\Carl Zeiss\ZEN 2\ZEN 2 (blue edition)\Zeiss.Micro.LM.Scripting.dll"
#     
#     regasm /u /codebase /tlb %dll-2%
#     regasm /codebase /tlb %dll-2%
#     popd
#
############################################################################################

# Import the ZEN OAD Scripting into Python
# This step works as long as the dlls are properly registered
Zen = microscopeConnection.GetActiveObject("Zeiss.Micro.Scripting.ZenWrapperLM")

# Close all open documents
# Works even after software upgrade

print(('Close all open windows: {}'.format(Zen.Application.Documents.RemoveAll(True))))

# Retrieve ZEN ObjectiveChanger object: Now working after upgrade to new dll
#
# This call work without any issues with our previous version of ZEN blue:
#     Version:        2.3.69.1017
#     File Version:   2.3.69.01017
#     ServicePack:    2.3.69.01000
#     Hotfix:         2.3.69.01017
#             
# Since we upgraded ZEN blue to
#     Version:        2.6.76.00000
#     File Version:   2.6.18298.1
#     Hotfix:         2.6.76.00002
# we are getting the error below:
#
#  File "D:\Automation\Anaconda\envs\microscope_automation\lib\site-packages\win32com\client\dynamic.py", line 516, in __getattr__
#     ret = self._oleobj_.Invoke(retEntry.dispid,0,invoke_type,1)
# pywintypes.com_error: (-2146233079, 'OLE error 0x80131509', (0, None, u'This type has a ComVisible(false) parent in its hierarchy, therefore QueryInterface calls for IDispatch or class interfaces are disallowed.', None, 0, -2146233079), None)
# Works after using new dlls

# working
# objective_changer = Zen.Devices.ObjectiveChanger
# print('Retrieved device ObjectiveChanger: {}'.format(objective_changer))
# position = objective_changer.ActualPosition
# objective_magnification = objective_changer.GetMagnificationByPosition(position)
# objective_name = objective_changer.GetNameByPosition(position)
# print('Current objective {} at {} has magnification of {}'.format(objective_name, position, objective_magnification))
# print('Move to objective changer to next position')
# objective_changer.TargetPosition = position + 1
# objective_changer.Apply()


# works after upgrade
active_experiment = Zen.Acquisition.Experiments.ActiveExperiment
print(('The active experiment is: {}'.format(active_experiment)))

# This call to snap an image used to work
image = Zen.Acquisition.AcquireImage_3(active_experiment)
# Now we have to add additional code to display the image
Zen.Application.Documents.Add(image)

# This method will snap an image with the current setting.
# After upgrade to new dll: The image is not displayed
# Now when using AcquireImage_2(True) the image is snapped using settings in Locate tab and displayed
image_snap = Zen.Acquisition.AcquireImage_2(True)
print(image_snap)

# executes experiment, but does not update display (pull down menu and Imaging Setup show previous experiment)
# Does now switch to experiment and displays image
setup_experiment = Zen.Acquisition.Experiments.GetByName('Setup_10x.czexp')
image_execute = Zen.Acquisition.Execute(setup_experiment)
print(image_execute)

# Does not start live mode after upgrade
print('Start live mode')
image_live = Zen.Acquisition.StartLive_2(setup_experiment)
print(image_live)
input('Stop live mode?')
Zen.Acquisition.StopLive_2(setup_experiment)