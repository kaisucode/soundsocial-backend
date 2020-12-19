
from flask import Flask, request, jsonify, redirect, session, url_for
from flask_pymongo import PyMongo
from flask_jwt_extended import JWTManager, jwt_required, create_access_token, create_refresh_token, get_jwt_identity, jwt_refresh_token_required
from flask_cors import CORS, cross_origin
import json
import os
import bcrypt

PORT = "5000"
app = Flask(__name__)

# JWT Manager
app.config['SECRET_KEY'] = os.environ.get("GOODPODS_SECRET_KEY")
jwt = JWTManager(app)

# CORS
CORS(app, resources={r"*": {"origins": "*", "supports_credentials": True}})

# MongoDB
connectionString = "mongodb+srv://bruno:" + str(os.environ.get("GOODPODS_MONGO_PASSWORD")) + "@cluster0.g2mr3.mongodb.net/goodpods?retryWrites=true&w=majority"
app.config["MONGO_URI"] = connectionString
mongo = PyMongo(app)
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
    mongo_id = db.users.insert_one({ "username": username, "password_hash": pw_hash }).inserted_id

    access_token = create_access_token(identity=username, expires_delta=False)
    return jsonify({"status": "success", 'access_token': access_token, 'mongo_id': mongo_id })

@app.route("/login", methods=("POST",))
def login(): 
    username = request.get("username")
    password = request.get("password")

    mongo_user = mongo.db.users.find_one({"username": username})
    pw_hash = mongo_user["password"]

    if bcrypt.checkpw(password, hashed):
        access_token = create_access_token(identity=username, expires_delta=False)
        return jsonify({"status": "success", 'access_token': access_token, 'mongo_id': mongo_user["_id"] })
    else: 
        return jsonify({"status": "error", "message": "incorrect username or password"})

@app.route("/createPost", methods=("POST",))
@jwt_required
def createPost(): 
    title = request.get("title")
    caption = request.get("caption")
    audioFile = request.get("audioFile")
    mongo_id = request.get("mongo_id")

    mongo_user = mongo.db.users.find_one({"_id": ObjectId(mongo_id)})
    username = mongo_user["username"]

    # generate transcript
    # generate soundwave

    newPost = {
            "user_id": mongo_id, 
            "title": title, 
            "caption": caption, 
            "audioFile": audioFile, 
            "transcript": transcript, 
            "soundwave": soundwave
            }
    postId = db.posts.insert_one(newPost).inserted_id
    return jsonify({"status": "success", 'post_id': postId })



if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)

