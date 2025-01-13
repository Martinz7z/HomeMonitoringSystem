import RPi.GPIO as GPIO
import time
from pubnub.pnconfiguration import PNConfiguration
from pubnub.pubnub import PubNub, SubscribeListener
from dotenv import load_dotenv
import os
import json
import board
import adafruit_dht

load_dotenv()

config = PNConfiguration()
config.subscribe_key = os.getenv("PUBNUB_SUBSCRIBE_KEY")
config.publish_key = os.getenv("PUBNUB_PUBLISH_KEY")
config.user_id = os.getenv("PUBNUB_UUID")

class Listener(SubscribeListener):
    def status(self, pubnub, status):
        print(f'Status: \n{status.category.name}')

pubnub = PubNub(config)
pubnub.add_listener(Listener())

app_channel = os.getenv("PUBNUB_CHANNEL")

subscription = pubnub.channel(app_channel).subscription()
subscription.subscribe()

publish_result = pubnub.publish().channel(app_channel).message("PI Connection Successful").sync()
      
dhtDevice = adafruit_dht.DHT22(board.D4, use_pulseio=False)
moisture_PIN = 21

GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
GPIO.setup(moisture_PIN, GPIO.IN)


ALL_GPIO_PINS = list(range(2, 28))  
USED_PINS = [moisture_PIN]  
UNUSED_PINS = [pin for pin in ALL_GPIO_PINS if pin not in USED_PINS]

for pin in UNUSED_PINS:
    GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_OFF)

def main():
    temperature_detection()
    humidity_detection()
    water_detection()

def temperature_detection():
    try:
        while True:
            try:
                # Read the temperature and humidity values
                temperature_c = dhtDevice.temperature
                pubnub.publish().channel(app_channel).message(temperature_c).sync()
                time.sleep(5.0)
                print("Temperature: ", temperature_c)
            except RuntimeError as error:
            # Handle common reading errors without exiting
                print(f"Reading error: {error.args[0]}")
                time.sleep(2.0)
                continue
            time.sleep(2.0)

    except KeyboardInterrupt:
        print("Exiting script")

    finally:
        dhtDevice.exit()

def humidity_detection():
    try:
        while True:
            try:
                # Read the temperature and humidity values
                humidity = dhtDevice.humidity
                pubnub.publish().channel(app_channel).message(humidity).sync()
                time.sleep(5.0)
                print("Humidity: ", humidity)
            except RuntimeError as error:
            # Handle common reading errors without exiting
                print(f"Reading error: {error.args[0]}")
                time.sleep(2.0)
                continue
            time.sleep(2.0)

    except KeyboardInterrupt:
        print("Exiting script")

    finally:
        dhtDevice.exit()

def water_detection():
    try:
        while True:
            if GPIO.input(moisture_PIN):
                pubnub.publish().channel(app_channel).message("HIGH").sync()
                print("Sensor State: No Water Detected")
                time.sleep(5.0)
            else:
                pubnub.publish().channel(app_channel).message("LOW").sync()
                print("Sensor State: Water Detected")
                time.sleep(5.0)
            time.sleep(1)
    except KeyboardInterrupt:
        print("Exiting Program")
    finally:
        GPIO.cleanup()


if __name__ == "__main__":
    main()