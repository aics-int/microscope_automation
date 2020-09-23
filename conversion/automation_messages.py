'''
Dialog boxes and other messages for Microscope Automation package
Created on Jun 13, 2016
https://docs.python.org/2/library/tkinter.html
https://docs.python.org/2/library/ttk.html
http://www.tkdocs.com/tutorial/index.html
http://effbot.org/tkinterbook/tkinter-dialog-windows.htm

@author: winfriedw
'''

import tkinter
import tkinter.ttk

messageTitle='Microscope Automation'
experiment='Test 1'
Well='B2'

class AutomationStatus:
    '''Show status of automation workflow'''
    
    
    def __init__(self, title=messageTitle):
        self.root=tkinter.Tk()
        self.root.title(messageTitle)
        # use Frame to ensure that theme is used, root is not part of ttk
        mainframe = tkinter.ttk.Frame(self.root, padding="3 3 12 12")
        mainframe.grid(column=0, row=0, sticky=(N, W, E, S))
        # allow grid to expand when window is resized
        mainframe.columnconfigure(0, weight=1)
        mainframe.rowconfigure(0, weight=1)
        
        tkinter.ttk.Label(mainframe, text='Microscope Settings:').grid(column=1, row=1, sticky=W)
        tkinter.ttk.Label(mainframe, text=experiment).grid(column=2, row=1, sticky=W)
        tkinter.ttk.Label(mainframe, text='Well:').grid(column=1, row=2, sticky=W)
        tkinter.ttk.Label(mainframe, text=Well).grid(column=2, row=2, sticky=W)
 #       ttk.Button(mainframe, text="Stop", command=stop).grid(column=1,row=3, sticky=E)
        tkinter.ttk.Button(mainframe, text="Continue", command=exit).grid(column=2,row=3, sticky=W)
        
        for child in mainframe.winfo_children(): child.grid_configure(padx=5, pady=5)
        self.root.bind('<Return>', exit)
        self.root.mainloop()
    
class AutomationMessage:
    '''Show blocking message for automation workflow'''
    
    def setTitle(self, title=messageTitle):
        self.title['text']=title
        
    def __init__(self, message, stop, title=messageTitle):
        self.root=tkinter.Tk()
        self.root.title(messageTitle)
        # use Frame to ensure that theme is used, root is not part of ttk
        mainframe = tkinter.ttk.Frame(self.root, padding="3 3 12 12")
        mainframe.grid(column=0, row=0, sticky=(tkinter.N, tkinter.W, tkinter.E, tkinter.S))
        # allow grid to expand when window is resized
        mainframe.columnconfigure(0, weight=1)
        mainframe.rowconfigure(0, weight=1)
        
        self.root.title=tkinter.ttk.Label(mainframe, text=message).grid(column=1, row=1, sticky=tkinter.W)
        tkinter.ttk.Button(mainframe, text="Stop", command=stop).grid(column=1, row=3, sticky=tkinter.E)
        tkinter.ttk.Button(mainframe, text="Continue", default="active", command=mainframe.quit).grid(column=2, row=3, sticky=tkinter.W)
        
        for child in mainframe.winfo_children(): child.grid_configure(padx=5, pady=5)
        self.root.mainloop()

    
def p():
    print('Stop pressed')

if __name__ == '__main__':
    print('Start')
    ms=AutomationMessage('Test message', p)
    print('After AutomationMessage')
    