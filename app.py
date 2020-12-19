
from flask import Flask, request, jsonify, redirect, session, url_for
import json
import os
import bcrypt
from flask_pymongo import PyMongo

app = Flask(__name__)
#  app.config["MONGO_URI"] = "mongodb://0.0.0.0:27017/blahblah"
#  mongo = PyMongo(app)

mongoPassword = os.environ.get("GOODPODS_MONGO_PASSWORD")
connectionString = "mongodb+srv://bruno:" + str(mongoPassword) + "@cluster0.g2mr3.mongodb.net/goodpods?retryWrites=true&w=majority"
print(connectionString)

app.config["MONGO_URI"] = connectionString
mongo = PyMongo(app)
#  mongo = PyMongo(app, connectionString)
db = mongo.db

@app.route("/signup", methods=("POST",))
def signup(): 
    username = request.get("username")
    password = request.get("password")

    same_username_users = db.users.find( {"username": username } ) 
    if any(True for _ in same_username_users):
        return jsonify({
            "status": "error", 
            "messsage": "username taken"
            })

    pw_hash = bcrypt.hashpw(password, bycrypt.gensalt())

    db.users.insert_one({
        "username": username,
        "password_hash": pw_hash
        })
    return jsonify({"status": "success"})

@app.route("/login", methods=("POST",))
def login(): 
    username = request.get("username")
    password = request.get("password")

    mongo_user = mongo.db.users.find_one({"username": username})
    pw_hash = mongo_user["password"]

    if bcrypt.checkpw(password, hashed):
        return jsonify({"status": "success"})
    else: 
        return jsonify({"status": "error", "message": "incorrect password"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port="5000", debug=True)

