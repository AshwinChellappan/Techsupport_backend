import requests

rolemap = {
    "FTV-AAD-FBSO-RSTD" : "2bc160c9-380c-4c7b-ae36-60be424073ec"
}


def resolve_role_object_id(tag=None):
    if(tag):
        keys_array = filter(lambda key:key.endswith(tag),rolemap.keys())
        for key in keys_array:
            return (key,rolemap[key])

    return ("No_Tag","NA")

def resolve_roles_to_object_ids(tags=[]):
    groupMap ={}
    if tags:
        for tag in tags:
            tag,objectId = resolve_role_object_id(tag=tag)
            if(tag):
                groupMap[tag] = objectId
        return groupMap
    else: 
        return groupMap
