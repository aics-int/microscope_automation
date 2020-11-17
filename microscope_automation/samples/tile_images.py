import numpy as np
from ..image_AICS import ImageAICS
import os
import logging

# from aicsimagetools.ome_tiff_writer import ome_tiff_writer
from aicsimageio.writers import ome_tiff_writer
import multiprocessing

log = logging.getLogger(__name__)


def tile_images(images, method="stack", output_image=True, image_output_path=None):
    """Restitch tiled images based off of location

    Input:
     images: (list, ImageAICS) images to tile

     method: (string) tiling method to use, currently only method is "stack"

     output_image: (bool) flag to output image

     image_output_path: (string) specified image output path

    Output:
     img: tiled image of type ImageAICS
    """
    func_map = {"stack": _tile_hard_rectangle, "anyShape": _tile_hard_any_shape}
    if not func_map.get(method, None):
        raise ValueError("Not a valid tiling method")
    # copy over all metadata from center image of tile
    tile_meta = images[int(len(images) / 2)].get_meta()
    for img in images:
        image_data = img.get_data()
        if len(image_data.shape) == 2:
            img.data = image_data[:, :, np.newaxis]
    if output_image:
        if image_output_path:
            tile_meta["aics_filePath"] = image_output_path
        else:
            tile_meta["aics_filePath"] = os.path.join(
                os.path.dirname(tile_meta["aics_filePath"]),
                tile_meta["aics_SampleName"] + "_tiled.ome.tif",
            )
    # Now the function returns a list of images & borders
    tiled_image_list = func_map[method](images, tile_meta)
    # borders are needed for segmentation
    tiled_image = tiled_image_list[0]

    if output_image:
        writer = ome_tiff_writer.OmeTiffWriter(
            tile_meta["aics_filePath"], overwrite_file=True
        )
        proc = multiprocessing.Process(
            target=writer.save, args=[np.transpose(tiled_image.get_data(), (2, 0, 1))]
        )
        proc.start()
    return tiled_image_list


def _tile_hard_any_shape(images, tile_metadata):
    """Restitch tiled images. Does not assume overlap of tiles.
    This method should be shape invariant

    Input:
     images: (list, ImageAICS) images to tile

     tile_metadata: (dictionary) metadata to tag to tiled image

    Output:
     img: (ImageAICS) tiled image
    """
    # Get meta list, data list, and position list
    meta_list = [img.get_meta() for img in images]
    data_list = [img.get_data() for img in images]

    # find out how large the final, rectangular image has to be and create empty array
    # find the maximum number of tiles in x and y
    positions_x = set([meta["aics_imageObjectPosX"] for meta in meta_list])
    number_tiles_x = len(positions_x)
    positions_y = set([meta["aics_imageObjectPosY"] for meta in meta_list])
    number_tiles_y = len(positions_y)

    # assume that all tiles have the identical number of pixels, dimensions,
    # and data type
    number_pixels_x, number_pixels_y, dimensions = data_list[0].shape
    dtype = meta_list[0]["Type"]
    container_pixels_x = number_pixels_x * number_tiles_x
    container_pixels_y = number_pixels_y * number_tiles_y
    tiles_container = np.zeros(
        (container_pixels_x, container_pixels_y, dimensions), dtype=dtype
    )

    # calibrate pixel size, assuming that individual tiles are flush to each other
    if number_tiles_x == 1:
        scaling_x = 1
        offset_x = 0
    else:
        scaling_x = (max(positions_x) - min(positions_x)) / (
            number_pixels_x * (number_tiles_x - 1)
        )
        offset_x = min(positions_x) / scaling_x
    if number_tiles_y == 1:
        scaling_y = 1
        offset_y = 0
    else:
        scaling_y = (max(positions_y) - min(positions_y)) / (
            number_pixels_y * (number_tiles_y - 1)
        )
        offset_y = min(positions_y) / scaling_y

    # add tiles to empty image
    image_num = 1
    # Lists to hold the borders - needed for segmentation to find colonies
    x_pos_list = []
    y_pos_list = []
    for image in images:
        image_num = image_num + 1
        xPos = int(image.get_meta("aics_imageObjectPosX") / scaling_x - offset_x)
        yPos = int(image.get_meta("aics_imageObjectPosY") / scaling_y - offset_y)
        # Populate the border dicts
        if xPos not in x_pos_list and xPos != 0:
            x_pos_list.append(xPos)
        if yPos not in y_pos_list and yPos != 0:
            y_pos_list.append(yPos)

        data = image.get_data()
        image_pixels_x, image_pixels_y, _image_pixels_z = data.shape

        # The data coordinates in y are flipped in respect to numpy coordinates
        y_low = min(
            container_pixels_y - yPos, container_pixels_y - yPos - image_pixels_y
        )
        y_high = max(
            container_pixels_y - yPos, container_pixels_y - yPos - image_pixels_y
        )
        tiles_container[xPos : xPos + image_pixels_x, y_low:y_high, :] = data

    return_image = ImageAICS(data=tiles_container, meta=tile_metadata)
    # Returns tiled image plus borders for segmentation if necessary
    return [return_image, x_pos_list, y_pos_list]


def _tile_hard_rectangle(images, tile_metadata):
    """Restitch tiled images given 3x3 array using array stack method.
    Performs as follows:
     from (min x to max x):
      from (min y to max y)
       ims_y.append(im(x,y))
      vstack(ims_y)
      ims_x.append(vstack)
     hstack(ims_x)

    This method assumes the tiles are laid out in a rectangular pattern.

    Input:
     images: (list, ImageAICS) images to tile

     tile_metadata: (dictionary) metadata to tag to tiled image

    Output:
     img: (ImageAICS) tiled image
    """
    # for easier tracking
    X = 0
    Y = 1
    INDEX = 2
    # Borders of the individual tiled images when put together.
    # Might be needed for segmentation later. Only added for consistency here
    x_border_list = []
    y_border_list = []
    # Get meta list, data list, and position list
    meta_list = [img.get_meta() for img in images]
    data_list = [img.get_data() for img in images]
    # the -y is here because the y axis is flipped for colony objects
    # TODO: make this more robust
    pos_list = [
        [meta["aics_imageObjectPosX"], -meta["aics_imageObjectPosY"], ind]
        for ind, meta in enumerate(meta_list)
    ]
    srt = sorted(pos_list, key=lambda m: (m[Y], m[X]))
    hstack_list = []
    i = 0
    while i < len(srt):
        y = int(srt[i][Y])
        img_y = []
        while i < len(srt) and int(srt[i][Y]) == y:
            # Images are YXC format, for accurate tiling this needs to be XYC
            img_y.append(np.transpose(data_list[srt[i][INDEX]], (1, 0, 2)))
            i += 1
        hstack_list.append(np.hstack(img_y))
    vstack = np.vstack(hstack_list)
    return [ImageAICS(data=vstack, meta=tile_metadata), x_border_list, y_border_list]
