'''
Correct background of microscope images.
For information see:
http://imagejdocu.tudor.lu/doku.php?id=howto:working:how_to_correct_background_illumination_in_brightfield_microscopy
https://clouard.users.greyc.fr/Pantheon/experiments/illumination-correction/index-en.html
https://en.wikipedia.org/wiki/Flat-field_correction

Created on 18 Jan 2017

@author: winfriedw
'''
import numpy
import getpass


def FixedPatternCorrection(image, blackReference):
    '''Correct for fixed pattern with black reference image.

    Input:
     image: one channel image to be corrected
     blackReference: correction image acquired with identical exposure settings but camera blocked

    Output:
     correctedImage: image after correction

    Cameras have faulty pixels that show up as a fixed pattern.
    To correct the image we use a reference image acquired under the same
    conditions as the image but with light blocked to reach the camera.
    We subtract the reference image from the image
    '''

    correctedImage = image - blackReference
    # correctedImage[correctedImage < 0] = 0
    # This has been removed because I was improperly enforcing a cutoff value for noise. Per Winfried, negative
    # values are acceptable in background corrected images
    return correctedImage


def IlluminationCorrection(image, blackReference, illuminationReference):
    '''Correct for uneven illumination.

    Input:
     image: one channel image to be corrected
     blackReference: correction image acquired with identical exposure settings but camera blocked
     illuminationReference: correction image acquired without sample (brightfield) or dye solution (fluorescence)

    Output:
     correctedImage: image after correction
    '''
    patternCorrectedImage = FixedPatternCorrection(image, blackReference)
    patternCorrectedIlluminationReference = FixedPatternCorrection(illuminationReference, blackReference)
    correctedImage = patternCorrectedImage / patternCorrectedIlluminationReference
    # correctedImage *= 65535 # prepare for conversion into uint8
    return correctedImage


if __name__ == '__main__':
    # import libraries used for testing only
    import sys
    import matplotlib.pyplot as plt
    from skimage import io
    from . import load_image_czi
    from . import image_AICS

    # define path to test images
    if sys.platform == 'darwin':
        imagePath = '/Users/winfriedw/Documents/ImageProcessing/2017_1_17/Colonies/D5_0001_x0_y0_z0.czi'
        blackReferencePath = '//Users/winfriedw/Documents/ImageProcessing/2017_1_17/References/BlackReferenceTransmitted10x.czi'
        illuminationReferencePath = '//Users/winfriedw/Documents/ImageProcessing/2017_1_17/References/BackgroundTransmitted_10x_mean.tif'
        outputOriginal = '//Users/winfriedw/Documents/ImageProcessing/original.tif'
        outputBlackCorrection = '//Users/winfriedw/Documents/ImageProcessing/blackCorrection.tif'
        outputIlluminationCorrection = '//Users/winfriedw/Documents/ImageProcessing/illuminationCorrection.tif'
    elif getpass.getuser() == 'mattb':
        imagePath = '/home/mattb/git/microscopeautomation/data/test_data_matthew/2017_2_16/Colonies/D7_0010_x0.0_y0.0_z0.czi'
        blackReferencePath = '/home/mattb/git/microscopeautomation/data/test_data_matthew/2017_2_16/References/BlackReferenceTransmitted10x.czi'
        illuminationReferencePath = '/home/mattb/git/microscopeautomation/data/test_data_matthew/2017_2_16/References/BackgroundTransmitted_10x_mean.tif'
        outputOriginal = '/home/mattb/git/microscopeautomation/data/test_data_matthew/background_test/original.tif'
        outputBlackCorrection = '/home/mattb/git/microscopeautomation/data/test_data_matthew/background_test/blackCorrection.tif'
        outputIlluminationCorrection = '/home/mattb/git/microscopeautomation/data/test_data_matthew/background_test/illuminationCorrection.tif'
    else:
        print('Not implemented')
        exit(1)

    # create LoadImage object to read Zeiss . czi images
    image = image_AICS.ImageAICS(meta={'aics_filePath': imagePath})
    blackReference = image_AICS.ImageAICS(meta={'aics_filePath': blackReferencePath})

    rz = load_image_czi.LoadImageCzi()
    image = rz.load_image(image, getMeta=True).get_data()[:, :, 0]
    print('image (min, max)', image.min(), image.max())
    # imgScaled = np.int8((image-image.min())/(image.max()-image.min())*255)
    imgScaled = ((image-image.min())/(image.max()-image.min())*255).astype(dtype=numpy.uint8)
    plt.imshow(imgScaled, cmap='Greys')
    plt.title('Image')
    plt.show()
    io.imsave(outputOriginal, imgScaled)

    blackReference = rz.load_image(blackReference, getMeta=True).get_data()
    print('blackReference (min, max)', blackReference.min(), blackReference.max())
    # imgScaled = np.int8((blackReference-blackReference.min())/(blackReference.max()-blackReference.min())*255)
    imgScaled = (((blackReference-blackReference.min())/(blackReference.max()-blackReference.min())*255)).astype(dtype=numpy.uint8)
    plt.imshow(imgScaled, cmap='Greys')
    plt.title('Black Reference')
    plt.show()

    # kill virtual machine
    rz.close()

    # read tiff images
    illuminationReference = io.imread(illuminationReferencePath)
    plt.imshow(illuminationReference, cmap='Greys')
    plt.title('Illumination Reference')
    plt.show()

    # correct fixed pattern noise
    testPatternCorrection = False
    if testPatternCorrection:
        print('Test fixed pattern correction')
        patternCorrectedImage = FixedPatternCorrection(image, blackReference)
        # imgScaled = np.int8((patternCorrectedImage-patternCorrectedImage.min())/(patternCorrectedImage.max()-patternCorrectedImage.min())*255)
        imgScaled = (((patternCorrectedImage-patternCorrectedImage.min())/(patternCorrectedImage.max()-patternCorrectedImage.min())*255)).astype(dtype=numpy.uint8)
        plt.imshow(imgScaled, cmap='Greys')
        plt.title('Fixed Pattern Corrected Image')
        plt.show()
        io.imsave(outputBlackCorrection, imgScaled)

    # correct uneven illumination
    testIlluminationCorrection = True
    if testIlluminationCorrection:
        illuminationCorrectedImage = IlluminationCorrection(image, blackReference, illuminationReference)
        # imgScaled = np.int8((illuminationCorrectedImage-illuminationCorrectedImage.min())/(illuminationCorrectedImage.max()-illuminationCorrectedImage.min())*255)
        imgScaled = (((illuminationCorrectedImage-illuminationCorrectedImage.min())/(illuminationCorrectedImage.max()-illuminationCorrectedImage.min())*255)).astype(dtype=numpy.uint8)
        plt.imshow(imgScaled, cmap='Greys')
        plt.title('Illumination Corrected Image')
        plt.show()
        io.imsave(outputIlluminationCorrection, imgScaled)

    print('Test correct_background done')
