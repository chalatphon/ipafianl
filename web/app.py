import os
from flask import Flask
from flask import request
from flask import render_template
from flask import redirect
from flask import url_for
from pymongo import MongoClient
from bson import ObjectId

mongo_uri  = os.environ.get("MONGO_URI")
db_name    = os.environ.get("DB_NAME")
client = MongoClient(mongo_uri)
mydb = client[db_name]
mycol = mydb["mycollection"]
mysw = mydb["switch"]



app = Flask(__name__)



@app.route("/")
def main():
    data = []
    sdata = []
    for x in mycol.find():
        data.append(x)
        print(data)
    for x in mysw.find():
        sdata.append(x)
        print(sdata)
    return render_template("index.html", data=data,sdata=sdata)

@app.route("/add", methods=["POST"])
def add_comment():
    ip = request.form.get("ip")
    username = request.form.get("username")
    password = request.form.get("password")
    if username and password and ip:
        x = mycol.insert_one({"ip": ip,"username": username,"password": password})

    return redirect(url_for("main"))


@app.route("/adds", methods=["POST"])
def add_switch():
    ip = request.form.get("ip")
    username = request.form.get("username")
    password = request.form.get("password")
    if username and password and ip:
        x = mysw.insert_one({"ip": ip,"username": username,"password": password})

    return redirect(url_for("main"))

@app.route("/delete/<id>", methods=["POST"])
def delete_comment(id):
    mycol.delete_one({"_id":ObjectId(id)})
    return redirect("/")
    

@app.route("/delete/<id>", methods=["POST"])
def delete_switch(id):
    mysw.delete_one({"_id":ObjectId(id)})
    return redirect("/")
    

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)