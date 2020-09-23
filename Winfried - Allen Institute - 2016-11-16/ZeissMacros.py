'''
Example Macros for ZEN Blue from Scott McDonald (Zeiss)
Created on Nov 18, 2016

@author: winfriedw
'''
# Example - Diagonal Stage Moves with DF2.czmac
# v0.1  2016-11-17  JSM

print "--------------------------------------------------"
print "Macro Start: 'Example - Diagonal Stage Moves with DF2'"

def Z_RelativeMove(zOffset):
    zStart = Zen.Devices.Focus.ActualPosition
    zEndCalc = zStart + zOffset
    Zen.Devices.Focus.MoveTo(zEndCalc)
    zEnd = Zen.Devices.Focus.ActualPosition
    print "Z_RelativeMove(" + str(zOffset) + "): zStart=" + str(zStart) + ", zEndCalc=" + str(zEndCalc) + ", zEnd=" + str(zEnd)
    return zEnd


def Z_Down():
    z = Z_RelativeMove(-5000)
    return z


def Z_Up():
    z = Z_RelativeMove(5000)
    return z


#--- Automatically train the DF2 offset using SW autofocus of the experiment ---
def Train_DF2(isInFocusAtStart = True, exp = None):
    if(exp == None):
        exp = Zen.Acquisition.Experiments.ActiveExperiment
    zStart = Zen.Devices.Focus.ActualPosition

    #--- Definite Focus finds the glass or plastic surface ---
    Zen.Acquisition.FindSurface()
    #zSurface = Zen.Devices.Focus.ActualPosition
    #print "zSurface = " + str(zSurface)
    
    if(isInFocusAtStart):
        Zen.Devices.Focus.MoveTo(zStart)
        print "Train_DF2(): zStart = " + str(zStart)
    else:
        #--- Use the autofocus of the current experiment to find the sample ---
        Zen.Acquisition.FindAutofocus(exp)
        zAF = Zen.Devices.Focus.ActualPosition
        #print "zAF = " + str(zAF) + " (offset = " + str(zAF - zSurface) + ")"
        print "Train_DF2(): zAF = " + str(zAF)
    
    #--- Save the offset for the Definite Focus for later reuse ---
    Zen.Acquisition.StoreFocus()


#--- Execute Definite Focus (Sample = Surface + Offset) ---
def Focus_DF2():
    Zen.Acquisition.RecallFocus()
    zDF = Zen.Devices.Focus.ActualPosition
    print "Focus_DF2(): zDF = " + str(zDF)


#---------------
#--- M A I N ---
#---------------

#--- The currently active experiment must be set correctly to acquire images ---
exp = Zen.Acquisition.Experiments.ActiveExperiment

if(exp == None):
    Zen.Application.Pause("Plesae click on the ZEN 'Acquisition' tab, and then run the macro again.")
    print "There is no active experiment"
else:
    #--- Read and capture 1st position (1a) ---
    imgLive = Zen.Acquisition.StartLive(exp)
    Zen.Application.Pause("Manually move to position 1 of 2")
    x1= Zen.Devices.Stage.ActualPositionX
    y1= Zen.Devices.Stage.ActualPositionY
    z1= Zen.Devices.Focus.ActualPosition
    Zen.Acquisition.StopLive(exp)
    #imgLive.Close()
    img1a = Zen.Acquisition.AcquireImage(exp)
    Zen.Application.Documents.Add(img1a)
    img1a.Name = "1a"
    print "1a: x=" + str(x1) + "; y=" + str(y1) + "; z=" + str(z1)
    
    #--- Automatically train the DF2 offset using SW autofocus of the experiment ---
    Train_DF2(exp)
    
    #--- Read and capture 2nd position (2a) ---
    imgLive = Zen.Acquisition.StartLive(exp)
    Zen.Application.Pause("Manually move to position 2 of 2")
    x2= Zen.Devices.Stage.ActualPositionX
    y2= Zen.Devices.Stage.ActualPositionY
    z2= Zen.Devices.Focus.ActualPosition
    Zen.Acquisition.StopLive(exp)
    #imgLive.Close()
    img2a = Zen.Acquisition.AcquireImage(exp)
    Zen.Application.Documents.Add(img2a)
    img2a.Name = "2a"
    print "2a: x=" + str(x2) + "; y=" + str(y2) + "; z=" + str(z2)
    
    #--- Return to 1st position and capture (1b) ---
    Z_Down()
    Zen.Devices.Stage.MoveTo(x1, y1)
    Z_Up()
    Zen.Devices.Focus.MoveTo(z1)
    x= Zen.Devices.Stage.ActualPositionX
    y= Zen.Devices.Stage.ActualPositionY
    z= Zen.Devices.Focus.ActualPosition
    Focus_DF2()
    img1b = Zen.Acquisition.AcquireImage(exp)
    Zen.Application.Documents.Add(img1b)
    img1b.Name = "1b"
    print "1b: x=" + str(x) + "; y=" + str(y) + "; z=" + str(z)
    
    #--- Return to 2nd position and capture (2b) ---
    Z_Down()
    Zen.Devices.Stage.MoveTo(x2, y2)
    Z_Up()
    Zen.Devices.Focus.MoveTo(z2)
    x= Zen.Devices.Stage.ActualPositionX
    y= Zen.Devices.Stage.ActualPositionY
    z= Zen.Devices.Focus.ActualPosition
    Focus_DF2()
    img2b = Zen.Acquisition.AcquireImage(exp)
    Zen.Application.Documents.Add(img2b)
    img2b.Name = "2b"
    print "2b: x=" + str(x) + "; y=" + str(y) + "; z=" + str(z)
    
    #--- Return to 1st position and capture (1c) ---
    Z_Down()
    Zen.Devices.Stage.MoveTo(x1, y1)
    Z_Up()
    Zen.Devices.Focus.MoveTo(z1)
    x= Zen.Devices.Stage.ActualPositionX
    y= Zen.Devices.Stage.ActualPositionY
    z= Zen.Devices.Focus.ActualPosition
    Focus_DF2()
    img1c = Zen.Acquisition.AcquireImage(exp)
    Zen.Application.Documents.Add(img1c)
    img1c.Name = "1c"
    print "1c: x=" + str(x) + "; y=" + str(y) + "; z=" + str(z)
    
    for i in range(0, 10):
        print "i=" + str(i)
        
        #--- Return to 2nd position and capture (2b) ---
        Z_Down()
        Zen.Devices.Stage.MoveTo(x2, y2)
        Z_Up()
        Zen.Devices.Focus.MoveTo(z2)
        x= Zen.Devices.Stage.ActualPositionX
        y= Zen.Devices.Stage.ActualPositionY
        z= Zen.Devices.Focus.ActualPosition
        img2 = Zen.Acquisition.AcquireImage(exp)
        Focus_DF2()
        Zen.Application.Documents.Add(img2)
        img2.Name = "2"
        print "2: x=" + str(x) + "; y=" + str(y) + "; z=" + str(z)
        
        #--- Return to 1st position and capture (1c) ---
        Z_Down()
        Zen.Devices.Stage.MoveTo(x1, y1)
        Z_Up()
        Zen.Devices.Focus.MoveTo(z1)
        x= Zen.Devices.Stage.ActualPositionX
        y= Zen.Devices.Stage.ActualPositionY
        z= Zen.Devices.Focus.ActualPosition
        Focus_DF2()
        img1 = Zen.Acquisition.AcquireImage(exp)
        Zen.Application.Documents.Add(img1)
        img1.Name = "1"
        print "1: x=" + str(x) + "; y=" + str(y) + "; z=" + str(z)
        

print "Macro End: 'Example - Diagonal Stage Moves with DF2'"
print "--------------------------------------------------"


##################################################################################################################

# Example - Diagonal Stage Moves.czmac
# v0.1  2016-11-17  JSM

print "--------------------------------------------------"
print "Macro Start: 'Example - Diagonal Stage Moves'"

def Z_RelativeMove(zOffset):
    zStart = Zen.Devices.Focus.ActualPosition
    zEndCalc = zStart + zOffset
    Zen.Devices.Focus.MoveTo(zEndCalc)
    zEnd = Zen.Devices.Focus.ActualPosition
    print "Z_RelativeMove(" + str(zOffset) + "): zStart=" + str(zStart) + ", zEndCalc=" + str(zEndCalc) + ", zEnd=" + str(zEnd)
    return zEnd


def Z_Down():
    z = Z_RelativeMove(-5000)
    return z


def Z_Up():
    z = Z_RelativeMove(5000)
    return z


#--- The currently active experiment must be set correctly to acquire images ---
exp = Zen.Acquisition.Experiments.ActiveExperiment

if(exp == None):
    Zen.Application.Pause("Plesae click on the ZEN 'Acquisition' tab, and then run the macro again.")
    print "There is no active experiment"
else:
    #--- Read and capture 1st position (1a) ---
    imgLive = Zen.Acquisition.StartLive(exp)
    Zen.Application.Pause("Manually move to position 1 of 2")
    x1= Zen.Devices.Stage.ActualPositionX
    y1= Zen.Devices.Stage.ActualPositionY
    z1= Zen.Devices.Focus.ActualPosition
    Zen.Acquisition.StopLive(exp)
    #imgLive.Close()
    img1a = Zen.Acquisition.AcquireImage(exp)
    Zen.Application.Documents.Add(img1a)
    img1a.Name = "1a"
    print "1a: x=" + str(x1) + "; y=" + str(y1) + "; z=" + str(z1)
    
    #--- Read and capture 2nd position (2a) ---
    imgLive = Zen.Acquisition.StartLive(exp)
    Zen.Application.Pause("Manually move to position 2 of 2")
    x2= Zen.Devices.Stage.ActualPositionX
    y2= Zen.Devices.Stage.ActualPositionY
    z2= Zen.Devices.Focus.ActualPosition
    Zen.Acquisition.StopLive(exp)
    #imgLive.Close()
    img2a = Zen.Acquisition.AcquireImage(exp)
    Zen.Application.Documents.Add(img2a)
    img2a.Name = "2a"
    print "2a: x=" + str(x2) + "; y=" + str(y2) + "; z=" + str(z2)
    
    #--- Return to 1st position and capture (1b) ---
    Z_Down()
    Zen.Devices.Stage.MoveTo(x1, y1)
    Z_Up()
    Zen.Devices.Focus.MoveTo(z1)
    x= Zen.Devices.Stage.ActualPositionX
    y= Zen.Devices.Stage.ActualPositionY
    z= Zen.Devices.Focus.ActualPosition
    img1b = Zen.Acquisition.AcquireImage(exp)
    Zen.Application.Documents.Add(img1b)
    img1b.Name = "1b"
    print "1b: x=" + str(x) + "; y=" + str(y) + "; z=" + str(z)
    
    #--- Return to 2nd position and capture (2b) ---
    Z_Down()
    Zen.Devices.Stage.MoveTo(x2, y2)
    Z_Up()
    Zen.Devices.Focus.MoveTo(z2)
    x= Zen.Devices.Stage.ActualPositionX
    y= Zen.Devices.Stage.ActualPositionY
    z= Zen.Devices.Focus.ActualPosition
    img2b = Zen.Acquisition.AcquireImage(exp)
    Zen.Application.Documents.Add(img2b)
    img2b.Name = "2b"
    print "2b: x=" + str(x) + "; y=" + str(y) + "; z=" + str(z)
    
    #--- Return to 1st position and capture (1c) ---
    Z_Down()
    Zen.Devices.Stage.MoveTo(x1, y1)
    Z_Up()
    Zen.Devices.Focus.MoveTo(z1)
    x= Zen.Devices.Stage.ActualPositionX
    y= Zen.Devices.Stage.ActualPositionY
    z= Zen.Devices.Focus.ActualPosition
    img1c = Zen.Acquisition.AcquireImage(exp)
    Zen.Application.Documents.Add(img1c)
    img1c.Name = "1c"
    print "1c: x=" + str(x) + "; y=" + str(y) + "; z=" + str(z)
    
    for i in range(0, 10):
        print "i=" + str(i)
        
        #--- Return to 2nd position and capture (2b) ---
        Z_Down()
        Zen.Devices.Stage.MoveTo(x2, y2)
        Z_Up()
        Zen.Devices.Focus.MoveTo(z2)
        x= Zen.Devices.Stage.ActualPositionX
        y= Zen.Devices.Stage.ActualPositionY
        z= Zen.Devices.Focus.ActualPosition
        img2 = Zen.Acquisition.AcquireImage(exp)
        Zen.Application.Documents.Add(img2)
        img2.Name = "2"
        print "2: x=" + str(x) + "; y=" + str(y) + "; z=" + str(z)
        
        #--- Return to 1st position and capture (1c) ---
        Z_Down()
        Zen.Devices.Stage.MoveTo(x1, y1)
        Z_Up()
        Zen.Devices.Focus.MoveTo(z1)
        x= Zen.Devices.Stage.ActualPositionX
        y= Zen.Devices.Stage.ActualPositionY
        z= Zen.Devices.Focus.ActualPosition
        img1 = Zen.Acquisition.AcquireImage(exp)
        Zen.Application.Documents.Add(img1)
        img1c.Name = "1"
        print "1: x=" + str(x) + "; y=" + str(y) + "; z=" + str(z)
        

print "Macro End: 'Example - Diagonal Stage Moves'"
print "--------------------------------------------------"

#######################################################################################################################################

# Example - Experiment Reuse.czmac
# v0.1  2016-11-17  JSM


#--- Activate IO libraries ---
from System.IO import File, Directory, FileInfo


#------------------------------------------------------------
#--- Split a full filename with path into its components. ---
#------------------------------------------------------------
#--- Example: "C:\Folder\SubFolder\FileName.czi" returns: ---
#---          "C:\Folder\SubFolder" (1st returned value)  ---
#---          "FileName"            (2nd returned value)  ---
#---          ".czi"                (3rd returned value)  ---
#------------------------------------------------------------
def SplitFullFilename(strFullFilename):
    fileInfo = FileInfo(strFullFilename)
    strFolder = fileInfo.DirectoryName
    strExt = fileInfo.Extension
    if(len(strExt) > 0):
        strName = fileInfo.Name.Replace(strExt, "")
    else:
        strName = fileInfo.Name
    return strFolder, strName, strExt


#------------------------------------------------------------
#--- Get list of existing settings files and index of the ---
#--- file designated in the "strFileToSelect" parameter.  ---
#------------------------------------------------------------
def GetAvailableZenFiles(strFileToSelect, strSubFolder, strFileTypeExt):
    nSelected = 0
    
    #--- Get Settings Folder ---
    strUserDocsFolder = Zen.Application.Environment.GetFolderPath(ZenSpecialFolder.UserDocuments)
    #strIasDocsFolder = strUserDocsFolder + "\\Image Analysis Settings"
    strSettingsDocsFolder = strUserDocsFolder + "\\" + strSubFolder
    
    #--- Get list of settings files and 0-based index of the initially selected file ---
    #files = Directory.GetFiles(strIasDocsFolder,"*czias")
    files = Directory.GetFiles(strSettingsDocsFolder, strFileTypeExt)
    listSettings = []
    for i in range(0, files.Length):
        #--- Get the next CZIAS filename ---
        file = files[i]
        strFolder, strName, strExt = SplitFullFilename(file)
        #--- Add the settings filename to the list (no path, no extensiion) ---
        listSettings.append(strName)
        #--- Get 0-based index of the initially selected file ---
        if(strName == strFileToSelect):
            nSelected = i
    
    #--- Return the list of CZIAS files (no path or ext) ---
    #--- and the index of the designated CZIAS.          ---
    return listSettings, nSelected


#----------------------------------------
#--- Display a window for user input. ---
#----------------------------------------
def GetUserInput(strSetting, strSubFolder, strFileTypeExt):
    #--- To detect "Cancel" button press ---
    success = False
    #--- Get settings file Info ---
    #listCzias, nSelected = GetAvailableCziasFiles(strAnalysis)
    listSettings, nSelected = GetAvailableZenFiles(strSetting, strSubFolder, strFileTypeExt)
    #--- Initialize GUI ---
    mainWindow = ZenWindow()
    mainWindow.Initialize("Select Experiment")
    mainWindow.AddDropDown("textboxSetting", "Experiment:", listSettings, nSelected)
    #--- Display GUI ---
    result = mainWindow.Show()
    #--- Process GUI Inputs ---
    if result.Contains('textboxSetting'):
        strSetting = result.GetValue('textboxSetting')
        success = True
    #--- Return User Input ---
    return success, strSetting


expActive = Zen.Acquisition.Experiments.ActiveExperiment
strFolder, strName, strExt = SplitFullFilename(expActive.Name)
success, strExpName = GetUserInput(strName, "Experiment Setups", "*czexp")
if(success):
    #--- Explicit use of the selected experiment ---
    expSelected = Zen.Acquisition.Experiments.GetByName(strExpName)
    img1 = Zen.Acquisition.AcquireImage(expSelected)
    Zen.Application.Documents.Add(img1)
    img1.Name = "1"
    
    #--- Use of the selected experiment as the active experiment ---
    Zen.Acquisition.Experiments.ActiveExperiment = expSelected
    img2 = Zen.Acquisition.AcquireImage(Zen.Acquisition.Experiments.ActiveExperiment)
    Zen.Application.Documents.Add(img2)
    img2.Name = "2"
    
    #--- And again... ---
    img3 = Zen.Acquisition.AcquireImage(Zen.Acquisition.Experiments.ActiveExperiment)
    Zen.Application.Documents.Add(img3)
    img3.Name = "3"



###############################################################################################################################

# Example - Get Image Scaling.czmac
# 2016-07-28  v1.0  JSM
#----------------------------------------------
# Requires the following CZIAS files:
# 1. Example - Get Image Scaling.czias
# 2. Example - Get Image Scaling (08-bit).czias
# 3. Example - Get Image Scaling (16-bit).czias
#----------------------------------------------

#------------------------------------------------
#--- Get the scaling from the image metadata. ---
#------------------------------------------------
def GetScalingFromMetadata(imgIn):
    xScale = 1.0
    yScale = 1.0
    strUnits = "pixels"
    #--- Get Metadata ---
    strScaleAsText = ""
    info = imgIn.Metadata.GetAllMetadata()
    for i in info:
        #--- Format: "1.29 um x 1.29 um" ---
        if(i.Key == "ScalingInfo"):
            strScaleAsText = i.Value
    if(len(strScaleAsText) > 0):
        scalingWords = strScaleAsText.split(" ") #--- e.g. "0.325 um x 0.325 um"
        if(scalingWords.Count == 5):
            #--- Scale X ---
            strScaleX = scalingWords[0]
            xScale = float(strScaleX)
            #xScale = float("%.3f" % scaleX)
            #--- Scale Y ---
            strScaleY = scalingWords[3]
            yScale = float(strScaleY)
            #scaleY = float("%.3f" % scaleY)
            #--- Units ---
            strUnits = scalingWords[1]
    #--- Return the scaling values ---
    return xScale, yScale, strUnits


#------------------------------------------------
#--- Get the scaling from the image metadata. ---
#------------------------------------------------
def GetScalingUnitsFromMetadata(imgIn):
    strUnits = "pixels"
    #--- Get Metadata ---
    strScaleAsText = ""
    info = imgIn.Metadata.GetAllMetadata()
    for i in info:
        #--- Format: "1.29 um x 1.29 um" ---
        if(i.Key == "ScalingInfo"):
            strScaleAsText = i.Value
    if(len(strScaleAsText) > 0):
        scalingWords = strScaleAsText.split(" ") #--- e.g. "0.325 um x 0.325 um"
        if(scalingWords.Count == 5):
            #--- Units ---
            strUnits = scalingWords[1]
    #--- Return the scaling values ---
    return strUnits


#------------------------------------------------
#--- Get the scaling from the image metadata. ---
#------------------------------------------------
def GetScalingFromMeas(imgIn):
    fDebug = True
    xScale = 1.0
    yScale = 1.0
    strUnits = "pixels"
    #--- Limit the size of the region to be measured ---
    w = imgIn.Bounds.SizeX
    if(w > 1000):
        w = 1000
    h = imgIn.Bounds.SizeX
    if(h > 1000):
        h = 1000
    #strSubImage = "C(1)|X(0-999)|Y(0-999)"
    strSubImage = "C(1)|X(0-" + str(w-1) + ")|Y(0-" + str(h-1) + ")"
    #--- Extract just the first channel as "C1" (so it matches the IAS) ---
    imgC1 = Zen.Processing.Utilities.CreateSubset(imgIn, strSubImage, False, False)
    imgC1.SetChannelName(0, "C1")
    if(fDebug):
        Zen.Application.Documents.Add(imgC1)
        imgC1.Name = imgIn.Name + " (C1)"
    
    #--- Handle common pixel types ---
    pixelType = img.Metadata.PixelType
    if((pixelType == ZenPixelType.Bgr24) or (pixelType == ZenPixelType.Bgr48)):
        #--- Split RGB channels ---
        imagesRGB = Zen.Processing.Utilities.SplitRgb(imgC1, ZenPixelType.Gray8)
        imgToMeas = imagesRGB[0]
        if(fDebug):
            Zen.Application.Documents.Add(imgToMeas)
            imgC1.Name = imgIn.Name + " (C1, 8-bit)"
        imagesRGB[1].Close()
        imagesRGB[2].Close()
        imgC1.Close()
        pixelType = ZenPixelType.Gray8
    else:
        imgToMeas = imgC1
    strPixelType = ""
    if(pixelType == ZenPixelType.Gray8):
        strPixelType = " (08-bit)"
    elif(pixelType == ZenPixelType.Gray16):
        strPixelType = " (16-bit)"
    
    #--- Measure the image to get the scaled width and height of the entire image ---
    strAnalysis = "Example - Get Image Scaling" + strPixelType
    ias = ZenImageAnalysisSetting()
    ias.Load(strAnalysis)
    Zen.Analyzing.Analyze(imgToMeas, ias)
    
    #--- Get the measured data ---
    table = Zen.Analyzing.CreateRegionTable(imgToMeas, "Class1")
    if(fDebug):
        Zen.Application.Documents.Add(table)
        table.Name = "Scaled Dimensions"
    wScaled = table.GetValue(0, 1)
    hScaled = table.GetValue(0, 2)
    
    #--- Calculate the scaling ---
    wPixels = imgToMeas.Bounds.SizeX
    hPixels = imgToMeas.Bounds.SizeY
    xScale = float(wScaled) / float(wPixels)
    yScale = float(hScaled) / float(hPixels)
    
    #--- Get scaling units ---
    strUnits = GetScalingUnitsFromMetadata(imgIn)
    
    #--- Clean up ---
    imgToMeas.Close()
    table.Close()
    
    #--- Return the scaling values ---
    return xScale, yScale, strUnits


#-------------------------------
#--- Show ZEN scaling window ---
#-------------------------------
def ShowScalingWindow():
    Zen.Application.ShowWindow(ZenApplicationWindows.Scaling)


#---------------
#--- M A I N ---
#---------------

#--- Get active image ---
img = Zen.Application.Documents.ActiveDocument

#--- Get scaling from metadata ---
x, y, strScaleUnits = GetScalingFromMetadata(img)
strInfo = "Scaling from Metadata:\n   Scale X: " + str(x) + "\n   Scale Y: " + str(y)
strInfo += "\n   Units:   " + strScaleUnits

#--- Get scaling from measurement ---
x, y, strScaleUnits = GetScalingFromMeas(img)
strInfo += "\n\nScaling from Measurement:\n   Scale X: " + str(x) + "\n   Scale Y: " + str(y)
strInfo += "\n   Units:   " + strScaleUnits

#--- Display scaling information ---
Zen.Application.Pause(strInfo)

#######################################################################################################################

#Example - Get Objective List
# 2015-11-16  v1.0  JSM

def GetObjectiveList():
    listObj = []
    for o in range(1, 10):
        mag = Zen.Devices.ObjectiveChanger.GetMagnificationByPosition(o)
        if(mag > 1):
            name = Zen.Devices.ObjectiveChanger.GetNameByPosition(o)
            listObj.Add(name)
    return listObj

#--- M A I N ---
listObj = GetObjectiveList()
strObjectives = ""
for o in range(0, listObj.Count):
    strObjCurrent = listObj[o]
    if(o > 0):
        strObjectives += "\n"
    strObjectives += strObjCurrent
Zen.Application.Pause(strObjectives)

#--- Position Objective (1-based) ---
#Zen.Devices.ObjectiveChanger.TargetPosition = 1
#Zen.Devices.ObjectiveChanger.Apply()

################################################################################################################################

#Example - Get Objective List
# 2015-11-16  v1.0  JSM

def GetObjectiveList():
    listObj = []
    for o in range(1, 10):
        mag = Zen.Devices.ObjectiveChanger.GetMagnificationByPosition(o)
        if(mag > 1):
            name = Zen.Devices.ObjectiveChanger.GetNameByPosition(o)
            listObj.Add(name)
    return listObj

#--- M A I N ---
listObj = GetObjectiveList()
strObjectives = ""
for o in range(0, listObj.Count):
    strObjCurrent = listObj[o]
    if(o > 0):
        strObjectives += "\n"
    strObjectives += strObjCurrent
Zen.Application.Pause(strObjectives)

#--- Position Objective (1-based) ---
#Zen.Devices.ObjectiveChanger.TargetPosition = 1
#Zen.Devices.ObjectiveChanger.Apply()

######################################################################################################################################

# Find Focus 2.czmac
# v0.1 2016-11-17 JSM

print "--------------------------------------------------"
print "Macro Start: 'Find Focus 2.czmac'"

#--- Definite Focus finds the glass or plastic surface ---
Zen.Acquisition.FindSurface()
#    --- DF2 controller box shows the following message:
#    ---     LOCATING SAMPLE
#    ---     SURFACE ---->--
#zSurface = Zen.Devices.Focus.ActualPosition
#print "zSurface = " + str(zSurface)

#--- Use the autofocus of the current experiment to find the sample ---
Zen.Acquisition.FindAutofocus(Zen.Acquisition.Experiments.ActiveExperiment)
zAF = Zen.Devices.Focus.ActualPosition
#print "zAF = " + str(zAF) + " (offset = " + str(zAF - zSurface) + ")"
print "zAF = " + str(zAF)

#--- Save the offset for the Definite Focus for later reuse ---
Zen.Acquisition.StoreFocus()
#    --- DF2 controller box showed the following message:
#    ---     INITIALIZING MONITORING
#    --- DF2 controller box then had the following error message:
#    ---     ERROR: 0x0065
#    ---     CHECK MANUAL
#    --- Cause: Plate was at an angle.

#--- Execute Definite Focus (Sample = Surface + Offset) ---
Zen.Acquisition.RecallFocus()
zDF1 = Zen.Devices.Focus.ActualPosition
print "zDF1 = " + str(zDF1)

#--- Prompt User ---
Zen.Application.Pause("Manually move out of focus")
zOutOfFocus = Zen.Devices.Focus.ActualPosition
print "zOutOfFocus = " + str(zOutOfFocus)

#--- Execute Definite Focus to return to focus (Sample = Surface + Offset) ---
Zen.Acquisition.RecallFocus()
#    --- Gave ZEN error message:
#    ---     "Stabilizing position is not set, and
#    --- DF2 controller box had the following error message:
#    ---     ERROR: 0x0065
#    ---     CHECK MANUAL
#    --- Cause: Plate was at an angle.
zDF2 = Zen.Devices.Focus.ActualPosition
print "zDF2 = " + str(zDF1)

print "Macro End: 'Find Focus 2.czmac'"
print "--------------------------------------------------"

#######################################################################################################################################

# *************** Find Focus ************************
Zen.Acquisition.FindSurface()
Zen.Acquisition.FindAutofocus(Zen.Acquisition.Experiments.ActiveExperiment)
Zen.Acquisition.StoreFocus()
# *************** End of Code Block *****************




