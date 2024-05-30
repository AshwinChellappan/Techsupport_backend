import os
import json
import logging
import azure.functions as func
from .prep import docs_chunk_run, index_name

def main(event: func.EventGridEvent):
    result = json.dumps({
        'id': event.id,
        'data': event.get_json(),
        'topic': event.topic,
        'subject': event.subject,
        'event_type': event.event_type,
    }, indent=4)

    logging.info('Python EventGrid trigger processed an event: %s', result)
    event_type = event.event_type
    url = event.get_json()['url']
    # get file name of blob
    filename = os.path.basename(url)
    logging.info(f"Catching file {filename} under event type {event_type}")
    docs_chunk_run(event_type=event_type, filename=filename)
    
    
