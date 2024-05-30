import os
import dotenv
import requests
from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential

# relies upon dotenv compilation for env var imports (currently happens in config.py)
def get_search_client():
    # Get the service endpoint and API key from the environment
    search_endpoint = os.getenv("SEARCH_ENDPOINT")
    search_key = os.getenv("SEARCH_API_KEY")
    index_name = os.getenv("AZURE_SEARCH_INDEX")
    # Create a searchclient
    search_credential = AzureKeyCredential(search_key)
    search_client = SearchClient(endpoint=search_endpoint,
                        index_name=index_name,
                        credential=search_credential)
    return search_client

if __name__=="__main__":
    dotenv.load_dotenv()
    search_client = get_search_client()
    results = search_client.search(search_text="hospitals", top=2)
    content = " ".join([result['content'] for result in results])
    print(content)