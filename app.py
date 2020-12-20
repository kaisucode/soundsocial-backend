from flask import Flask, request, jsonify, redirect, session, url_for, send_file
from flask_pymongo import PyMongo, ObjectId
from flask_jwt_extended import JWTManager, jwt_required, create_access_token, create_refresh_token, get_jwt_identity, jwt_refresh_token_required
from flask_cors import CORS, cross_origin
import json
import os
from flask_bcrypt import Bcrypt
from dotenv import load_dotenv
from google.cloud import storage
from werkzeug.utils import secure_filename
import time
from gsutils import download_blob, generate_wav, upload_blob
import uuid
import speech_recognition as sr
import tempfile

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

CORS(app, resources={r"*": {"origins": origin, "supports_credentials": True}})

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

    return_json = {"status": "success", 'access_token': access_token, 'mongo_id': mongo_id}
    return json.dumps(return_json, default=str), 200

@app.route("/login", methods=["POST"])
def login(): 
    username = request.json["username"]
    password = request.json["password"]

    mongo_user = mongo.db.users.find_one({"username": username})
    pw_hash = mongo_user["password"]

    if bcrypt.check_password_hash(pw_hash, password):

        access_token = create_access_token(identity=username, expires_delta=False)
        print(json.dumps(mongo_user["_id"], default=str))
        return_json = {"status": "success", 'access_token': access_token, 'mongo_id': mongo_user["_id"]}
        return json.dumps(return_json, default=str), 200
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
            # print("filepath of wav", filepath_of_wav)

            destination_wav_name = file_uuid + "." + file.filename.split(".")[1]
            destination_image_name = file_uuid + ".png"
            upload_blob("goodpodswaveforms", filepath_of_wav, filepath_of_image, destination_wav_name, destination_image_name)

            r = sr.Recognizer()
            transcript = ""
            with sr.WavFile(filepath_of_wav) as source:              # use filepath_of_wav as the audio source
                audio = r.record(source)                        # extract audio data from the file
            try:
                transcript = r.recognize_google(audio)
                print("Transcription: " + transcript)   # recognize speech using Google Speech Recognition
            except LookupError:                                 # speech is unintelligible
                print("Could not understand audio")

            # add the newly uploaded clip to mongodb
            # add a reference to the post in the user object
            clip = {
                "_id": file_uuid,
                "title": title,
                "source_url": url,
                "transcript": transcript,
                "gcs_wavefile": destination_wav_name,
                "gcs_wavefile_image": destination_image_name
            }
            
            inserted_clip_id = mongo.db.clips.insert_one(clip).inserted_id
            mongo.db.users.find_one_and_update({"_id": ObjectId(mongo_id)}, { "$push": { "clips": inserted_clip_id} })
    return {}, 200

@app.route("/getClips", methods=['POST'])
@cross_origin()
def get_clip_names():
    mongo_id = request.json["mongo_id"]
    user = mongo.db.users.find_one({"_id": ObjectId(mongo_id)})
    clip_names = []
    for clip in user["clips"]:
        clip_object = mongo.db.clips.find_one({"_id": clip}) 
        clip_names.append(clip_object["title"])
    return jsonify({"status": "success", "clip_names": clip_names, "clip_ids": user["clips"]})

@app.route("/getAllClips", methods=['POST'])
@cross_origin()
def getAllClips():
    mongo_id = request.json["mongo_id"]
    user = mongo.db.users.find_one({"_id": ObjectId(mongo_id)})
    clips_data = []
    for clip in user["clips"]:
        clip_object = mongo.db.clips.find_one({"_id": clip}) 
        clips_data.append({
            "title": clip_object["title"],
            "source_url": clip_object["source_url"],
            "transcript": clip_object["transcript"], 
            "gcs_wavefile": clip_object["gcs_wavefile"],
            "gcs_wavefile_image": clip_object["gcs_wavefile_image"]
            })
    return jsonify({"status": "success", "clips_data": clips_data})

@app.route("/feed/<num>", methods=['GET'])
@cross_origin()
def feed(num):
    posts_cursor = mongo.db.posts.find().sort([('timestamp', -1)]).limit(int(num))
    posts = [post for post in posts_cursor]
    return jsonify({"status": "success", "posts": posts})

@app.route("/clip/<clip_id>", methods=['GET'])
@cross_origin()
def get_clip(clip_id):
    clip = mongo.db.clips.find_one({"_id": clip_id})
    return jsonify({"status": "success", "clip": clip})


@app.route("/createPost", methods=["POST"])
@jwt_required
def createPost(): 
    mongo_id = request.json["mongo_id"]
    title = request.json["title"]
    caption = request.json["caption"]
    clip_id = request.json["clip_id"]

    mongo_user = mongo.db.users.find_one({"_id": ObjectId(mongo_id)})
    username = mongo_user["username"]

    # mongo_clip = mongo.db.clips.find_one({"clip_id": clip_id})
    # transcript = mongo_clip["transcript"]
    # waveform = mongo_clip["waveform"]

    post_id = str(uuid.uuid1())

    ret = { 
        "_id": post_id,
        "timestamp": time.time(),
        "mongo_id": mongo_id, 
        "username": username, 
        "title": title, 
        "caption": caption, 
        "clip_id": clip_id
    }
    
    db.posts.insert_one(ret)

    return jsonify({"status": "success", 'post_id': post_id}), 200

@app.route('/image/<filename>', methods=['GET'])
def image(filename):
    with tempfile.NamedTemporaryFile() as temp:
        download_blob("goodpodswaveforms", filename, temp.name)
        return send_file(temp.name, attachment_filename=filename)

@app.route('/audio/<filename>', methods=['GET'])
def audio(filename):
    with tempfile.NamedTemporaryFile() as temp:
        download_blob("goodpodswaveforms", filename, temp.name)
        return send_file(temp.name, attachment_filename=filename)

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

