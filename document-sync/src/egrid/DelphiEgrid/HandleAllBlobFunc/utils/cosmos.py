import os 
import dotenv
import logging
from azure.cosmos import CosmosClient


class AzureCosmosDBConnector:
    def __init__(self):
        self.__uri = os.getenv("COSMOS_DB_URI")
        self.__primary_key = os.getenv("COSMOS_DB_PRIMARY_KEY")
        self.__database = os.getenv("COSMOS_DB_DATABASE")
        self.__container = os.getenv("COSMOS_DB_CONTAINER")
        self.__cosmosClient = CosmosClient(self.__uri, self.__primary_key)
        self.__dbClient = self.__cosmosClient.get_database_client(database = self.__database)
        self.__containerClient = self.__dbClient.get_container_client(self.__container)


    def get_search_results(self,blobname='Fort - Delphi.pdf'):
        blobname = os.path.basename(blobname)
        query = f'SELECT * FROM c where c.blobname="{blobname}" ORDER BY c.blobname DESC'
        docs = self.__containerClient.query_items(query=query,enable_cross_partition_query=True) 
        return docs
    
    def get_group_from_resultsObject(self,results:list):

        for result in results:
            groupNames = result.get("assignedroles")
            logging.info(f"Group Result :{result}")
            logging.info(f"GroupNames :{groupNames}")
            if(groupNames):
                return groupNames
        return None

    def get_url_from_resultsObject(self,results:list):

        for result in results:
            docURL = result.get("url")
            logging.info(f"Sharepoint Document URL :{docURL}")
            if(docURL):
                return docURL
        return ""

    def get_url_groups_from_resultsObject(self,results:list):
        docURL = None
        groupNames = None
        for result in results:
            url = result.get("url")
            assignedroles = result.get("assignedroles")
            logging.info(f"Group Result :{result}")
            logging.info(f"GroupNames :{assignedroles}")
            logging.info(f"Sharepoint Document URL :{url}")
            if(url): docURL = url
            if(assignedroles): groupNames = assignedroles
            if(docURL and groupNames): break

        return docURL,groupNames

if __name__=="__main__":
    dotenv.load_dotenv()
    cosmos_db_client = AzureCosmosDBConnector()
    filename="FMS_Main_Deck1.pdf"
    print(filename)
    resultsObj = cosmos_db_client.get_search_results(blobname=filename)
    groups = cosmos_db_client.get_group_from_resultsObject(results=resultsObj)
    resultsObj = cosmos_db_client.get_search_results(blobname=filename)
    url = cosmos_db_client.get_url_from_resultsObject(results=resultsObj)
    print(groups)
    print(url)
    print(list(resultsObj))

    print("Getting URL and groups togather")
    resultsObj = cosmos_db_client.get_search_results(blobname=filename)
    url,groups = cosmos_db_client.get_url_groups_from_resultsObject(results=resultsObj)
    print(groups)
    print(url)
    filename = "Leader's Meeting Template_Aug11.pdf"
    print("Getting URL and groups for ",filename)
    resultsObj = cosmos_db_client.get_search_results(blobname=filename)
    url,groups = cosmos_db_client.get_url_groups_from_resultsObject(results=resultsObj)
    print(groups)
    print(url)
