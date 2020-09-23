:: Author: Matthew Bowden (mattb@alleninstitute.org)
:: This is a workaround for scipy imshow errors on Windows
:: Copy this into a location in the PATH environment variable to allow
::   scipy to properly launch the image viewer
:: Inputs: path to image to be viewed (must be absolute path)
rundll32 "%ProgramFiles%\Windows Photo Viewer\PhotoViewer.dll" %1
