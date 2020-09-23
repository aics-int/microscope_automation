'''
Write meta data to file.
Created on Oct 17, 2016

@author: winfriedw
'''

import pandas
import datetime

class meta_data_file():
    '''Class to save meta data associated with samples and images.
    '''

    def __init__(self, filePath, format = 'csv'):
        '''Write meta data to .csv file.
        
        Input:
         metaHeader: list with keys for meta data directory
         filePath: path and name of .csv file.
                     If file does not exist, create new file.
         type: format of output file. At this moment only .csv is supported  
                     
        Output:
         none
        '''
#         meta = {el:'' for el in [i.strip() for i in metaHeader.split(',')]}
#         write_csv(meta, filePath)
        if format != 'csv':
            print(('Format {} is not supported.'.format(format)))
            return
        else:
            self.format = format
        self.filePath = filePath
        self.metaData = pandas.DataFrame()
    
    def write_csv(self, meta, filePath):
        '''Write meta data to .csv file.
        
        Input:
         meta: dictionary with meta data
         filePath: path and name of .csv file.
                     If file does not exist, create new file.
                     
        Output:
         none
        '''
        meta.to_csv(filePath, header = True, mode = 'w', index_label = 'IndexRow')
        
             
    def write_meta(self, meta):
        '''Write meta data to .csv file.
        
        Input:
         meta: dictionary or pandas DataFrame with meta data
         filePath: path and name of .csv file.
                     If file does not exist, create new file.
         type: format of output file. At this moment only .csv is supported  
                     
        Output:
         none
        '''
        # convert meta data to Dataframe if necessary
        if not isinstance(meta, pandas.DataFrame):
            metaRow = pandas.DataFrame.from_dict({1: meta}, orient='index')
        else:
            metaRow = meta
        
        # Add time stamp
        timeStamp = pandas.DataFrame({'MetaDataSavedDate': datetime.datetime.today().strftime('%m/%d/%Y'),
                                  'MetaDataSavedTime': datetime.datetime.now().strftime('%H:%M:%S')}, index = [1])
        metaRow = metaRow.join(timeStamp)
        # append new data to existing data
        # We will always write the whole meta data set to disk to ensure that new columns are added 
        # and missing meta data entries do not shift the content in the csv file        
        self.metaData = self.metaData.append(metaRow, ignore_index=True)
            
        if self.format == 'csv':
            self.write_csv(self.metaData, self.filePath)
        else:
            print(('Format {} not implemented'.format(self.format)))

        return self.metaData
    
if __name__ == '__main__':
    filePath = '/Users/winfriedw/Documents/Programming/Production/TestMeta.csv'
    # test with wrong format (only csc is implemented
    meta = meta_data_file(filePath, format ='abc')

    # initialize method correctly
    meta = meta_data_file(filePath, format ='csv')
    
    # create dict with meta data and write to disk
    metaData = {'Path': 'C:/data', 'SizeY': 512}
    print((meta.write_meta(metaData)))

    # add more data  
    metaData = {'Path': 'C:/data', 'SizeX': 100,'SizeY': 200}
    print((meta.write_meta(metaData)))

    # add more data  
    metaData = {'Path': 'C:/data', 'SizeX': 300,'SizeY': 400}
    print((meta.write_meta(metaData)))

    # add more data  
    metaData = {'SizeY': 500}
    print((meta.write_meta(metaData)))
  
    print ('Done testing')