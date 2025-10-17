from bson import json_util
from router_client import get_interfaces,get_route_table
from database import save_interface_status,save_route_table


def callback_router(ch, method, props, body):
    job = json_util.loads(body.decode())
    ip = job["ip"]
    username = job["username"]
    password = job["password"]

    print(f"Received job for router {ip}")

    try:
        output = get_interfaces(ip,username,password)
        save_interface_status(ip, output)
        print(f"Stored interface status for {ip}")
        table = get_route_table(ip,username,password)
        save_route_table(ip, table)

    except Exception as e:
        print(f" Error: {e}")
