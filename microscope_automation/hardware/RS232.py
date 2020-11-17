"""
Communicate with RS232 interface
Based on pySerial
Install with pip install pyserial
https://pypi.python.org/pypi/pyserial/2.7
http://pythonhosted.org/pyserial/

Created on Sep 6, 2016

@author: winfriedw
"""
import serial


class Braintree:
    """Control Braintree BS-8000/9000 syringe pump through RS232.
    http://www.braintreesci.com/prodinfo.asp?number=BS-8000
    http://www.braintreesci.com/images/BS8000.pdf
    """

    def __init__(self, port="COM1", baudrate=19200):
        """Opens RS232 connection to syringe pump.

        Input:
         port: com port, default = 'COM1'
         baudrate: baudrate for connection, can be set on pump, typically = 19200

        Output:
         none
        """
        # open serial port
        self.ser = serial.Serial(port=port, baudrate=baudrate)

    def start_pump(self):
        """Start pump.

        Input:
         none

        Output:
         none
        """
        self.ser.write(b"RUN\r")

    def stop_pump(self):
        """Stop pump.

        Input:
         none

        Output:
         none
        """
        self.ser.write(b"STP\r")

    def close_connection(self):
        """Stop pump and close connection.

        Input:
         none

        Output:
         none
        """
        self.stop_pump()
        self.ser.close()
