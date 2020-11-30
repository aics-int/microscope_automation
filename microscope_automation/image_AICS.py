"""
Module with class ImageAICS to wrap image data
as numpy arrays and meta data as dictionaries.
Add display methods
Created on Jul 11, 2016

@author: winfriedw
"""

import matplotlib.pyplot as plt
from tifffile import imsave
import os

# create logger
import logging

logger = logging.getLogger("microscopeAutomation")


class ImageAICS:
    """store and display image data"""

    def __init__(self, data=None, meta=None):
        """create image class

        Input:
         data: numpy array with image data

         meta: dictionary with metadata

        Output:
         none
        """
        self.data = data
        if meta is None:
            self.meta = {}
        else:
            self.meta = meta

    def add_data(self, data):
        """add image data

        Input:
         data: numpy array with image data

        Output:
         none
        """
        self.data = data

    def get_data(self):
        """retrieve image data as numpy array.

        Input:
         none

        Output:
         data: numpy array with image data
        """
        data = self.data
        return data

    def add_meta(self, meta):
        """Add meta data. Use keys as defined in OME-XML.

        Input:
         meta: dictionary with meta data

        Output:
         none
        """
        if meta:
            self.meta.update(meta)

    def get_meta(self, key=None):
        """Retrieve meta data. Use keys as defined in OME-XML.

        Input:
         none

        Output:
         meta: dictionary with meta data
        """
        if key is not None:
            if key not in self.meta.keys():
                return None
            try:
                data = self.meta[key]
            except KeyError:
                print("Error getting data for key {}".format(key))
                raise
            # if data is a number encoded as string convert to float
            if type(data) == str:
                if data.isdigit():
                    value = int(data)
                else:
                    try:
                        value = float(data)
                    except ValueError:
                        value = data
            else:
                value = data
            return value
        else:
            return self.meta

    def parse_file_template(self, template):
        """Create file name based on meta data and template.

        Input:
         template: string with filename

        Output:
         fileName: file name for image
        """
        # get meta data for image
        filename = ""
        if template is None:
            return None
        for element in template:
            if element.startswith("#"):
                # element is name for meta data entry
                metaKey = element[1:]
                metaString = str(self.get_meta(metaKey))
                filename = filename + metaString
            else:
                # element is text
                filename = filename + element

        return os.path.normpath(filename)

    def create_file_name(self, template):
        """Create file name based on meta data and template.

        Input:
         template: string with filename with path for saved image in original format
         or tuple with path to directory and template for file name

        Output:
         filePath: file name and path for image
        """
        # get meta data for image
        filePath = ""

        # is template a tuple of path and filename or is it a file name only?
        if isinstance(template, tuple):
            for pathElement in template:
                if pathElement is None:
                    break
                fileName = self.parse_file_template(pathElement)
                filePath = os.path.join(filePath, fileName)
        else:
            filePath = self.parse_file_template(template)
        if filePath is None:
            return None
        return os.path.normpath(filePath)

    def save_as_tiff(self, path, bits=16):
        """Save data portion of image as .tif file.

        Input:
         path: file path with extension .tif as string

         bits: bit depth of image. Default: 16

        Output:
         none
        """
        data = self.get_data()
        imsave(path, data)
        self.add_meta({"aics_filePath": path})

    def show(self, title="ImageAICS", channel=0, z=0, t=0):
        """display image data

        Input:
         title: string with title for window. Default='ImageAICS'

         channel: channel for display. Default = 0

         z: z slice. Default = 0

         t: time point. Default = 0

        Output:
         none
        """
        fig, axes = plt.subplots(1, 2)
        fig.canvas.set_window_title(title)
        # display only the first slice for multidimensional images
        if self.data.ndim == 2:
            image_slice = self.data
        elif self.data.ndim == 3:
            image_slice = self.data[:, :, channel]
        elif self.data.ndim == 4:
            image_slice = self.data[:, :, channel, z]
        elif self.data.ndim == 5:
            image_slice = self.data[:, :, channel, z, t]
        else:
            logger.error("ImageAICS.show does not support these image dimensions")
        axes[0].imshow(image_slice, aspect="equal", animated=True, cmap="gray")
        i = len(self.meta) - 1
        for key, val in self.meta.items():
            axes[1].text(0, i, key + str(val))
            i -= 1
        plt.show()
