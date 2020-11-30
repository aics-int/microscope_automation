"""
Draw 96 Well plate.
Colorcode wells based on content.
Get information from yml file.

Created on Jun 28, 2016

@author: winfriedw
"""
import numpy
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import string


def draw_label(x=0, y=0, text="Hallo World!", align="center"):
    label = plt.text(x, y, text, ha=align, va="center", family="sans-serif", size=20)
    return label


def draw_well(pos, diameter, color):
    """Draws Well

    Input:
     pos: [x,y] position of Well center in mm

     diameter: diameter of Well in mm

    Output:
     none
    """
    # add a circle
    well = mpatches.Circle(pos, diameter / 2.0, ec="black", fc=color)
    return well


def draw_wells(ax, n_col=12, n_row=8, pitch=9, diameter=6.94, prefs=None):
    """Draw plate wells based on content

    Input:
     n_col: number of columns, labeled from 1 to n_col

     n_row: number of rows, labeled alphabetically

     pitch: distance between individual wells in mm

     diameter: diameter of Well in mm

    Output:
     none
    """
    # create n_col x n_row grid to plot the wells with distance pitch
    # with additional column and row for labels
    grid = numpy.mgrid[0:n_row, 0:n_col].reshape(2, -1).T

    # get information about Well content
    if prefs is None:
        row = []
        wells = []
        for i in range(n_col):
            row.append("empty")
        for j in range(n_row):
            wells.append(row)
    else:
        wells = prefs.get_pref("wells")

    # draw wells
    for row, col in grid:
        well_content = wells[row][col]
        x = (col + 1) * pitch + pitch / 2.0
        y = (n_row - row) * pitch + pitch / 2.0
        if prefs is None:
            color = "white"
        else:
            color = prefs.get_pref(well_content)["color"]
        ax.add_patch(draw_well([x, y], diameter, color))


def draw_column_labels(n_row=8, n_col=12, pitch=9):
    """Draw plate wells based on content

    Input:
     n_col: number of columns, labeled from 1 to n_col

     pitch: distance between individual wells in mm

    Output:
     none
    """
    for i in range(1, n_col + 1):
        x = i * pitch + pitch / 2
        y = (n_row + 1) * pitch + pitch / 2.0
        draw_label(x, y, str(i))


def draw_row_labels(n_row=8, pitch=9):
    """Draw plate wells based on content

    Input:
     n_row: number of rows, labeled alphabetically

     pitch: distance between individual wells in mm

    Output:
     none
    """
    for i in range(0, n_row):
        x = pitch / 2.0
        y = (n_row - i) * pitch + pitch / 2.0
        draw_label(x, y, string.ascii_uppercase[i])


def draw_legend(ax, n_row, n_col, pitch, prefs):
    """Draw legend

    Input:
     n_row: number of rows, labeled alphabetically

     n_col: number of columns

     pitch: distance between individual wells in mm

     prefs: preferences

    Output:
     none
    """
    legend = prefs.get_pref("legend")
    n_legend = len(legend)

    # x=(n_col+1)*pitch
    x = 0
    for i in range(0, n_legend):
        y = i
        if legend[i][0] == "title":
            draw_label(x, y, legend[i][1], "left")
        else:
            color = prefs.get_pref(legend[i][1])["color"]
            ax.add_patch(draw_well([x, y], 0.6, color=color))
            # drawWell([x, y], diameter, color='black')
            text = prefs.get_pref(legend[i][1])["label"]
            draw_label(x + 0.8, y, text, "left")


def draw_plate(n_col=12, n_row=8, pitch=9, diameter=6.94, prefs=None):
    """Draw plate and label wells based on content

    Input:
     n_col: number of columns, labeled from 1 to n_col

     n_row: number of rows, labeled alphabetically

     pitch: distance between individual wells in mm

     diameter: diameter of Well in mm

    Output:
     none
    """
    ax1 = plt.subplot(121)

    # draw row and column labels
    draw_column_labels(n_row, n_col, pitch)
    draw_row_labels(n_row, pitch)

    # draw wells
    draw_wells(ax1, n_col, n_row, pitch, diameter, prefs)
    plt.tight_layout()
    plt.axis("equal")
    plt.axis("off")

    if not (prefs is None):
        # draw legend
        ax2 = plt.subplot(122)

        draw_legend(ax2, n_row, n_col, pitch, prefs)
        legends = prefs.get_pref("legend")
        nLengends = len(legends)
        plt.axis([-1, 5, nLengends, -1])
        # create plot
        plt.axis("off")

    plt.show()
