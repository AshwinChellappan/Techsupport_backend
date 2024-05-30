import os
import jwt
import requests
import json
from fastapi import Request
import dotenv


def get_user_upn_from_token_header(request:Request):
    authorizationHeaderValue = request.headers.get("Authorization")
    if authorizationHeaderValue:
        encodedToken = authorizationHeaderValue.split(" ")[1]
        decodedToken = jwt.decode(encodedToken, options={"verify_signature": False})
        return decodedToken["upn"] or decodedToken["unique_name"]

def get_user_membership_information_from_auth_header(request:Request):
    authorizationHeaderValue = request.headers.get("Authorization")
    if authorizationHeaderValue:
        encodedToken = authorizationHeaderValue.split(" ")[1]
        decodedToken = jwt.decode(encodedToken, options={"verify_signature": False})
        print("Retrieved access token from Authorization header: " + str(decodedToken))
        if "groups" in decodedToken.keys():
            print("token contains groups: {}".format(','.join(decodedToken["groups"])))
            return decodedToken["groups"]
        else:
            print("token contains no group claims.")
            return []

def get_user_membership_information_from_id_token_header(request:Request):
    result = "\n"
    myDict = sorted(dict(request.headers))
    for key in myDict:
        result += f"{key} = {dict(request.headers)[key]}\n"
    print("Headers: ")
    print(result)

    authorizationHeaderValue = request.headers.get("X-MS-TOKEN-AAD-ID-TOKEN")
    print("Retrieved encoded id token from X-Ms-Token-Aad-Id-Token header: ")
    print(authorizationHeaderValue)
    if authorizationHeaderValue:
        encodedToken = authorizationHeaderValue
        decodedToken = jwt.decode(encodedToken, options={"verify_signature": False})
        print("Retrieved id token from X-Ms-Token-Aad-Id-Token header: " + decodedToken)
        print("token contains ".format(','.join(decodedToken["groups"]))+" groups.")
        return decodedToken["groups"]