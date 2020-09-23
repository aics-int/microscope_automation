'''
Check python path and other installation parametre
Created on May 31, 2019

@author: winfriedw
'''

import sys

print('Current Python version:')
print((sys.version + '\n\n'))
print('Current sys.path:')
print(('\n'.join(sys.path)))