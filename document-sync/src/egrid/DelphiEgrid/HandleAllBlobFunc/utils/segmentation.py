import itertools
import pandas as pd
import nltk
# download punkt package if available
nltk.download('punkt')



#Extracting sentence from a given list of string and returning a list of list where in the inner loop 5 sentences will be coupled together
def para(arg):
    list_sen=nltk.tokenize.sent_tokenize(arg)
    final_list=[]
    if len(list_sen)>5:
        chunked_list = list()
        chunk_size = 5
        for i in range(0, len(list_sen), chunk_size):
            chunked_list.append(list_sen[i:i+chunk_size])
        for x in chunked_list:
            final_list.append("".join(x))
    else: 
        # if less than 5 sentences, return the paragraph
        chunked_list = list()
        chunked_list.append(list_sen)
        # add chunked list to final list
        final_list.append("".join(chunked_list[0]))
    return final_list

def remove_table_tags_from_paragraph(paragraph_text: str):
    # replace start and end table tag 
    paragraph_text = paragraph_text.replace("</table>", "").replace("<table>", "")
    return paragraph_text


def get_paragraphs_and_tables(text: str, table_tag: str="table"):
    """Retrieve mapped chunks of all paragraphs and tables present in pdf document

    Args: 
        text (str): string of full text, with HTML comprehension of tables
        table_tag (str): HTML tag used to parse out paragraphs and tables
    """
    # set tag to table tag in arguments
    tag = table_tag
    test_str = text
    # finding the index of the first occurrence of the opening tag
    start_idx = test_str.find("<" + tag + ">")
    # initializing an empty list to store the extracted strings
    table_res = []
    # extracting the strings between the tags
    while start_idx != -1:
        end_idx = test_str.find("</" + tag + ">", start_idx)
        if end_idx == -1:
            break
        table_res.append(test_str[start_idx+len(tag)+2:end_idx])
        start_idx = test_str.find("<" + tag + ">", end_idx)
    # finding the index of the first occurrence of the opening tag
    start_idx=0
    # initializing an empty list to store the extracted strings
    para_res = []
    # extracting the strings between the tags
    while start_idx != -1:
        end_idx = test_str.find("<" + tag + ">", start_idx)
        if end_idx == -1:
            para_res.append(test_str[start_idx:])
            break
        para_res.append(test_str[start_idx:end_idx])
        start_idx = test_str.find("</" + tag + ">", end_idx)
    
    upd_para=list(map(para,para_res))

    # Bringing together Paragraphs and HTML table in a master list with their types
    overall=[]
    doc_type=[]
    # unpack list of chunk lists into single list
    upd_para_flat = list(itertools.chain(*upd_para))
    # iterate through list of paragraphs
    for paragraph in upd_para_flat:
        para_text = remove_table_tags_from_paragraph(paragraph)
        overall.append(para_text)
        doc_type.append("paragraph")
    # iterate through list of tables
    for table in table_res:
        overall.append(table)
        doc_type.append("table")

    # place into table
    text_df=pd.DataFrame({"text":overall,"type": doc_type})
    chunk_list = text_df.to_dict('records')
    # remove empty fields from dictionary list
    chunk_list = [chunk for chunk in chunk_list if chunk['text']]
    
    return chunk_list
    