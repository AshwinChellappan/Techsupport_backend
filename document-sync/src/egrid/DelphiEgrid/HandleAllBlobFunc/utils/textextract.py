import pandas as pd
import json
from .document import get_mok_fileObject
from .custom_logger import custom_logging


# Get Data/Chunked Data for xlsx
def get_chunks_for_xlsx(FILE_CONTENT):
    mokfileObj = get_mok_fileObject(FILE_CONTENT)
    xlreader = pd.read_excel(mokfileObj,sheet_name=None)
    chunk_list = []
    for i,sheetDf in enumerate(xlreader.values()):
        for row in sheetDf.to_dict(orient="records"):
            custom_logging("Processing row")
            custom_logging(row)
            chunk_list.append(
                {
                    "text":json.dumps(str(row)),
                    "type": "xlsx_row",
                    "page_no":i
                 }
            )
    return chunk_list

# Get Data/Chunked Data for csv
def get_chunks_for_csv(FILE_CONTENT):
    mokfileObj = get_mok_fileObject(FILE_CONTENT)
    csvDf = pd.read_csv(mokfileObj)
    chunk_list = []
    #TODO add column name
    #'Product Family' ,'Model Group' ,'UNSPSC','Model',	'Market Model',	'Item',	'Description','Country Of Origin','List Price','Gross Weight','Item Status'
    csvDf.rename( columns ={'Product Family':'product_famly',
                            'Model Group':'model_group',
                            'Market Model':'market_model',
                            'Country Of Origin':'country_of_origin',
                            'List Price':'list_price',
                            'Item Status':'item_status'}, inplace=True)
    column_list=['product_famly' ,'model_group' ,'Model','market_model','Item','Description','country_of_origin','list_price','item_status']
    csvDf =csvDf[csvDf['country_of_origin'].str.lower()=='us']
    csvDf =csvDf[column_list]
    for row in csvDf.to_dict(orient="records"):
        custom_logging("Processing row")
        custom_logging(row)
        row_dict =  {
                "type": "csv_row",
                "page_no":0
             }
        row_dict.update(row)
        chunk_list.append(
            row_dict
        )
    return chunk_list

# Get Data/Chunked Data for txt
def get_page_map_for_txt_file(FILE_CONTENT):
    mokfileObj = get_mok_fileObject(FILE_CONTENT)
    text = mokfileObj.read().decode()
    page_map = [(0,0,text)]
    return page_map
