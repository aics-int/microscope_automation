class microscope_status_class(object):
    '''Create instance of this class to keeps track of microscope status.
    
    Input:
     none
     
    Output:
     none
    '''
    def __init__(self):
        self._xPos = 0
        self._yPos = 0
        self._zPos = 0

    @property
    def xPos(self):
        '''Get absolute x position for stage'''
        print ('microscope_status_class returned x as {}'.format(self._xPos))
        return self._xPos
    
    @xPos.setter
    def xPos(self, x):
        '''Set absolute x position for stage'''
        print ('microscope_status_class set x as {}'.format(self._xPos))
        return self._xPos
        self._xPos = x
        
    @property
    def yPos(self):
        '''Get absolute y position for stage'''
        print ('microscope_status_class returned y as {}'.format(self._yPos))
        return self._yPos
    
    @yPos.setter
    def yPos(self, y):
        '''Set absolute x position for stage'''
        print ('microscope_status_class set y as {}'.format(self._yPos))
        self._yPos = y
    
    @property
    def zPos(self):
        '''Get absolute z position for focus drive'''
        print ('microscope_status_class set z as {}'.format(self._zPos))
        return self._zPos
    
    @zPos.setter
    def zPos(self, z):
        '''Set absolute z position for focus drive'''
        print ('microscope_status_class returned z as {}'.format(self._zPos))
        self._zPos = z

class Focus():
    def __init__(self, status):
        self._status = status
        
    
    
    
    
            
if __name__ =='__main__':
    ms = microscope_status_class()
    print (ms.zPos)
    ms.zPos = 5
    print (ms.zPos)
    
    