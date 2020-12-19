
from flask import Flask, request, jsonify, redirect, session, url_for
import json
from flask_pymongo import PyMongo

#  app = Flask(__name__)
#  app.config["MONGO_URI"] = "mongodb://0.0.0.0:27017/blahblah"
#  mongo = PyMongo(app)

client = MongoClient("mongodb://0.0.0.0:27017/blahblah")
db = client['test-database']


@app.route("/signup", methods=("POST",))
def signup(): 
    username = request.form.get("username")
    same_username_users = mongo.db.users.find( {"username": request.form.get("username") } ) 
if any(True for _ in same_username_users):
    return jsonify({
        "status": "error", 
        "messsage": "username taken"
        })





