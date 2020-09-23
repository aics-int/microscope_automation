'''
Connect to and control dummy Microscope.

Created on Jun 9, 2016

@author: winfriedw
'''
# call methods from real connect module as often as possible
from skimage import data
from skimage.external.tifffile import imread
import random

# create logger
import logging
log = logging.getLogger('microscopeAutomation Connect ZenBlue Test')

# import modules from project MicroscopeAutomation
from .load_image_czi import LoadImageCzi
from . import findWellCenter
Microscope='Test'


class ConnectMicroscope():
    '''
    Simulate connection to Microscope
    '''
    def __init__(self):
        '''
        Simulate connection to Microscope
        '''
        # setup logging
        # predefine internal settings
        self.zLoad = None
        self.zWork = None
        log.info('Connected to ZEN')

    def save_image(self, fileName):
        '''save last acquired ImageAICS in original file format using microscope software.

        Input:
         file: file name and path for ImageAICS save

        Does not save anything in this test environment.
        '''
        log.info('save ImageAICS to ' + fileName)

    def load_image(self, image, getMeta=False):
        '''Load image using bioformats and return it a class ImageAICS

        Input:
         image: image object of class ImageAICS. Holds meta data at this moment, no image data.
         getMeta: if true, retrieve meta data from file. Default is False

        Output:
         image: image with data and meta data as ImageAICS class

        Methods ads image and meta data to image.
        Methods forwards call to load image using bioformats.
        This part should be replaced if microscope software file format is not supported by bioformats.
        '''
        # load image
        rz=LoadImageCzi()
        image=rz.load_image(image, getMeta)
#         rz.close()  Do not close Java VM!
        log.info('loaded file ' + image.get_meta('aics_filePath'))
        return image

    def execute_experiment(self, experiment):
        '''Acquire ImageAICS with parameters defined in experiment.
        Image object is stored in self.image

        Input:
         experiment: string with name of experiment as defined within Microscope software

        Return:
         none
        '''

        log.info('acquire ImageAICS using experiment ', experiment)

        if experiment=='ImageFindWellCenter.czexp':
            diameter=2000
            length=512
            r=1000
            phi=0
            self.image=findWellCenter.create_edge_image(diameter, length, r, phi)
        elif experiment=='ImageBarcode.czexp':
            self.image=imread('/Users/winfriedw/Documents/Programming/barcode_1_25x.tif')
        else:
            self.image=data.hubble_deep_field()

    def get_stage_pos(self):
        '''Return current position of Microscope stage.

        Return:
         xPos, yPos: x and y position of stage in micrometer
        '''
        xPos=float(input('Enter x stage position: '))
        yPos=float(input('Enter y stage position: '))
        log.info('actual stage position is ', str(xPos), ', ', str(yPos))
        return xPos, yPos

    def move_stage_to(self, xPos, yPos, load):
        '''Move stage to new postion.

        Input:
         xPos, yPos: new stage position in micrometers.
        '''
        log.info('moved stage to position ', str(xPos), ', ', str(yPos))
        xStage=xPos
        yStage=yPos
        focus = 10
        return xStage, yStage, focus

    def get_focus_pos(self):
        '''Return current position of focus drive.

        Return:
         zPos: position of focus drive in micrometer
        '''
        ## Get current stage position
        zPos = float(input('Enter focus position: '))
        return zPos

    def move_focus_to(self, zPos):
        '''Move focus to new position.

        Input:
         zPos, yPos: new focus position in micrometers.
        '''
        zFocus = zPos

        log.info('moved focus to position ', str(zPos))

        return zFocus

    def set_focus_work_position(self):
        '''retrieve current position and set as work position.

        Input:
         none

        Output:
         z_work: current focus position in mum
        '''
        zWork=self.get_focus_pos()
        self.zWork=zWork

        log.info('Stored current focus position as work position ', str(zWork))

        return zWork

    def set_focus_load_position(self):
        '''retrieve current position and set as load position.

        Input:
         none

        Output:
         zLoad: current focus position in mum
        '''
        zLoad=self.get_focus_pos()
        self.zLoad=zLoad

        log.info('Stored current focus position as load position ', str(zLoad))

        return zLoad

    def move_focus_to_load(self):
        '''Move focus to load position if defined.

        Input:
         zPos, yPos: new focus position in micrometers.
        '''
        # check if load position is defined
        if self.zLoad == None:
            log.error('Load position not defined')
            return None

        # move to load position if defined
        zFocus = self.move_focus_to(self.zLoad)

        log.info('moved focus to load position ', str(zFocus))

        return zFocus

    def move_focus_to_work(self):
        '''Move focus to work position if defined.

        Input:
         zPos, yPos: new focus position in micrometers.
        '''
        # check if load position is defined
        if self.zLoad == None:
            log.error('Work position not defined')
            return None

        # move to load position if defined
        zFocus = self.move_focus_to(self.zWork)

        log.info('moved focus to load position ', str(zFocus))

        return zFocus

    def trigger_pump(self):
        '''Trigger pump

        Input:
         none

        Output:
         none
        '''
        log.info('triggered pump')

    def getPixelSize(self):
        '''Return pixel size for last ImageAICS in mum

        Input:
         none

        Return:
         pixSize: pixel size in mum
        '''
        pixelSize = random.uniform(0.3, 4)
        log.info('actual pixel size is ', str(pixelSize), ' micrometer')
        return pixelSize

    def get_microscope_name(self):
        '''Returns name of the microscope from hardware that is controlled by this class.

         Return:
          Microscope: name of Microscope'''

        name='Test Microscope'
        log.info('This class controls the microscope ', name)
        return name

    def stop(self):
        '''Stop Microscope immediately'''
        log.info('Microscope operation aborted')



if __name__ =='__main__':
    # test class ConnectMicroscope
    from .image_AICS import ImageAICS

    filePath='/home/shailjad/git/microscopeautomation/data/test_data_shailja/' #Changed the path to the local folder
    m=ConnectMicroscope()                               # get instance of type ConnectMicroscope
    print('Microscope name: ', m.get_microscope_name())    # return name of microscope from hardware settings
    print('Pixel size ', m.getPixelSize())               # return pixel size as defined by microscope hardware
    x, y = m.get_stage_pos()                              # retrieve stage position in mum
    print('Stage position x: ', x, 'y: ', y)
    m.move_stage_to(x+10, y+20.5)                         # move stage to specified position in mum

    m.trigger_pump()                                     # trigger pump
    print('Pump triggered')

    m.execute_experiment('test.czexp')                        # acquire test ImageAICS
    m.save_image(filePath+'test.tif')
    imageTest=ImageAICS(meta={'aics_filePath': filePath+'test.tif','aics_SizeX': 1000, 'aics_SizeY': 872})

    image=m.load_image(imageTest, getMeta=False)
    image.show('test.tiff')
    image=m.load_image(imageTest, getMeta=False)
    print(image.meta)
    m.execute_experiment('ImageFindWellCenter.czexp')  # acquire well edge ImageAICS
    imWell=m.save_image(filePath+'ImageFindWellCenter.tif')
    imBarcode=m.execute_experiment('ImageBarcode.czexp')      # acquire barcode ImageAICS
    imBarcode=m.save_image(imBarcode)
