'''
Function to setup hardware and samples based on reference files
Created on Aug 1, 2016

@author: winfriedw
'''
# import standard Python modules
import string
import pandas
import numpy
import math
# import external modules written for MicroscopeAutomation
# from . import preferences
# from . import hardware
# from . import samples
# from . import automationMessagesFormLayout as message
# from .getPath import get_hardware_settings_path, get_colony_file_path
import preferences
import hardware
import samples
import automationMessagesFormLayout as message
from getPath import get_hardware_settings_path, get_colony_file_path, get_experiment_path
# create logger
import logging
logger = logging.getLogger('microscopeAutomation')

def setup_microscope(prefs):
    '''Create object of class Microscope from module hardware.
    
    Input:
     prefs: preferences with information about microscope hardware
     
    Output:
     microscope: object of class Microscope
    '''
    # get description about microscope
    pathMicroscopeSpecs = get_hardware_settings_path(prefs)
    
    # load specs for hardware
    try:
        specs = preferences.Preferences(pathMicroscopeSpecs)    
    except Exception as e:
        print (e)
        # use data from development environment if not using real setup       
        pathMicroscopeSpecs_RD = '../GeneralSettings/microscopeSpecifications_RD.yml'
        specs = preferences.Preferences(pathMicroscopeSpecs_RD)
        print ('Could not read microscope specifications from {}.\nRead from R&D environment from {}.'.format(pathMicroscopeSpecs, pathMicroscopeSpecs_RD))
    
    # get object to connect to software based on software name  
    software=specs.getPref('Software') 
    connectObject=hardware.ControlSoftware(software)
 
    # create microscope
    microscope = specs.getPrefAsMeta('Microscope')
    microscopeObject = hardware.Microscope(controlSoftwareObject = connectObject, 
                                           name=microscope.getPref('Name'),
                                           experiments_path = get_experiment_path(prefs, dir = True))

    # setup cameras and add to microscopeObject
    cameras=specs.getPref('Cameras')
    
    for name, camera in cameras.iteritems():
        try:
            pixelNumber = (int(camera['pixelNumber_x']), int(camera['pixelNumber_x']))
        except:
            pixelNumber = (0, 0)
        cameraObject=hardware.Camera(name,
                                     pixelSize = (float(camera['pixelSize_x']), float(camera['pixelSize_y'])),
                                     pixelNumber=pixelNumber,
                                     pixelType= camera['pixelType'],
                                     name=camera['name'],
                                     detectorType=camera['detectorType'],
                                     manufacturer=camera['manufacturer']
                                     )

        microscopeObject.add_microscope_object(cameraObject)
     
    # setup save Area to prevent crashes between stage and objective
    saveAreas = specs.getPref('SaveAreas')
    
    for name, areas in saveAreas.iteritems():
        safe_area_object = hardware.Safety(name)
        for safe_area_id, area in areas.iteritems():
            safe_area_object.add_save_area(area['area'], safe_area_id, area['zMax'])

        microscopeObject.add_microscope_object(safe_area_object)

    # setup stages and add to microscopeObject
    stages_specifications = specs.getPref('Stages')

    for name, stage in stages_specifications.iteritems():
        stageObject=hardware.Stage(stageId = name,
                             safe_area = stage['SafeArea'], 
                             safe_position = stage['SafePosition'],
                             objective_changer = stage['ObjectiveChanger'],
                             microscope_object = microscopeObject)
        microscopeObject.add_microscope_object(stageObject)

    # setup focus drive and add to microscopeObject
    focus_specifications = specs.getPrefAsMeta('Focus')
    focusDriveObject=hardware.FocusDrive(focus_drive_id = focus_specifications.getPref('Name'),
                                   max_load_position = focus_specifications.getPref('MaxLoadPosition'), 
                                   min_work_position = focus_specifications.getPref('MinWorkPosition'),
                                   auto_focus_id = focus_specifications.getPref('AutoFocus'),
                                   objective_changer = stage['ObjectiveChanger'],
                                   microscope_object = microscopeObject)
    microscopeObject.add_microscope_object(focusDriveObject)

    # setup objective changer and add to microscopeObject
    objective_changer_specifications = specs.getPrefAsMeta('ObjectiveChanger')

    objectiveChangerObject=hardware.ObjectiveChanger(objective_changer_specifications)

    microscopeObject.add_microscope_object(objectiveChangerObject)

    # setup autofocus  and add to microscopeObject
    auto_focus_specifications = specs.getPrefAsMeta('AutoFocus')
    autoFocusObject=hardware.AutoFocus(auto_focus_id = auto_focus_specifications.getPref('Name'),
#                                    init_experiment = auto_focus_specifications.getPref('DefaultExperiment'),
                                   default_camera = auto_focus_specifications.getPref('DefaultCamera'),
                                   objective_changer_instance = objectiveChangerObject,
                                   default_reference_position = auto_focus_specifications.getPref('DefaultReferencePosition'))

    microscopeObject.add_microscope_object(autoFocusObject)
    
    # setup pump and add to microscopeObject
    pump=specs.getPref('Pump')
    timePump=specs.getPref('TimePump')
    comPortPump=specs.getPref('ComPortPump')
    baudratePump=specs.getPref('BaudratePump')

    pumpObject=hardware.Pump(pump, seconds = timePump, \
                             port = comPortPump, baudrate = baudratePump)
    microscopeObject.add_microscope_object(pumpObject)
    
    # initialize microscope hardware moved to initialize_microscope in module microscopeAutomation.py
#     microscopeObject.initialize_hardware()
    return microscopeObject     

###########################################################################
#
# Create plate and add colonies from plate scanner and other content (barcode, controls)
#
############################################################################

def get_colony_data(prefs, colonyFile):
    '''Get data and positions of colonies.
    
    Input:
     prefs: preferences with information about colony file
     colonyFile: path to .csv file with colony data.     
    
    Output:
     colonies: pandas frame with content of .csv file
    '''
    # setup loggin
    logger = logging.getLogger('microscopeAutomation.setupAutomation.get_colony_data')
 
    ##############################
    # this portion will be replaces by calls to LIMS system
    ##############################
     
    # load .csv file with one row header
    # we should define the colomn type here
    # tried to use usecols to read data read in -> does not work
    print ('Read file {}'.format(colonyFile))
    coloniesAll=pandas.read_csv(colonyFile)

    # select plate to process
    # Use plateID list to be able to expand to multiple plates
    plateIdList = list(coloniesAll.loc[:, 'PlateID'].unique())
    
    selectedPlateIDList = [message.pull_down_select_dialog(plateIdList, 'Please select barcode of plate on microscope.\n947 is a good example.')]
    plateSelector = coloniesAll.loc[:,'PlateID'].isin(selectedPlateIDList)

    # select columns as defined in preferences.yml file and rename to software internal names
    colonyColumns = prefs.getPref('ColonyColumns')
    colonies = coloniesAll.loc[plateSelector,colonyColumns.keys()]
    colonies.rename(columns = colonyColumns, inplace = True)
 
     # get information about colonies to image
    print ('summary statistics about all colonies on plate ', plateIdList)
    print (colonies.describe())

    # calculate additional columns
    colonies.loc[:, 'WellColumn'] = colonies.loc[:, 'WellColumn'].fillna(-1)
    colonies.loc[:, 'Well'] = colonies.loc[:, 'WellRow'].str.cat(colonies.loc[:, 'WellColumn'].astype(int).astype(str))
    colonies.loc[:, 'Center_X^2'] = colonies.loc[:, 'Center_X'].apply(math.pow, args=(2,))
    colonies.loc[:, 'Center_Y^2'] = colonies.loc[:, 'Center_Y'].apply(math.pow, args=(2,))
    colonies.loc[:, 'CenterDistance']=colonies.loc[:, 'Center_X^2'].add(colonies.loc[:, 'Center_Y^2']).apply(math.sqrt)
    countPerWell=pandas.DataFrame(colonies.groupby(['PlateID', 'Well']).size(), columns=['CountPerWell']).reset_index()
    colonies = pandas.merge(colonies, countPerWell, left_on=['PlateID', 'Well'], right_on=['PlateID', 'Well'])
    return colonies
    
###########################################################################

def filter_colonies(prefs, colonies, wellDict):
    '''Select colonies to image based on settings in preferences file.
    
    Input:
     prefs: preferences with selection criteria
     colonies: table with colony data
     wellList: list with wells that should be considered. Well names in format 'A1'.
     
    Output:
     selectedColonies: subset of colonies to be imaged
    '''
    # get names of wells to scan
    wellList = wellDict.keys()
    wellsSelect=colonies['Well'].isin(wellList)

    # scan only wells with a minimum number of colonies in a give well before filtering
    minCountPerWell=prefs.getPref('MinCountPerWell')
    minCountSelect=colonies.CountPerWell >= minCountPerWell

    # scan only wells with a maximum number of colonies in a give well before filtering
    maxCountPerWell=prefs.getPref('MaxCountPerWell')
    maxCountSelect=colonies.CountPerWell <= maxCountPerWell
    
    # scan only colonies that are larger than MinAreaColonies based on Celigo measurements in mum^2
    minAreaColonies=prefs.getPref('MinAreaColonies')
    minAreaSelect=colonies.Area >= minAreaColonies
    
    # scan only colonies that are smaller than MinAreaColonies based on Celigo measurements in mum^2
    maxAreaColonies=prefs.getPref('MaxAreaColonies')
    maxAreaSelect=colonies.Area <= maxAreaColonies
    
    # scan only colonies that are within a circle around the well center 
    # with radius MaxDistanceToCenter based on Celigo measurements in mum
    maxDistanceToCenter=prefs.getPref('MaxDistanceToCenter')
    maxDistanceSelect=colonies.CenterDistance <= maxDistanceToCenter
    
    # remove colonies that are not in the correct wells
    filteredColonies = colonies.loc[minCountSelect \
                                     & maxCountSelect \
                                     & minAreaSelect \
                                     & maxAreaSelect \
                                     & maxDistanceSelect \
                                     & wellsSelect]

    # we want to scan a maximum number of colonies per well
    # if there are more valid colonies in a given well than select random colonies
    selectedColonies = pandas.DataFrame()
    for well, numberImages in wellDict.iteritems():
        # find all colonies within well
        wellSelect = filteredColonies.Well == well
        coloniesInWell = filteredColonies.loc[wellSelect]
        if coloniesInWell.shape[0] > numberImages:
            selectedColonies = selectedColonies.append(coloniesInWell.sample(numberImages))
            
    print 'summary statistics about colonies after filtering'
    print selectedColonies.describe()
    return selectedColonies

###########################################################################
    
def add_colonies(wellObject, colonies, hardwareSettings, prefs = None):
    '''Add colonies from Celigo scan to well.
    
    Input:
     wellObject: instance of wellObject from module samples
     colonies: pandas frame with colony information. This information was extracted with CellProfiler from plate-scanner images.
     hardwareSettings: preferences with description of microscope components, here coordinate transformation between colonies and well
     prefs: dictionary with preferences
     
    Output:
     colonyList: list with all colony objects
    '''
    # select all colonies that are located within well
    well=wellObject.name

    wellData=colonies['Well']==well
    
    # get calibration options for colonies
    xFlip=int(hardwareSettings.getPref('xFlipColony'))
    yFlip=int(hardwareSettings.getPref('yFlipColony'))
    zFlip=int(hardwareSettings.getPref('zFlipColony'))
    xCorrection=float(hardwareSettings.getPref('xCorrectionColony'))
    yCorrection=float(hardwareSettings.getPref('yCorrectionColony'))
    zCorrection=float(hardwareSettings.getPref('zCorrectionColony'))

    # List with all colonies to be imaged
    colonyList = []
    for colony in colonies[wellData].itertuples():
        center=(colony.Center_X, colony.Center_Y, 0)
        ellipse=(colony.ColonyMajorAxis, colony.ColonyMinorAxis, colony.Orientation)
        colonyName=well+'_'+str(colony.ColonyNumber).zfill(4)
        colonyObject=samples.Colony(name = colonyName, image = True, center=center, ellipse=ellipse, \
                                    meta=colony, wellObject=wellObject, \
                                    xFlip=xFlip, yFlip=yFlip, zFlip=zFlip, \
                                    xCorrection=xCorrection, yCorrection=yCorrection, zCorrection=zCorrection,
                                    prefs = prefs)
        
        # add additional meta data
        colonyObject.set_cell_line(colony.CellLine)
        colonyObject.set_clone(colony.CloneID)
        colonyObject.add_meta(colony._asdict())
        colonyList.append(colonyObject)
        wellObject.add_colonies({colonyName: colonyObject})

    return colonyList

###########################################################################
    
def add_barcode(name, wellObject, layout, prefs = None):
    '''Add barcode to well.
    
    Input:
     name: string with name for barcode
     wellObject: instance of wellObject from module samples
     layout: preferences for plate layout
     prefs: dictionary with preferences
     
    Output:
     none
    '''
    # get calibration options for barcode
    center=[float(layout.getPref('xBarcodePos')),\
            float(layout.getPref('yBarcodePos')),\
            float(layout.getPref('zBarcodePos'))]
    xFlip=int(layout.getPref('xFlipBarcode'))
    yFlip=int(layout.getPref('yFlipBarcode'))
    zFlip=int(layout.getPref('zFlipBarcode'))
    xCorrection=float(layout.getPref('xCorrectionBarcode'))
    yCorrection=float(layout.getPref('yCorrectionBarcode'))
    zCorrection=float(layout.getPref('zCorrectionBarcode'))

    barcodeObject=samples.Barcode(name=name, wellObject=wellObject, center =center, \
                                  xFlip=xFlip, yFlip=yFlip, zFlip=zFlip, \
                                  xCorrection=xCorrection, yCorrection=yCorrection, zCorrection=zCorrection,
                                  )
    wellObject.add_barcode({name: barcodeObject})
        
###########################################################################    

def setup_plate(prefs, colonyFile = None, microscopeObject = None):
    '''Create object of class plateholder from module sample that holds information about all colonies scanned with plate reader.
    
    Input:
     prefs: preferences file for experiment
     colonyFile: path to .csv file with colony data.     
     
    Output:
     plateHolderObject: object that contains all wells with sample information.
    '''
    # get description for microscope components
    pathHardwareSettings=get_hardware_settings_path(prefs)
    hardwareSettings=preferences.Preferences(pathHardwareSettings)
    
    # we will first get information about colonies to image. 
    # Some of this information (e.g. barcode) will be required to set up other components (e.g. plates)
    barcode = None
    meanDiameter = None
    if colonyFile is not None:
        # load file with colony data and filter colonies that should be imaged
        # get subset of preferences for colony scanning
        addColoniesPreferences = prefs.getPrefAsMeta('AddColonies')

        # calculate correction factor for wells
        coloniesPath = get_colony_file_path(addColoniesPreferences, colonyFile)
        colonies=get_colony_data(addColoniesPreferences, coloniesPath)
    
        # get names of wells to scan
        wellsDefinitions=addColoniesPreferences.getPref('Wells')
    
        colonies=filter_colonies(addColoniesPreferences, colonies, wellDict=wellsDefinitions)
        
        # get barcode from colonies and attach to plate
        barcode = colonies['PlateID'].unique()
        if barcode.size > 1:
            print ('More than one barcode selected for plate. Will use only first one.')
        barcode = barcode[0]
              
        # calculate median well diameter
        wellMinorAxisGrouped=colonies[['Well','WellMinorAxis']].groupby('Well')
        wellMajorAxisGrouped=colonies[['Well','WellMajorAxis']].groupby('Well')
        wellMinorAxisMedian=numpy.median(wellMinorAxisGrouped.aggregate(numpy.median))
        wellMajorAxisMedian=numpy.median(wellMajorAxisGrouped.aggregate(numpy.median))
        meanDiameter=numpy.mean([wellMinorAxisMedian, wellMajorAxisMedian])
            
    # create plate holder and fill with plate, wells, colonies, cells, and water delivery
    # create plate holder and connect it to microscope
    stageID = hardwareSettings.getPref('PlateHolderStageID')
    focusID = hardwareSettings.getPref('PlateHolderFocusID')
    autoFocusID = hardwareSettings.getPref('PlateHolderAutoFocusID')
    objectiveChangerID = hardwareSettings.getPref('PlateHolderObjectiveChangerID')
    safetyID = hardwareSettings.getPref('PlateHolderSafetyID')
    

    # Read settings for coordinate system of plate relative to stage (plate holder) from microscopeSpecifications.yml file
    name=hardwareSettings.getPref('PlateHolder')
    center=[float(hardwareSettings.getPref('xCenterPlateHolder')),\
            float(hardwareSettings.getPref('yCenterPlateHolder')),\
            float(hardwareSettings.getPref('zCenterPlateHolder'))]
    xFlip=int(hardwareSettings.getPref('xFlipPlateHolder'))
    yFlip=int(hardwareSettings.getPref('yFlipPlateHolder'))
    zFlip=int(hardwareSettings.getPref('zFlipPlateHolder'))
    xCorrection=float(hardwareSettings.getPref('xCorrectionPlateHolder'))
    yCorrection=float(hardwareSettings.getPref('yCorrectionPlateHolder'))
    zCorrection=float(hardwareSettings.getPref('zCorrectionPlateHolder'))
    xSavePosition=float(hardwareSettings.getPref('xSavePositionPlateHolder'))
    ySavePosition=float(hardwareSettings.getPref('ySavePositionPlateHolder'))
    zSavePosition=hardwareSettings.getPref('zSavePositionPlateHolder')
    
    plateHolderObject=samples.PlateHolder(name=name,
                                          microscope_object = microscopeObject,
                                          stage_id = stageID,
                                          focus_id = focusID,
                                          auto_focus_id = autoFocusID,
                                          objective_changer_id = objectiveChangerID,
                                          safety_id = safetyID,
                                          center=center,
                                          xFlip=xFlip, yFlip=yFlip, zFlip=zFlip,
                                          xCorrection=xCorrection, yCorrection=yCorrection, zCorrection=zCorrection,
                                          xSavePosition=xSavePosition, ySavePosition=ySavePosition, zSavePosition=zSavePosition
                                          )

    # create immersion delivery system as part of PlateHolder and add to PlateHolder
    pumpName=hardwareSettings.getPref('Pump')
    safetyID = hardwareSettings.getPref('PumpSafetyID')
    pumpObject = microscopeObject.get_microscope_object(pumpName)
    center=[float(hardwareSettings.getPref('xCenterPump')),\
            float(hardwareSettings.getPref('yCenterPump')),\
            float(hardwareSettings.getPref('zCenterPump'))]
    xFlip=int(hardwareSettings.getPref('xFlipPump'))
    yFlip=int(hardwareSettings.getPref('yFlipPump'))
    zFlip=int(hardwareSettings.getPref('zFlipPump'))
    xCorrection=float(hardwareSettings.getPref('xCorrectionPump'))
    yCorrection=float(hardwareSettings.getPref('yCorrectionPump'))
    zCorrection=float(hardwareSettings.getPref('zCorrectionPump'))
    
    ImmersionDeliveryObject=samples.ImmersionDelivery(name=pumpName, \
                                                      plateHolderObject=plateHolderObject, \
                                                      center=center, \
                                                      xFlip=xFlip, yFlip=yFlip, zFlip=zFlip, \
                                                      xCorrection=xCorrection, yCorrection=yCorrection, zCorrection=zCorrection,
                                                      )
    plateHolderObject.immersionDeliverySystem = ImmersionDeliveryObject

    
    # create Plate as part of PlateHolder and add it to PlateHolder
    # get description for plate dimensions and coordinate system from microscopeSpecifications.yml
    plateName=hardwareSettings.getPref('Plate')
    center=[float(hardwareSettings.getPref('xCenterPlate')),\
            float(hardwareSettings.getPref('yCenterPlate')),\
            float(hardwareSettings.getPref('zCenterPlate'))]
    xFlip=int(hardwareSettings.getPref('xFlipPlate'))
    yFlip=int(hardwareSettings.getPref('yFlipPlate'))
    zFlip=int(hardwareSettings.getPref('zFlipPlate'))
    xCorrection=float(hardwareSettings.getPref('xCorrectionPlate'))
    yCorrection=float(hardwareSettings.getPref('yCorrectionPlate'))
    zCorrection=float(hardwareSettings.getPref('zCorrectionPlate'))
    reference_well = hardwareSettings.getPref('InitialReferenceWell')

    plateObject=samples.Plate(name=plateName,
                              plateHolderObject=plateHolderObject,
                              center=center,
                              xFlip=xFlip, yFlip=yFlip, zFlip=zFlip, \
                              xCorrection=xCorrection, yCorrection=yCorrection, zCorrection=zCorrection)
    
    
    # barcode is typically retrieved from colony file, otherwise prompt for input
    if barcode is None:
        barcode = message.read_string('Barcode', 'Barcode:', default = '123', returnCode=False)
    plateObject.set_barcode(barcode)                    
    plateHolderObject.add_plates(plateObjectDict={barcode: plateObject})             

    # create Wells and add to Plate
    # get information from microscopeSpecifications.yml file
    ncol = int(hardwareSettings.getPref('ColumnsWell'))
    nrow = int(hardwareSettings.getPref('RowsWell'))
    pitch = float(hardwareSettings.getPref('PitchWell'))
    diameter = float(hardwareSettings.getPref('DiameterWell'))
    zCenterWells = float(hardwareSettings.getPref('zCenterWell'))
    
    xFlip=int(hardwareSettings.getPref('xFlipWell'))
    yFlip=int(hardwareSettings.getPref('yFlipWell'))
    zFlip=int(hardwareSettings.getPref('zFlipWell'))
    xCorrection=float(hardwareSettings.getPref('xCorrectionWell'))
    yCorrection=float(hardwareSettings.getPref('yCorrectionWell'))
    zCorrection=float(hardwareSettings.getPref('zCorrectionWell'))

    # create all wells for plate and add to plate
    for colIndex in range(ncol-1):
        colName=str(colIndex+1)
        colCoord=colIndex*pitch
        for rowIndex in range(nrow-1):   
            # create well       
            rowName = string.ascii_uppercase[rowIndex]            
            yCoord = rowIndex * pitch
            name = rowName + colName

            wellObject=samples.Well(name=name, center=(colCoord, yCoord, zCenterWells), \
                                    diameter=diameter, \
                                    plateObject=plateObject, \
                                    wellPositionNumeric = (colIndex, rowIndex), wellPositionString = (rowName, colName), \
                                    xFlip=xFlip, yFlip=yFlip, zFlip=zFlip, \
                                    xCorrection=xCorrection, yCorrection=yCorrection, zCorrection=zCorrection,
                                    )

            plateObject.add_wells({name: wellObject})
 
     # update well diameter based on platescanner reads stored in colonies file
    if meanDiameter is not None:
        [wellObject.set_setDiameter(meanDiameter) for wellName, wellObject in plateObject.get_wells().iteritems()]

    # add reference well
    reference_well = hardwareSettings.getPref('InitialReferenceWell')
    reference_object = plateObject.get_well(reference_well)
    plateObject.set_reference_object(reference_object)
    
    # add colonies to wells
    if colonyFile is not None:
        wellsColoniesList = [add_colonies(wellObject, colonies, hardwareSettings, addColoniesPreferences) for wellName, wellObject in plateObject.get_wells().iteritems()]
        
        colonyList = []
        for wellEntry in wellsColoniesList:
            if wellEntry is True:
                colonyList.extend(wellEntry)
        image_dir_key = prefs.prefs['AddColonies']['NextName']
        plateObject.add_to_image_dir(image_dir_key, colonyList, position = None)   
    # TODO: add barcodes to wells
    
    # TODO:add controls to wells
              
    # add default reference images
    # get black reference images
#     default_images = prefs.getPref('DefaultImages')
#     li = LoadImage()
#     for reference in default_images:
#         name = reference['Name']
#         location = get_calibration_path(prefs) if reference['CalibrationFolder'] else reference['CalibrationLocation']
#         metaDir = {
#             'aics_SampleType': reference['Type'],
#             'aics_SampleName': name,
#             'aics_barcode': barcode,
#             'aics_filePath': location + name + reference['FileType']
#         }
#         ref_image = ImageAICS(meta=metaDir)
#         li.load_image(ref_image, True)
#         plateHolderObject.add_attached_image(name, ref_image)

    return plateHolderObject

def setup_slide(prefs, microscopeObject = None):
    '''Create basic object of class slide from module sample that consists of plate holder and slide.
    
    Input:
     prefs: preferences file for experiment  
     
    Output:
     plateHolderObject: object that contains one slide.
    '''
    # get description for microscope components
    pathHardwareSettings=get_hardware_settings_path(prefs)
    hardwareSettings=preferences.Preferences(pathHardwareSettings)     
    
    # create plate holder and connect it to microscope
    stageID = hardwareSettings.getPref('PlateHolderStageID')
    focusID = hardwareSettings.getPref('PlateHolderFocusID')
    autoFocusID = hardwareSettings.getPref('PlateHolderAutoFocusID')
    objectiveChangerID = hardwareSettings.getPref('PlateHolderObjectiveChangerID')
    safetyID = hardwareSettings.getPref('SlideSafetyID')
    

    # Read settings for coordinate system of slide relative to stage (plate holder) from microscopeSpecifications.yml file
    name=hardwareSettings.getPref('PlateHolder')
    center=[float(hardwareSettings.getPref('xCenterPlateHolder')),\
            float(hardwareSettings.getPref('yCenterPlateHolder')),\
            float(hardwareSettings.getPref('zCenterPlateHolder'))]
    xFlip=int(hardwareSettings.getPref('xFlipPlateHolder'))
    yFlip=int(hardwareSettings.getPref('yFlipPlateHolder'))
    zFlip=int(hardwareSettings.getPref('zFlipPlateHolder'))
    xCorrection=float(hardwareSettings.getPref('xCorrectionPlateHolder'))
    yCorrection=float(hardwareSettings.getPref('yCorrectionPlateHolder'))
    zCorrection=float(hardwareSettings.getPref('zCorrectionPlateHolder'))
    xSavePosition=float(hardwareSettings.getPref('xSavePositionPlateHolder'))
    ySavePosition=float(hardwareSettings.getPref('ySavePositionPlateHolder'))
    zSavePosition=hardwareSettings.getPref('zSavePositionPlateHolder')
    
    plate_holder_object=samples.PlateHolder(name=name, 
                                      microscope_object = microscopeObject,
                                      stage_id = stageID, 
                                      focus_id = focusID,
                                      auto_focus_id = autoFocusID,
                                      objective_changer_id = objectiveChangerID,
                                      safety_id = safetyID,
                                      center=center,
                                      xFlip=xFlip, yFlip=yFlip, zFlip=zFlip,
                                      xCorrection=xCorrection, yCorrection=yCorrection, zCorrection=zCorrection,
                                      xSavePosition=xSavePosition, ySavePosition=ySavePosition, zSavePosition=zSavePosition
                                      )

    
    # create slide of class Sample as part of PlateHolder and add it to PlateHolder
    # get description for plate dimensions and coordinate system from microscopeSpecifications.yml
    slide_name=hardwareSettings.getPref('Slide')
    center=[float(hardwareSettings.getPref('xCenterSlide')),\
            float(hardwareSettings.getPref('yCenterSlide')),\
            float(hardwareSettings.getPref('zCenterSlide'))]
    xFlip=int(hardwareSettings.getPref('xFlipSlide'))
    yFlip=int(hardwareSettings.getPref('yFlipSlide'))
    zFlip=int(hardwareSettings.getPref('zFlipSlide'))
    xCorrection=float(hardwareSettings.getPref('xCorrectionSlide'))
    yCorrection=float(hardwareSettings.getPref('yCorrectionSlide'))
    zCorrection=float(hardwareSettings.getPref('zCorrectionSlide'))

    slide_object = samples.Slide(name = slide_name,
                                 plate_holder_object = plate_holder_object,
                                 center = center,
                                 xFlip = xFlip, yFlip = yFlip, zFlip = zFlip,
                                 xCorrection = xCorrection, yCorrection = yCorrection, zCorrection = zCorrection)
    reference_object = samples.Slide(name = 'Reference',
                                 plate_holder_object = slide_object,
                                 center = [0, 0, 0])
    slide_object.set_reference_object(reference_object)
    plate_holder_object.add_slide(slide_object)    
    return plate_holder_object

###########################################################################
#
# Test functions
#
############################################################################    
    
if __name__ == '__main__':
    # get all information about experiment

    try:
        # location of preferences file on Mac
        prefsFile='../GeneralSettings/preferences.yml'
        dirPath='/Users/winfriedw/Documents/Programming/ResultTestImages/'
        barcode='3500000077'
        colonyFile='PipelineData_Celigo.csv'

        colonyPath = '../PlateSpecifications/PipelineData_Celigo.csv'
        # test function setup_microscope
        prefs=preferences.Preferences(prefsFile)
    except:
        # location of preferences file on Zeiss SD 1
        prefsFile='D:\\Winfried\\Production\\GeneralSettings\\preferences_ZSD3_drugScreen_Winfried.yml'
        dirPath='D:\\Winfried\\Production\\'
        barcode='3500000093'
        colonyFile='3500000860_ColonyDATA.csv'
        colonyPath = 'D:\\Winfried\\Production\\Daily\\2017_5_10\\PlateSpecifications\\3500000860_ColonyDATA.csv'

        # test function setup_microscope
        prefs = preferences.Preferences(prefsFile)

    
    microscopeObject = setup_microscope(prefs)
    print 'Microscope Object created'
    print microscopeObject
    
    # test function find_colon_file
#     colonyPrefs = prefs.getPrefAsMeta('AddColonies')
#     colonies=get_colony_data(colonyPrefs, colonyPath)
#     print 'Colony file loaded'
#     print colonies.head()
#     print '_______________________________________________'
    
#     # test function setup_plate
#     plateholderObject=setup_plate(prefs, colonyFile, microscopeObject)
#     print plateholderObject
#     print 'Plate holder with plate, wells and colonies created'
#     print 'Done'

    # test function slide
    plate_holder_bject=setup_slide(prefs, microscopeObject)
    print plate_holder_bject
    print 'Plate holder with slide created'
    print 'Done'
