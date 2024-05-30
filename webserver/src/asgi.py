import json
import re
import time
import os
from .config import openai
#from config import openai
from fastapi.middleware.cors import CORSMiddleware
from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential
from starlette.middleware.errors import ServerErrorMiddleware
from starlette.requests import Request
from starlette.types import ASGIApp
from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from .auth.auth_handler import get_user_upn_from_token_header
from .auth.auth_handler import get_user_membership_information_from_auth_header
from .auth.auth_handler import get_user_membership_information_from_id_token_header
from .database import save_completion_response, save_chat_rating ,read_chat_history
from .auth.docs import get_search_client
from .intent import get_user_intent
from .product_recommendation import get_product_recommendation
import requests
from nltk.tokenize import sent_tokenize


import logging


async def global_execution_handler(request: Request, exc: Exception) -> ASGIApp:
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content="Unknown Error",
    )

app = FastAPI()

app.add_middleware(
    ServerErrorMiddleware,
    handler=global_execution_handler,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)


@app.post("/v1/chat/ratings")
async def post_ratings_data(data: dict, request: Request):
    """ Posts the chat rating value to the Azure Sql"""
    chatUniqueId = data["chatId"]
    chatRating = data["chatRating"]
    messages = data["messages"]
    print('authorized user:' + get_user_upn_from_token_header(request))
    result = save_chat_rating(
        get_user_upn_from_token_header(request),
        chatUniqueId,
        chatRating,
        messages)

    return result


# def completion_stream( chatId, messages, chat_completion):
#     message = {'role': '', 'content': ''}
#     for chunk in chat_completion:
#         delta = chunk['choices'][0]['delta']
#         if 'role' in delta:
#             message['role'] = delta['role']
#         elif 'content' in delta:
#             message['content'] += delta['content']

#         string = json.dumps(chunk, separators=(',', ':'))
#         string = ''.join(('data: ', string, '\n\n'))
#         yield string

#     yield 'data: [DONE]'

#     messages.append(message)
#     save_completion_response(chatId, messages)

def completion_stream( chatId, messages, chat_completion):
    message = {'role': '', 'content': ''}
    for chunk in chat_completion:
            if len(chunk['choices'])>0:
                delta = chunk['choices'][0]['delta']
                if 'role' in delta:
                    message['role'] = delta['role']
                elif 'content' in delta:
                    message['content'] += delta['content']
               # print("--chunk ",chunk)
                string = json.dumps(chunk, separators=(',', ':'))
                string = ''.join(('data: ', string, '\n\n'))
                yield string 
    yield 'data: [DONE]'

    messages.append(message)
    save_completion_response(chatId, messages)



def search_index(query: str, top: int = 10, filter: str = ""):
    # load authenticated client
    search_client = get_search_client()
    # get results using query text,
    search_results = search_client.search(
        search_text=query, top=top, filter=filter)
    # print full metadata and search
    search_results = list(search_results)
    print(
        f"COGNITIVE SERVICE INDEX RESPONSES ON INDEX {os.getenv('AZURE_SEARCH_INDEX')}:")
    print([result['id'] for result in search_results])
    # collate content into single string
    # document_content = {result['id']:result['content'] for result in search_results}
    # content = " ".join([result['content'] for result in search_results])
    return search_results

# Define a route to handle POST requests

def url_ok(url):
    r = requests.head(url)
    return r.status_code != 404

def update_href_tag(text):
    text = re.sub(r'<a[^>]*>([^<]*)</a>', r'\1', text)

   # Regular expression to match URLs outside of <a> tags
    url_pattern = r'https?://\S+'

    # Regular expression to match <a> tags
    a_tag_pattern = r'<a\s+[^>]*>.*?</a>'

    # Function to add <a> tags around URLs that are not part of an <a> tag
    def add_a_tag(match):
        url = match.group(0)
        if url.endswith(".") or url.endswith(")"):
            url = url[:-1]
        # Check if the URL is already part of an <a> tag
        # if url not in all_url:
        #     return ''
        if ((not re.search(a_tag_pattern, url) ) and url_ok(url=url)):
            return f'<a href="{url}">{url}</a>'
        else:
            return "remove_sentence"

    sentences = sent_tokenize(text)

    sentences_without_urls = [
        re.sub(url_pattern, add_a_tag, sentence)
        for sentence in sentences

    ]

    final_sentence = [sentence for sentence in sentences_without_urls if not "remove_sentence" in sentence]

    recreated_paragraph = ' '.join(final_sentence)
    print("Modified Text:")
    print(recreated_paragraph)

    return recreated_paragraph



@app.post("/v1/chat/completions")
async def post_data(data: dict, request: Request):
    """Posts chat completion and conversation to the Azure Sql"""

    messages = data["messages"]
    instructions = messages[-1]["content"]

    model = data.get("model", openai.default_deployment)

    stream = data.get("stream", False)
    userPrincipalName = get_user_upn_from_token_header(request)
    chatId = data["chatId"]
    print('authorized user:' + str(userPrincipalName))
    print('model:' + model)

    chat_completion = openai.ChatCompletion.create(
        deployment_id=model,
        # model="gpt-3.5-turbo",
        frequency_penalty=data.get("frequency_penalty", 0),
        max_tokens=data.get("max_tokens", None),
        n=data.get("n", 1),  # Number of messages
        presence_penalty=data.get("presence_penalty", 0),
        temperature=data.get("temperature", 1),
        top_p=data.get("top_p", 1),  # Nucleus Sampling
        messages=messages,
        stream=stream,
    )
    if stream:
        compl_gen = completion_stream(
            userPrincipalName, chatId, messages, chat_completion)
        return StreamingResponse(compl_gen)
    else:
        messages.append({
            "role": chat_completion['choices'][0]['message'].role,
            "content": chat_completion['choices'][0]['message'].content
        })
        save_completion_response(userPrincipalName, chatId, messages)
        return JSONResponse(chat_completion)


# Define a route to handle POST requests
@app.post("/v2/chat/completions")
async def post_data(data: dict, request: Request):
    """Posts chat completion utilizing Cog Search for system prompting and persisting conversation to the Azure Sql"""

    messages = data["messages"]
    instructions = messages[-1]["content"]

    siteInfo= data["siteInfo"]
    domain =siteInfo["domain"]

    history_context = f"""Below is a history of the conversation so far, and a new question asked by the user that needs to be answered by searching in a knowledge base about Fluke products.
    If the person has provided a model number, such as BP881, TP88/WWG, FLUKE-STICKYBEAT, C550, or FL-45 EX, that must be a keyword you generate.
    Generate a search query based on the conversation and the new question. 
    Do not include cited source filenames and document names e.g info.txt or doc.pdf in the search query terms.
    Do not include any text inside [] or <<>> in the search query terms."""

    history_system_context = {
                'role': 'system',
                'content': history_context
            }

    search_message=[]
    bot_message=[]
    logging.info("Domain name ::"+domain)

    model = openai.default_deployment

    #appGroups = get_user_membership_information_from_auth_header(request)
    stream = data.get("stream", False)
    #userPrincipalName = get_user_upn_from_token_header(request)
    chatId = data["chatId"]

    history = read_chat_history(chatId=chatId)

    print("history ::", history)

    # set default filter string
    filterString = 'not group_ids/any()'
    #if groups are available, set for security trimming
    # if appGroups:
    #     # construct filter from list of groups
    #     filterString = " ".join(
    #         ["group_ids/any(g: search.in(g, '{}'))".format(','.join(appGroups)), "or", filterString])

    if len(history) == 0:
        
        #call the cognitive search index
        results = search_index(
            query=instructions, top=10, filter=filterString)
        # create list of source content
    else:
      #user message should appear at the end ...add srachquery string
      search_message.append(history_system_context)
      search_message.extend(history[:2])
      search_message.extend(messages)
      print(search_message)
      search_query_response = openai.ChatCompletion.create(
                deployment_id=model,
                # model="gpt-3.5-turbo",
                frequency_penalty=data.get("frequency_penalty", 0),
                max_tokens=data.get("max_tokens", 50),
                n=data.get("n", 1),  # Number of messages
                presence_penalty=data.get("presence_penalty", 0),
                temperature=data.get("temperature", 0.0),
                top_p=data.get("top_p", 1),  # Nucleus Sampling
                messages=search_message,
                stream=False,
            ) 
      search_string= search_query_response['choices'][0]['message']['content'] 
      print("search string :",search_string)
      results = search_index(
            query=search_string, top=5, filter=filterString)

    source_content = []
    all_url=[]
    for result in results:
        # check to see if url is present
        if ("url" in result.keys()):
            if (result["url"] is not None) and (result["url"] != ""):
                url = result["url"]
            else: 
                id = result['sourcefile']
                url = id.replace('_xyz_','?').replace('_', ':', 1).replace('_', '/').replace('.pdf', '')
        else: 
            id =  result['sourcefile']
            url = id.replace('_xyz_','?').replace('_', ':', 1).replace('_', '/').replace('.pdf', '')
        # create template
        template = f"URL: {url} CONTENT: {result['content']} "
        all_url.append(url)
        source_content.append(template)
    # join by newline characters
    search_content = "\n".join(source_content)
    print("search content::",search_content)

    # #get intent of user
    intent = get_user_intent(data=instructions)
    print(instructions)
    print("intent :", intent)
    logging.info("intent :"+ intent)

    if domain =="fcal":
        content = "Please contact the FlukeCal Customer Care Center. You can find relevant contact information at https://us.flukecal.com/about/contact"
    elif domain == "fnet":
        content = "Please contact the Fluke Networks Customer Care Center. You can find your region specific relevant contact information at https://www.flukenetworks.com/contact"
    elif domain == "fpi" :
        content = "Please contact the Fluke Networks Customer Care Center. You can find your region specific relevant contact information at https://www.flukeprocessinstruments.com/en-us/service-and-support"
    else:
        content = "Please contact the Fluke Customer Care Center. You can find relevant contact information at https://www.fluke.com/en-us/support/about-us/contact-us"

    contact =[]
    contact.append("https://us.flukecal.com/about/contact")
    contact.append("https://www.flukenetworks.com/contact")
    contact.append("https://www.flukeprocessinstruments.com/en-us/service-and-support")
    contact.append("https://www.fluke.com/en-us/support/about-us/contact-us")
    contact.append("https://flkext.fluke.com/OA_HTML/jtflogin.jsp")
    contact.append("https://www.fluke.com")
    contact.append("https://us.flukecal.com")
    contact.append("https://www.flukenetworks.com")
    contact.append("https://www.flukeprocessinstruments.com")
    contact.append("https://www.fluke.com/en-us/support/calibration-services")

    all_url.extend(contact)


    if intent.lower() in  {'safety', 'safe','s'}:
        intent_content = f"For questions regarding the safe use of Fluke tools, please refer to your owners manual. You must comply with your employer’s safety standards and obtain necessary training before making electrical measurements.If you need help, {content}"
        # role = 'assistant'
        stream = data.get("stream", False)
        userPrincipalName = get_user_upn_from_token_header(request)
        chatId = data["chatId"]
        # print('authorized user:' + str(userPrincipalName))
        # print('model:' + model)
        chat_completion= {
            "choices": [
                {
                "content_filter_results": {
                    "hate": {
                    "filtered": False,
                    "severity": "safe"
                    },
                    "self_harm": {
                    "filtered": False,
                    "severity": "safe"
                    },
                    "sexual": {
                    "filtered": False,
                    "severity": "safe"
                    },
                    "violence": {
                    "filtered": False,
                    "severity": "safe"
                    }
                },
                "finish_reason": "stop",
                "index": 0,
                "message": {
                    "content": intent_content,      
                    "role": "assistant"
                }
                }
            ],
            "created": 1694151829,
            "id": "chatcmpl-7wOZRdYcyrq9cJNu8wiY1qMV8xlLv",
            "model": "gpt-35-turbo-16k",
            "object": "chat.completion",
            "prompt_annotations": [
                {
                "content_filter_results": {
                    "hate": {
                    "filtered": False,
                    "severity": "safe"
                    },
                    "self_harm": {
                    "filtered": False,
                    "severity": "safe"
                    },
                    "sexual": {
                    "filtered": False,
                    "severity": "safe"
                    },
                    "violence": {
                    "filtered": False,
                    "severity": "safe"
                    }
                },
                "prompt_index": 0
                }
            ],
            "usage": {
                "completion_tokens": None,  #Hard coded , care to be taken in case it is getting used.
                "prompt_tokens": None,  #Hard coded , care to be taken in case it is getting used.
                "total_tokens": None   #Hard coded , care to be taken in case it is getting used.
            }
            }

    elif intent.lower() in  {'legal', 'spam', 'competitors','compet','sanctioned','compliance','infringement','violation','confidential','personal','conf','hr', 'discounts','unrelated','unrelat'}:
        intent_content = f"I'm Sorry, I can't seem to answer that question.  I'm always learning and will be able to answer more questions in the future.  In the meantime, if you need support for this question, {content}"
        # role = 'assistant'
        stream = data.get("stream", False)
        userPrincipalName = get_user_upn_from_token_header(request)
        chatId = data["chatId"]
        # print('authorized user:' + str(userPrincipalName))
        # print('model:' + model)
        chat_completion= {
            "choices": [
                {
                "content_filter_results": {
                    "hate": {
                    "filtered": False,
                    "severity": "safe"
                    },
                    "self_harm": {
                    "filtered": False,
                    "severity": "safe"
                    },
                    "sexual": {
                    "filtered": False,
                    "severity": "safe"
                    },
                    "violence": {
                    "filtered": False,
                    "severity": "safe"
                    }
                },
                "finish_reason": "stop",
                "index": 0,
                "message": {
                    "content": intent_content,      
                    "role": "assistant"
                }
                }
            ],
            "created": 1694151829,
            "id": "chatcmpl-7wOZRdYcyrq9cJNu8wiY1qMV8xlLv",
            "model": "gpt-35-turbo-16k",
            "object": "chat.completion",
            "prompt_annotations": [
                {
                "content_filter_results": {
                    "hate": {
                    "filtered": False,
                    "severity": "safe"
                    },
                    "self_harm": {
                    "filtered": False,
                    "severity": "safe"
                    },
                    "sexual": {
                    "filtered": False,
                    "severity": "safe"
                    },
                    "violence": {
                    "filtered": False,
                    "severity": "safe"
                    }
                },
                "prompt_index": 0
                }
            ],
            "usage": {
                "completion_tokens": None,  #Hard coded , care to be taken in case it is getting used.
                "prompt_tokens": None,  #Hard coded , care to be taken in case it is getting used.
                "total_tokens": None   #Hard coded , care to be taken in case it is getting used.
            }
            }
    elif intent.lower() in  {'contact'}:
        #TODO  add incoming website name and change the response
        #expected domain names -fluke, fnet, fcal, fpi
        intent_content = f"I'm Sorry, I can't seem to answer that question.  I'm always learning and will be able to answer more questions in the future.  In the meantime, if you need support for this question, {content}"
        # role = 'assistant'
        stream = data.get("stream", False)
        userPrincipalName = get_user_upn_from_token_header(request)
        chatId = data["chatId"]
        # print('authorized user:' + str(userPrincipalName))
        # print('model:' + model)
        chat_completion= {
            "choices": [
                {
                "content_filter_results": {
                    "hate": {
                    "filtered": False,
                    "severity": "safe"
                    },
                    "self_harm": {
                    "filtered": False,
                    "severity": "safe"
                    },
                    "sexual": {
                    "filtered": False,
                    "severity": "safe"
                    },
                    "violence": {
                    "filtered": False,
                    "severity": "safe"
                    }
                },
                "finish_reason": "stop",
                "index": 0,
                "message": {
                    "content": intent_content,      
                    "role": "assistant"
                }
                }
            ],
            "created": 1694151829,
            "id": "chatcmpl-7wOZRdYcyrq9cJNu8wiY1qMV8xlLv",
            "model": "gpt-35-turbo-16k",
            "object": "chat.completion",
            "prompt_annotations": [
                {
                "content_filter_results": {
                    "hate": {
                    "filtered": False,
                    "severity": "safe"
                    },
                    "self_harm": {
                    "filtered": False,
                    "severity": "safe"
                    },
                    "sexual": {
                    "filtered": False,
                    "severity": "safe"
                    },
                    "violence": {
                    "filtered": False,
                    "severity": "safe"
                    }
                },
                "prompt_index": 0
                }
            ],
            "usage": {
                "completion_tokens": None,  #Hard coded , care to be taken in case it is getting used.
                "prompt_tokens": None,  #Hard coded , care to be taken in case it is getting used.
                "total_tokens": None   #Hard coded , care to be taken in case it is getting used.
            }
            }
    elif intent.lower() in  {'warranty','w'}:
        #TODO  add incoming website name and change the response
        #expected domain names -fluke, fnet, fcal, fpi
        intent_content = f"For information about the warranty coverage for Fluke tools, {content}"
        # role = 'assistant'
        stream = data.get("stream", False)
        userPrincipalName = get_user_upn_from_token_header(request)
        chatId = data["chatId"]
        # print('authorized user:' + str(userPrincipalName))
        # print('model:' + model)
        chat_completion= {
            "choices": [
                {
                "content_filter_results": {
                    "hate": {
                    "filtered": False,
                    "severity": "safe"
                    },
                    "self_harm": {
                    "filtered": False,
                    "severity": "safe"
                    },
                    "sexual": {
                    "filtered": False,
                    "severity": "safe"
                    },
                    "violence": {
                    "filtered": False,
                    "severity": "safe"
                    }
                },
                "finish_reason": "stop",
                "index": 0,
                "message": {
                    "content": intent_content,      
                    "role": "assistant"
                }
                }
            ],
            "created": 1694151829,
            "id": "chatcmpl-7wOZRdYcyrq9cJNu8wiY1qMV8xlLv",
            "model": "gpt-35-turbo-16k",
            "object": "chat.completion",
            "prompt_annotations": [
                {
                "content_filter_results": {
                    "hate": {
                    "filtered": False,
                    "severity": "safe"
                    },
                    "self_harm": {
                    "filtered": False,
                    "severity": "safe"
                    },
                    "sexual": {
                    "filtered": False,
                    "severity": "safe"
                    },
                    "violence": {
                    "filtered": False,
                    "severity": "safe"
                    }
                },
                "prompt_index": 0
                }
            ],
            "usage": {
                "completion_tokens": None,  #Hard coded , care to be taken in case it is getting used.
                "prompt_tokens": None,  #Hard coded , care to be taken in case it is getting used.
                "total_tokens": None   #Hard coded , care to be taken in case it is getting used.
            }
            }
    elif intent.lower() in  {'recommendation','recommend'}:

        top_5_purchases, top_5_products = get_product_recommendation(instructions)
        prev_purchases =", ".join([f"{row['title']}" for index, row in top_5_purchases.iterrows()])
        products = ", ".join([f"{row['title']}" for index, row in top_5_products.iterrows()])

        context_template = f"""

            You are a chatbot for Fluke.com.

            Don't justify your answers. Don't give information not mentioned in the CONTEXT INFORMATION.

            Answer the QUESTION from the CONTEXT below only and follow the INSTRUCTIONS.

 

            CONTEXT :

            **************

 
            1. Here is the search context {search_content}.

            2. Here is the list of product URL which match the user's description {products}.

            3. Here is the list pf products purchased URL together with the asked product {prev_purchases}.

 

            **************
 

            INSTRUCTIONS :

            1. Please provide a brief explanation of your recommendations using the CONTEXT provided above.

            2. If answers are not present in the above Context, Generate a message that includes our contact information instead of apologizing give {content}.

            3. Talk like a person, do not just give a list of recommendations.

            4. List the recommendations along with the URL mentioned in the CONTEXT.

           

            """

        system_context = {
                'role': 'system',
                'content': context_template
            }
        
        print(system_context)
        logging.info("context_template :"+ context_template)

        bot_message.append(system_context)
        if history:
            bot_message.extend(history[:2])
        bot_message.extend(messages)
        print(bot_message)

        all_url.extend(products)
        all_url.extend(prev_purchases)

        chat_completion = openai.ChatCompletion.create(
                deployment_id=model,
                # model="gpt-3.5-turbo",
                frequency_penalty=data.get("frequency_penalty", 0),
                max_tokens=data.get("max_tokens", None),
                n=data.get("n", 1),  # Number of messages
                presence_penalty=data.get("presence_penalty", 0),
                temperature=data.get("temperature", 0.0),
                top_p=data.get("top_p", 1),  # Nucleus Sampling
                messages=bot_message,
                stream=stream,
            )  
    elif intent.lower() in  {'price'}:

        context_template = f"""

            You are a chatbot for Fluke.com.

            Don't justify your answers. Don't give information not mentioned in the CONTEXT INFORMATION.

            Answer the QUESTION from the CONTEXT below only and follow the INSTRUCTIONS.

 

            CONTEXT :

            **************

 
            1. Here is the search context {search_content}.
 

            **************
 

            INSTRUCTIONS :

            1. Mandatorily include the URL for each content at the end of the response. List the URL's Seperately.

            2. Always answer assuming the price is area/region independent.
            
            3. If answers are not present in the above Context, Generate a message that includes our contact information instead of apologizing give {content}.

            """

        system_context = {
                'role': 'system',
                'content': context_template
            }
        
        print(system_context)
        logging.info("context_template :"+ context_template)

        bot_message.append(system_context)
        if history:
            bot_message.extend(history[:2])
        instructions = messages[-1]["content"] + " Point to US price"
        #instructions.join("Point to US price")
        messages[-1]["content"] = instructions
        bot_message.extend(messages)
        print(bot_message)

        chat_completion = openai.ChatCompletion.create(
                deployment_id=model,
                # model="gpt-3.5-turbo",
                frequency_penalty=data.get("frequency_penalty", 0),
                max_tokens=data.get("max_tokens", None),
                n=data.get("n", 1),  # Number of messages
                presence_penalty=data.get("presence_penalty", 0),
                temperature=data.get("temperature", 0.0),
                top_p=data.get("top_p", 1),  # Nucleus Sampling
                messages=bot_message,
                stream=stream,
            )  
    
    elif intent.lower() in  {'repair'}:

        context_template = f"""

            You are a chatbot for Fluke.com.

            Don't justify your answers. Don't give information not mentioned in the CONTEXT INFORMATION.

            Answer the QUESTION from the CONTEXT below only and follow the INSTRUCTIONS.

 

            CONTEXT :

            **************

 
            1. Here is the search context {search_content}.
 

            **************
 

            INSTRUCTIONS :

            1. Mandatorily include the URL for each content at the end of the response. List the URL's Seperately.
            
             2. If answers are not present in the above Context, Generate a message to visit below link for service related queries https://www.fluke.com/en-us/support/return-materials-authorization .

            """

        system_context = {
                'role': 'system',
                'content': context_template
            }
        
        print(system_context)
        logging.info("context_template :"+ context_template)

        bot_message.append(system_context)
        if history:
            bot_message.extend(history[:2])
        instructions = messages[-1]["content"]
        #instructions.join("Point to US price")
        messages[-1]["content"] = instructions
        bot_message.extend(messages)
        print(bot_message)

        chat_completion = openai.ChatCompletion.create(
                deployment_id=model,
                # model="gpt-3.5-turbo",
                frequency_penalty=data.get("frequency_penalty", 0),
                max_tokens=data.get("max_tokens", None),
                n=data.get("n", 1),  # Number of messages
                presence_penalty=data.get("presence_penalty", 0),
                temperature=data.get("temperature", 0.0),
                top_p=data.get("top_p", 1),  # Nucleus Sampling
                messages=bot_message,
                stream=stream,
            )
        
    else:
        # create context template
        context_template = f"""

            You are a chatbot for Fluke.com.

            Don't justify your answers. Don't give information not mentioned in the CONTEXT INFORMATION.

            Answer the QUESTION from the CONTEXT below only and follow the INSTRUCTIONS.

 

            CONTEXT :

            **************

 

            {search_content}

 

            **************

 

 

 

 

            QUESTION : {instructions}

 

 

            INSTRUCTIONS :

            1. Mandatorily include the URL for each content at the end of the response. List the URL's Seperately.

            2. If answers are not present in the above Context, Generate a message that includes our contact information instead of apologizing give {content} .

            3. Do not answer any QUESTION which is not related to fluke.com

            4. Answer in Brief with the details from the context and also provide the URL's.

            5. If QUESTION is related to Russia say "I can't answer" and ask them to contact support {content}.

            6. Do not Generate a response that contains any reference URLs that mention Russia or Europe Union . 

            7. If the {intent} is related with 'repair' or 'service' then add this message For RMA queries please visit https://flkext.fluke.com/OA_HTML/jtflogin.jsp 

            8. For tabular information return it as an html table. Do not return markdown format.


            """
            # create system context
        prompt_context = {

            "role": "user",

            "content": "Answer form the information given only. Don't answers anything which is not related to FLUKE or fluke.com"

        }
        system_context = {
                'role': 'system',
                'content': context_template
            }
            # append cog search context to messages
            # log system context to module, derived from cog search
        #print(system_context)
        logging.info("context_template :"+ context_template)
        bot_message.append(prompt_context)
        bot_message.append(system_context)
        if history:
            bot_message.extend(history[:2])
        bot_message.extend(messages)
        print(bot_message)

        chat_completion = openai.ChatCompletion.create(
                deployment_id=model,
                # model="gpt-3.5-turbo",
                frequency_penalty=data.get("frequency_penalty", 0),
                max_tokens=data.get("max_tokens", None),
                n=data.get("n", 1),  # Number of messages
                presence_penalty=data.get("presence_penalty", 0),
                temperature=data.get("temperature", 0.0),
                top_p=data.get("top_p", 1),  # Nucleus Sampling
                messages=bot_message,
                stream=stream,
            )  
    #chat_completion['choices'][0]['message']['content'] =update_href_tag(chat_completion['choices'][0]['message']['content'])

    
    if stream:
        compl_gen = completion_stream(
             chatId, bot_message, chat_completion)
        return StreamingResponse(compl_gen)
    else:
        messages.append({
            "role": chat_completion['choices'][0]['message']['role'],
            "content": chat_completion['choices'][0]['message']['content']
        })
        db_message=[]
        db_message.extend(messages)
        if history:
            db_message.extend(history)
        #db_message_top_8=db_message[:8]
        save_completion_response(chatId, db_message)
        return JSONResponse(chat_completion)


@app.get("/v1/models")
async def list_models():
    """Returns a list of models to get app to work."""
    result = openai.Deployment.list()
    print(result)

    return result


@app.post("/")
async def post_data(data: dict):
    """Basic route for testing the API works"""
    print("Hello World!")
    result = {"message": "Data received", "data": data}
    return result
