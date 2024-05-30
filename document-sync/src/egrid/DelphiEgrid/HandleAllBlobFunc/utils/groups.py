import os
import requests
import json
import dotenv

dotenv.load_dotenv()

def get_group_status(group_name):
    # Set the necessary variables
    tenant_id = os.getenv("BACKEND_TENANT_ID")
    client_id = os.getenv("BACKEND_CLIENT_ID")
    client_secret = os.getenv("BACKEND_CLIENT_SECRET")
    resource = 'https://graph.microsoft.com/'
    token_url = f'https://login.microsoftonline.com/{tenant_id}/oauth2/token'
    # Authenticate and obtain an access token token_url = f'https://login.microsoftonline.com/{tenant_id}/oauth2/token'
    payload = {
    'grant_type': 'client_credentials',
    'client_id': client_id,
    'client_secret': client_secret,
    'resource': resource
    }
    response = requests.post(token_url, data=payload)
    access_token = response.json()['access_token']
    # Retrieve the security group's object ID
    groups_url = f'{resource}v1.0/groups?$filter=displayName eq \'{group_name}\''
    headers = {
    'Authorization': 'Bearer ' + access_token,
    'Accept': 'application/json'
    }
    response = requests.get(groups_url, headers=headers)
    if response.status_code == 200:
        group_data = response.json()
        if 'value' in group_data and len(group_data['value']) > 0:
            group_id = group_data['value'][0]['id']
            # Security group found
            print('Security group found.')
            print('Group ID:', group_id)
        else:
            # Security group not found
            print('Security group not found.')

    else:
        # Error occurred while retrieving the security group
        print('Error occurred while retrieving the security group. Error:', response.status_code)
        print('Error details:')
        print(json.dumps(response.json(), indent=4))

if __name__=="__main__":
    get_group_status(group_name="FTV-AAD-FBSO-RSTD")