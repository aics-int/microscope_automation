import pyqtgraph
from pyqtgraph.Qt import QtGui, QtCore

# from PySide import QtGui, QtCore
import numpy
from aicsimageio import AICSImage
import logging

log = logging.getLogger(__name__)

KEY_ADD_POINTS = "A"
KEY_DELETE_POINTS = "D"
KEY_DELETE_ALL_POINTS = "-"
KEY_FAIL_ACQUISITION = "`"
KEY_UNDO = "\\"
# Different modes of using the interactive tool
ADD_MODE = "add"
DELETE_MODE = "delete"
NEUTRAL_MODE = "neutral"


class KeyPressWindow(pyqtgraph.GraphicsWindow):
    """
    Creating a class to define a custom key press signal
    for selecting modes.
    """

    sigKeyPress = QtCore.pyqtSignal(object)

    def __init__(self, *args, **kwargs):
        super(KeyPressWindow, self).__init__(*args, **kwargs)

    def keyPressEvent(self, ev):
        self.scene().keyPressEvent(ev)
        self.sigKeyPress.emit(ev)


class ImageLocationPicker(object):
    def __init__(
        self,
        image=None,
        location_list=[],
        app=None,
        spot_size=10,
        spot_brush="r",
        spot_symbol="+",
        spot_pen="r",
    ):
        """
        Input:
         image: Image in the form of a numpy array

         location_list: List of tuples in the form of (x,y) coordinates
         of the points selected

         app: QtGui application object initialized in the beginning
         to automation software in microscopeAutomation.py

        Output:
         none
        """
        # flip image to have same orientation than in ZEN software
        self.image = numpy.fliplr(image)

        # ZEN and pyQTgraph have different coordinate origins
        self.location_list = self.flip_coordinates(location_list)
        self.mode = NEUTRAL_MODE
        self.spot_size = spot_size
        self.spot_brush = spot_brush
        self.spot_symbol = spot_symbol
        self.spot_pen = spot_pen
        self.__window = None
        self.__app = app
        self.scatterplot = None
        self.counter = 0
        # Double curly braces ({{}}) in the help string allows for formatting twice,
        # after the single curly braces.
        self.help_string = (
            "Press {} to add points, {} to delete points,"
            " and {} to delete all points."
            "\nPress {} to toggle failed acquisition tag."
            "\n# of Locations Selected = {{}}".format(
                KEY_ADD_POINTS,
                KEY_DELETE_POINTS,
                KEY_DELETE_ALL_POINTS,
                KEY_FAIL_ACQUISITION,
            )
        )
        self.help_text = pyqtgraph.TextItem(
            self.help_string.format(self.counter), color="g"
        )
        self.failed_text = pyqtgraph.TextItem(
            "This image has been failed", color="r", anchor=(-4, 0)
        )
        self._failed_image = False
        self.prev_points = []
        self.text_items = []

    def failed_image(self):
        return self._failed_image

    def flip_coordinates(self, location_list):
        """ZEN has the image origin in the upper left corner,
        QTgraph in the lower left corner.
        This methods transforms coordinates between the two systems.

        Input:
         location_list: List of tuples (or single tuple) in the form of (x,y)
         coordinates to be transformed

        Output:
         flipped_location_list: list with (x, y) tuples after transformation
        """
        xdim, ydim = self.image.shape
        flipped_location_list = []

        # handle single tuple as well as list of tuples
        if isinstance(location_list, tuple):
            location_list = [location_list]
        for location in location_list:
            x_flipped = location[0]
            y_flipped = ydim - location[1]
            flipped_location_list.append((x_flipped, y_flipped))
        return flipped_location_list

    def plot_points(self, window_title):
        """Plots a given list of location on the image, gives the user ability
        to edit them using add and delete modes

        Input:
         window_title: name to give the GUI window

        Output:
         none
        """
        self.__window = QtGui.QMainWindow()
        self.__window.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        # Resizing the window with an aspect ratio to support rectangular images
        # throws off the coordinates that the automation software gives to the user,
        # so this is hard coded to 1100x1100.
        self.__window.resize(1100, 1100)
        view = KeyPressWindow()
        self.__window.setCentralWidget(view)
        self.__window.setWindowTitle(window_title)
        self.__window.show()

        # Function to update the help text on the ui to current self.counter value
        def _display_help_text():
            w.removeItem(self.help_text)
            self.help_text = pyqtgraph.TextItem(
                self.help_string.format(self.counter), color="g"
            )
            w.addItem(self.help_text)

        # Add image to the plot
        w = view.addPlot()

        def refresh_point_index():
            for numhelp in self.text_items:
                w.removeItem(numhelp)
            self.text_items = []
            for index, location in enumerate(self.location_list):
                point_index = pyqtgraph.TextItem(str(index + 1), color="b")
                # Offset the numbering slightly to be next to the points
                point_index.setPos(location[0] + 10, location[1] + 10)
                self.text_items.append(point_index)
                # Keep track of numbering added to scatterplot to be taken out
                w.addItem(point_index)

        image = pyqtgraph.ImageItem(self.image)
        w.addItem(image)
        w.addItem(self.help_text)
        # Add points to the plot + image
        self.scatterplot = pyqtgraph.ScatterPlotItem(
            size=self.spot_size,
            brush=self.spot_brush,
            symbol=self.spot_symbol,
            pen=self.spot_pen,
        )
        self.scatterplot.addPoints(pos=self.location_list)
        refresh_point_index()
        self.counter = len(self.location_list)
        _display_help_text()
        w.addItem(self.scatterplot)

        # Given user selected points,
        # delete from current list of points and decrement counter.
        def _handle_delete_points(plot, points):
            location_selected = self.round_locations(
                points[0].pos()[0], points[0].pos()[1]
            )
            if location_selected in self.location_list:
                idx = self.location_list.index(location_selected)
                # Delete the point that the user clicked on from the text items array
                w.removeItem(self.text_items[idx])
                del self.text_items[idx]
                self.location_list.remove(location_selected)
            self.scatterplot.setData(pos=self.location_list)
            self.counter = len(self.location_list)
            refresh_point_index()
            _display_help_text()

        # Delete all selected points, and set counter back to zero.
        def _handle_delete_all_points():
            self.prev_points = self.location_list
            # To empty the list, then set counter accordingly
            self.location_list = []
            self.counter = 0
            self.scatterplot.setData(pos=self.location_list)
            _display_help_text()
            refresh_point_index()

        # Given user click event, create a new selected point
        def _handle_plot_point(event):
            if self.failed_image():
                _handle_toggle_fail()

            if self.mode == ADD_MODE:
                pos = w.vb.mapSceneToView(event.scenePos())
                location_selected = self.round_locations(pos.x(), pos.y())
                if location_selected not in self.location_list:
                    self.location_list.append(location_selected)
                    self.scatterplot.setData(pos=self.location_list)
                    point_index = pyqtgraph.TextItem(
                        str(len(self.location_list)), color="b"
                    )
                    point_index.setPos(
                        location_selected[0] + 10, location_selected[1] + 10
                    )
                    w.addItem(point_index)
                    self.text_items.append(point_index)
                    self.counter = len(self.location_list)
                    _display_help_text()

        # Tags this current acquisition as a failed acquisition
        def _handle_toggle_fail():
            # Toggle failed image boolean
            if self._failed_image:
                self._failed_image = False
                w.removeItem(self.failed_text)
            else:
                _handle_delete_all_points()
                self._failed_image = True
                w.addItem(self.failed_text)
            _display_help_text()

        # This function works well for undoing the last "fail"
        # but does not remember beyond that
        def _handle_undo():
            self.location_list = self.prev_points
            self.prev_points = []
            self.counter = len(self.location_list)
            self.scatterplot.setData(pos=self.location_list)
            _handle_toggle_fail()

        # Handle UI Events
        def select_mode(event):
            if event.key() == ord(KEY_DELETE_POINTS):
                self.mode = DELETE_MODE
                self.scatterplot.sigClicked.connect(_handle_delete_points)

            elif event.key() == ord(KEY_ADD_POINTS):
                self.mode = ADD_MODE
                self.scatterplot.scene().sigMouseClicked.connect(_handle_plot_point)

            elif event.key() == ord(KEY_DELETE_ALL_POINTS):
                _handle_delete_all_points()

            elif event.key() == ord(KEY_FAIL_ACQUISITION):
                _handle_toggle_fail()

            elif event.key() == ord(KEY_UNDO):
                _handle_undo()

        view.sigKeyPress.connect(select_mode)
        # if sys.flags.interactive != 1 or not hasattr(QtCore, 'PYQT_VERSION'):
        #     QtGui.QApplication.exec_()
        self.__window.show()
        self.__app.exec_()
        # ZEN and pyQTgraph have different coordinate origins
        self.location_list = self.flip_coordinates(self.location_list)

    def round_locations(self, pos_x, pos_y):
        # Rounding all the locations to four decimal point (arbitrary)
        # Reason - when deleting the points, we need to find if the point
        # selected is in the location list, and the comparison fails
        # if they have different number of digits after the decimal points
        location_selected = (round(pos_x, 4), round(pos_y, 4))
        return location_selected


################################################################################
#
# Test functions
#
################################################################################
def test_ImageLocationPicker(prefs, image_save_path, app, verbose=False):
    """Test location picker on ZEN blue hardware with slide.

    Input:
     prefs: path to experiment preferences
     image_save_path: path to directory to save test images
     app: object of class QtGui.QApplication

    Output:
     None
    """
    # setup microscope
    from . import setup_samples

    microscope_object = setup_samples.setup_microscope(prefs)

    # setup plateholder with slide
    plate_holder_object = setup_samples.setup_slide(
        prefs, microscope_object=microscope_object
    )
    # get slide object, we will need object coordinates for reference correction to work
    slide_object = next(iter(plate_holder_object.get_slides().values()))

    # switch to live mode with 20 x and select position
    microscope_object.live_mode(
        camera_id="Camera1 (back)", experiment="Setup_20x", live=True
    )
    # set position for next experiments
    input("Move to image position")
    images = slide_object.acquire_images(
        "Setup_20x",
        "Camera1 (back)",
        reference_object=slide_object.get_reference_object(),
        file_path=image_save_path + "image1.czi",
        pos_list=None,
        load=False,
        verbose=verbose,
    )

    # Find position of new object
    image = microscope_object.load_image(images[0], get_meta=True)
    image_data = image.get_data()
    if image_data.ndim == 3:
        # Remove the channel dimension before calling the location_picker module
        # Because the module only deals with the XY dimension.
        image_data = image_data[:, :, 0]
    pre_plotted_locations = [(271, 497)]
    interactive_plot = ImageLocationPicker(image_data, pre_plotted_locations, app)
    interactive_plot.plot_points("Well Overview Image")
    location_list = interactive_plot.location_list
    print("Locations clicked = ", location_list)


def test_offline():
    # pyqt = os.path.dirname(PyQt5.__file__)
    # QtGui.QApplication.addLibraryPath(os.path.join(pyqt, "plugins"))
    app = QtGui.QApplication([])
    # Path of test image
    image_path = r"D:\Winfried\Automation\TestFiles\Capture 2_XY1580769716_Z0_T0_C0.tif"
    image = AICSImage(image_path)
    image_data = image.data[0, 0, 0]
    location_list = [(100.0000, 100.0000), (300.0000, 300.0000), (800.0000, 800.0000)]
    example = ImageLocationPicker(image_data, location_list, app)
    example.plot_points("Well Overview Image")


def test_online():
    # import modules used only for testing
    import argparse
    from ..preferences import Preferences
    import pyqtgraph
    from pyqtgraph.Qt import QtGui

    # get path to preferences file
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument("-p", "--preferences", help="path to the preferences file")
    args = arg_parser.parse_args()
    if args.preferences is not None:
        prefs = Preferences(args.preferences)
    else:
        prefs = None

    image_save_path = "D:\\Winfried\\Production\\testing\\"
    #     image_save_path = '/Users/winfriedw/Documents/Programming/ResultTestImages'

    # initialize the pyqt application object here (not in the location picker module)
    # as it only needs to be initialized once
    app = QtGui.QApplication([])
    test_ImageLocationPicker(prefs=prefs, image_save_path=image_save_path, app=app)
    # Properly close pyqtgraph to avoid exit crash
    pyqtgraph.exit()
    print("After exit pyqtgraph")
