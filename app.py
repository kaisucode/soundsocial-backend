
from flask import Flask, request, jsonify, redirect, session, url_for
import json
import os
from flask_pymongo import PyMongo

#  app = Flask(__name__)
#  app.config["MONGO_URI"] = "mongodb://0.0.0.0:27017/blahblah"
#  mongo = PyMongo(app)

mongoPassword = os.environ.get("GOODPODS_MONGO_PASSWORD")

client = MongoClient("mongodb+srv://bruno:" + mongoPassword + "@cluster0.g2mr3.mongodb.net/goodpods?retryWrites=true&w=majority")
db = client.test


@app.route("/signup", methods=("POST",))
def signup(): 
    username = request.form.get("username")
    same_username_users = mongo.db.users.find( {"username": request.form.get("username") } ) 
    if any(True for _ in same_username_users):
        return jsonify({
            "status": "error", 
            "messsage": "username taken"
            })





