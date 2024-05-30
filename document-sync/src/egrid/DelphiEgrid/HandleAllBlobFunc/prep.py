import os
from typing import Dict
from dotenv import load_dotenv
#load_dotenv()
from azure.core.credentials import AzureKeyCredential
from azure.storage.blob import BlobServiceClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import *
from azure.search.documents import SearchClient
from azure.ai.formrecognizer import DocumentAnalysisClient
from tiktoken.model import encoding_for_model
from .utils.custom_logger import custom_logging
from .utils.segmentation import get_paragraphs_and_tables
from .utils.document import get_all_text, get_document_text, create_chunk_sections
from .utils.blob import remove_blobs, upload_blobs, download_blob_to_memory
from .utils.search_index import remove_from_index, create_search_index, index_sections
from .utils.cosmos import AzureCosmosDBConnector
from .utils.rolemap import resolve_roles_to_object_ids
from .utils.textextract import get_chunks_for_xlsx,get_chunks_for_csv,get_page_map_for_txt_file


global index_name
index_name = os.getenv("AZURE_SEARCH_INDEX")
global verbose
verbose = int(os.getenv("VERBOSE_FLAG"))
global removeall
removeall = int(os.getenv("REMOVEALL_FLAG"))
global remove
remove = int(os.getenv("REMOVE_FLAG"))
global skipblobs
skipblobs = int(os.getenv("SKIPBLOBS_FLAG"))
global localpdfparser
localpdfparser = int(os.getenv("LOCALPDFPARSER_FLAG"))
global category
category = None
global model_name
model_name = os.getenv("MODEL_NAME")

MS_EVENT_TYPE_MAP = {
    "Microsoft.Storage.BlobDeleted":"delete",
    "Microsoft.Storage.BlobCreated":"create_or_update"
}

def valid_filename(filename:str):
    filename = filename.lower()
    return filename.endswith(".pdf") or filename.endswith(".xlsx") or filename.endswith(".csv") or filename.endswith(".txt")


def docs_chunk_run(event_type: str, filename=None, filename_path=None):

    # flag for delete set if event type is specified
    DELETE_FLAG = MS_EVENT_TYPE_MAP[event_type] == "delete"

    enc = encoding_for_model(model_name=model_name)
    sink_blob_client = BlobServiceClient.from_connection_string(os.getenv("AZURE_SINK_STORAGE_CONNECTION_STRING"))
    source_blob_client = BlobServiceClient.from_connection_string(os.getenv("AZURE_SOURCE_STORAGE_CONNECTION_STRING"))

    # Get the service endpoint and API key from the environment
    search_endpoint = os.getenv("SEARCH_ENDPOINT")
    search_key = os.getenv("SEARCH_API_KEY")
    # Create a searchclient
    search_credential = AzureKeyCredential(search_key)
    search_client = SearchClient(endpoint=search_endpoint,
                                 index_name=index_name,
                                 credential=search_credential)

    # create a search index client
    index_client = SearchIndexClient(endpoint=search_endpoint,
                                     credential=search_credential)

    # If delete all than delete all blobs from sync container and delete all data from cog search index
    if removeall:
        remove_blobs(None, client=sink_blob_client)
        remove_from_index(None, search_client=search_client)
        return None

    # create block
    if not DELETE_FLAG:
        # create document analysis client
        document_analysis_endpoint = os.environ["AZURE_FORM_RECOGNIZER_ENDPOINT"]
        document_analysis_key = os.environ["AZURE_FORM_RECOGNIZER_KEY"]
        document_analysis_key = AzureKeyCredential(document_analysis_key)
        document_analysis_client = DocumentAnalysisClient(
            document_analysis_endpoint, document_analysis_key, headers={
                "x-ms-useragent": "azure-search-chat-demo/1.0.0"})

        # connect to cosmos client for access to group permissions from document tag
        cosmos_db_client = AzureCosmosDBConnector()

        # create search index
        create_search_index(search_index_client=index_client)

        # check for PDF type of file
        if not valid_filename(filename):
            # Exiting the function is the file is not PDF
            custom_logging(f"File {filename} should be a PDF, xlsx or csv ")
            return None

        # download file to memory
        custom_logging(f"Downloading file '{filename}' content to memory ")
        FILE_CONTENT = download_blob_to_memory(filename, client=source_blob_client)
        # if blob is not in source container (set in env) then return none
        if not FILE_CONTENT:
            custom_logging(f"FILE_CONTENT is None, blob not present in source container {os.getenv('AZURE_SOURCE_CONTAINER')}")
            return None
        
        # cosmos DB operations
        # 1. Getting results from cosmos DB
        resultsObj = cosmos_db_client.get_search_results(blobname=filename)

        # 2. Getting sharepoint URL and tags for the file
        custom_logging(f"Getting sharepoint url and tags for  '{filename}' from cosmos DB ")
        sharepointURL,groups = cosmos_db_client.get_url_groups_from_resultsObject(results=resultsObj)
        custom_logging(f"Groups for '{filename}' are {groups} ")
        custom_logging(f"Sharepoint url for '{filename}' is {sharepointURL} ")
        # Getting Groups to Object id Mapping 
        groupsMap = resolve_roles_to_object_ids(groups)
        
        # skip blob upload  
        if not skipblobs:
            upload_blobs(filename,FILE_CONTENT,client=sink_blob_client)

        all_chunks = None
        # If dataset is PDF
        if(filename.lower().endswith(".pdf")):
            # get document text
            page_map = get_document_text(filename, FILE_CONTENT, client=document_analysis_client)
            # get all text that, including cleaning for tabular
            # comprehension done in split_text
            all_cleaned_text = get_all_text(filename=filename, page_map=page_map)
            # do paragraph chunking
            all_chunks = get_paragraphs_and_tables(all_cleaned_text)

        elif(filename.lower().endswith(".txt")):
            # get document text
            page_map = get_page_map_for_txt_file(FILE_CONTENT)
            # get all text that, including cleaning for tabular
            # comprehension done in split_text
            all_cleaned_text = get_all_text(filename=filename, page_map=page_map)
            # do paragraph chunking
            all_chunks = get_paragraphs_and_tables(all_cleaned_text)

        # If dataset is .xlsx
        elif(filename.lower().endswith(".xlsx")):
            all_chunks = get_chunks_for_xlsx(FILE_CONTENT)

        # If dataset is .csv
        elif(filename.lower().endswith(".csv")):
            all_chunks = get_chunks_for_csv(FILE_CONTENT)

        # create chunks from paragraphs
        sections = create_chunk_sections(os.path.basename(filename), all_chunks, enc=enc, groups=groupsMap,url=sharepointURL)
        # send chunks to index
        index_sections(os.path.basename(filename),sections,search_client=search_client)
        custom_logging(f"Document sync completed. Indexed into cog search {index_name}")
        
    # delete block
    else:
        # remove blobs from sink container
        remove_blobs(filename, client=sink_blob_client)
        # remove blobs from search index 
        remove_from_index(filename, search_client=search_client)
        custom_logging(f"Document sync Completed. Deleted from cogsearch {index_name}")
        


if __name__ == "__main__":
    event_type="Microsoft.Storage.BlobDeleted"
    source_blob_client = BlobServiceClient.from_connection_string(os.getenv("AZURE_SOURCE_STORAGE_CONNECTION_STRING"))
    blob_container = source_blob_client.get_container_client(os.getenv("AZURE_SOURCE_CONTAINER"))
    blob_list = ['price_list.csv']#[blob for blob in blob_container.list_blob_names() if "MLOPS" in blob]
    print(blob_list)
    for i, blob_name in enumerate(blob_list):
        print(blob_name)
        chunk_status = docs_chunk_run(event_type=event_type, filename=blob_name)
        print(chunk_status)
    print("complete")
