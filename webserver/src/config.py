import os
from dotenv import load_dotenv
import openai

load_dotenv()

openai.api_key = os.getenv("AZURE_OPENAI_KEY")
# your endpoint should look like the following https://YOUR_RESOURCE_NAME.openai.azure.com/
openai.api_base = os.getenv("AZURE_OPENAI_ENDPOINT")
openai.api_type = os.getenv("AZURE_OPENAI_API_TYPE")
# This may change in the future
openai.api_version = os.getenv("AZURE_OPENAI_API_VERSION")
# This will correspond to the custom name you chose for your deployment when you deployed a model.
openai.default_deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT")

openai.embedding_model =os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT")
