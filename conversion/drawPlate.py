'''
Draw 96 Well plate.
Colorcode wells based on content.
Get information from yml file.

Created on Jun 28, 2016

@author: winfriedw
'''

# location of preferences file with plate layout
prefsFile='/Users/winfriedw/Documents/Eclipse/Mars_011816/microscopeAutomation/src/PlateLayout_short.yml'

import numpy
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

import string

# import external modules written for microscopeAutomation
# from . import preferences
from . import preferences

def drawLabel(x=0, y=0, text='Hallo World!',align='center'):
    label=plt.text(x, y, text, ha=align, va='center',family='sans-serif', size=20)
    return label

def drawWell(pos, diameter, color):
    '''Draws Well
    
    Input:
     pos: [x,y] position of Well center in mm
     diameter: diameter of Well in mm
     
    Return:
     none
    '''    
    # add a circle
    Well = mpatches.Circle(pos, diameter/2.0, ec="black", fc=color)
    return Well

def drawWells (ax, nCol=12, nRow=8, pitch=9, diameter=6.94, prefs=None):
    '''Draw plate wells based on content
    
    Input:
     nCol: number of columns, labeled from 1 to nCol
     nRow: number of rows, labeled alphabetically
     pitch: distance between individual wells in mm
     diameter: diameter of Well in mm
    Return:
     patches
    '''
    # create nCol x nRow grid to plot the wells with distance pitch
    # with additional column and row for labels
    grid = numpy.mgrid[0:nRow, 0:nCol].reshape(2, -1).T
    
    # get information about Well content
    if prefs is None:
        row=[]
        wells=[]
        for i in range(nCol):
            row.append('empty')
        for j in range(nRow):
            wells.append(row)
    else:
        wells=prefs.getPref('wells')
        
    # draw wells
    for row, col in grid:
        wellContent=wells[row][col]
        x=(col+1)*pitch+pitch/2.0
        y=(nRow-row)*pitch+pitch/2.0
        if prefs is None:
            color='white'
        else:
            color=prefs.getPref(wellContent)['color']
        ax.add_patch(drawWell([x, y], diameter, color))


def drawColumnLabels (nRow=8, nCol=12, pitch=9):
    '''Draw plate wells based on content
    
    Input:
     nCol: number of columns, labeled from 1 to nCol
     pitch: distance between individual wells in mm
    Return:
     none
    '''
    for i in range(1,nCol+1):
        x=i*pitch+pitch/2
        y=(nRow+1)*pitch+pitch/2.0
        drawLabel(x, y, str(i))

    
def drawRowLabels (nRow=8, pitch=9):
    '''Draw plate wells based on content
    
    Input:
     nRow: number of rows, labeled alphabetically
     pitch: distance between individual wells in mm
    Return:
     none
    '''
    for i in range(0,nRow):
        x=pitch/2.0
        y=(nRow-i)*pitch+pitch/2.0
        drawLabel(x, y, string.ascii_uppercase[i])

def drawLegend(ax, nRow, nCol, pitch, prefs):
    '''Draw legend
    
    Input:
     nRow: number of rows, labeled alphabetically
     nCol: number of columns
     pitch: distance between individual wells in mm
     prefs: preferences
    Return:
     none
    '''
    legend=prefs.getPref('legend')
    nLegend=len(legend)
    
#     x=(nCol+1)*pitch
    x=0
    for i in range(0,nLegend):
        y=i
        if legend[i][0]=='title':
            drawLabel(x, y, legend[i][1],'left')
        else:
            color=prefs.getPref(legend[i][1])['color']
            ax.add_patch(drawWell([x, y], 0.6, color=color))
#             drawWell([x, y], diameter, color='black')
            text=prefs.getPref(legend[i][1])['label']
            drawLabel(x+0.8,y,text,'left')

    
  
def drawPlate (nCol=12, nRow=8, pitch=9, diameter=6.94, prefs=None):
    '''Draw plate and label wells based on content
    
    Input:
     nCol: number of columns, labeled from 1 to nCol
     nRow: number of rows, labeled alphabetically
     pitch: distance between individual wells in mm
     diameter: diameter of Well in mm
    Return:
     none
    '''
    ax1 = plt.subplot(121)
    
        
    # draw row and column labels
    drawColumnLabels(nRow, nCol, pitch)
    drawRowLabels(nRow, pitch)    
 
    # draw wells
    drawWells(ax1, nCol, nRow, pitch, diameter, prefs)
    plt.tight_layout()
    plt.axis('equal')
    plt.axis('off')

    if not(prefs is None):
        # draw legend
        ax2 = plt.subplot(122)
        
        drawLegend(ax2, nRow, nCol, pitch, prefs)
        legends=prefs.getPref('legend')
        nLengends=len(legends)
        plt.axis([-1,5,nLengends,-1])
        # create plot
        plt.axis('off')
    
    plt.show()
 
if __name__ == '__main__':
    # draw plate without preferences
    drawPlate(nCol=4, nRow=3, pitch=26, diameter=22.05)
    
    # draw plate with preferences
    prefs=preferences.Preferences(prefsFile)
    nRow=prefs.getPref('Rows') 
    nCol=prefs.getPref('Columns')
    pitch=prefs.getPref('Pitch')
    diameter=prefs.getPref('Diameter')
    drawPlate(nCol, nRow, pitch, diameter, prefs)