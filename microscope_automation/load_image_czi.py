from aicsimageio import AICSImage


class LoadImageCzi:
    def __init__(self):
        """Create object to read image files using aicsimage

        Input:
         none

        Output:
         none
        """

    def load_image(self, image, get_meta_data):
        """

        :param image: ImageAICS object
        :param get_meta_data: Flag if the user wants the meta data
        :return: ImageAICS object with full pixel data and relevant meta data
        """
        file_path = image.get_meta("aics_filePath")
        importer = AICSImage(file_path)
        # Reason for getting the XY slice and in that order
        # In the current version of the automation software,
        # we are processing only single channel 2D images.
        # When this functionality is extended, it will be added to this file as well.
        # Essentially ImageAICS is a specific use case of aicsimage module
        # (2D single channel czi images)
        # As for the ordering the microscope, camera, stage, and
        # automation software all have their versions of the
        # ordering. This ordering currently works best for image acquisition and tiling.
        image_data = importer.get_image_data("XY")
        image.add_data(image_data)
        if get_meta_data:
            meta = {}
            physical_size = importer.get_physical_pixel_size()
            # Values multiplied by 10e6 to convert from meters to micrometers
            meta["PhysicalSizeX"] = physical_size[0] * 1000000
            meta["PhysicalSizeXUnit"] = "mum"
            meta["PhysicalSizeY"] = physical_size[1] * 1000000
            meta["PhysicalSizeYUnit"] = "mum"
            meta["PhysicalSizeZ"] = 1.0
            if physical_size[2] != 1.0:
                meta["PhysicalSizeZ"] = [physical_size[2]] * 1000000
            meta["PhysicalSizeZUnit"] = "mum"
            channel_size = importer.get_image_data("C").size
            # Test the channel stuff
            for c in range(channel_size):
                meta["Channel_" + str(c)] = "Channel_" + str(c)
            dtype = importer.reader.dtype()
            meta["Type"] = dtype
            image.add_meta(meta)
        return image
