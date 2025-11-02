import os
import ipaddress
from flask import Flask
from flask import request
from flask import render_template
from flask import redirect
from flask import url_for
from flask import flash
from pymongo import MongoClient
from bson import ObjectId
from check import get_device_info
from router_actions import create_loopback, set_loopback_state, delete_loopback
from switch_actions import (
    create_vlan_interface,
    set_vlan_state,
    delete_vlan,
)

mongo_uri = os.environ.get("MONGO_URI")
db_name = os.environ.get("DB_NAME")
client = MongoClient(mongo_uri)
mydb = client[db_name]
mycol = mydb["mycollection"]
mysw = mydb["switch"]
loopbacks = mydb["loopbacks"]
switch_vlans = mydb["switch_vlans"]


app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("FLASK_SECRET", "change-me")


@app.route("/")
def main():
    routers = list(mycol.find())
    switches = list(mysw.find())
    return render_template("index.html", routers=routers, switches=switches)


@app.route("/add", methods=["POST"])
def add_comment():
    ip = request.form.get("ip")
    username = request.form.get("username")
    password = request.form.get("password")
    secret = request.form.get("secret", "").strip()
    if username and password and ip:
        device = {
            "device_type": "cisco_ios",
            "host": ip,  # <-- IP อุปกรณ์ของคุณ
            "username": username,  # <-- Username
            "password": password,  # <-- Password
        }
        if secret:
            device["secret"] = secret
        success, message = get_device_info(device)
        category = "success" if success else "error"
        flash(message, category=category)
    else:
        flash("กรุณากรอก IP, Username, Password ให้ครบ", category="error")

    return redirect(url_for("main"))


@app.route("/routers/<id>/delete", methods=["POST"])
def delete_router(id):
    result = mycol.delete_one({"_id": ObjectId(id)})
    if result.deleted_count:
        flash("ลบ Router เรียบร้อย", category="success")
    else:
        flash("ไม่พบ Router ที่ต้องการลบ", category="error")
    return redirect(url_for("main"))


@app.route("/switches/<id>/delete", methods=["POST"])
def delete_switch(id):
    result = mysw.delete_one({"_id": ObjectId(id)})
    if result.deleted_count:
        flash("ลบ Switch เรียบร้อย", category="success")
    else:
        flash("ไม่พบ Switch ที่ต้องการลบ", category="error")
    return redirect(url_for("main"))


@app.route("/router/<string:ip>")
def router_detail(ip):
    docs = list(
        mydb.route_table.find({"router_ip": ip}).sort("timestamp", -1).limit(1)
    )
    docsi = list(
        mydb.interface_status.find({"router_ip": ip}).sort("timestamp", -1).limit(1)
    )
    loopback_records = list(loopbacks.find({"router_ip": ip}))

    status_map = {}
    if docsi:
        for intf in docsi[0].get("interfaces", []):
            name = intf.get("interface")
            if name and name.lower().startswith("loopback"):
                status_map[name] = intf

    return render_template(
        "router.html",
        router_ip=ip,
        routing=docs,
        interface_data=docsi,
        loopbacks=loopback_records,
        loopback_status=status_map,
    )


@app.route("/switch/<string:ip>")
def switch_detail(ip):
    status = list(
        mydb.switch_status.find({"switch_ip": ip})
        .sort("timestamp", -1)
        .limit(1)
    )
    vlans = list(switch_vlans.find({"switch_ip": ip}))
    vlan_status_map = {entry["interface"]: entry for entry in vlans}
    return render_template(
        "switch.html",
        switch_ip=ip,
        switch_status=status,
        vlans=vlans,
        vlan_status=vlan_status_map,
    )


@app.route("/switch/<string:ip>/vlans", methods=["POST"])
def create_switch_vlan(ip):
    vlan_id = request.form.get("vlan_id", "").strip()
    name = request.form.get("vlan_name", "").strip()
    ip_address = request.form.get("vlan_ip", "").strip()
    netmask = request.form.get("vlan_netmask", "").strip()
    override_secret = request.form.get("vlan_secret", "").strip()

    if not all([vlan_id, ip_address, netmask]):
        flash("กรุณากรอก VLAN, IP, Netmask ให้ครบ", category="error")
        return redirect(url_for("switch_detail", ip=ip))

    try:
        if "/" in ip_address:
            iface = ipaddress.IPv4Interface(ip_address)
            ip_address = str(iface.ip)
            if not netmask or netmask.startswith("/"):
                netmask = str(iface.netmask)
        if netmask.startswith("/"):
            prefix = int(netmask.lstrip("/"))
            netmask = str(ipaddress.IPv4Network(f"0.0.0.0/{prefix}").netmask)
        ipaddress.IPv4Address(ip_address)
        ipaddress.IPv4Address(netmask)
    except ValueError:
        flash("รูปแบบ IP หรือ Netmask ไม่ถูกต้อง", category="error")
        return redirect(url_for("switch_detail", ip=ip))

    creds = mysw.find_one({"ip": ip})
    if not creds:
        flash("ไม่พบข้อมูล Switch ในระบบ", category="error")
        return redirect(url_for("switch_detail", ip=ip))

    try:
        success, payload = create_vlan_interface(
            creds,
            vlan_id,
            ip_address,
            netmask,
            name=name or None,
            secret=override_secret or None,
        )
    except ValueError as exc:
        flash(str(exc), category="error")
        return redirect(url_for("switch_detail", ip=ip))

    if success:
        switch_vlans.update_one(
            {"switch_ip": payload["switch_ip"], "vlan": payload["vlan"]},
            {"$set": payload, "$setOnInsert": {"created_at": payload["updated_at"]}},
            upsert=True,
        )
        flash(f"สร้าง {payload['interface']} สำเร็จ", category="success")
    else:
        flash(payload, category="error")
        if "privileged mode" in payload.lower() and not creds.get("secret"):
            flash(
                "กรุณาเพิ่ม Enable Secret ให้ Switch ในหน้าหลัก แล้วลองอีกครั้ง",
                category="error",
            )
    return redirect(url_for("switch_detail", ip=ip))


@app.route("/switch/<string:ip>/vlans/<vlan_id>/state", methods=["POST"])
def update_switch_vlan_state(ip, vlan_id):
    action = request.form.get("action")
    override_secret = request.form.get("vlan_secret", "").strip()
    creds = mysw.find_one({"ip": ip})
    if not creds:
        flash("ไม่พบข้อมูล Switch ในระบบ", category="error")
        return redirect(url_for("switch_detail", ip=ip))

    if action not in {"enable", "disable"}:
        flash("ไม่ทราบคำสั่งสำหรับ VLAN", category="error")
        return redirect(url_for("switch_detail", ip=ip))

    enabled = action == "enable"
    try:
        success, payload = set_vlan_state(
            creds, vlan_id, enabled=enabled, secret=override_secret or None
        )
    except ValueError as exc:
        flash(str(exc), category="error")
        return redirect(url_for("switch_detail", ip=ip))

    if success:
        switch_vlans.update_one(
            {"switch_ip": ip, "vlan": payload["vlan"]},
            {
                "$set": {
                    "admin_state": payload["admin_state"],
                    "updated_at": payload["updated_at"],
                },
                "$setOnInsert": {
                    "switch_ip": ip,
                    "vlan": payload["vlan"],
                    "interface": payload["interface"],
                },
            },
            upsert=True,
        )
        state_text = "เปิด" if enabled else "ปิด"
        flash(f"{state_text} {payload['interface']} สำเร็จ", category="success")
    else:
        flash(payload, category="error")
        if "privileged mode" in payload.lower() and not creds.get("secret"):
            flash(
                "กรุณาเพิ่ม Enable Secret ให้ Switch ในหน้าหลัก แล้วลองอีกครั้ง",
                category="error",
            )
    return redirect(url_for("switch_detail", ip=ip))


@app.route("/switch/<string:ip>/vlans/<vlan_id>/delete", methods=["POST"])
def delete_switch_vlan(ip, vlan_id):
    override_secret = request.form.get("vlan_secret", "").strip()
    creds = mysw.find_one({"ip": ip})
    if not creds:
        flash("ไม่พบข้อมูล Switch ในระบบ", category="error")
        return redirect(url_for("switch_detail", ip=ip))

    try:
        success, payload = delete_vlan(creds, vlan_id, secret=override_secret or None)
    except ValueError as exc:
        flash(str(exc), category="error")
        return redirect(url_for("switch_detail", ip=ip))

    if success:
        switch_vlans.delete_one({"switch_ip": ip, "vlan": payload["vlan"]})
        flash(f"ลบ {payload['interface']} สำเร็จ", category="success")
    else:
        flash(payload, category="error")
        if "privileged mode" in payload.lower() and not creds.get("secret"):
            flash(
                "กรุณาเพิ่ม Enable Secret ให้ Switch ในหน้าหลัก แล้วลองอีกครั้ง",
                category="error",
            )
    return redirect(url_for("switch_detail", ip=ip))


@app.route("/router/<string:ip>/loopbacks", methods=["POST"])
def create_loopback_route(ip):
    loopback_id = request.form.get("loopback_id", "").strip()
    ip_address = request.form.get("loopback_ip", "").strip()
    netmask = request.form.get("loopback_netmask", "").strip()
    override_secret = request.form.get("loopback_secret", "").strip()

    if not all([loopback_id, ip_address, netmask]):
        flash("กรุณากรอก Loopback, IP และ Netmask ให้ครบ", category="error")
        return redirect(url_for("router_detail", ip=ip))

    try:
        if "/" in ip_address:
            iface = ipaddress.IPv4Interface(ip_address)
            ip_address = str(iface.ip)
            if not netmask or netmask.startswith("/"):
                netmask = str(iface.netmask)
        if netmask.startswith("/"):
            prefix = int(netmask.lstrip("/"))
            netmask = str(ipaddress.IPv4Network(f"0.0.0.0/{prefix}").netmask)
        # Validate addresses
        ipaddress.IPv4Address(ip_address)
        ipaddress.IPv4Address(netmask)
    except ValueError:
        flash("รูปแบบ IP หรือ Netmask ไม่ถูกต้อง", category="error")
        return redirect(url_for("router_detail", ip=ip))

    creds = mycol.find_one({"ip": ip})
    if not creds:
        flash("ไม่พบข้อมูล Router ในระบบ", category="error")
        return redirect(url_for("router_detail", ip=ip))

    try:
        success, payload = create_loopback(
            creds, loopback_id, ip_address, netmask, secret=override_secret or None
        )
    except ValueError as exc:
        flash(str(exc), category="error")
        return redirect(url_for("router_detail", ip=ip))

    if success:
        loopbacks.update_one(
            {
                "router_ip": payload["router_ip"],
                "interface": payload["interface"],
            },
            {"$set": payload, "$setOnInsert": {"created_at": payload["updated_at"]}},
            upsert=True,
        )
        flash(f"สร้าง {payload['interface']} สำเร็จ", category="success")
    else:
        flash(payload, category="error")
        if "privileged mode" in payload.lower() and not creds.get("secret"):
            flash(
                "กรุณาเพิ่ม Enable Secret ให้ Router ในหน้าหลัก แล้วลองอีกครั้ง",
                category="error",
            )
    return redirect(url_for("router_detail", ip=ip))


@app.route("/router/<string:ip>/loopbacks/<loop_id>/state", methods=["POST"])
def update_loopback_state(ip, loop_id):
    action = request.form.get("action")
    creds = mycol.find_one({"ip": ip})
    if not creds:
        flash("ไม่พบข้อมูล Router ในระบบ", category="error")
        return redirect(url_for("router_detail", ip=ip))

    if action not in {"enable", "disable"}:
        flash("ไม่ทราบคำสั่งสำหรับ Loopback", category="error")
        return redirect(url_for("router_detail", ip=ip))

    enabled = action == "enable"
    try:
        success, payload = set_loopback_state(creds, loop_id, enabled=enabled)
    except ValueError as exc:
        flash(str(exc), category="error")
        return redirect(url_for("router_detail", ip=ip))
    if success:
        loopbacks.update_one(
            {"router_ip": ip, "interface": payload["interface"]},
            {
                "$set": {
                    "admin_state": payload["admin_state"],
                    "updated_at": payload["updated_at"],
                },
                "$setOnInsert": {
                    "router_ip": ip,
                    "interface": payload["interface"],
                },
            },
            upsert=True,
        )
        state_text = "เปิด" if enabled else "ปิด"
        flash(f"{state_text} {payload['interface']} สำเร็จ", category="success")
    else:
        flash(payload, category="error")
        if "privileged mode" in payload.lower() and not creds.get("secret"):
            flash(
                "กรุณาเพิ่ม Enable Secret ให้ Router ในหน้าหลัก แล้วลองอีกครั้ง",
                category="error",
            )
    return redirect(url_for("router_detail", ip=ip))


@app.route("/router/<string:ip>/loopbacks/<loop_id>/delete", methods=["POST"])
def delete_loopback_route(ip, loop_id):
    creds = mycol.find_one({"ip": ip})
    if not creds:
        flash("ไม่พบข้อมูล Router ในระบบ", category="error")
        return redirect(url_for("router_detail", ip=ip))

    override_secret = request.form.get("loopback_secret", "").strip()
    try:
        success, payload = delete_loopback(
            creds, loop_id, secret=override_secret or None
        )
    except ValueError as exc:
        flash(str(exc), category="error")
        return redirect(url_for("router_detail", ip=ip))

    if success:
        loopbacks.delete_one({"router_ip": ip, "interface": payload["interface"]})
        flash(f"ลบ {payload['interface']} สำเร็จ", category="success")
    else:
        flash(payload, category="error")
        if "privileged mode" in payload.lower() and not creds.get("secret"):
            flash(
                "กรุณาเพิ่ม Enable Secret ให้ Router ในหน้าหลัก แล้วลองอีกครั้ง",
                category="error",
            )
    return redirect(url_for("router_detail", ip=ip))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
