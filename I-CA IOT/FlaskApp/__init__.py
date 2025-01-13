import json
import time
import os
import pathlib
import requests
from pymongo import MongoClient
from flask import Flask, session, redirect, request, abort, render_template,jsonify
from google.oauth2 import id_token
from google_auth_oauthlib.flow import Flow
from pip._vendor import cachecontrol
import google.auth.transport.requests
from .config import config
from . import my_db, pb
from pubnub.pnconfiguration import PNConfiguration
from pubnub.pubnub import PubNub
from pubnub.callbacks import SubscribeCallback



db = my_db.db
app = Flask(__name__)
app.secret_key = config.get("APP_SECRET_KEY")
app.config['SQLALCHEMY_DATABASE_URI'] = config.get('SQLALCHEMY_DATABASE_URI')
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db.init_app(app)
Plant = my_db.Plant
Soil = my_db.Soil
Temperature = my_db.Temperature
Humidity = my_db.Humidity

GOOGLE_CLIENT_ID = config.get("GOOGLE_CLIENT_ID")
client_secrets_file = os.path.join(pathlib.Path(__file__).parent, ".client_secrets.json")

flow = Flow.from_client_secrets_file(
    client_secrets_file=client_secrets_file,
    scopes=[
        "https://www.googleapis.com/auth/userinfo.profile",
        "https://www.googleapis.com/auth/userinfo.email",
        "openid",
    ],
    redirect_uri="https://homemonitoringsystem.online/callback",
)

alive = 0
data = {}

pubnub_config = config.get("PUBNUB")

cipher_key = pubnub_config.get("PUBNUB_CIPHER_KEY")

pn_config = PNConfiguration()
pn_config.publish_key = pubnub_config.get("PUBNUB_PUBLISH_KEY") 
pn_config.subscribe_key = pubnub_config.get("PUBNUB_SUBSCRIBE_KEY") 
pn_config.uuid = pubnub_config.get("PUBNUB_UUID") 
pn_config.secret_key = pubnub_config.get("PUBNUB_SECRET_KEY")
pn_config.cipher_key = cipher_key
pubnub = PubNub(pn_config)

# Global variable to store the latest data
latest_data = {"motion": "No", "temperature": "--", "humidity": "--"}

class MySubscribeCallback(SubscribeCallback):
    def message(self, pubnub, message):
        global latest_data
        data = message.message
        if isinstance(data, dict):
            latest_data = {
                "motion": data.get("Motion", "No"),
                "temperature": data.get("temperature", "--"),
                "humidity": data.get("humidity", "--")
            }
            print(f"Received data: {latest_data}")
        return latest_data

# Subscribe to the channel to get updates
pubnub.add_listener(MySubscribeCallback())
pubnub.subscribe().channels("Tempify").execute()

def login_is_required(function):
    def wrapper(*args, **kwargs):
        if "google_id" not in session:
            return abort(401)  # Authorization required
        else:
            return function()
    return wrapper

@app.route("/")
def index():
    return render_template("home.html", logged_in=("google_id" in session), username=session.get("name"))

@app.route("/main")
def main():
    plant_data = db.session.query(Plant).all()
    return render_template("main.html", plants=plant_data, logged_in=("google_id" in session), username=session.get("name"))

@app.route("/temp")
def temp():
    # Fetch the latest temperature data from PubNub
    temperature_data = {"current": latest_data.get("temperature", "--")}
    
    return render_template("temp.html", logged_in=("google_id" in session), username=session.get("name"), temperature_data=temperature_data)
# Initialize a variable to store the last valid temperature value
last_valid_temperature = None

@app.route("/api/temperature")
def get_temperature():
    global last_valid_temperature
    
    # Fetch the latest temperature data from PubNub
    current_temperature = latest_data.get("temperature", None)
    
    # If the current temperature is None or '--', keep the last valid value
    if current_temperature is None or current_temperature == "--":
        current_temperature = last_valid_temperature
    
    # Update the last valid temperature if current data is valid
    if current_temperature != "--" and current_temperature is not None:
        last_valid_temperature = current_temperature

    # Return the latest temperature data
    temperature_data = {"current": current_temperature}
    return jsonify(temperature_data)



@app.route('/soilTemp')
def soilTemp():
    motion_data = latest_data.get("motion", "No")
    return render_template("soilTemp.html", motion_data=motion_data, logged_in=("google_id" in session), username=session.get("name"))


@app.route("/api/soilTemp")
def get_motion_status():
    motion_data = latest_data.get("motion", "No")  # Replace with actual motion data logic
    return jsonify({"motion": motion_data})



@app.route("/humidity")
def humidity():
    # Fetch the latest humidity data from PubNub
    humidity_data = {"current": latest_data.get("humidity", "--")}  # Get the latest humidity
    
    return render_template("humidity.html", logged_in=("google_id" in session), username=session.get("name"), humidity_data=humidity_data)
# Initialize a variable to store the last valid humidity value
last_valid_humidity = None

@app.route("/api/humidity")
def get_humidity():
    global last_valid_humidity
    
    # Fetch the latest humidity data from PubNub
    current_humidity = latest_data.get("humidity", None)
    
    # If the current humidity is None or '--', keep the last valid value
    if current_humidity is None or current_humidity == "--":
        current_humidity = last_valid_humidity
    
    # Update the last valid humidity if current data is valid
    if current_humidity != "--" and current_humidity is not None:
        last_valid_humidity = current_humidity

    # Return the latest humidity data
    humidity_data = {"current": current_humidity}
    return jsonify(humidity_data)



@app.route("/protected_area")
@login_is_required
def protected_area():
    my_db.add_user_and_login(session['name'], session['google_id'])
    return render_template("protected_area.html", user_id=session['google_id'], online_users=my_db.get_all_logged_in_users(), admin_id=config.get('GOOGLE_ADMIN_ID'), logged_in=("google_id" in session), username=session.get("name"))

@app.route("/login")
def login():
    authorization_url, state = flow.authorization_url()
    session["state"] = state
    return redirect(authorization_url)

@app.route("/logout")
def logout():
    my_db.user_logout(session['google_id'])
    session.clear()
    return redirect("/")

@app.route("/callback")
def callback():
    flow.fetch_token(authorization_response=request.url)

    if not session["state"] == request.args["state"]:
        abort(500)  # States don't match

    credentials = flow.credentials
    request_session = requests.session()
    cached_session = cachecontrol.CacheControl(request_session)
    token_request = google.auth.transport.requests.Request(session=cached_session)

    id_info = id_token.verify_oauth2_token(
        id_token=credentials._id_token, request=token_request, audience=GOOGLE_CLIENT_ID
    )

    session["google_id"] = id_info.get("sub")
    session["name"] = id_info.get("name")
    print(session["google_id"])
    print(session["name"])
    return redirect("/")  # was protected_area

@app.route("/keep_alive")
def keep_alive():
    global alive, data
    alive += 1
    keep_alive_count = str(alive)
    data["keep_alive"] = keep_alive_count
    parsed_json = json.dumps(data)
    print(parsed_json)
    return str(parsed_json)

@app.route('/grant-<user_id>-<read>-<write>', methods=["POST"])
def grant_access(user_id, read, write):
    if session.get('google_id'):
        if session['google_id'] == config.get("GOOGLE_ADMIN_ID"):
            print(f"Admin granting {user_id}-{read}-{write}")
            my_db.add_user_permission(user_id, read, write)
            if read == "true" and write == "true":
                token = pb.grant_read_write_access(user_id)
                my_db.add_token(user_id, token)
                access_response = {'token': token, 'cipher_key': pb.cipher_key, 'uuid': user_id}
                return json.dumps(access_response)
            elif read == "true" and write == "false":
                token = pb.grant_read_access(user_id)
                my_db.add_token(user_id, token)
                access_response = {'token': token, 'cipher_key': pb.cipher_key, 'uuid': user_id}
                return json.dumps(access_response)
            elif read == "false" and write == "true":
                token = pb.grant_write_access(user_id)
                my_db.add_token(user_id, token)
                access_response = {'token': token, 'cipher_key': pb.cipher_key, 'uuid': user_id}
                return json.dumps(access_response)
            else:
                # Remove any existing token from the database
                my_db.delete_revoked_token(user_id)
                access_response = {'token': 123, 'cipher_key': "Thiswillnotwork", 'uuid': user_id}
                return json.dumps(access_response)
        else:
            print(f"Non admin attempting to grant privileges {user_id}-{read}-{write}")
            my_db.add_user_permission(user_id, read, write)
            token = my_db.get_token(user_id)
            if token is not None:
                timestamp, ttl, user_id, read, write = pb.parse_token(token)
                current_time = time.time()
                if (timestamp + (ttl * 60)) - current_time > 0:
                    print("Token is still valid")
                    access_response = {'token': token, 'cipher_key': pb.cipher_key, 'uuid': user_id}
                    return json.dumps(access_response)
                else:
                    print("Token refresh needed")
                    if read and write:
                        token = pb.grant_read_write_access(user_id)
                        my_db.add_token(user_id, token)
                        access_response = {'token': token, 'cipher_key': pb.cipher_key, 'uuid': user_id}
                        return json.dumps(access_response)
                    elif read:
                        token = pb.grant_read_access(user_id)
                        my_db.add_token(user_id, token)
                        access_response = {'token': token, 'cipher_key': pb.cipher_key, 'uuid': user_id}
                        return json.dumps(access_response)
                    elif write:
                        token = pb.grant_write_access(user_id)
                        my_db.add_token(user_id, token)
                        access_response = {'token': token, 'cipher_key': pb.cipher_key, 'uuid': user_id}
                        return json.dumps(access_response)
                    else:
                        access_response = {'token': 123, 'cipher_key': "Thiswillnotwork", 'uuid': user_id}
                        return json.dumps(access_response)

@app.route('/get_user_token', methods=['POST'])
def get_user_token():
    user_id = session['google_id']
    token = my_db.get_token(user_id)
    if token is not None:
        token = get_or_refresh_token(token)
        token_response = {'token': token, 'cipher_key': pb.cipher_key, 'uuid': user_id}
    else:
        token_response = {'token': 123, 'cipher_key': "thiswillnotwork", 'uuid': user_id}
    return json.dumps(token_response)


def get_or_refresh_token(token):
    timestamp, ttl, uuid, read, write = pb.parse_token(token)
    current_time = time.time()
    if (timestamp + (ttl * 60)) - current_time > 0:
        return token
    else:
        # The token has expired
        return grant_access(uuid, read, write)


if __name__ == "__main__":
    app.run()
