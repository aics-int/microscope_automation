'''
Quick tests for formlayout
https://pypi.python.org/pypi/formlayout
Requires PyQt4 or PyQt5, set installed API below

Created on Jun 23, 2016

@author: winfriedw
'''

# select PyQT5 as QT_API
# make sure QT5 is installed on system
import os
os.environ['QT_API']='pyqt5'

from formlayout import fedit

def AutomationMessage(message, action):
    datalist = [('Name', 'Paul'),
                (None, None),
                (None, 'Information:'),
                ('Age', 30),
                ('Sex', [0, 'Male', 'Female']),
                ('Size', 12.1),
                ('Eyes', 'green'),
                ('Married', True),
                ]
    fedit(datalist, title="Describe yourself", comment="This is just an <b>example</b>.")