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


def normalize_loopback(loopback_id):
    match = re.fullmatch(r"(?:Loopback)?(\d+)", loopback_id.strip(), re.IGNORECASE)
    if not match:
        raise ValueError("Loopback ID ต้องเป็นตัวเลข เช่น 0 หรือ Loopback0")
    return f"Loopback{match.group(1)}"


def create_loopback(creds, loopback_id, ip_address, netmask, secret=None):
    interface = normalize_loopback(loopback_id)
    device = _build_device(creds, override_secret=secret)

    commands = [
        f"interface {interface}",
        f"ip address {ip_address} {netmask}",
        "no shutdown",
    ]
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
        "router_ip": creds["ip"],
        "interface": interface,
        "ip": ip_address,
        "netmask": netmask,
        "admin_state": "up",
        "updated_at": datetime.now(UTC),
    }
    return True, payload


def set_loopback_state(creds, loopback_id, enabled=True, secret=None):
    interface = normalize_loopback(loopback_id)
    device = _build_device(creds, override_secret=secret)
    command = "no shutdown" if enabled else "shutdown"
    try:
        with ConnectHandler(**device) as conn:
            try:
                conn.enable()
            except Exception as exc:
                state = "เปิด" if enabled else "ปิด"
                return (
                    False,
                    f"เข้าสู่ privileged mode ไม่สำเร็จ จึง{state} {interface} ไม่ได้: {exc}",
                )
            conn.send_config_set([f"interface {interface}", command])
    except NetmikoTimeoutException as exc:
        return False, f"เชื่อมต่อ {device['host']} ไม่สำเร็จ: {exc}"
    except NetmikoAuthenticationException as exc:
        return False, f"เข้าสู่ระบบ {device['host']} ไม่สำเร็จ: {exc}"
    except Exception as exc:
        state = "เปิด" if enabled else "ปิด"
        return False, f"{state} {interface} ไม่สำเร็จ: {exc}"

    payload = {
        "interface": interface,
        "admin_state": "up" if enabled else "down",
        "updated_at": datetime.now(UTC),
    }
    return True, payload


def delete_loopback(creds, loopback_id, secret=None):
    interface = normalize_loopback(loopback_id)
    device = _build_device(creds, override_secret=secret)
    commands = [f"no interface {interface}"]
    try:
        with ConnectHandler(**device) as conn:
            try:
                conn.enable()
            except Exception as exc:
                return False, f"เข้าสู่ privileged mode ไม่ได้ จึงลบ {interface} ไม่ได้: {exc}"
            conn.send_config_set(commands)
    except NetmikoTimeoutException as exc:
        return False, f"เชื่อมต่อ {device['host']} ไม่สำเร็จ: {exc}"
    except NetmikoAuthenticationException as exc:
        return False, f"เข้าสู่ระบบ {device['host']} ไม่สำเร็จ: {exc}"
    except Exception as exc:
        return False, f"ลบ {interface} ไม่สำเร็จ: {exc}"

    payload = {
        "interface": interface,
        "updated_at": datetime.now(UTC),
    }
    return True, payload
