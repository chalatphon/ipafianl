import os

from pymongo import MongoClient



mongo_uri = os.environ.get("MONGO_URI")
db_name = os.environ.get("DB_NAME")
client = MongoClient(mongo_uri)
db = client[db_name]

def get_router_info():
    
    routers = db["mycollection"]
    router_data = routers.find()
    return router_data
    

def get_switch_info():
    switch = db["switch"]
    switch_data = switch.find()
    return switch_data

if __name__=='__main__':
    get_router_info()
