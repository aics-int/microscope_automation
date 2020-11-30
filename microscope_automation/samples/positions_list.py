"""
Class to create position lists for tiling and multi-position imaging.
Created on Aug 14, 2017

@author: winfriedw
"""

import numpy
import matplotlib.pyplot as plt
import math

VALID_TILE_TYPE = ["none", "rectangle", "ellipse"]


class CreateTilePositions(object):
    """Create position lists for tiling and multi-position imaging."""

    def __init__(
        self, tile_type="none", tile_number=(2, 2), tile_size=(1, 1), degrees=0
    ):
        """Create position lists for tiling and multi-position imaging.

        Input:
         tile_type: string to describe type of tiling. Allowed values:
          'none': do not tile

          'rectangle': tiles are arranged to form a rectangle

          'ellipse': tiles are arranged to form an ellipse

         tile_number: tuple with number of tiles in x and y direction

         tile_size: tuple with size of tiles in x and y direction

         degrees: Angle the tile field is rotated counterclockwise in degrees

        Output:
         none
        """
        self.set_tile_type(tile_type)
        self.set_tile_number(tile_number)
        self.set_tile_size(tile_size)
        self.set_field_rotation(degrees)

    def set_tile_type(self, tile_type="none"):
        """Set type of tiling.

        Input:
         tile_type: string to describe type of tiling. Allowed values:
          'none': do not tile

          'rectangle': tiles are arranged to form a rectangle

          'ellipse': tiles are arranged to form an ellipse

        Output:
         none
        """
        # TODO: Check that tile type is valid and throw error if not
        self.tile_type = tile_type

    def get_tile_type(self):
        """Return type of tiling.

        Input:
         none

        Output:
         tile_type: string to describe type of tiling. Allowed values:
          'none': do not tile

          'rectangle': tiles are arranged to form a rectangle

          'ellipse': tiles are arranged to form an ellipse

        """
        tile_type = self.tile_type
        return tile_type

    def set_tile_number(self, tile_number=(2, 2)):
        """Set number of tiles in x and y.

        Input:
         tile_number: tuple with number of tiles in x and y direction

        Output:
         none
        """
        self.tile_number = tile_number

    def get_tile_number(self):
        """Return number of tiles in x and y.

        Input:
         none

        Output:
         tile_number: tuple with number of tiles in x and y direction
        """
        tile_number = self.tile_number
        return tile_number

    def set_tile_size(self, tile_size=(1, 1)):
        """Set size of tiles in x and y.

        Input:
         tile_size: tuple with size of tiles in x and y direction

        Output:
         none
        """
        self.tile_size = tile_size

    def get_tile_size(self):
        """Retrieve size of tiles in x and y.

        Input:
         none

        Output:
         tile_size: tuple with size of tiles in x and y direction
        """
        tile_size = self.tile_size
        return tile_size

    def set_field_rotation(self, degrees=0):
        """Set size of tiles in x and y.

        Input:
         degrees: Angle the tile field is rotated counterclockwise in degrees

        Output:
         none
        """
        if degrees is None:
            degrees = 0
        self.field_rotation = degrees

    def get_field_rotation(self):
        """Set size of tiles in x and y.

        Input:
         none

        Output:
         degrees: Angle the tile field is rotated counterclockwise in degrees
        """
        degrees = self.field_rotation
        return degrees

    def create_rectangle(self, nx, ny):
        """Return positions for rectangle with step size of one.

        Input:
         nx, ny: number of tiles in x and y

        Output:
         rect_list: list for rectangle positions, centered around zero
         and with step size of one
        """
        x_array = numpy.arange(-nx / 2.0, nx / 2.0) + 0.5
        y_array = numpy.arange(-ny / 2.0, ny / 2.0) + 0.5
        rect_list = [(x, y, 0) for x in x_array for y in y_array]
        return rect_list

    def create_ellipse(self, nx, ny):
        """Return positions for ellipse with step size of one.

        Input:
         nx, ny: number of tiles in x and y

        Output:
         ellipse_list: list for rectangle positions, centered around zero
         and with step size of one
        """
        # Start with rectangle
        rect_list = self.create_rectangle(nx, ny)
        # delete positions outside of ellipse
        ellipse_list = [
            (x, y, z)
            for (x, y, z) in rect_list
            if x ** 2 / (nx / 2) ** 2 + y ** 2 / (ny / 2) ** 2 <= 1
        ]
        return ellipse_list

    def rotate_pos_list(self, pos_list, degrees):
        """Rotate all coordinates in pos_list counterclockwise
        by angle degree around center = (0, 0, 0).

        Input:
         pos_list: list with (x, y, z) coordinates

         degrees: amount of counterclock rotation around origin in degree

        Output:
         rot_list: list with (x, y, z) coordinates after rotation.
        """
        # convert angle from degrees to radians.
        rad = math.radians(degrees)

        # rotate
        rotate_list = [
            (
                math.cos(rad) * px - math.sin(rad) * py,
                math.sin(rad) * px + math.cos(rad) * py,
                pz,
            )
            for px, py, pz in pos_list
        ]
        return rotate_list

    def get_pos_list(self, center=(0, 0, 0)):
        """Return list with positions.

        Input:
         center: Center position for tiles as tuple (x, y, z)

        Output:
         pos_list: list with tuples (x,y) for tile centers.
        """
        # calculate tile positions for different tile types centered around (0, 0, 0)
        if self.get_tile_type() == "none":
            pos_list = [(0, 0, 0)]
            x_size, y_size = (0, 0)
        elif self.get_tile_type() == "rectangle":
            nx, ny = self.get_tile_number()
            pos_list = self.create_rectangle(nx, ny)
            x_size, y_size = self.get_tile_size()
        elif self.get_tile_type() == "ellipse":
            nx, ny = self.get_tile_number()
            pos_list = self.create_ellipse(nx, ny)
            x_size, y_size = self.get_tile_size()

        # rotate tile field
        if self.get_field_rotation() != 0:
            pos_list = self.rotate_pos_list(pos_list, self.get_field_rotation())
        # multiply with tile size

        pos_list = [(x * x_size, y * y_size, z) for x, y, z in pos_list]
        # add offset
        pos_list = [
            (x + center[0], y + center[1], z + center[2]) for (x, y, z) in pos_list
        ]
        return pos_list

    def show(self, center=(0, 0, 0)):
        """Display positions.

        Input:
         center: Center position for tiles

        Output:
         none
        """
        # create data
        pos_list = self.get_pos_list(center)
        x_pos = [xyz[0] for xyz in pos_list]
        y_pos = [xyz[1] for xyz in pos_list]
        plt.plot(x_pos, y_pos, "bo")
        plt.show()
