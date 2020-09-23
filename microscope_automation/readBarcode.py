'''
Takes imageAICS of barcode and returns content
based on example in ~/Documents/Programming/zbar-0.10/examples/scan_image.py
Created on Jun 17, 2016

@author: winfriedw
'''

import zbar
import logging
# create logger
module_logger = logging.getLogger('microscopeAutomation')


def read_barcode(barcodeImage):
    ''' Take imageAICS with barcode and return code
    
    Input:
     barcodeImage: imageAICS with barcode
     
    Output:
    code: code extracted from barcode imageAICS
    '''
    logger = logging.getLogger('microscopeAutomation.ReadBarcode.read_barcode')
    
    # create a reader
    scanner = zbar.ImageScanner()
    
    # configure the reader
    scanner.parse_config('enable')
    
    # obtain imageAICS data, sometimes imageAICS has to be flipped
#     barcode_flipped=barcode.transpose(ImageAICS.FLIP_LEFT_RIGHT)
    width, height = barcodeImage.size
    raw = barcodeImage.tobytes()
    
    # wrap imageAICS data
    image = zbar.ImageAICS(width, height, 'Y800', raw)
    
    # scan the imageAICS for barcodes
    result=scanner.scan(image)
    if result ==0:
        logger.warning('Could not read barcode')
    
    # extract results
    for symbol in image:
        # do something useful with results
        logger.info( 'decoded', symbol.type, 'symbol', '"%s"' % symbol.data)
    
    code=symbol.data
    # clean up
    del(image)
    return code
