import logging
from pprint import pprint

def custom_logging(msg, use_logger=True):
    if (use_logger):
        #pprint(msg)
        logging.info(msg)
    else:
        pprint(msg)
