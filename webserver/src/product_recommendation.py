from .config import openai
import os
import re
import requests
import sys
#from num2words import num2words
import os
#import fitz
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from sklearn.metrics.pairwise import cosine_similarity
import ast
import re
from azure.storage.blob import BlobServiceClient
#import tiktoken

script_directory = os.path.dirname(os.path.abspath(__file__))

def get_product_code_url_mapping():
    script_directory = os.path.dirname(os.path.abspath(__file__))
    data_path = os.path.join(script_directory, 'data', 'product_url_map.csv')
    price_list = pd.read_csv(data_path, encoding='utf-8')

    # Rename columns using the rename() function
    price_list.rename(columns={'Variant SKU': 'line_item', 'Variant Metafield: my_fields.website_product_url [url]': 'url'}, inplace=True)

    product_url_mapper = price_list[['line_item', 'url']].copy()
    return product_url_mapper


pdf_folder = '/Users/shimleesengupta/OneDrive - Fortive/Fluke/Pdf/product/'

def get_embedding(text_to_embed):
	# Embed a line of text
	response = openai.Embedding.create(
    	engine= openai.embedding_model,
    	input=[text_to_embed]
	)
	# Extract the AI output embedding as a list of floats
	embedding = response["data"][0]["embedding"]
    
	return embedding

def extract_text_from_pdf(pdf_path):
    #pdf_document = fitz.open(pdf_path)
    pdf_document = [] #just making it dummy
    pdf_filename =os.path.basename(pdf_path)

    title = pdf_filename.replace('_', ':', 1).replace('_', '/').replace('.pdf', '')
    # metadata = pdf_document.metadata
    # title = metadata.get("title", "Title not found")
    text = ""
    for page_number in range(pdf_document.page_count):
        page = pdf_document.load_page(page_number)
        text += page.get_text("text")
    pdf_document.close()
    return title,text
	
def fetch_product_pdf_files():
    data = []
     # Get a list of all PDF files in the folder
    pdf_files = [file for file in os.listdir(pdf_folder) if file.lower().endswith('.pdf')]
    # Read and print the content of each PDF
    for pdf_file in pdf_files:
        pdf_path = os.path.join(pdf_folder, pdf_file)
        pdf_title,pdf_text = extract_text_from_pdf(pdf_path)
        pdf_embedding =get_embedding(pdf_text)
        #print(pdf_text)
        
        # Append data to the list
        data.append({
            'title': pdf_title,
            # 'Text': pdf_text
            'product_embedding': pdf_embedding
        })

    # Create a pandas DataFrame from the extracted data
    df = pd.DataFrame(data)
    return df

def create_sku_mapping(grouped: pd.DataFrame):
    # Create a dictionary to hold the mappings
    sku_mapping = {}

    # Iterate through the groups and populate the mapping
    for _, group in grouped.iterrows():
        skus = group['Lineitem sku']
        for sku in skus:
            if sku not in sku_mapping:
                sku_mapping[sku] = set()  # Use a set to store unique values

            # Add other skus in the same group to the set
            other_skus = [s for s in skus if s != sku]
            sku_mapping[sku].update(other_skus)  # Use update to add unique values to the set

    # Convert the dictionary values (sets) to lists
    sku_mapping = {sku: list(other_skus) for sku, other_skus in sku_mapping.items()}

    # Create a DataFrame from the mapping dictionary
    sku_mapping_df = pd.DataFrame(sku_mapping.items(), columns=['line_item', 'cross_sell_lineitem'])

    return sku_mapping_df



def get_product_per_customer_id():
    script_directory = os.path.dirname(os.path.abspath(__file__))
    data_path = os.path.join(script_directory, 'data', 'purchase_order_history.csv')
    purchase_history=  pd.read_csv(data_path, encoding='utf-8')
    purchase_history['Created at'] = pd.to_datetime(purchase_history['Created at'])

    time_interval = timedelta(weeks=1)
    grouped = purchase_history.groupby(['Customer ID', pd.Grouper(key='Created at', freq=time_interval)])['Lineitem sku'].apply(list).reset_index()
    grouped['num_line_item_skus'] = grouped['Lineitem sku'].apply(len)
    sku_mapping =create_sku_mapping(grouped)
    return sku_mapping

# Function to concatenate embeddings
def concatenate_embeddings(emb1, emb2):
    if isinstance(emb1, str) and isinstance(emb2, str):
        return emb1+emb2
    elif isinstance(emb1, str):
        return emb1
    elif isinstance(emb2, str):
        return emb2
    return None  # Handle other cases as NaN

def get_product_and_purchase_embedding():
    product_url_map=get_product_code_url_mapping()
    pdf_embedding = fetch_product_pdf_files()
    embedding_data_path = os.path.join(script_directory, 'data', 'product_embedding.csv')
    pdf_embedding.to_csv(embedding_data_path,index=False)
  
    merged_df = pdf_embedding.merge(product_url_map, left_on='title', right_on='url', how='left')

    sku_map = get_product_per_customer_id()

    sku_map['cross_sell_lineitem_len'] = sku_map['cross_sell_lineitem'].apply(len)
    sku_map['cross_sell_lineitem'].apply(lambda x: print(str(x)))

    sku_map['purchase_embedding'] = sku_map['cross_sell_lineitem'].apply(lambda x: get_embedding(str(x)))

    merged_df['line_item'] = merged_df['line_item'].astype(str)
    sku_map['line_item'] = sku_map['line_item'].astype(int)
    sku_map['line_item'] = sku_map['line_item'].astype(str)

    print("merged df shape ",merged_df.shape)
    print("sku map shape ",sku_map.shape)
    final_df= merged_df.merge(sku_map, on='line_item',how='left')

    final_df['product_embedding'] = final_df['product_embedding'].apply(lambda x: np.array(ast.literal_eval(x), dtype=np.float64))
    final_df['product_embedding'] = final_df['product_embedding'].apply(lambda x: np.nan if not isinstance(x, np.ndarray) else x)

    final_df['purchase_embedding'].fillna(0, inplace=True)

    final_df['purchase_embedding'] = final_df['purchase_embedding'].apply(convert_to_numpy)
    
    final_data_path = os.path.join(script_directory, 'data', 'final_embedding.csv')
    final_df.to_csv(final_data_path,index=False)

# Function to calculate cosine similarity safely
def cosine_similarity_safe(a, b):
    # Ensure a is a NumPy array
    if isinstance(a, np.ndarray):
        a = a.reshape(1, -1)
    else:
        # Handle the case where a is not an array (e.g., a float)
        a = np.array([a]).reshape(1, -1)
    b = b.reshape(1, -1)
    if isinstance(a, np.ndarray) and isinstance(b, np.ndarray):
        if pd.isna(a).any() or pd.isna(b).any():
            return np.nan  # Handle NaN values gracefully
        else:
            return cosine_similarity(a,b)[0][0]
    else :
        print("not ndarray")
        return np.nan

# Define a function to handle the conversion
def convert_to_numpy(x):
    try:
        return np.array(ast.literal_eval(x), dtype=np.float64)
    except (ValueError, SyntaxError):
        return np.nan  # Handle invalid values with NaN


def get_product_recommendation(instructions:str):
    #get user question embedding
    user_intruction_embedding = np.array(get_embedding(instructions))
    print(type(user_intruction_embedding))
    data_type = user_intruction_embedding.dtype
    print(f"user_instruction_embedding is a NumPy ndarray with data type {data_type}")


    #print(user_intruction_embedding)

    #get product and purchase embeddings
    final_data_path = os.path.join(script_directory, 'data', 'final_embedding.csv')
    df= pd.read_csv(final_data_path)

    #df['extended_embedding'] = df['extended_embedding'].apply(parse_embedding_string)

    df['product_embedding'] = df['product_embedding'].apply(lambda x: np.array(ast.literal_eval(x), dtype=np.float64))
    df['product_embedding'] = df['product_embedding'].apply(lambda x: np.nan if not isinstance(x, np.ndarray) else x)

    df['purchase_embedding'].fillna(0, inplace=True)
    # print(df.info())

    df['purchase_embedding'] = df['purchase_embedding'].apply(convert_to_numpy)
    df['product_similarity'] = df.product_embedding.apply(lambda x: cosine_similarity_safe(x,user_intruction_embedding))
    df['purchase_similarity'] = df.purchase_embedding.apply(lambda x: cosine_similarity_safe(x,user_intruction_embedding))



    top_3_products = df.sort_values('product_similarity', ascending=False).head(3)
    top_3_purchases = df.sort_values('purchase_similarity', ascending=False).head(3)


    return top_3_purchases,top_3_products

# Function to parse the string and convert to a NumPy array
def parse_embedding_string(embedding_str):
    # Remove square brackets and split by comma
    values = re.split(r',\s*', embedding_str.strip('[]'))
    # Convert the values to float and create a NumPy array
    return np.array(values, dtype=np.float64)

    
     
# if __name__ == "__main__":

#     #get_product_and_purchase_embedding()
#     query ='What products have features similar to Fluke 2052 Advanced Wire Tracer Kit?'
#     get_product_recommendation(query)
    # final_data_path = os.path.join(script_directory, 'data', 'final_embedding_pre.csv')
    # df= pd.read_csv(final_data_path)

    # embedding1_arrays = df['product_embedding'].values
    # embedding2_arrays = df['purchase_embedding'].values

    # df['extended_embedding'] = [concatenate_embeddings(emb1, emb2) for emb1, emb2 in zip(embedding1_arrays, embedding2_arrays)]
    # final_data_path = os.path.join(script_directory, 'data', 'final_embedding.csv')
    # df.to_csv(final_data_path,index=False)

    # print(df.info())