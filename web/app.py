import os
from flask import Flask
from flask import request
from flask import render_template
from flask import redirect
from flask import url_for
from flask import flash
from pymongo import MongoClient
from bson import ObjectId
from check import get_device_info

mongo_uri = os.environ.get("MONGO_URI")
db_name = os.environ.get("DB_NAME")
client = MongoClient(mongo_uri)
mydb = client[db_name]
mycol = mydb["mycollection"]
mysw = mydb["switch"]


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
    if username and password and ip:
        device = {
            "device_type": "cisco_ios",
            "host": ip,  # <-- IP อุปกรณ์ของคุณ
            "username": username,  # <-- Username
            "password": password,  # <-- Password
        }
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
    return render_template(
        "router.html", router_ip=ip, routing=docs, interface_data=docsi
    )


@app.route("/switch/<string:ip>")
def switch_detail(ip):
    status = list(
        mydb.switch_status.find({"switch_ip": ip})
        .sort("timestamp", -1)
        .limit(1)
    )
    return render_template("switch.html", switch_ip=ip, switch_status=status)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
