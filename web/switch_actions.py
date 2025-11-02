import re
from datetime import datetime, UTC

from netmiko import ConnectHandler
from netmiko.exceptions import (
    NetmikoAuthenticationException,
    NetmikoTimeoutException,
)


def _build_device(creds, override_secret=None):
    device = {
        "device_type": "cisco_ios",
        "host": creds["ip"],
        "username": creds["username"],
        "password": creds["password"],
    }
    secret = override_secret or creds.get("secret") or creds["password"]
    device["secret"] = secret
    return device


def _normalize_vlan(vlan_id):
    match = re.fullmatch(r"(?:Vlan)?(\d+)", vlan_id.strip(), re.IGNORECASE)
    if not match:
        raise ValueError("VLAN ID ต้องเป็นตัวเลข เช่น 10 หรือ Vlan10")
    return int(match.group(1))


def create_vlan_interface(creds, vlan_id, ip_address, netmask, name=None, secret=None):
    vlan = _normalize_vlan(vlan_id)
    interface = f"Vlan{vlan}"
    device = _build_device(creds, override_secret=secret)

    commands = [
        f"vlan {vlan}",
    ]
    if name:
        commands.append(f"name {name}")
    commands.extend(
        [
            "exit",
            f"interface {interface}",
            f"ip address {ip_address} {netmask}",
            "no shutdown",
        ]
    )

    try:
        with ConnectHandler(**device) as conn:
            try:
                conn.enable()
            except Exception as exc:
                return False, f"เข้าสู่ privileged mode ไม่ได้: {exc}"
            conn.send_config_set(commands)
    except NetmikoTimeoutException as exc:
        return False, f"เชื่อมต่อ {device['host']} ไม่สำเร็จ: {exc}"
    except NetmikoAuthenticationException as exc:
        return False, f"เข้าสู่ระบบ {device['host']} ไม่สำเร็จ: {exc}"
    except Exception as exc:
        return False, f"สร้าง {interface} ไม่สำเร็จ: {exc}"

    payload = {
        "switch_ip": creds["ip"],
        "vlan": vlan,
        "interface": interface,
        "ip": ip_address,
        "netmask": netmask,
        "name": name or "",
        "admin_state": "up",
        "updated_at": datetime.now(UTC),
    }
    return True, payload


def set_vlan_state(creds, vlan_id, enabled=True, secret=None):
    vlan = _normalize_vlan(vlan_id)
    interface = f"Vlan{vlan}"
    device = _build_device(creds, override_secret=secret)
    command = "no shutdown" if enabled else "shutdown"
    try:
        with ConnectHandler(**device) as conn:
            try:
                conn.enable()
            except Exception as exc:
                state = "เปิด" if enabled else "ปิด"
                return False, f"เข้าสู่ privileged mode ไม่สำเร็จ จึง{state} {interface} ไม่ได้: {exc}"
            conn.send_config_set([f"interface {interface}", command])
    except NetmikoTimeoutException as exc:
        return False, f"เชื่อมต่อ {device['host']} ไม่สำเร็จ: {exc}"
    except NetmikoAuthenticationException as exc:
        return False, f"เข้าสู่ระบบ {device['host']} ไม่สำเร็จ: {exc}"
    except Exception as exc:
        state = "เปิด" if enabled else "ปิด"
        return False, f"{state} {interface} ไม่สำเร็จ: {exc}"

    payload = {
        "vlan": vlan,
        "interface": interface,
        "admin_state": "up" if enabled else "down",
        "updated_at": datetime.now(UTC),
    }
    return True, payload


def delete_vlan(creds, vlan_id, secret=None):
    vlan = _normalize_vlan(vlan_id)
    interface = f"Vlan{vlan}"
    device = _build_device(creds, override_secret=secret)
    commands = [f"no interface {interface}", f"no vlan {vlan}"]
    try:
        with ConnectHandler(**device) as conn:
            try:
                conn.enable()
            except Exception as exc:
                return False, f"เข้าสู่ privileged mode ไม่สำเร็จ จึงลบ {interface} ไม่ได้: {exc}"
            conn.send_config_set(commands)
    except NetmikoTimeoutException as exc:
        return False, f"เชื่อมต่อ {device['host']} ไม่สำเร็จ: {exc}"
    except NetmikoAuthenticationException as exc:
        return False, f"เข้าสู่ระบบ {device['host']} ไม่สำเร็จ: {exc}"
    except Exception as exc:
        return False, f"ลบ {interface} ไม่สำเร็จ: {exc}"

    payload = {
        "vlan": vlan,
        "interface": interface,
        "updated_at": datetime.now(UTC),
    }
    return True, payload
