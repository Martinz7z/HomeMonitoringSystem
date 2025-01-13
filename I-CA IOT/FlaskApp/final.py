import time
import os
import json
import RPi.GPIO as GPIO
import Adafruit_DHT
from pubnub.pnconfiguration import PNConfiguration
from pubnub.pubnub import PubNub, SubscribeListener
from dotenv import load_dotenv

load_dotenv()

sensors_list = ["led", "temperature", "humidity"]
data = {'alarm': False, 'motion': False, 'temperature': '--', 'humidity': '--'}

app_channel = "Tempify"

class Listener(SubscribeListener):
    def status(self, pubnub, status):
        print(f'Status: \n{status.category.name}')

    def message(self, pubnub, message):
        handle_message(message)

config = PNConfiguration()
config.subscribe_key = os.getenv("PUBNUB_SUBSCRIBE_KEY")
config.publish_key = os.getenv("PUBNUB_PUBLISH_KEY")
config.uuid = os.getenv("PUBNUB_UUID")
config.secret_key = os.getenv("PUBNUB_SECRET_KEY")
config.cipher_key = os.getenv("PUBNUB_CIPHER_KEY")

pubnub = PubNub(config)
pubnub.add_listener(Listener())

subscription = pubnub.channel(app_channel).subscription()
subscription.subscribe()

def handle_message(message):
    print(message.message)
    msg = json.loads(json.dumps(message.message))
    print(type(msg))
    print(msg)
    if 'led' in msg:
        print(f"Setting LED state: {msg['led']}")
        if msg['led'] == 'on':
            GPIO.output(LED_pin, GPIO.HIGH)  # Turn on LED
        elif msg['led'] == 'off':
            GPIO.output(LED_pin, GPIO.LOW)  # Turn off LED

PIR_pin = 4
LED_pin = 18
DHT_PIN = 14  # DHT11 sensor connected to GPIO14
sensor = Adafruit_DHT.DHT11  # DHT11 sensor type

GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
GPIO.setup(PIR_pin, GPIO.IN)
GPIO.setup(LED_pin, GPIO.OUT)

def read_dht11():
    humidity, temperature = Adafruit_DHT.read(sensor, DHT_PIN)
    if humidity is not None and temperature is not None:
        data['temperature'] = temperature
        data['humidity'] = humidity
        return True  # Valid data
    else:
        data['temperature'], data['humidity'] = '--', '--'
        return False  # Invalid data

def motion_detection():
    trigger = False
    while True:
        if GPIO.input(PIR_pin):  # Motion detected
            print("Motion detected")
            trigger = True
            pubnub.publish().channel(app_channel).message({"Motion": "Yes"}).sync()
            data['motion'] = True
            GPIO.output(LED_pin, GPIO.HIGH)  # Turn on LED when motion is detected
            time.sleep(1)
        elif trigger:  # Motion stopped
            pubnub.publish().channel(app_channel).message({"Motion": "No"}).sync()
            trigger = False
            data['motion'] = False
            GPIO.output(LED_pin, GPIO.LOW)  # Turn off LED when motion stops
            time.sleep(1)
        
        if read_dht11():
            pubnub.publish().channel(app_channel).message({
                "temperature": data['temperature'],
                "humidity": data['humidity'],
                "motion": data['motion']
            }).sync()
        else:
            print("Invalid temperature or humidity data. Skipping upload.")
        
       
        time.sleep(2)  # Adjust delay as needed


def main():
    motion_detection()


if __name__ == "__main__":
    main()
