import os
import time
from azure.search.documents.indexes.models import *
from .custom_logger import custom_logging

global verbose
verbose = int(os.getenv("VERBOSE_FLAG"))

global index_name
index_name = os.getenv("AZURE_SEARCH_INDEX")

def create_search_index(search_index_client):
    if os.getenv("VERBOSE_FLAG"):
        custom_logging(
            f"Ensuring search index {os.getenv('AZURE_SEARCH_INDEX')} exists")
    index = SearchIndex(
        name=os.getenv("AZURE_SEARCH_INDEX"),
        fields=[
            SimpleField(
                name="id",
                type="Edm.String",
                key=True),
            SearchableField(
                name="content",
                type="Edm.String",
                analyzer_name="en.microsoft"),
            SimpleField(
                name="content_type",
                type="Edm.String",
                filterable=True
            ),
            SimpleField(
                name="group_ids", 
                type="Collection(Edm.String)", 
                filterable=True
            ),
            SimpleField(
                name="group_names",
                type="Collection(Edm.String)",
                filterable=True
            ),
            SimpleField(
                name="url",
                type="Edm.String",
                filterable=True
            ),
            SimpleField(
                name="category",
                type="Edm.String",
                filterable=True,
                facetable=True),
            SimpleField(
                name="sourcechunk",
                type="Edm.String",
                filterable=True,
                facetable=True),
            SimpleField(
                name="sourcefile",
                type="Edm.String",
                filterable=True,
                facetable=True),
            SimpleField(
                name="token_count",
                type="Edm.Double",
                filterable=True
            ),
            SimpleField(
                name="upload_ts",
                type="Edm.String",
                filterable=True
            ),
            SearchableField(
                name="product_famly",
                type="Edm.String",
                analyzer_name="en.microsoft"),
            SearchableField(
                name="model_group",
                type="Edm.String",
                analyzer_name="en.microsoft"),
            SearchableField(
                name="Model",
                type="Edm.String",
                analyzer_name="en.microsoft"),
            SearchableField(
                name="market_model",
                type="Edm.String",
                analyzer_name="en.microsoft"),
            SearchableField(
                name="Item",
                type="Edm.Double",
                analyzer_name="en.microsoft"),
            SearchableField(
                name="Description",
                type="Edm.String",
                analyzer_name="en.microsoft"),
            SearchableField(
                name="country_of_origin",
                type="Edm.String",
                analyzer_name="en.microsoft"),
            SearchableField(
                name="list_price",
                type="Edm.Double",
                analyzer_name="en.microsoft"),
            SearchableField(
                name="item_status",
                type="Edm.String",
                analyzer_name="en.microsoft")

            ],
        semantic_settings=SemanticSettings(
            configurations=[
                SemanticConfiguration(
                    name='default',
                    prioritized_fields=PrioritizedFields(
                        title_field=None,
                        prioritized_content_fields=[
                            SemanticField(
                                field_name='content')]))]))
    search_index_client.create_or_update_index(index)

def index_sections(filename, sections, search_client):
    if verbose:
        custom_logging(
            f"Indexing sections from '{filename}' into search index '{index_name}'")
    i = 0
    batch = []
    for s in sections:
        batch.append(s)
        i += 1
        if i % 1000 == 0:
            results = search_client.upload_documents(documents=batch)
            succeeded = sum([1 for r in results if r.succeeded])
            if verbose:
                custom_logging(
                    f"\tIndexed {len(results)} sections, {succeeded} succeeded")
            batch = []

    if len(batch) > 0:
        results = search_client.upload_documents(documents=batch)
        succeeded = sum([1 for r in results if r.succeeded])
        if verbose:
            custom_logging(
                f"\tIndexed {len(results)} sections, {succeeded} succeeded")

def remove_from_index(filename, search_client):
    while True:
        filter = None if filename is None else f"sourcefile eq '{os.path.basename(filename)}'"
        r = search_client.search(
            "",
            filter=filter,
            top=1000,
            include_total_count=True)
        if r.get_count() == 0:
            break
        r = search_client.delete_documents(
            documents=[{"id": d["id"]} for d in r])
        if verbose:
            custom_logging(f"\tRemoved {len(r)} sections from index")
        # It can take a few seconds for search results to reflect changes, so
        # wait a bit
        time.sleep(2)
