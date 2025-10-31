from pymongo import MongoClient
from datetime import datetime, UTC
import os


def save_interface_status(router_ip, interfaces):

    MONGO_URI = os.getenv("MONGO_URI")
    DB_NAME = os.getenv("DB_NAME")

    client = MongoClient(MONGO_URI)
    db = client[DB_NAME]
    collection = db["interface_status"]

    data = {
        "router_ip": router_ip,
        "timestamp": datetime.now(UTC),
        "interfaces": interfaces,
    }
    collection.insert_one(data)
    client.close()


def save_route_table(router_ip, route_table_info):
    MONGO_URI = os.getenv("MONGO_URI")
    DB_NAME = os.getenv("DB_NAME")

    client = MongoClient(MONGO_URI)
    db = client[DB_NAME]
    collection = db["route_table"]
    data = {
        "router_ip": router_ip,
        "timestamp": datetime.now(UTC),
        "route": route_table_info,
    }
    collection.insert_one(data)
    client.close()
