import math
import numpy
from skimage import filters, util
from scipy import ndimage
from aicsimagetools import CziReader, TifReader, OmeTifWriter


def make_feature_cube(image):
    directions = [0, 45, 90, 135]
    i, j = 0.2, 2
    wavelengths = [i]
    while max(wavelengths) < math.hypot(image.shape[0], image.shape[1]):
        wavelengths.append(i * j)
        j *= 2
    wavelengths.pop() # remove largest
    feat_cube = numpy.empty((image.shape[0], image.shape[1], len(directions) * len(wavelengths)))

    # kernel = np.real(filters.gabor_kernel(0.2, (1./4.)*np.pi, 1, 2, 2))
    kernels = []
    for theta in directions:
        for lambda_ in wavelengths:
            kernel = numpy.real(filters.gabor_kernel(lambda_, theta))
            kernels.append(kernel)

    n_image = util.img_as_float(image)
    for k, kernel in enumerate(kernels):
        feat_cube[:, :, k] = ndimage.convolve(n_image, kernel, mode='wrap')
    # for theta, t in enumerate(directions):
    #     for lambda_, l in enumerate(wavelengths):
    #          feat_cube[:, :, t * len(wavelengths) + l] = np.real(filters.gabor_kernel(lambda_, theta))

    # filtered = ndi.convolve(n_image, kernel, mode='wrap')
    output_dir = "/home/mattb/git/microscopeautomation/data/test_data_matthew/ml_output/"
    writer = OmeTifWriter(output_dir + "kernal.tif", overwrite_file=True)
    writer.save(numpy.transpose(feat_cube.astype(numpy.float32), (2, 0, 1)))
    # writer.save(np.transpose(np.concatenate((n_image[:, :, np.newaxis], filtered[:, :, np.newaxis]), axis=2)
    #                          .astype(np.float32), (2, 0, 1)))


if __name__ == "__main__":
    image_file = "/home/mattb/git/microscopeautomation/data/test_data_matthew/ml_colony_images/colony_0.tif"
    image = TifReader(image_file)
    img_data = image.load()
    make_feature_cube(img_data)
