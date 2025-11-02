import os
import json

import ntc_templates
from netmiko import ConnectHandler
from paramiko.transport import Transport

LEGACY_KEX = (
    "diffie-hellman-group14-sha1",
    "diffie-hellman-group-exchange-sha1",
)
Transport._preferred_kex = tuple(
    dict.fromkeys(LEGACY_KEX + Transport._preferred_kex)
)
LEGACY_KEYS = ("ssh-rsa",)
for attr in ("_preferred_keys", "_preferred_pubkeys"):
    current = getattr(Transport, attr, None)
    if current:
        setattr(
            Transport,
            attr,
            tuple(dict.fromkeys(LEGACY_KEYS + current)),
        )


def get_interfaces(ip, username, password):

    os.environ["NET_TEXTFSM"] = os.path.join(
        os.path.dirname(ntc_templates.__file__), "templates"
    )

    device = {
        "device_type": "cisco_ios",
        "host": ip,
        "username": username,
        "password": password,
        "secret": password,
    }

    with ConnectHandler(**device) as conn:
        try:
            conn.enable()
        except Exception as exc:
            print(f"Failed to enter enable mode on {ip}: {exc}. Continuing without enable.")
        result = conn.send_command("show ip int br", use_textfsm=True)
        conn.disconnect()

    print(json.dumps(result, indent=2))
    return result


def get_route_table(ip, username, password):
    os.environ["NET_TEXTFSM"] = os.path.join(
        os.path.dirname(ntc_templates.__file__), "templates"
    )
    device = {
        "device_type": "cisco_ios",
        "host": ip,
        "username": username,
        "password": password,
        "secret": password,
    }

    with ConnectHandler(**device) as conn:
        try:
            conn.enable()
        except Exception as exc:
            print(f"Failed to enter enable mode on {ip}: {exc}. Continuing without enable.")
        result = conn.send_command("show ip route", use_textfsm=True)
        conn.disconnect()

    print(json.dumps(result, indent=2))
    return result


def get_switch_ports(ip, username, password):
    os.environ["NET_TEXTFSM"] = os.path.join(
        os.path.dirname(ntc_templates.__file__), "templates"
    )

    device = {
        "device_type": "cisco_ios",
        "host": ip,
        "username": username,
        "password": password,
        "secret": password,
    }

    with ConnectHandler(**device) as conn:
        try:
            conn.enable()
        except Exception as exc:
            print(f"Failed to enter enable mode on {ip}: {exc}. Continuing without enable.")
        result = conn.send_command("show interfaces status", use_textfsm=True)
        conn.disconnect()

    print(json.dumps(result, indent=2))
    return result


if __name__ == "__main__":
    get_route_table("10.0.15.133", "admin", "cisco")
