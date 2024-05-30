from .config import openai
# from config import openai


def get_user_intent(data:dict):
    '''This method is used to understand teh intent of the user from their query'''

    intent_template = f"""
    "Identify user intent and respond with one word:

        -Lawsuit or legal advice: 'legal'
        -hazards: 'safe'
        -Competitor-related: 'competitors'
        -Related to Klein tools, Transmille , Keysight, Starrett, Megger products: 'competitors'
        -Policy or HR: 'hr'
        -Discounts or offers: 'discounts'
        -Hack or spam: 'spam'
        -Product recommendations: 'recommendation'
        -Contact details: 'contact'
        -Fluke confidential information: 'confidential'
        -Transfer of export-controlled tech: 'sanctioned'
        -Compliance with laws/regulations: 'compliance'
        -Intellectual property infringement: 'infringement'
        -Personal information: 'personal'
        -Company reputation or views: 'personal'
        -Unsafe applications or violations: 'violation'
        -Patented technology: 'patent'
        -Unrelated to Fluke products/services: 'unrelated'
        -Repair or products/services or fix or Replace or part not working or service: 'repair'
        -Price-related query: 'price'
        -Product warranty: 'warranty'
        -All other cases: 'clear'"

    """
    intent_messages= [

            {

                "role": "system",

                "content": intent_template

            },

            {

                "role": "user",

                "content": data

            }

        ]
    model = openai.default_deployment
    # stream = data.get("stream", False)

    print('model:' + model)

    chat_completion = openai.ChatCompletion.create(
        deployment_id=model,
        # model="gpt-3.5-turbo",
        frequency_penalty= 0,     #data.get("frequency_penalty", 0),
        max_tokens=1,
        n=1,  # Number of messages
        presence_penalty=0,
        temperature=0.0,
        top_p=0.0,  # Nucleus Sampling
        messages=intent_messages,
        # stream=stream,
    )

    intent: str = chat_completion['choices'][0]['message']['content']  
    print(f"intent: {intent}")

    return intent


# if __name__ == "__main__":

#     print('model')
#     model = openai.default_deployment
#     print(model)

#     data= {
#     "chatId": "47f6150d-4258-48f3-beaf-5ae65fadb4dc",
#     "messages": [
#         {
#             "role": "user",
#             "content": "Can you suggest best multimeters in range of 400$ - 500$?"
#         }
#     ],
#     "model": "gpt-35-turbo-16k",
#     "stream": False
# }
#     get_user_intent(data)