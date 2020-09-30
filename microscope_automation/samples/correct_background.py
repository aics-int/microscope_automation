'''
Correct background of microscope images.
For information see:
http://imagejdocu.tudor.lu/doku.php?id=howto:working:how_to_correct_background_illumination_in_brightfield_microscopy
https://clouard.users.greyc.fr/Pantheon/experiments/illumination-correction/index-en.html
https://en.wikipedia.org/wiki/Flat-field_correction

Created on 18 Jan 2017

@author: winfriedw
'''  # noqa
import numpy
import getpass


def fixed_pattern_correction(image, black_reference):
    '''Correct for fixed pattern with black reference image.

    Cameras have faulty pixels that show up as a fixed pattern.
    To correct the image we use a reference image acquired under the same
    conditions as the image but with light blocked to reach the camera.
    We subtract the reference image from the image

    Input:
     image: one channel image to be corrected

     black_reference: correction image acquired with identical exposure
     settings but camera blocked

    Output:
     corrected_image: image after correction
    '''

    corrected_image = image - black_reference
    # correctedImage[correctedImage < 0] = 0
    # This has been removed because I was improperly enforcing a cutoff value for noise.
    #  Per Winfried, negative values are acceptable in background corrected images
    return corrected_image


def illumination_correction(image, black_reference, illumination_reference):
    '''Correct for uneven illumination.

    Input:
     image: one channel image to be corrected

     black_reference: correction image acquired with identical exposure settings
     but camera blocked

     illumination_reference: correction image acquired without sample (brightfield)
     or dye solution (fluorescence)

    Output:
     corrected_image: image after correction
    '''
    pattern_corrected_image = fixed_pattern_correction(image, black_reference)
    pattern_corrected_illumination_reference = fixed_pattern_correction(
        illumination_reference, black_reference)
    corrected_image = pattern_corrected_image / pattern_corrected_illumination_reference
    # correctedImage *= 65535 # prepare for conversion into uint8
    return corrected_image


if __name__ == '__main__':
    # import libraries used for testing only
    import sys
    import matplotlib.pyplot as plt
    from skimage import io
    import load_image_czi

    # define path to test images
    if sys.platform == 'darwin':
        imagePath = '/Users/winfriedw/Documents/ImageProcessing/2017_1_17/Colonies/D5_0001_x0_y0_z0.czi'  # noqa
        black_reference_path = '//Users/winfriedw/Documents/ImageProcessing/2017_1_17/References/BlackReferenceTransmitted10x.czi'  # noqa
        illumination_reference_path = '//Users/winfriedw/Documents/ImageProcessing/2017_1_17/References/BackgroundTransmitted_10x_mean.tif'  # noqa
        output_original = '//Users/winfriedw/Documents/ImageProcessing/original.tif'  # noqa
        output_black_correction = '//Users/winfriedw/Documents/ImageProcessing/blackCorrection.tif'  # noqa
        output_illumination_correction = '//Users/winfriedw/Documents/ImageProcessing/illuminationCorrection.tif'  # noqa
    elif getpass.getuser() == 'mattb':
        imagePath = '/home/mattb/git/microscopeautomation/data/test_data_matthew/2017_2_16/Colonies/D7_0010_x0.0_y0.0_z0.czi'  # noqa
        black_reference_path = '/home/mattb/git/microscopeautomation/data/test_data_matthew/2017_2_16/References/BlackReferenceTransmitted10x.czi'  # noqa
        illumination_reference_path = '/home/mattb/git/microscopeautomation/data/test_data_matthew/2017_2_16/References/BackgroundTransmitted_10x_mean.tif'  # noqa
        output_original = '/home/mattb/git/microscopeautomation/data/test_data_matthew/background_test/original.tif'  # noqa
        output_black_correction = '/home/mattb/git/microscopeautomation/data/test_data_matthew/background_test/blackCorrection.tif'  # noqa
        output_illumination_correction = '/home/mattb/git/microscopeautomation/data/test_data_matthew/background_test/illuminationCorrection.tif'  # noqa
    else:
        print('Not implemented')
        exit(1)

    # create LoadImage object to read Zeiss . czi images
    image = load_image_czi.ImageAICS(meta={'aics_filePath': imagePath})
    black_reference = load_image_czi.ImageAICS(
        meta={'aics_filePath': black_reference_path})

    rz = load_image_czi.LoadImageCzi()
    image = rz.load_image(image, getMeta=True).get_data()[:, :, 0]
    print('image (min, max)', image.min(), image.max())
    # imgScaled = np.int8((image-image.min())/(image.max()-image.min())*255)
    img_scaled = ((image - image.min()) / (image.max() - image.min())
                  * 255).astype(dtype=numpy.uint8)
    plt.imshow(img_scaled, cmap='Greys')
    plt.title('Image')
    plt.show()
    io.imsave(output_original, img_scaled)

    black_reference = rz.load_image(black_reference, getMeta=True).get_data()
    print('black_reference (min, max)', black_reference.min(), black_reference.max())
    # imgScaled = np.int8((black_reference-black_reference.min())/(black_reference.max()-black_reference.min())*255)  # noqa
    imgScaled = (((black_reference - black_reference.min())
                  / (black_reference.max() - black_reference.min())
                  * 255)).astype(dtype=numpy.uint8)
    plt.imshow(imgScaled, cmap='Greys')
    plt.title('Black Reference')
    plt.show()

    # kill virtual machine
    rz.close()

    # read tiff images
    illumination_reference = io.imread(illumination_reference_path)
    plt.imshow(illumination_reference, cmap='Greys')
    plt.title('Illumination Reference')
    plt.show()

    # correct fixed pattern noise
    testPatternCorrection = False
    if testPatternCorrection:
        print('Test fixed pattern correction')
        patternCorrectedImage = fixed_pattern_correction(image, black_reference)
        # imgScaled = np.int8((patternCorrectedImage-patternCorrectedImage.min())/(patternCorrectedImage.max()-patternCorrectedImage.min())*255)  # noqa
        imgScaled = (((patternCorrectedImage - patternCorrectedImage.min())
                      / (patternCorrectedImage.max() - patternCorrectedImage.min())
                      * 255)).astype(dtype=numpy.uint8)
        plt.imshow(imgScaled, cmap='Greys')
        plt.title('Fixed Pattern Corrected Image')
        plt.show()
        io.imsave(output_black_correction, imgScaled)

    # correct uneven illumination
    test_illumination_correction = True
    if test_illumination_correction:
        illumination_corrected_image = illumination_correction(image, black_reference,
                                                               illumination_reference)
        # imgScaled = np.int8((illuminationCorrectedImage-illuminationCorrectedImage.min())/(illuminationCorrectedImage.max()-illuminationCorrectedImage.min())*255)  # noqa
        img_scaled = (((illumination_corrected_image
                        - illumination_corrected_image.min())
                       / (illumination_corrected_image.max()
                          - illumination_corrected_image.min())
                       * 255)).astype(dtype=numpy.uint8)
        plt.imshow(img_scaled, cmap='Greys')
        plt.title('Illumination Corrected Image')
        plt.show()
        io.imsave(output_illumination_correction, img_scaled)

    print('Test correct_background done')
