import os 
import io
import re
import pandas as pd
from PyPDF2 import PdfReader, PdfWriter
from .document import get_mok_fileObject, blob_name_from_file_page
from .custom_logger import custom_logging

global verbose
verbose = int(os.getenv("VERBOSE_FLAG"))

def upload_blobs(filename, content, client):

    blob_container = client.get_container_client(os.getenv("AZURE_SINK_CONTAINER"))
    if not blob_container.exists():
        blob_container.create_container()

    # Create mok file object using io
    mokfileObj = get_mok_fileObject(content)
    getFileExtension = lambda filename: os.path.splitext(filename)[1].lower()
    # if file is PDF split into pages and upload each page as a separate blob
    if getFileExtension(filename) == ".pdf":
        reader = PdfReader(mokfileObj)
        pages = reader.pages
        for i in range(len(pages)):
            blob_name = blob_name_from_file_page(filename, i)
            if verbose:
                custom_logging(f"\tUploading blob for page {i} -> {blob_name}")
            f = io.BytesIO()
            writer = PdfWriter()
            writer.add_page(pages[i])
            writer.write(f)
            f.seek(0)
            blob_container.upload_blob(blob_name, f, overwrite=True)

    # if file is .xlsx split into sheets and upload each sheet as a separate blob
    elif getFileExtension(filename) == ".xlsx":
        xlreader = pd.read_excel(mokfileObj,sheet_name=None)
        custom_logging(f"Sheets present {xlreader.keys()}")
        for i,sheetDf in enumerate(xlreader.values()):
            blob_name = blob_name_from_file_page(filename,i)
            if verbose:
                custom_logging(f"\tUploading blob for sheet no {i} -> {blob_name}")
            f = io.BytesIO()
            sheetDf.to_excel(f)
            f.seek(0)
            blob_container.upload_blob(blob_name, f, overwrite=True)

    # if file is .csv directly upload as a blob
    elif getFileExtension(filename) == ".csv":
        i = 0
        blob_name = blob_name_from_file_page(filename,i)
        if verbose:
            custom_logging(f"\tUploading blob for sheet no {i} -> {blob_name}")
        blob_container.upload_blob(blob_name, mokfileObj, overwrite=True)

    # if file is .txt directly upload as a blob
    elif getFileExtension(filename) == ".txt":
        i = 0
        blob_name = blob_name_from_file_page(filename,i)
        if verbose:
            custom_logging(f"\tUploading blob for sheet no {i} -> {blob_name}")
        blob_container.upload_blob(blob_name, mokfileObj, overwrite=True)

    else:
        blob_name = blob_name_from_file_page(filename)
        # Uploading blob bytes
        blob_container.upload_blob(blob_name, mokfileObj, overwrite=True)

def remove_blobs(filename, client):
    blobs = []
    blob_container = client.get_container_client(os.getenv("AZURE_SINK_CONTAINER"))
    if blob_container.exists():
        if filename is None:
            blobs = blob_container.list_blob_names()
        else:
            prefix,file_extension = os.path.splitext(os.path.basename(filename))
            # Preserve File extension if it is .pdf , .csv, .xlsx or .txt
            if(file_extension not in [".pdf" , ".csv", ".xlsx",".txt"]): file_extension = "pdf"
            else: file_extension = file_extension.lstrip(".")

            blobs = filter(lambda b: re.match(f"{prefix}-\\d+\\.{file_extension}",b),blob_container.list_blob_names(name_starts_with=os.path.splitext(os.path.basename(prefix))[0]))
        for b in blobs:
            if verbose:
                custom_logging(f"\tRemoving blob {b}")
            blob_container.delete_blob(b)
    else:
        # log conditions for blob not existing
        custom_logging("Blobs not present, cancelling removal from sink.")

def download_blob_to_memory(filename, client):
    custom_logging(f"Current Working Directory {os.getcwd()}")
    blob_client = client.get_blob_client(container=os.getenv("AZURE_SOURCE_CONTAINER"),blob=os.path.basename(filename))
    # Downloading blob to memory
    BLOB_EXIST_FLAG = blob_client.exists()
    print("Blob Exists",BLOB_EXIST_FLAG)
    if BLOB_EXIST_FLAG:
        download_stream = blob_client.download_blob()
        FILE_CONTENT = download_stream.readall()
        # custom_logging(f"\nFile content {FILE_CONTENT} \n")
        custom_logging("Download Complete...")
        return FILE_CONTENT
