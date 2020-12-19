from flask import Flask, request, jsonify, redirect, session, url_for
from flask_pymongo import PyMongo, ObjectId
from flask_jwt_extended import JWTManager, jwt_required, create_access_token, create_refresh_token, get_jwt_identity, jwt_refresh_token_required
from flask_cors import CORS, cross_origin
import json
import os
from flask_bcrypt import Bcrypt
from dotenv import load_dotenv
from google.cloud import storage
from werkzeug.utils import secure_filename

from gsutils import download_blob, generate_wav, upload_blob
import uuid

UPLOAD_FOLDER = './WavefileUploads'
ALLOWED_EXTENSIONS = {'mp4'}


#download_blob("goodpodswaveforms", "sampleAudio.m4a", "./audioFromGS.mp4")

load_dotenv()

PORT = "5000"
app = Flask(__name__)

#gcp client
storage_client = storage.Client()

# JWT Manager
app.config['SECRET_KEY'] = os.environ.get("GOODPODS_SECRET_KEY")
jwt = JWTManager(app)

# CORS

origin = "http://localhost:3000"

app.config['CORS_HEADERS'] = 'Content-Type'
CORS(app, resources={r"/*": {"origins": origin, "supports_credentials": True}})

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

@app.route("/clip", methods=['POST'])
def saveToLibrary(): 
    mongo_id = request.form.get("mongo_id")
    title = request.form.get("title")
    url = request.form.get("url")
    if 'file' in request.files:
        file = request.files['file']
        if file:
            
            file_uuid = str(uuid.uuid4())

            filename = file_uuid + "." + file.filename.split(".")[1]
            filepath_of_wav = os.path.join(UPLOAD_FOLDER, filename)
            file.save(filepath_of_wav)  
              
            generate_wav(filepath_of_wav)

            filepath_of_image = filepath_of_wav[:-4] + ".png"
            print("filepath of wav", filepath_of_image)

            destination_wav_name = file_uuid + "." + file.filename.split(".")[1]
            destination_image_name = file_uuid + ".png"
            upload_blob("goodpodswaveforms", filepath_of_wav, filepath_of_image, destination_wav_name, destination_image_name)

            # add the newly uploaded clip to mongodb
            # add a reference to the post in the user object
            clip = {
                "_id": file_uuid,
                "title": title,
                "source_url": url,
                "gcs_wavefile": destination_wav_name,
                "gcs_wavefile_image": destination_image_name
            }
            
            inserted_clip_id = mongo.db.clips.insert_one(clip).inserted_id
            mongo.db.users.find_one_and_update({"_id": ObjectId(mongo_id)}, { "$push": { "clips": inserted_clip_id} })
    return {}, 200

@app.route("/getClips", methods=['POST'])
def get_clip_names():
    user = mongo.db.users.find_one({"_id": ObjectId(request.json["mongo_id"])})
    clip_names = []
    for clip in user["clips"]:
        clip_object = mongo.db.clips.find_one({"_id": clip}) 
        clip_names.append(clip_object["title"])
    return jsonify({"status": "success", "clip_names": clip_names})

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

@app.route("/verify", methods=['POST'])
@jwt_required
def verify():
    current_user = get_jwt_identity()
    if current_user:
        return jsonify({"status": "valid"}), 200
    else:
        return jsonify({"status": "invalid"}), 401 

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)

