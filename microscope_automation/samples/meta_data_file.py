'''
Write meta data to file.
Created on Oct 17, 2016

@author: winfriedw
'''

import pandas
import datetime


class MetaDataFile():
    '''Class to save meta data associated with samples and images.'''

    def __init__(self, file_path, format='csv'):
        '''Write meta data to .csv file.

        Input:
         file_path: path and name of .csv file. If file does not exist, create new file.

         format: format of output file. At this moment only .csv is supported

        Output:
         none
        '''
        # meta = {el:'' for el in [i.strip() for i in metaHeader.split(',')]}
        # write_csv(meta, filePath)
        if format != 'csv':
            print('Format {} is not supported.'.format(format))
            return
        else:
            self.format = format
        self.file_path = filePath
        self.meta_data = pandas.DataFrame()

    def write_csv(self, meta, file_path):
        '''Write meta data to .csv file.

        Input:
         meta: dictionary with meta data

         file_path: path and name of .csv file. If file does not exist, create new file.

        Output:
         none
        '''
        meta.to_csv(file_path, header=True, mode='w', index_label='IndexRow')

    def write_meta(self, meta):
        '''Write meta data to .csv file.

        Input:
         meta: dictionary or pandas DataFrame with meta data

        Output:
         none
        '''
        # convert meta data to Dataframe if necessary
        if not isinstance(meta, pandas.DataFrame):
            metaRow = pandas.DataFrame.from_dict({1: meta}, orient='index')
        else:
            metaRow = meta

        # Add time stamp
        timeStamp = pandas.DataFrame(
            {'MetaDataSavedDate': datetime.datetime.today().strftime('%m/%d/%Y'),
             'MetaDataSavedTime': datetime.datetime.now().strftime('%H:%M:%S')},
            index=[1])
        metaRow = metaRow.join(timeStamp)
        # Append new data to existing data. We will always write
        # the whole meta data set to disk to ensure that new columns are added
        # and missing meta data entries do not shift the content in the csv file
        self.meta_data = self.meta_data.append(metaRow, ignore_index=True)

        if self.format == 'csv':
            self.write_csv(self.meta_data, self.file_path)
        else:
            print('Format {} not implemented'.format(self.format))

        return self.meta_data


if __name__ == '__main__':
    filePath = '/Users/winfriedw/Documents/Programming/Production/TestMeta.csv'
    # test with wrong format (only csc is implemented
    meta = MetaDataFile(filePath, format='abc')

    # initialize method correctly
    meta = MetaDataFile(filePath, format='csv')

    # create dict with meta data and write to disk
    meta_data = {'Path': 'C:/data', 'SizeY': 512}
    print(meta.write_meta(meta_data))

    # add more data
    meta_data = {'Path': 'C:/data', 'SizeX': 100, 'SizeY': 200}
    print(meta.write_meta(meta_data))

    # add more data
    meta_data = {'Path': 'C:/data', 'SizeX': 300, 'SizeY': 400}
    print(meta.write_meta(meta_data))

    # add more data
    meta_data = {'SizeY': 500}
    print(meta.write_meta(meta_data))

    print('Done testing')
