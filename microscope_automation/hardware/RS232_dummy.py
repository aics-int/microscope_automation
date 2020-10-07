"""
Dummy functions to replace RS232 for dummy functions
Created on Sep 23, 2016

@author: winfriedw
"""


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
        print("Simulation: Connect to RS232")

    def start_pump(self):
        """Start pump.

        Input:
         none

        Output:
         none
        """
        print("Simulation: Start pump")

    def stop_pump(self):
        """Stop pump.

        Input:
         none

        Output:
         none
        """
        print("Simulation: Stop pump")

    def close_connection(self):
        """Stop pump and close connection.

        Input:
         none

        Output:
         none
        """
        print("Simulation: Stop connection to pump.")
