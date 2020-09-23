'''
Use Zeiss Definite Focus 2 for spinning disk
Created on Feb 28, 2017

@author: winfriedw
'''

# try to connect to ZEN blue dll through win32com, otherwise connect to dummy implementation for testing purposes
try:
    import win32com.client as microscopeConnection
except:
    from . import connect_zen_blue_dummy as microscopeConnection


class definiteFocus():
    '''
    Connect to Zeiss Zen Blue software and control definite focus
    '''


    def __init__(self):
        '''
        Connect to Carl Zeiss ZEN blue Python API
        '''
        # Import the ZEN OAD Scripting into Python
        self.Zen = microscopeConnection.GetActiveObject("Zeiss.Micro.Scripting.ZenWrapperLM")

    def live_mode_start(self, experiment = None):
        '''Start live mode of ZEN software.

        Input:
         experiment: name of ZEN experiment (default = None)

        Output:
         liveImage: image of type ZenImage
        '''
        if experiment:
            # get experiment as type ZenExperiment by name
            expClass = self.Zen.Acquisition.Experiments.GetByName(experiment)
            imgLive = self.Zen.Acquisition.StartLive_2(expClass)
        else:
            imgLive = self.Zen.Acquisition.StartLive()

        return imgLive

    def live_mode_stop(self, experiment = None):
        '''Stop live mode of ZEN software.

        Input:
         experiment: name of ZEN experiment (default = None)

        Output:
         none
        '''
        if experiment:
            self.Zen.Acquisition.StopLive_2(experiment)
        else:
            self.Zen.Acquisition.StopLive()

    def find_surface(self):
        '''Find cover slip using Definite Focus 2.

        Input:
         none

        Output:
         z: position of focus drive after find surface
        '''
        # FindSurface always returns None
        try:
            self.Zen.Acquisition.FindSurface()
        except:
            print('Could not find surface')
        z = self.Zen.Devices.Focus.ActualPosition
        return z

    def store_focus(self):
        '''Store actual focus position as offset from coverslip.

        Input:
         none

        Output:
         z: position of focus drive after store focus
        '''
        self.Zen.Acquisition.StoreFocus()
        z = self.Zen.Devices.Focus.ActualPosition
        return z

    def recall_focus(self):
        '''Find stored focus position as offset from coverslip.

        Input:
         none

        Output:
         z: position of focus drive after recall focus
        '''
        self.Zen.Acquisition.RecallFocus()
        z = self.Zen.Devices.Focus.ActualPosition
        return z

    def z_relative_move(self, delta):
        '''Move focus relative to current position.

        Input:
         delta: distance in mum

        Output:
         z: new position of focus drive
        '''

        zStart = self.Zen.Devices.Focus.ActualPosition
        zEndCalc = zStart + delta
        self.Zen.Devices.Focus.MoveTo(zEndCalc)
        z = self.Zen.Devices.Focus.ActualPosition
        return z

    def z_down_relative(self, delta):
        '''Move focus relative to current position away from sample.

        Input:
         delta: absolute distance in mum

        Output:
         z: new position of focus drive
        '''
        z = self.z_relative_move(-delta)
        return z


    def z_up_relative(self, delta):
        '''Move focus relative to current position towards sample.

        Input:
         delta: absolute distance in mum

        Output:
         z: new position of focus drive
        '''
        z = self.z_relative_move(delta)
        return z

    def snap_image(self, experiment):
        '''Snap image with parameters defined in experiment.

        Input:
         experiment: string with name of experiment as defined within Microscope software

        Return:
         none

        Image object is stored in self.image.
        Acquires single image from experiment (e.g. single slice of stack)
        '''
        expClass = self.Zen.Acquisition.Experiments.GetByName(experiment)
        img1a = self.Zen.Acquisition.AcquireImage_3(expClass)
        self.Zen.Application.Documents.Add(img1a)


    def execute_experiment(self, experiment):
        '''Execute experiments with parameters defined in experiment.

        Input:
         experiment: string with name of experiment as defined within Microscope software

        Return:
         none

        Image object is stored in self.image
        Takes all images that are part of experiment (e.g. all slices)
        '''

        # call ZEN API to set experiment
        exp = self.Zen.Acquisition.Experiments.GetByName(experiment)
        self.image = self.Zen.Acquisition.Execute(exp)

if __name__ =='__main__':
    # connect to Zen Blue software
    defFocus = definiteFocus()
    # start live mode
    experiment = 'TestFocus.czexp'
    print(defFocus.live_mode_start(experiment = experiment))

    # test find surface
    print('Focus position for surface: ', defFocus.find_surface())

    # set Definite Focus to fixed distance above bottome of cell
    defFocus.Zen.Application.Pause("Focus on bottom of cell")
    centerDistance = 8.15
    print('Center postion for stack: ', defFocus.z_up_relative(centerDistance))
    print('Focus position after store_focus: ', defFocus.store_focus())

    # move to new positions and acquire z-stacks
    for i in range(1):
        defFocus.live_mode_start()
        defFocus.Zen.Application.Pause("Move sample in xyz to test recall focus")
        cellBottom = defFocus.recall_focus()
        print('Focus position after recall_focus: ', cellBottom)

        # stop live mode after user input
        defFocus.Zen.Application.Pause("Stop live mode and start experiment?")
        defFocus.live_mode_stop()

        # acquire image using experiment
        # for z-stack set up z stack in center tab
        defFocus.execute_experiment(experiment)

    print('Finished module ZeissDefinitFocus2')
