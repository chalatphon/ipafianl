from netmiko import ConnectHandler
from netmiko.exceptions import NetmikoAuthenticationException, NetmikoTimeoutException
import os
from pymongo import MongoClient


mongo_uri = os.environ.get("MONGO_URI")
db_name = os.environ.get("DB_NAME")
client = MongoClient(mongo_uri)
mydb = client[db_name]
mycol = mydb["mycollection"]
mysw = mydb["switch"]


def get_device_info(device):
    """
    Connects to a device using Netmiko and determines its type based on its
    functional tables (Routing Table vs. MAC Address Table).
    """
    try:
        print(f"\n--- Connecting to {device['host']} ---")
        with ConnectHandler(**device) as net_connect:

            has_routing_table = False
            has_mac_table = False

            # 1. ตรวจสอบ Routing Table (ความสามารถ Layer 3)
            try:
                # ส่งคำสั่งและตรวจสอบว่าผลลัพธ์ไม่มี error
                output = net_connect.send_command("show ip route", expect_string=r"#")
                # ตรวจสอบว่าผลลัพธ์ที่ได้ไม่ใช่ข้อความ error มาตรฐาน
                if (
                    output
                    and "Invalid input detected" not in output
                    and "ambiguous command" not in output
                ):
                    has_routing_table = True
            except Exception:
                # หากคำสั่งล้มเหลว อาจเพราะอุปกรณ์ไม่รองรับ
                has_routing_table = False

            print(f"  > Routing table found: {has_routing_table}")

            # 2. ตรวจสอบ MAC Address Table (ความสามารถ Layer 2)
            try:
                # ส่งคำสั่งและตรวจสอบว่าผลลัพธ์ไม่มี error
                output = net_connect.send_command(
                    "show mac address-table", expect_string=r"#"
                )
                if (
                    output
                    and "Invalid input detected" not in output
                    and "ambiguous command" not in output
                ):
                    has_mac_table = True
            except Exception:
                # หากคำสั่งล้มเหลว อาจเพราะอุปกรณ์ไม่รองรับ (เป็น Router)
                has_mac_table = False

            print(f"  > MAC address table found: {has_mac_table}")

            # 3. ตัดสินใจประเภทของอุปกรณ์จากผลลัพธ์
            if has_routing_table and not has_mac_table:
                device_type = "Router"
            elif not has_routing_table and has_mac_table:
                device_type = "Layer 2 Switch"
            elif has_routing_table and has_mac_table:
                device_type = "Layer 3 Switch"
            else:
                device_type = "Unknown or unsupported device"

            print(f"  ✅ Detected Device Type: {device_type}")
            if "Switch" in device_type:
                print("  Device is a Switch. Saving credentials to MongoDB...")

                # --- CORRECTION 3: แก้ไข Key ของ Dictionary ให้ตรงกับ Netmiko ---
                switch_data = {
                    "ip": device["host"],
                    "username": device["username"],
                    "password": device["password"],
                }
                mysw.insert_one(switch_data)
                print(f"  Successfully saved {device['host']} to the database.")
            elif "Router" in device_type:
                print("  Device is a Router. Saving credentials to MongoDB...")

                # --- CORRECTION 3: แก้ไข Key ของ Dictionary ให้ตรงกับ Netmiko ---
                Router_data = {
                    "ip": device["host"],
                    "username": device["username"],
                    "password": device["password"],
                }
                mycol.insert_one(Router_data)
                print(f"  Successfully saved {device['host']} to the database.")
            return device_type

    except NetmikoTimeoutException:
        error_msg = f"Error: Connection to {device['host']} timed out."
        print(error_msg)
        return error_msg
    except NetmikoAuthenticationException:
        error_msg = f"Error: Authentication failed for {device['host']}."
        print(error_msg)
        return error_msg
    except Exception as e:
        error_msg = f"An unexpected error occurred with {device['host']}: {e}"
        print(error_msg)
        return error_msg


if __name__ == "__main__":
    # --- ตัวอย่างการใช้งาน ---
    # อุปกรณ์ที่คุณทดสอบคือ Router (IOSv) ดังนั้นผลที่คาดหวังคือ "Router"
    cisco_router = {
        "device_type": "cisco_ios",
        "host": "10.0.15.133",  # <-- IP อุปกรณ์ของคุณ
        "username": "admin",  # <-- Username
        "password": "cisco",  # <-- Password
    }

    devices_to_check = [cisco_router]  # , cisco_switch]

    for dev in devices_to_check:
        get_device_info(dev)
