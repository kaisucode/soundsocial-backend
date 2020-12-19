from flask import Flask, request, jsonify, redirect, session, url_for
from flask_pymongo import PyMongo, ObjectId
from flask_jwt_extended import JWTManager, jwt_required, create_access_token, create_refresh_token, get_jwt_identity, jwt_refresh_token_required
from flask_cors import CORS, cross_origin
import json
import os
from flask_bcrypt import Bcrypt
from dotenv import load_dotenv
load_dotenv()

PORT = "5000"
app = Flask(__name__)

# JWT Manager
app.config['SECRET_KEY'] = os.environ.get("GOODPODS_SECRET_KEY")
jwt = JWTManager(app)

# CORS
CORS(app, resources={r"/*": {"origins": "*", "supports_credentials": True}})

# bcrypt
bcrypt = Bcrypt(app)

# MongoDB
connectionString = "mongodb+srv://bruno:" + str(os.environ.get("GOODPODS_MONGO_PASSWORD")) + "@cluster0.g2mr3.mongodb.net/goodpods?retryWrites=true&w=majority"
app.config["MONGO_URI"] = connectionString
mongo = PyMongo(app)
db = mongo.db

@app.route("/signup", methods=["POST"])
def signup(): 
    print("in signup")
    username = request.json["username"]
    password = request.json["password"]

    same_username_users = db.users.find( {"username": username } ) 
    if any(True for _ in same_username_users):
        return jsonify({ "status": "error", "messsage": "username taken" }), 409

    pw_hash = bcrypt.generate_password_hash(password)
    mongo_id = db.users.insert_one({ "username": username, "password": pw_hash }).inserted_id

    print(mongo_id)

    access_token = create_access_token(identity=username, expires_delta=False)

    return_json = {"status": "success", 'access_token': access_token, 'mongo_id': json.dumps(mongo_id, default=str) }
    return return_json, 200

@app.route("/login", methods=["POST"])
def login(): 
    username = request.json["username"]
    password = request.json["password"]

    mongo_user = mongo.db.users.find_one({"username": username})
    pw_hash = mongo_user["password"]

    if bcrypt.check_password_hash(pw_hash, password):

        access_token = create_access_token(identity=username, expires_delta=False)
        return_json = {"status": "success", 'access_token': access_token, 'mongo_id': json.dumps(mongo_user["_id"], default=str)}
        return return_json, 200
    else: 
        return jsonify({"status": "error", "message": "incorrect username or password"}), 401

@app.route("/saveToLibrary", methods=['POST'])
@jwt_required
def saveToLibrary(): 
    mongo_id = request.json["mongo_id"]
    # generate uuid
    # save file
    # generate transcript
    # generate soundwave
    ret = {
            "clip_id": clip_id, 
            "mongo_id": mongo_id, 
            "transcript": transcript, 
            "waveform": waveform
            }

    db.clips.insert_one(ret)


@app.route("/createPost", methods=["POST"])
@jwt_required
def createPost(): 
    mongo_id = request.json["mongo_id"]
    title = request.json["title"]
    caption = request.json["caption"]
    audioFile = request.json["audioFile"]
    clip_id = request.json["clip_id"]

    mongo_user = mongo.db.users.find_one({"_id": ObjectId(mongo_id)})
    username = mongo_user["username"]

    mongo_clip = mongo.db.clips.find_one({"clip_id": clip_id})
    transcript = mongo_clip["transcript"]
    waveform = mongo_clip["waveform"]

    ret = {
            "mongo_id": mongo_id, 
            "username": username, 
            "title": title, 
            "caption": caption, 
            "clip_id": clip_id
            }
    postId = db.posts.insert_one(ret).inserted_id
    return jsonify({"status": "success", 'post_id': postId }), 200



if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)

