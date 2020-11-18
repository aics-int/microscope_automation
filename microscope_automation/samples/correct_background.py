"""
Correct background of microscope images.
For information see:
http://imagejdocu.tudor.lu/doku.php?id=howto:working:how_to_correct_background_illumination_in_brightfield_microscopy
https://clouard.users.greyc.fr/Pantheon/experiments/illumination-correction/index-en.html
https://en.wikipedia.org/wiki/Flat-field_correction

Created on 18 Jan 2017

@author: winfriedw
"""


def fixed_pattern_correction(image, black_reference):
    """Correct for fixed pattern with black reference image.

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
    """
    corrected_image = image - black_reference
    # correctedImage[correctedImage < 0] = 0
    # This has been removed because I was improperly enforcing a cutoff value for noise.
    #  Per Winfried, negative values are acceptable in background corrected images
    return corrected_image


def illumination_correction(image, black_reference, illumination_reference):
    """Correct for uneven illumination.

    Input:
     image: one channel image to be corrected

     black_reference: correction image acquired with identical exposure settings
     but camera blocked

     illumination_reference: correction image acquired without sample (brightfield)
     or dye solution (fluorescence)

    Output:
     corrected_image: image after correction
    """
    pattern_corrected_image = fixed_pattern_correction(image, black_reference)
    pattern_corrected_illumination_reference = fixed_pattern_correction(
        illumination_reference, black_reference
    )
    corrected_image = pattern_corrected_image / pattern_corrected_illumination_reference
    # correctedImage *= 65535 # prepare for conversion into uint8
    return corrected_image
