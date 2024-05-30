import os
import pyodbc, struct
from azure import identity
import json
import traceback
import logging

connection_string = os.environ.get('AZURE_SQL_ODBC_CONNECTIONSTRING')

def save_chat_rating(userPrincipalName, chatUniqueId, rating, messages):
    try:
        with get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute('''
            INSERT INTO [dbo].Ratings
                ([userid]
                ,[chatid]
                ,[chat-history]
                ,[rating])
            VALUES
                (?,
                 ?,
                 ?,
                 ?)
            ''', userPrincipalName, chatUniqueId, json.dumps(messages), rating)
            cursor.commit()
    except:
        tb = traceback.format_exc()
        print("error occurred during insert operation. Stack Trace: " + tb)
        return False
    else:
        tb = "Saved chat rating with chatid=${chatuniqueid} and userid=${userPrincipalName}"
        print(tb)
    return True

def save_completion_response(chatId, completion_response ):
    try:
        # Reason for comment - @amit.gupta@fortive.com
        # The completion response/db_message coming from line number 674-677 
        # of asgi.py, already adds news messages to the history.
        # so there is no need to again extend the new messages 
        # to history in the following lines (line 112)

        # history = read_chat_history(chatId=chatId)
        # print("history: ", history)
        # print("completion_response: ", completion_response)
        # history.extend(completion_response)
        # updatedCompletedResponse=history

        updatedCompletedResponse=completion_response
        print("updatedCompletedResponse: ", updatedCompletedResponse)
        print(chatId,type(chatId))
        with get_conn() as conn:
            cursor = conn.cursor()               
            cursor.execute('''
            MERGE [dbo].[tblBotChat] AS [chth]
            USING (SELECT ?, ?) as src (ChatId, ChatHistory)
            ON ([chth].ChatId = src.ChatId)
            WHEN MATCHED THEN
                UPDATE SET [ChatHistory] =  src.ChatHistory, [updated_date]=GETDATE()         
            WHEN NOT MATCHED THEN
                INSERT ([ChatId],[ChatHistory],[updated_date])
                VALUES (src.ChatId, src.ChatHistory, GETDATE())
            OUTPUT $action;
            ''',chatId, json.dumps(updatedCompletedResponse))
            cursor.commit()
    except:
        tb = traceback.format_exc()
        print("error occurred: " + tb)
    else:
        tb = "No error"




def read_chat_history( chatId):
    try:
        print("Inside read_chat_history - ChatID: ", chatId)
        with get_conn() as conn:
            cursor = conn.cursor()
            # Define the SQL query to retrieve chat history
            query = '''
                SELECT [ChatHistory]
                FROM [dbo].[tblBotChat]
                WHERE [ChatId] = ?
            '''

            # Execute the query with user_id and chat_id as parameters
            cursor.execute(query, chatId)

            # Fetch the result (assuming one row is expected)
            result = cursor.fetchone()

            # Close the cursor and connection
            cursor.close()
            conn.close()
            # print(result)
            chat_history_list = json.loads(result[0])
            # print(chat_history_list)
            # print("before history")

            if chat_history_list is not None:
                # print("inside chat_history_list")
                #chat_history_list = json.loads(result)
                # print(chat_history_list)

                # commented lines 163, 164 by amit.gupta@fortive.com while testing

                # logging.info("result ::"+result)
                # logging.info("result[0] ::"+chat_history_list)
                return chat_history_list  # Return (UserId, ChatId, ChatHistory) as a tuple
            else:
                # print("inside else condition")
                return []  # No matching record found
    except Exception as e:
        # print("exception: ",str(e))
        logging.info(f"Error occured: {str(e)}")
#         return [
#     {
#         "role": "user",
#         "content": "Hi! what are some of your products for thermal imaging"
#     },
#     {
#         "role": "assistant",
#         "content": "Hello! As a Fluke salesperson, I can recommend the following products for thermal imaging:\n\n1. Fluke Ti401 PRO Infrared Camera - This camera is designed for professional use and features a high-resolution display, laser-assisted autofocus, and wireless connectivity. It's perfect for industrial and commercial applications.\n\n2. Fluke TiS60+ Infrared Camera - This camera is ideal for building inspections and HVAC applications. It features a large, 5-inch display, IR-Fusion technology, and a rugged design.\n\n3. Fluke TiS20+ Infrared Camera - This camera is a great entry-level option for those new to thermal imaging. It features a 3.5-inch display, IR-Fusion technology, and a compact design.\n\n4. Fluke i800 AC Current Clamp - This accessory allows you to measure AC current without breaking the circuit. It's compatible with most Fluke multimeters and thermal imagers.\n\n5. Fluke 1555 Insulation Resistance Tester Kit - This kit includes everything you need to test insulation resistance in high-voltage equipment. It features a large, backlit display and a rugged design.\n\nAdditionally, I would recommend the Fluke Lens Wide2 accessory, which expands the field of view on compatible thermal imagers. This is especially useful for building inspections and other applications where a wider view is needed.\n\nYou can find more information on these products at the following URLs:\n\n- Fluke Ti401 PRO Infrared Camera: https://www.fluke.com/en-us/product/thermal-imaging/infrared-cameras/fluke-ti401-pro\n- Fluke TiS60+ Infrared Camera: https://www.fluke.com/en-us/product/thermal-imaging/infrared-cameras/fluke-tis60-plus\n- Fluke TiS20+ Infrared Camera: https://www.fluke.com/en-us/product/thermal-imaging/infrared-cameras/fluke-tis20-plus\n- Fluke i800 AC Current Clamp: https://www.fluke.com/en-us/product/accessories/probes/fluke-i800\n- Fluke 1555 Insulation Resistance Tester Kit: https://www.fluke.com/en-us/product/electrical-testing/insulation-testers/fluke-1555-kit\n- Fluke Lens Wide2: https://www.fluke.com/en-us/product/accessories/thermal-imaging/fluke-lens-wide2"
#     }
# ]
        # print("inside exception")
        return []


def get_conn():
    # credential = identity.DefaultAzureCredential()
    # token_bytes = credential.get_token("https://database.windows.net/.default").token.encode("UTF-16-LE")
    # token_struct = struct.pack(f'<I{len(token_bytes)}s', len(token_bytes), token_bytes)
    # SQL_COPT_SS_ACCESS_TOKEN = 1256  # This connection option is defined by microsoft in msodbcsql.h
    # conn = pyodbc.connect(connection_string, attrs_before={SQL_COPT_SS_ACCESS_TOKEN: token_struct})
    conn = pyodbc.connect(connection_string, autocommit=True)
    return conn